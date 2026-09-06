"""Demo/sanity check for human_review_node and the "flag" -> interrupt path.

Runs the compiled graph (src/graph/build_graph.py) against a flagged
invoice (INV-1002) and confirms the run pauses at `interrupt()` with the
expected review payload, without resuming it. Also runs an auto-approved
invoice (INV-1001) to confirm that path still completes normally and never
hits the interrupt.

Usage:
    python scripts/test_human_review.py

Requires TENSORMUX_API_KEY to be set (see src/extraction.py and
README.md).
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.graph.build_graph import graph

INVOICES_DIR = BASE_DIR / "data" / "invoices"


def run_flagged_invoice() -> None:
    print("--- INV-1002 (expected: flag -> interrupt) ---")
    config = {"configurable": {"thread_id": "test-inv-1002"}}
    invoice_path = INVOICES_DIR / "INV-1002.txt"

    result = graph.invoke({"invoice_file": str(invoice_path)}, config=config)

    interrupts = result.get("__interrupt__")
    if not interrupts:
        print("ERROR: expected an interrupt, but run completed normally.")
        print(json.dumps(result, indent=2, default=str))
        return

    payload = interrupts[0].value
    print("Interrupted as expected. Review payload:")
    print(json.dumps(payload, indent=2, default=str))

    state = graph.get_state(config)
    print(f"graph.get_state(config).next: {state.next}")


def run_auto_approved_invoice() -> None:
    print("\n--- INV-1001 (expected: auto_approve, no interrupt) ---")
    config = {"configurable": {"thread_id": "test-inv-1001"}}
    invoice_path = INVOICES_DIR / "INV-1001.txt"

    result = graph.invoke({"invoice_file": str(invoice_path)}, config=config)

    if result.get("__interrupt__"):
        print("ERROR: did not expect an interrupt on the auto-approve path.")
        print(json.dumps(result, indent=2, default=str))
        return

    print(f"decision: {result['decision']}")
    print(f"reasoning: {result['reasoning']}")


def main() -> None:
    run_flagged_invoice()
    run_auto_approved_invoice()


if __name__ == "__main__":
    main()
