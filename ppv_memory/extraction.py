"""LLM-based invoice field extraction for PPV Memory.

Reads a plain-text invoice (see scripts/generate_data.py for the format
used to generate data/invoices/*.txt) and calls an LLM to pull out the
fields needed by the downstream variance-calculation and
resolution-memory steps: vendor, item, PO reference, quantity, unit
price, invoice date, and invoice number.

This uses Tensormux's OpenAI-compatible endpoint (GLM-4.7-Flash) per
docs/PLAN.md section 4, which reserves Tensormux for high-volume/bulk
calls like extraction and Claude for the final decision reasoning shown
to a human reviewer (a later build step).

Required environment variable:
    TENSORMUX_API_KEY - API key for the Tensormux endpoint.

Optional environment variables:
    TENSORMUX_BASE_URL     - defaults to "https://api.tensormux.com/v1"
    PPV_EXTRACTION_MODEL   - defaults to "glm-4-7-flash"

These can be set in the shell, or dropped in a .env file at the repo
root (see .env.example) — it's loaded automatically on import and never
committed (.env is gitignored).

GLM-4.7-Flash is a reasoning model: it emits a "reasoning" trace before
its final answer, both counted against max_tokens. A too-low max_tokens
truncates the response before the final JSON is produced, so this module
uses a generous budget.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DEFAULT_BASE_URL = "https://api.tensormux.com/v1"
DEFAULT_MODEL = "glm-4-7-flash"
MAX_TOKENS = 2048

FIELDS = [
    "vendor",
    "item",
    "po_reference",
    "quantity",
    "unit_price",
    "invoice_date",
    "invoice_number",
]

_SYSTEM_PROMPT = """You are an accounts-payable data extraction assistant. You will be given the plain text of a single vendor invoice. Extract exactly these fields and respond with ONLY a single JSON object, no markdown, no commentary:
{
  "vendor": string, name of the vendor/supplier that issued the invoice,
  "item": string, the line-item product/service description billed,
  "po_reference": string, the purchase order number this invoice references,
  "quantity": number, quantity of the item billed,
  "unit_price": number, price per unit in dollars (no currency symbols),
  "invoice_date": string, the invoice date in YYYY-MM-DD format,
  "invoice_number": string, the invoice's own identifying number
}
If an invoice lists multiple line items, extract the first/primary one.
Do not invent values that aren't present in the text."""


def _get_client() -> OpenAI:
    api_key = os.environ.get("TENSORMUX_API_KEY")
    if not api_key:
        raise RuntimeError(
            "TENSORMUX_API_KEY environment variable is not set. "
            "Set it to a valid Tensormux API key to run extraction "
            "(see README.md for setup)."
        )
    base_url = os.environ.get("TENSORMUX_BASE_URL", DEFAULT_BASE_URL)
    return OpenAI(api_key=api_key, base_url=base_url)


def _parse_json_response(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
    return json.loads(text)


def extract_invoice_fields(
    invoice_text: str, *, model: str | None = None
) -> dict[str, Any]:
    """Extract structured fields from raw invoice text via an LLM call.

    Returns a dict with exactly the keys in FIELDS: vendor, item,
    po_reference, quantity, unit_price, invoice_date, invoice_number.
    Raises ValueError if the model's response can't be parsed into that
    shape, and RuntimeError if TENSORMUX_API_KEY isn't set.
    """
    client = _get_client()
    model = model or os.environ.get("PPV_EXTRACTION_MODEL", DEFAULT_MODEL)

    response = client.chat.completions.create(
        model=model,
        max_tokens=MAX_TOKENS,
        temperature=0,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": invoice_text},
        ],
    )

    raw = response.choices[0].message.content
    if not raw:
        raise ValueError(
            f"Empty response from model (finish_reason="
            f"{response.choices[0].finish_reason!r}); it may have run out "
            f"of tokens during its reasoning trace."
        )

    try:
        fields = _parse_json_response(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse JSON from model response: {raw!r}") from exc

    missing = [f for f in FIELDS if f not in fields]
    if missing:
        raise ValueError(f"Extraction missing required fields {missing}: {fields}")

    try:
        fields["quantity"] = int(fields["quantity"])
        fields["unit_price"] = float(fields["unit_price"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"quantity/unit_price were not numeric: {fields}") from exc

    return {field: fields[field] for field in FIELDS}


def extract_invoice_file(path: str | Path, *, model: str | None = None) -> dict[str, Any]:
    """Read an invoice text file and extract structured fields from it."""
    text = Path(path).read_text(encoding="utf-8")
    fields = extract_invoice_fields(text, model=model)
    fields["source_file"] = Path(path).name
    return fields
