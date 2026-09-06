"""LangGraph node functions for the PPV Memory pipeline.

See docs/BUILD_PLAN.md for the full graph design. Nodes are added here
incrementally as later build steps are implemented.
"""

from __future__ import annotations

from src.extraction import extract_invoice_file
from src.graph.state import PPVState


def extract_node(state: PPVState) -> PPVState:
    """Extract structured invoice fields and merge them into the state.

    Calls the existing LLM-based extraction logic on `state["invoice_file"]`
    and returns the state with an added `extracted_data` key.
    """
    fields = extract_invoice_file(state["invoice_file"])
    return {**state, "extracted_data": fields}
