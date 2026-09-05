"""CLI to run LLM-based invoice extraction against the sample invoices.

Loops over data/invoices/*.txt, extracts structured fields from each via
ppv_memory.extraction, and prints the result.

Usage:
    python scripts/extract_invoices.py

Requires TENSORMUX_API_KEY to be set (see ppv_memory/extraction.py and
README.md).
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ppv_memory.extraction import extract_invoice_file

INVOICES_DIR = BASE_DIR / "data" / "invoices"


def main() -> None:
    invoice_paths = sorted(INVOICES_DIR.glob("*.txt"))
    if not invoice_paths:
        print(f"No invoice files found in {INVOICES_DIR}")
        return

    for path in invoice_paths:
        print(f"--- {path.name} ---")
        try:
            fields = extract_invoice_file(path)
            print(json.dumps(fields, indent=2))
        except Exception as exc:
            print(f"ERROR: {exc}")
        print()


if __name__ == "__main__":
    main()
