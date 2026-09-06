"""Demo/sanity check for src.graph.nodes.extract_node.

Runs extract_node against all invoices in data/invoices/ and prints the
resulting state dict for each, to visually confirm the shape of the
output (an `extracted_data` key merged into the input state).

Usage:
    python scripts/test_extract_node.py

Requires TENSORMUX_API_KEY to be set (see src/extraction.py and
README.md).
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.graph.nodes import extract_node

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
            result_state = extract_node(state)
            print(json.dumps(result_state, indent=2))
        except Exception as exc:
            print(f"ERROR: {exc}")
        print()


if __name__ == "__main__":
    main()
