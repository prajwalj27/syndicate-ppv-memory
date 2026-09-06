"""Mini-eval for PPV Memory: does resolution memory actually change outcomes?

Runs all 5 invoices in data/invoices/ through the compiled graph twice:

1. Without memory: `reset_resolutions()`, then run each invoice fresh. Any
   invoice that hits `human_review_node`'s interrupt is auto-resumed with a
   stand-in decline (no live human available in an eval harness).
2. With memory: `reset_resolutions()` again, then `insert_resolution(...)`
   for INV-1002's vendor/item, simulating that a buyer already approved the
   substitution-driven price increase. Each invoice is then run fresh again
   (new thread_ids), so INV-1002 and INV-1003 should now auto-approve via
   the memory-match path in decide_node.

Each invoice's final `decision` is bucketed as "auto_approve" (exact string
match) or "flag" (anything else, e.g. "rejected") and compared against the
ground truth in data/SCENARIO_KEY.md.

Usage:
    python eval/mini_eval.py

Requires TENSORMUX_API_KEY to be set (see src/extraction.py, README.md).
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from langgraph.types import Command

from src.db import insert_resolution, reset_resolutions
from src.graph.build_graph import graph

INVOICES_DIR = BASE_DIR / "data" / "invoices"
INVOICE_FILES = sorted(INVOICES_DIR.glob("INV-*.txt"))

# Ground truth from data/SCENARIO_KEY.md.
EXPECTED_VERDICTS = {
    "INV-1001": "auto_approve",
    "INV-1002": "auto_approve",
    "INV-1003": "auto_approve",
    "INV-1004": "flag",
    "INV-1005": "flag",
}

STAND_IN_DECLINE = {
    "approved": False,
    "resolved_price": None,
    "resolver_name": "eval-harness",
    "reason": "Left flagged for review (eval stand-in, no live human)",
}

MEMORY_RESOLVER_NAME = "Jordan Ellis"
MEMORY_RESOLVED_PRICE = 190.00
MEMORY_REASON = (
    "Approved -- substitute model due to unavailability, this is now the "
    "standard price for this vendor/item"
)
MEMORY_DATE_RESOLVED = "2026-07-20"


def bucket(decision: str) -> str:
    """Collapse a final `decision` value to "auto_approve" or "flag"."""
    return "auto_approve" if decision == "auto_approve" else "flag"


def run_invoice(invoice_path: Path, thread_id: str) -> dict:
    """Run one invoice through the graph, auto-declining any interrupt."""
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"invoice_file": str(invoice_path)}, config=config)
    if result.get("__interrupt__"):
        result = graph.invoke(Command(resume=STAND_IN_DECLINE), config=config)
    return result


def run_pass(thread_prefix: str) -> dict[str, dict]:
    """Run all 5 invoices through the graph, each on its own fresh thread."""
    results = {}
    for invoice_path in INVOICE_FILES:
        stem = invoice_path.stem
        results[stem] = run_invoice(invoice_path, f"{thread_prefix}{stem}")
    return results


def main() -> None:
    print("=== Pass 1: without memory ===")
    reset_resolutions()
    without_memory = run_pass("eval-nomem-")

    # Simulate the human step from Step 3 having already happened, using
    # INV-1002's own extracted vendor/item so the resolution row matches
    # exactly regardless of the LLM's precise wording.
    inv_1002_extracted = without_memory["INV-1002"]["extracted_data"]

    print("\n=== Pass 2: with memory ===")
    reset_resolutions()
    insert_resolution(
        inv_1002_extracted["vendor"],
        inv_1002_extracted["item"],
        MEMORY_RESOLVED_PRICE,
        MEMORY_RESOLVER_NAME,
        MEMORY_REASON,
        MEMORY_DATE_RESOLVED,
    )
    with_memory = run_pass("eval-withmem-")

    print("\n=== Results ===")
    header = f"{'Invoice':<10} {'Expected':<13} {'No-Memory':<13} {'Match':<7} {'With-Memory':<13} {'Match':<7}"
    print(header)
    print("-" * len(header))

    without_score = 0
    with_score = 0
    for stem in EXPECTED_VERDICTS:
        expected = EXPECTED_VERDICTS[stem]

        without_actual = bucket(without_memory[stem]["decision"])
        without_match = without_actual == expected
        without_score += without_match

        with_actual = bucket(with_memory[stem]["decision"])
        with_match = with_actual == expected
        with_score += with_match

        print(
            f"{stem:<10} {expected:<13} {without_actual:<13} "
            f"{'yes' if without_match else 'NO':<7} {with_actual:<13} "
            f"{'yes' if with_match else 'NO':<7}"
        )

    total = len(EXPECTED_VERDICTS)
    print()
    print(f"Without memory: {without_score}/{total} correct")
    print(f"With memory:    {with_score}/{total} correct")


if __name__ == "__main__":
    main()
