"""LangGraph node functions for the PPV Memory pipeline.

See docs/BUILD_PLAN.md for the full graph design. Nodes are added here
incrementally as later build steps are implemented.
"""

from __future__ import annotations

from langgraph.types import interrupt

from src.db import get_latest_resolution, get_po
from src.extraction import extract_invoice_file
from src.graph.state import PPVState

RESOLUTION_MATCH_TOLERANCE = 0.01


def extract_node(state: PPVState) -> PPVState:
    """Extract structured invoice fields and merge them into the state.

    Calls the existing LLM-based extraction logic on `state["invoice_file"]`
    and returns the state with an added `extracted_data` key.
    """
    fields = extract_invoice_file(state["invoice_file"])
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


def human_review_node(state: PPVState) -> PPVState:
    """Pause a flagged invoice for buyer review via LangGraph's `interrupt()`.

    Surfaces everything a human buyer needs to make a call: vendor, item,
    invoice vs. PO unit price, variance %, the flagging reasoning, and any
    prior resolution for context. The review-queue UI (Step 4) reads this
    payload from the graph's interrupt state.
    """
    extracted = state["extracted_data"]
    po_record = state["po_record"]

    payload = {
        "vendor": extracted["vendor"],
        "item": extracted["item"],
        "invoice_unit_price": extracted["unit_price"],
        "po_unit_price": po_record["unit_price"],
        "variance_pct": state["variance_pct"],
        "reasoning": state["reasoning"],
        "prior_resolution": state["prior_resolution"],
    }
    human_resolution = interrupt(payload)

    return {**state, "human_resolution": human_resolution}
