# PPV Memory

A Purchase Price Variance (PPV) agent — see [docs/PLAN.md](docs/PLAN.md) for the full project plan.

## Setup

Use a virtual environment — `langgraph` pulls in a `langchain-core` version
that can conflict with other, unrelated projects if installed globally:

```
python -m venv .venv
.venv/Scripts/activate   # or `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
```

## Synthetic data

Regenerates `data/ppv_memory.db` (purchase orders + empty resolutions table)
and `data/invoices/*.txt`:

```
python scripts/generate_data.py
```

## Invoice extraction

`src/extraction.py` reads a plain-text invoice and uses an LLM
(Tensormux's OpenAI-compatible endpoint, GLM-4.7-Flash — see PLAN.md
section 4) to extract structured fields: vendor, item, PO reference,
quantity, unit price, invoice date, invoice number.

Requires the `TENSORMUX_API_KEY` environment variable to be set to a valid
Tensormux API key. Optionally override `TENSORMUX_BASE_URL` (default
`https://api.tensormux.com/v1`) or `PPV_EXTRACTION_MODEL` (default
`glm-4-7-flash`).

Set these via a `.env` file (copy `.env.example` to `.env` and fill in your
key — it's loaded automatically and gitignored):

```
cp .env.example .env
# edit .env and paste in your key
```

or export them directly in your shell instead. Then run extraction against
the 5 sample invoices and print the results:

```
python scripts/extract_invoices.py
```

## Graph pipeline

`src/graph/build_graph.py` wires the LangGraph pipeline:
`extract_node -> lookup_node -> decide_node`, with a conditional edge from
`decide_node` based on `decision` (`auto_approve` / `flag`). Both branches
currently end the graph — the `flag` branch will route to
`human_review_node` once it's built (Step 3 in `docs/BUILD_PLAN.md`).

Run the compiled graph against the 5 sample invoices and print each
decision:

```
python scripts/test_graph.py
```