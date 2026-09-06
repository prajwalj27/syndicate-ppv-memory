"""LangGraph node functions for the PPV Memory pipeline.

See docs/BUILD_PLAN.md for the full graph design. Nodes are added here
incrementally as later build steps are implemented.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from langgraph.types import interrupt

from src.db import get_latest_resolution, get_po, insert_resolution
from src.extraction import extract_invoice_fields, extract_invoice_file
from src.graph.state import PPVState
from src.pdf_extract import extract_pdf_text

RESOLUTION_MATCH_TOLERANCE = 0.01


def extract_node(state: PPVState) -> PPVState:
    """Extract structured invoice fields and merge them into the state.

    Calls the existing LLM-based extraction logic on `state["invoice_file"]`
    and returns the state with an added `extracted_data` key. PDF invoices
    are read via `pdf_extract` first since `extract_invoice_file` only
    reads plain text; .txt invoices go through the existing path unchanged.
    """
    path = state["invoice_file"]
    if path.endswith(".pdf"):
        text = extract_pdf_text(path)
        fields = extract_invoice_fields(text)
        fields["source_file"] = Path(path).name
    else:
        fields = extract_invoice_file(path)
    return {**state, "extracted_data": fields}


def lookup_node(state: PPVState) -> PPVState:
    """Look up the referenced PO and any prior resolution, and compute variance.

    Uses `extracted_data["po_reference"]` to find the matching
    `purchase_orders` row, and the invoice's vendor+item to find the most
    recent matching `resolutions` row (if any). Sets `po_record`,
    `prior_resolution`, and `variance_pct` in the returned state.
    """
    extracted = state["extracted_data"]
    po_record = get_po(extracted["po_reference"])
    prior_resolution = get_latest_resolution(extracted["vendor"], extracted["item"])

    variance_pct = None
    if po_record is not None:
        po_unit_price = po_record["unit_price"]
        variance_pct = (extracted["unit_price"] - po_unit_price) / po_unit_price

    return {
        **state,
        "po_record": po_record,
        "prior_resolution": prior_resolution,
        "variance_pct": variance_pct,
    }


def decide_node(state: PPVState) -> PPVState:
    """Decide whether to auto-approve or flag the invoice, with reasoning.

    Auto-approves when the invoice price matches a prior resolution's
    resolved price (within a cent) or exactly matches the PO price;
    otherwise flags it for review.
    """
    extracted = state["extracted_data"]
    po_record = state["po_record"]
    prior_resolution = state["prior_resolution"]
    variance_pct = state["variance_pct"]
    invoice_unit_price = extracted["unit_price"]

    if prior_resolution is not None and (
        abs(invoice_unit_price - prior_resolution["resolved_price"])
        <= RESOLUTION_MATCH_TOLERANCE
    ):
        decision = "auto_approve"
        reasoning = (
            f"Consistent with prior approval on {prior_resolution['date_resolved']}: "
            f"'{prior_resolution['reason']}'. Auto-approved, no review needed."
        )
    elif variance_pct == 0:
        decision = "auto_approve"
        reasoning = (
            f"Invoice unit price ${invoice_unit_price:.2f} is an exact match to "
            f"PO {po_record['po_number']}'s price. Auto-approved, no review needed."
        )
    else:
        decision = "flag"
        reasoning = (
            f"Vendor {extracted['vendor']}, item {extracted['item']}: invoice unit "
            f"price ${invoice_unit_price:.2f} vs PO price ${po_record['unit_price']:.2f} "
            f"({variance_pct:+.1%} variance), no prior resolution on file."
        )

    return {**state, "decision": decision, "reasoning": reasoning}


def build_review_payload(state: PPVState) -> dict:
    """Build the payload a human buyer needs to review a flagged invoice.

    Surfaces everything a human buyer needs to make a call: vendor, item,
    invoice vs. PO unit price, variance %, the flagging reasoning, and any
    prior resolution for context. Used both by `human_review_node` (via
    `interrupt()`) and directly by the API layer, which calls this plain
    function instead of pausing a graph run to get the payload.
    """
    extracted = state["extracted_data"]
    po_record = state["po_record"]

    return {
        "vendor": extracted["vendor"],
        "item": extracted["item"],
        "invoice_unit_price": extracted["unit_price"],
        "po_unit_price": po_record["unit_price"],
        "variance_pct": state["variance_pct"],
        "reasoning": state["reasoning"],
        "prior_resolution": state["prior_resolution"],
    }


def human_review_node(state: PPVState) -> PPVState:
    """Pause a flagged invoice for buyer review via LangGraph's `interrupt()`.

    Kept for old test scripts that exercise the interrupt/resume path
    directly against the graph; the API layer calls `build_review_payload`
    instead and never invokes this node or `interrupt()`.
    """
    human_resolution = interrupt(build_review_payload(state))

    return {**state, "human_resolution": human_resolution}


def record_resolution_node(state: PPVState) -> PPVState:
    """Apply the human's resume decision after `human_review_node`'s interrupt.

    If approved, writes a new `resolutions` row so future invoices for this
    vendor+item can auto-approve against it. Either way, appends the human's
    reason to `reasoning` so it captures the full history: why the invoice
    was flagged, and how it was resolved.
    """
    extracted = state["extracted_data"]
    human_resolution = state["human_resolution"]

    if human_resolution["approved"]:
        insert_resolution(
            vendor=extracted["vendor"],
            item=extracted["item"],
            resolved_price=human_resolution["resolved_price"],
            resolved_by=human_resolution["resolver_name"],
            reason=human_resolution["reason"],
            date_resolved=date.today().isoformat(),
        )
        decision = "resolved"
    else:
        decision = "rejected"

    reasoning = f"{state['reasoning']} Resolved by {human_resolution['resolver_name']}: {human_resolution['reason']}"

    return {**state, "decision": decision, "reasoning": reasoning}
