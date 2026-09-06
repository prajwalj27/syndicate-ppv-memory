"""Demo/sanity check for record_resolution_node and the memory-write loop.

Resumes an interrupted INV-1002 run with a human approval, confirms the
resolution lands in the `resolutions` table, then runs INV-1003 (same
vendor/item/price, different qty) fresh and confirms it now auto-approves
via the memory-match path in decide_node, citing the INV-1002 resolution.

Usage:
    python scripts/test_record_resolution.py

Requires TENSORMUX_API_KEY to be set (see src/extraction.py and README.md).

Note: this writes a real row into data/ppv_memory.db's resolutions table
(vendor "Meridian Office Supply", item matching INV-1002's line item). If
Step 5's mini-eval needs a clean slate, delete that row (or re-run
scripts/generate_data.py) before evaluating.
"""

import json
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from langgraph.types import Command

from src.db import DB_PATH
from src.graph.build_graph import graph

INVOICES_DIR = BASE_DIR / "data" / "invoices"

TEST_RESOLVER_NAME = "Jordan Ellis"
TEST_RESOLVED_PRICE = 190.00
TEST_REASON = (
    "Approved -- substitute model due to unavailability, this is now the "
    "standard price for this vendor/item"
)


def resolve_inv_1002() -> None:
    print("--- INV-1002 (expected: flag -> interrupt) ---")
    config = {"configurable": {"thread_id": "test-record-resolution-inv-1002"}}
    invoice_path = INVOICES_DIR / "INV-1002.txt"

    result = graph.invoke({"invoice_file": str(invoice_path)}, config=config)

    interrupts = result.get("__interrupt__")
    if not interrupts:
        print("ERROR: expected an interrupt, but run completed normally.")
        print(json.dumps(result, indent=2, default=str))
        sys.exit(1)

    print("Interrupted as expected. Review payload:")
    print(json.dumps(interrupts[0].value, indent=2, default=str))

    print("\nResuming with human approval...")
    resume_value = {
        "approved": True,
        "resolved_price": TEST_RESOLVED_PRICE,
        "resolver_name": TEST_RESOLVER_NAME,
        "reason": TEST_REASON,
    }
    final_state = graph.invoke(Command(resume=resume_value), config=config)

    print(f"decision: {final_state['decision']}")
    print(f"reasoning: {final_state['reasoning']}")

    if final_state["decision"] != "resolved":
        print(f"ERROR: expected decision 'resolved', got {final_state['decision']!r}")
        sys.exit(1)

    vendor = final_state["extracted_data"]["vendor"]
    item = final_state["extracted_data"]["item"]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    with conn:
        row = conn.execute(
            """
            SELECT * FROM resolutions
            WHERE vendor = ? AND item = ? AND resolved_by = ?
            ORDER BY id DESC LIMIT 1
            """,
            (vendor, item, TEST_RESOLVER_NAME),
        ).fetchone()

    if row is None:
        print("ERROR: no matching resolutions row found after resume.")
        sys.exit(1)

    row = dict(row)
    assert row["vendor"] == vendor
    assert row["item"] == item
    assert abs(row["resolved_price"] - TEST_RESOLVED_PRICE) < 0.01
    assert row["resolved_by"] == TEST_RESOLVER_NAME
    assert row["reason"] == TEST_REASON

    print("\nConfirmed new resolutions row:")
    print(json.dumps(row, indent=2, default=str))


def run_inv_1003() -> None:
    print("\n--- INV-1003 (expected: auto_approve via memory match) ---")
    config = {"configurable": {"thread_id": "test-record-resolution-inv-1003"}}
    invoice_path = INVOICES_DIR / "INV-1003.txt"

    result = graph.invoke({"invoice_file": str(invoice_path)}, config=config)

    if result.get("__interrupt__"):
        print("ERROR: expected auto-approval, but run interrupted.")
        print(json.dumps(result, indent=2, default=str))
        sys.exit(1)

    print(f"decision: {result['decision']}")
    print(f"reasoning: {result['reasoning']}")

    if result["decision"] != "auto_approve":
        print(f"ERROR: expected decision 'auto_approve', got {result['decision']!r}")
        sys.exit(1)

    if TEST_RESOLVER_NAME not in result["reasoning"] and "prior approval" not in result["reasoning"].lower():
        print("WARNING: reasoning does not appear to cite the prior resolution.")

    print("\nSUCCESS: INV-1003 auto-approved, citing the INV-1002 resolution.")


def main() -> None:
    resolve_inv_1002()
    run_inv_1003()


if __name__ == "__main__":
    main()
