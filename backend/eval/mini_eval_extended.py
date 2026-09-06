"""Extended mini-eval for PPV Memory: all 12 invoices, three vendors.

Same approach as `mini_eval.py`, generalized to cover the 5 original
Meridian Office Supply invoices plus the 7 added for Brightline Logistics
and Crestpoint IT Services (see data/SCENARIO_KEY.md). In particular this
exercises the AUTO_APPROVE_VARIANCE_TOLERANCE band (INV-3003) alongside the
existing prior-resolution memory-match path (INV-1002/1003, INV-2002/2003),
and a same-vendor/different-item guardrail (INV-2004) proving memory
doesn't over-generalize across items for the same vendor.

Runs all 12 invoices in data/invoices/ through the compiled graph twice:

1. Without memory: `reset_resolutions()`, then run each invoice fresh.
2. With memory: `reset_resolutions()` again, then `insert_resolution(...)`
   for INV-1002, INV-2002, and INV-3002 (in that order), simulating that a
   buyer already approved each of those price increases. Each invoice is
   then run fresh again (new thread_ids).

Each invoice's final `decision` is bucketed as "auto_approve" (exact string
match) or "flag" (anything else) and compared against the ground truth in
data/SCENARIO_KEY.md.

Usage:
    python eval/mini_eval_extended.py

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
    "INV-2001": "auto_approve",
    "INV-2002": "auto_approve",
    "INV-2003": "auto_approve",
    "INV-2004": "flag",
    "INV-3001": "auto_approve",
    "INV-3002": "auto_approve",
    "INV-3003": "auto_approve",
}

# Ground truth for the specific pass each invoice is expected to flag in,
# independent of `EXPECTED_VERDICTS` (the eventual correct end-state once
# resolved). Invoices absent from a list are expected to match
# EXPECTED_VERDICTS in that pass.
EXPECTED_WITHOUT_MEMORY_FLAGS = {"INV-1002", "INV-1003", "INV-2002", "INV-2003", "INV-3002"}

STAND_IN_DECLINE = {
    "approved": False,
    "resolved_price": None,
    "resolver_name": "eval-harness",
    "reason": "Left flagged for review (eval stand-in, no live human)",
}

# Resolutions to insert for the "with memory" pass, in this order.
MEMORY_RESOLUTIONS = [
    {
        "invoice": "INV-1002",
        "resolved_price": 190.00,
        "resolved_by": "Jordan Ellis",
        "reason": (
            "Approved -- substitute model due to unavailability, this is "
            "now the standard price for this vendor/item"
        ),
        "date_resolved": "2026-07-20",
    },
    {
        "invoice": "INV-2002",
        "resolved_price": 2321.00,
        "resolved_by": "Priya Nair",
        "reason": (
            "Approved -- fuel surcharge is now the standard price for this "
            "vendor/item"
        ),
        "date_resolved": "2026-07-24",
    },
    {
        "invoice": "INV-3002",
        "resolved_price": 3063.00,
        "resolved_by": "Sam Osei",
        "reason": (
            "Approved -- retainer rate increase is now the standard price "
            "for this vendor/item"
        ),
        "date_resolved": "2026-07-28",
    },
]


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
    """Run all 12 invoices through the graph, each on its own fresh thread."""
    results = {}
    for invoice_path in INVOICE_FILES:
        stem = invoice_path.stem
        results[stem] = run_invoice(invoice_path, f"{thread_prefix}{stem}")
    return results


def main() -> None:
    print("=== Pass 1: without memory ===")
    reset_resolutions()
    without_memory = run_pass("eval-nomem-")

    print("\n=== Pass 2: with memory ===")
    reset_resolutions()
    for mem in MEMORY_RESOLUTIONS:
        extracted = without_memory[mem["invoice"]]["extracted_data"]
        insert_resolution(
            extracted["vendor"],
            extracted["item"],
            mem["resolved_price"],
            mem["resolved_by"],
            mem["reason"],
            mem["date_resolved"],
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
        expected_without = "flag" if stem in EXPECTED_WITHOUT_MEMORY_FLAGS else expected

        without_actual = bucket(without_memory[stem]["decision"])
        without_match = without_actual == expected_without
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
