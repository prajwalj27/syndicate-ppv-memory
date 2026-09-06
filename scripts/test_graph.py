"""Demo/sanity check for the compiled PPV Memory graph.

Runs the full graph (extract_node -> lookup_node -> decide_node, per
src/graph/build_graph.py) against all invoices in data/invoices/ and
prints the resulting `decision` and `reasoning` for each, to visually
confirm the wired graph's behavior end to end.

Usage:
    python scripts/test_graph.py

Requires TENSORMUX_API_KEY to be set (see src/extraction.py and
README.md).
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.graph.build_graph import graph

INVOICES_DIR = BASE_DIR / "data" / "invoices"


def main() -> None:
    invoice_paths = sorted(INVOICES_DIR.glob("*.txt"))
    if not invoice_paths:
        print(f"No invoice files found in {INVOICES_DIR}")
        return

    for path in invoice_paths:
        print(f"--- {path.name} ---")
        try:
            result_state = graph.invoke({"invoice_file": str(path)})
            print(f"decision: {result_state['decision']}")
            print(f"reasoning: {result_state['reasoning']}")
        except Exception as exc:
            print(f"ERROR: {exc}")
        print()


if __name__ == "__main__":
    main()
