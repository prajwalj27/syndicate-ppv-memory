# PPV Memory

An agent that decides whether a vendor invoice priced above its purchase order is a real problem or already-approved drift it's seen before — and remembers the difference so a human only has to make the same call once.

**Track:** Track 2 — Autonomous Office of the CFO, Syndicate by Maximor, hosted by Agent Orchestrator.

---

## The problem

When a recurring vendor's invoice comes in above the price on its purchase order, someone has to decide whether it's a real issue or a legitimate change that was already approved verbally but never updated on the PO — a substitute item shipped instead of the original, a fuel surcharge added at time of shipment, a contract/retainer renewal at a new rate. Today that judgment gets made fresh every time, by whoever happens to review it, with no memory of what was decided last time for that exact vendor and item. That's expensive: Peakflo estimates 45–60 minutes of manual work per price-variance exception, and Ardent Partners research (via Centime) puts roughly 62% of AP staff time toward handling exceptions like this one. PPV Memory targets that specific gap — not invoice processing in general, but the repeated, un-learned judgment call on price variance.

## How it works (architecture)

```
Invoice arrives
      |
      v
  Extract (LLM)              <- Tensormux / GLM-4.7-Flash pulls vendor, item,
      |                          PO reference, qty, unit price, date, invoice #
      v
  Look up PO + resolution     <- SQLite: purchase_orders + resolutions tables
  history
      |
      v
  Decide (variance + tolerance
  band + memory check)
      |
      +--> within tolerance / matches a prior resolution --> Auto-approve
      |
      +--> otherwise --------------------------------------> Flag
                                                                  |
                                                                  v
                                                     Buyer resolves in the UI
                                                                  |
                                                                  v
                                                        Writes to memory
                                                     (resolutions table)
```

This is a LangGraph graph (`extract_node -> lookup_node -> decide_node`, see `backend/src/graph/build_graph.py`) invoked once per `POST /invoices/trigger` call. It runs straight through to a decision and returns it in the same response — flagging an invoice does **not** pause the graph mid-run. `human_review_node` and `interrupt()` still exist in `backend/src/graph/nodes.py`, but only the legacy test scripts under `backend/scripts/` (e.g. `test_human_review.py`) exercise them directly against the compiled graph; `build_graph()` itself only wires `extract -> lookup -> decide -> END`. A flagged invoice is simply persisted with status `pending_review` and its full computed state (why it was flagged, invoice vs. PO price, variance, any prior resolution). Resolving it later is a separate call, `POST /invoices/{id}/resolve`, which loads that stored state, applies the buyer's decision, and writes a new row directly to the `resolutions` table — there's no graph run being resumed, just a fresh, independent request.

## Tech stack

| Component | Used for |
|---|---|
| **LangGraph** | Wires the linear `extract -> lookup -> decide` pipeline as a graph |
| **FastAPI** | Backend API — `trigger` / `list` / `detail` / `resolve` endpoints |
| **Next.js** | Frontend — invoice dashboard, invoice detail/resolution page, vendor invoice simulator |
| **SQLite** | Stores purchase orders, resolution memory, and every triggered invoice's full state |
| **Tensormux (GLM-4.7-Flash)** | The only LLM actually called at runtime — extracts structured fields from raw invoice text/PDF text |
| **Claude / Anthropic** | Used via Agent Orchestrator (Claude Code) to build the project. *Not* called at runtime: the plan originally reserved Claude for the final decision reasoning shown to a reviewer, but that reasoning is generated deterministically in `decide_node` from the computed variance and memory match, not by an LLM call |
| **Agent Orchestrator** | Used to build the project — see the AO Kanban/session history for the build process |


## Setup instructions

**Prerequisites**
- Python 3.12+ (built/tested with 3.12.6)
- Node.js 20+ and npm 10+ (built/tested with Node v20.11.1, npm 10.8.3)
- No extra system dependency for PDF generation: `weasyprint>=61.0` (currently resolves to 69.x) renders PDFs with its own pure-Python backend, verified by installing from a clean virtualenv and running `generate_pdf_invoices.py` with no GTK/Cairo/Pango installed. You may see harmless `Fontconfig error: Cannot load default config file` warnings printed to the console on Windows — PDFs still generate correctly.

### Backend setup

```bash
git clone <repo-url>
cd backend
```

Create and activate a virtual environment:

