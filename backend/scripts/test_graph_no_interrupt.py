"""Ad-hoc validation for Step 2: confirms the graph now runs start-to-finish
in a single graph.invoke() call, with no interrupt/pause, for both an
auto-approve case (INV-1001) and a flag case (INV-1002).

Usage:
    python scripts/test_graph_no_interrupt.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR.parent / ".env")

from src.graph.build_graph import graph

INVOICES_DIR = BASE_DIR / "data" / "invoices"


def run(invoice_id: str, expected_decision: str) -> None:
    path = INVOICES_DIR / f"{invoice_id}.txt"
    result_state = graph.invoke({"invoice_file": str(path)})
    assert "__interrupt__" not in result_state, f"{invoice_id} unexpectedly paused: {result_state}"
    decision = result_state["decision"]
    reasoning = result_state["reasoning"]
    print(f"--- {invoice_id} ---")
    print(f"decision: {decision}")
    print(f"reasoning: {reasoning}")
    assert decision == expected_decision, f"expected {expected_decision}, got {decision}"
    assert reasoning, "reasoning is empty"
    print("OK: single invoke() call, no interrupt, full state returned.\n")


if __name__ == "__main__":
    run("INV-1001", "auto_approve")
    run("INV-1002", "flag")
