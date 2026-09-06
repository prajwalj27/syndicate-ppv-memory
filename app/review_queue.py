"""Streamlit buyer review queue for PPV Memory.

Drives the compiled LangGraph pipeline (src/graph/build_graph.py) over
data/invoices/*.txt in order, surfacing auto-approved invoices and pausing
on flagged ones for buyer review via the graph's interrupt() mechanism.
Approving a flagged invoice resumes its graph run, writes a resolution to
memory, and unblocks the next invoice in the queue.

Usage:
    streamlit run app/review_queue.py

Requires TENSORMUX_API_KEY to be set (see src/extraction.py, README.md).
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
from langgraph.types import Command

from src.db import reset_resolutions
from src.graph.build_graph import graph

INVOICES_DIR = BASE_DIR / "data" / "invoices"
INVOICE_FILES = sorted(INVOICES_DIR.glob("INV-*.txt"))

st.set_page_config(page_title="PPV Memory - Buyer Review Queue", layout="wide")


def _init_state() -> None:
    st.session_state.setdefault("invoice_results", {})


def _reset_demo_data() -> None:
    reset_resolutions()
    st.session_state["invoice_results"] = {}


def _process_invoices() -> None:
    """Run each invoice through the graph in order.

    Stops as soon as an invoice is still awaiting buyer review, so a later
    invoice (e.g. INV-1003) is never extracted/evaluated until an earlier
    one (INV-1002) has been resolved.
    """
    for invoice_path in INVOICE_FILES:
        stem = invoice_path.stem
        if stem not in st.session_state.invoice_results:
            config = {"configurable": {"thread_id": stem}}
            with st.spinner(f"Extracting and evaluating {stem}..."):
                result = graph.invoke(
                    {"invoice_file": str(invoice_path)}, config=config
                )
            st.session_state.invoice_results[stem] = result

        if st.session_state.invoice_results[stem].get("__interrupt__"):
            break


def _resume_invoice(
    stem: str, *, resolver_name: str, reason: str, resolved_price: float
) -> None:
    config = {"configurable": {"thread_id": stem}}
    resume_value = {
        "approved": True,
        "resolved_price": resolved_price,
        "resolver_name": resolver_name,
        "reason": reason,
    }
    result = graph.invoke(Command(resume=resume_value), config=config)
    st.session_state.invoice_results[stem] = result


def _render_sidebar() -> None:
    with st.sidebar:
        st.header("Demo controls")
        st.caption(
            "Clears the resolutions table so INV-1002 and INV-1003 both "
            "need buyer review again on a fresh run."
        )
        if st.button("Reset Demo Data"):
            _reset_demo_data()
            st.rerun()


def _render_auto_approved(results: dict) -> None:
    st.subheader("Auto-Approved")
    entries = [
        (stem, result)
        for stem, result in results.items()
        if not result.get("__interrupt__") and result.get("decision") == "auto_approve"
    ]
    if not entries:
        st.caption("No invoices auto-approved yet.")
        return
    for stem, result in entries:
        extracted = result["extracted_data"]
        with st.container(border=True):
            st.markdown(f"**{stem}** — {extracted['vendor']} / {extracted['item']}")
            st.write(result["reasoning"])


def _render_needs_review(results: dict) -> None:
    st.subheader("Needs Review — Buyer")
    entries = [
        (stem, result) for stem, result in results.items() if result.get("__interrupt__")
    ]
    if not entries:
        st.caption("No invoices currently awaiting buyer review.")
        return

    for stem, result in entries:
        payload = result["__interrupt__"][0].value
        with st.container(border=True):
            st.markdown(f"**{stem}** — {payload['vendor']} / {payload['item']}")

            col1, col2, col3 = st.columns(3)
            col1.metric("Invoice price", f"${payload['invoice_unit_price']:.2f}")
            col2.metric("PO price", f"${payload['po_unit_price']:.2f}")
            col3.metric("Variance", f"{payload['variance_pct']:+.1%}")

            st.write(payload["reasoning"])

            prior = payload.get("prior_resolution")
            if prior:
                st.caption(
                    f"Prior resolution on file: ${prior['resolved_price']:.2f}, "
                    f"resolved by {prior['resolved_by']} on {prior['date_resolved']} "
                    f"— \"{prior['reason']}\""
                )

            st.markdown("**Buyer decision**")
            resolver_name = st.text_input("Your name", key=f"resolver_name_{stem}")
            resolved_price = st.number_input(
                "Approved unit price",
                min_value=0.0,
                value=float(payload["invoice_unit_price"]),
                step=0.01,
                key=f"resolved_price_{stem}",
            )
            reason = st.text_area("Reason for approval (required)", key=f"reason_{stem}")

            if st.button("Approve", key=f"approve_{stem}"):
                if not resolver_name.strip() or not reason.strip():
                    st.error("Your name and a reason are required to approve.")
                else:
                    _resume_invoice(
                        stem,
                        resolver_name=resolver_name.strip(),
                        reason=reason.strip(),
                        resolved_price=resolved_price,
                    )
                    st.rerun()


def _render_resolved(results: dict) -> None:
    entries = [
        (stem, result)
        for stem, result in results.items()
        if not result.get("__interrupt__") and result.get("decision") == "resolved"
    ]
    if not entries:
        return
    st.subheader("Resolved by Buyer")
    for stem, result in entries:
        extracted = result["extracted_data"]
        with st.container(border=True):
            st.markdown(f"**{stem}** — {extracted['vendor']} / {extracted['item']}")
            st.write(result["reasoning"])


def main() -> None:
    st.title("PPV Memory — Buyer Review Queue")
    st.caption(
        "Purchase-price-variance triage: invoices matching PO price or a "
        "prior buyer decision auto-approve; the rest wait here for buyer "
        "review."
    )

    _init_state()
    _render_sidebar()
    _process_invoices()

    _render_auto_approved(st.session_state.invoice_results)
    st.divider()
    _render_needs_review(st.session_state.invoice_results)
    _render_resolved(st.session_state.invoice_results)


if __name__ == "__main__":
    main()
