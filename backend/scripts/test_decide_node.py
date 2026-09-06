"""Demo/sanity check for lookup_node and decide_node.

Runs all invoices in data/invoices/ through extract_node -> lookup_node ->
decide_node in sequence, and prints the resulting `decision` and
`reasoning` for each, to visually confirm the PPV pipeline's logic up
through the decision step.

Usage:
    python scripts/test_decide_node.py

Requires TENSORMUX_API_KEY to be set (see src/extraction.py and
README.md).
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.graph.nodes import decide_node, extract_node, lookup_node

INVOICES_DIR = BASE_DIR / "data" / "invoices"


def main() -> None:
    invoice_paths = sorted(INVOICES_DIR.glob("*.txt"))
    if not invoice_paths:
        print(f"No invoice files found in {INVOICES_DIR}")
        return

    for path in invoice_paths:
        print(f"--- {path.name} ---")
        state = {"invoice_file": str(path)}
        try:
            state = extract_node(state)
            state = lookup_node(state)
            state = decide_node(state)
            print(f"decision: {state['decision']}")
            print(f"reasoning: {state['reasoning']}")
        except Exception as exc:
            print(f"ERROR: {exc}")
        print()


if __name__ == "__main__":
    main()
