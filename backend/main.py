"""FastAPI backend for PPV Memory.

Runs invoices through the graph (extract -> lookup -> decide), persists
each triggered invoice's full state, and lets a buyer resolve flagged
invoices without ever pausing/resuming a graph run. See
ppv-memory-fullstack-plan.md.md, Step 3, for the endpoint spec.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.db import (
    get_invoice_record,
    insert_invoice_record,
    list_invoice_records,
    update_invoice_record,
)
from src.graph.build_graph import graph
from src.graph.nodes import build_review_payload, record_resolution_node

INVOICES_DIR = BASE_DIR / "data" / "invoices"
INVOICES_PDF_DIR = BASE_DIR / "data" / "invoices_pdf"

DECISION_TO_STATUS = {
    "auto_approve": "auto_approved",
    "flag": "pending_review",
    "resolved": "resolved",
    "rejected": "rejected",
}

DECISION_TO_STEP_DETAIL = {
    "auto_approve": "Auto-approved",
    "flag": "Flagged for review",
    "resolved": "Resolved",
    "rejected": "Rejected",
}

app = FastAPI(title="PPV Memory API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file mounts for the invoice simulator page (frontend/app/simulator) to
# preview raw invoice documents. Read-only file serving, no endpoint logic.
app.mount("/static/invoices", StaticFiles(directory=str(INVOICES_DIR)), name="invoice_txt_static")
app.mount(
    "/static/invoices_pdf", StaticFiles(directory=str(INVOICES_PDF_DIR)), name="invoice_pdf_static"
)


class TriggerRequest(BaseModel):
    filename: str


class ResolveRequest(BaseModel):
    resolver_name: str
    resolved_price: float
    reason: str


def _resolve_invoice_path(filename: str) -> Path:
    name = filename if filename.endswith(".txt") else f"{filename}.txt"
    path = INVOICES_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Invoice file not found: {name}")
    return path


def _build_steps(state: dict) -> list[dict]:
    """Reshape a completed graph state into an ordered steps list for display.

    No new computation — just formatting what's already in state.
    """
    extracted = state["extracted_data"]
    po_record = state["po_record"]
    prior_resolution = state["prior_resolution"]
    variance_pct = state["variance_pct"]

    return [
        {
            "label": "Extracted invoice data",
            "detail": (
                f"Vendor: {extracted['vendor']}, Item: {extracted['item']}, "
                f"Price: ${extracted['unit_price']:.2f}"
            ),
            "done": True,
        },
        {
            "label": f"Looked up PO {po_record['po_number']}",
            "detail": f"PO price: ${po_record['unit_price']:.2f}",
            "done": True,
        },
        {
            "label": "Checked resolution history",
            "detail": (
                f"Found prior resolution from {prior_resolution['date_resolved']}"
                if prior_resolution
                else "None found"
            ),
            "done": True,
        },
        {
            "label": "Calculated variance",
            "detail": f"{variance_pct:+.1%}",
            "done": True,
        },
        {
            "label": "Decision",
            "detail": DECISION_TO_STEP_DETAIL[state["decision"]],
            "done": True,
        },
    ]


def _record_to_response(record: dict) -> dict:
    """Shape a stored invoice_records row into an API response."""
    state = record["state"]
    review = build_review_payload(state)

    return {
        "id": record["id"],
        "invoice_filename": record["invoice_filename"],
        "status": record["status"],
        "created_at": record["created_at"],
        "vendor": review["vendor"],
        "item": review["item"],
        "invoice_unit_price": review["invoice_unit_price"],
        "po_unit_price": review["po_unit_price"],
        "variance_pct": review["variance_pct"],
        "reasoning": review["reasoning"],
        "prior_resolution": review["prior_resolution"],
        "extracted_data": state["extracted_data"],
        "po_record": state["po_record"],
        "steps": _build_steps(state),
    }


@app.post("/invoices/trigger")
def trigger_invoice(body: TriggerRequest):
    path = _resolve_invoice_path(body.filename)

    state = graph.invoke({"invoice_file": str(path)})
    status = DECISION_TO_STATUS[state["decision"]]

    record_id = insert_invoice_record(
        invoice_filename=path.name,
        status=status,
        state=state,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    return _record_to_response(get_invoice_record(record_id))


@app.get("/invoices")
def get_invoices():
    return [_record_to_response(record) for record in list_invoice_records()]


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int):
    record = get_invoice_record(invoice_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No invoice record with id {invoice_id}")
    return _record_to_response(record)


@app.post("/invoices/{invoice_id}/resolve")
def resolve_invoice(invoice_id: int, body: ResolveRequest):
    record = get_invoice_record(invoice_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No invoice record with id {invoice_id}")

    state = record["state"]
    state["human_resolution"] = {
        "approved": True,
        "resolved_price": body.resolved_price,
        "resolver_name": body.resolver_name,
        "reason": body.reason,
    }

    updated_state = record_resolution_node(state)
    status = DECISION_TO_STATUS[updated_state["decision"]]

    update_invoice_record(invoice_id, status=status, state=updated_state)

    return _record_to_response(get_invoice_record(invoice_id))
