"""PDF text extraction for PPV Memory.

Pulls raw text out of a PDF invoice so it can be handed to the same
LLM-based field extraction used for .txt invoices (see src/extraction.py).
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber


def extract_pdf_text(path: str | Path) -> str:
    """Read a PDF file and return its concatenated page text."""
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
