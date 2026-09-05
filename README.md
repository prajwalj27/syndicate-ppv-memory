# PPV Memory

A Purchase Price Variance (PPV) agent — see [docs/PLAN.md](docs/PLAN.md) for the full project plan.

## Setup

```
pip install -r requirements.txt
```

## Synthetic data

Regenerates `data/ppv_memory.db` (purchase orders + empty resolutions table)
and `data/invoices/*.txt`:

```
python scripts/generate_data.py
```

## Invoice extraction

`ppv_memory/extraction.py` reads a plain-text invoice and uses an LLM
(Tensormux's OpenAI-compatible endpoint, GLM-4.7-Flash — see PLAN.md
section 4) to extract structured fields: vendor, item, PO reference,
quantity, unit price, invoice date, invoice number.

Requires the `TENSORMUX_API_KEY` environment variable to be set to a valid
Tensormux API key. Optionally override `TENSORMUX_BASE_URL` (default
`https://api.tensormux.com/v1`) or `PPV_EXTRACTION_MODEL` (default
`glm-4-7-flash`).

Run extraction against the 5 sample invoices and print the results:

```
export TENSORMUX_API_KEY=your-key-here
python scripts/extract_invoices.py
```