```bash
# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

**Environment variables.** The only variable actually read by the code (`backend/src/extraction.py`) is `TENSORMUX_API_KEY` (required), plus two optional overrides. Copy the example file and fill it in — but note it needs to end up at the **repo root**, not inside `backend/`: `extraction.py`'s `load_dotenv()` call resolves three directories up from itself, which lands on the repo root.

```bash
# from the repo root
cp backend/.env.example .env
# then edit .env and paste in your Tensormux key
```

| Variable | Required | Default |
|---|---|---|
| `TENSORMUX_API_KEY` | Yes | — |
| `TENSORMUX_BASE_URL` | No | `https://api.tensormux.com/v1` |
| `PPV_EXTRACTION_MODEL` | No | `glm-4-7-flash` |

Generate the database and synthetic invoices (run from `backend/`):

```bash
python scripts/generate_data.py          # creates data/ppv_memory.db and data/invoices/*.txt
python scripts/generate_pdf_invoices.py  # creates data/invoices_pdf/*.pdf (same 12 invoices)
```

Start the backend (from `backend/`, with the venv active):

```bash
uvicorn main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

### Frontend setup

```bash
cd frontend
npm install
```

**Environment variables.** The frontend reads the backend URL from `NEXT_PUBLIC_API_BASE_URL` (see `frontend/lib/api.ts`), falling back to `http://localhost:8000` if unset. No `.env` file is required for local development against the default backend port.

Start the frontend:

```bash
npm run dev
```

The dashboard is now at `http://localhost:3000`. Both the backend (port 8000) and frontend (port 3000) need to be running at the same time — the backend's CORS config only allows `http://localhost:3000`.

### Regenerating a clean demo state

Re-running `python scripts/generate_data.py` from `backend/` drops and recreates `data/ppv_memory.db` from scratch, clearing any resolutions recorded during a demo run, and rewrites the `.txt` invoices. Useful for resetting before re-running the demo scenarios. Note: the "Send Invoice" button on the simulator page always triggers the `.txt` version of the selected invoice (`main.py`'s `/invoices/trigger` endpoint normalizes any filename to `.txt`); the PDF files are wired up for preview and for direct extraction via `pdf_extract.py`, but aren't currently reachable through that button.

## Which track, what agent workflow

**Track 2 — Autonomous Office of the CFO.** The agent workflow, matching the current code:

1. **Extraction** — an LLM (Tensormux/GLM-4.7-Flash) reads the raw invoice text and pulls structured fields.
2. **Lookup** — the vendor's PO and any prior resolution for this exact vendor+item are pulled from SQLite; variance % against the PO price is computed.
3. **Decision** — auto-approve if the price matches a prior resolution (within a cent) or falls within the 2% tolerance band; otherwise flag for review, with reasoning that states the invoice price, PO price, and variance %.
4. **Human-in-the-loop resolution** — a flagged invoice sits as `pending_review` until a buyer submits a resolution (resolver name, resolved price, reason) via a separate API call; this is a fresh request, not a resumed graph run.
5. **Memory write** — an approved resolution is written to the `resolutions` table, keyed to vendor + item, so a later invoice at that same price auto-approves and cites the earlier decision by date and reason.

## What improved across iterations

- **Streamlit prototype first.** The pipeline was originally built as `extract_node -> lookup_node -> decide_node -> human_review_node`, with `human_review_node` using LangGraph's `interrupt()` to pause the graph for a Streamlit-based buyer review queue.
- **Moved to a FastAPI + Next.js fullstack version.** The backend was restructured into `backend/`, and the LangGraph-`interrupt()`-based human-in-the-loop was replaced with a re-run approach: the graph now always runs start-to-finish to a decision in one request, and review/resolution became its own endpoint that writes directly to the `resolutions` table instead of resuming a paused run. (`human_review_node`/`interrupt()` are kept only for the older test scripts that still exercise the graph directly.)
- **Tolerance band added.** `decide_node` originally only auto-approved on an exact PO-price match or a matching prior resolution; a 2% variance tolerance band (`AUTO_APPROVE_VARIANCE_TOLERANCE`) was added afterward so a small, undisputed variance doesn't need a human decision on file at all (see INV-3003 below).
- **Multi-vendor scenarios added.** A second and third vendor (Brightline Logistics, Crestpoint IT Services) were added to exercise the tolerance band and a same-vendor/different-item memory guardrail (INV-2004) beyond the original single-vendor scenario set.
- **PDF invoice support added.** `pdf_extract.py` (via `pdfplumber`) extracts text from real, text-layer PDF invoices — no OCR — feeding the same extraction/decision pipeline as the original plain-text invoices.
- **Vendor Invoice Simulator page added.** A frontend page (`frontend/app/simulator/page.tsx`) stands in for the external system that would send invoices in, letting a demo preview and trigger any of the 12 seeded invoices without using `curl`.

