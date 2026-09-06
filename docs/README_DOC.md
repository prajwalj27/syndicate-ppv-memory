AO Task — Final README

Write the complete README.md at the repo root for PPV Memory. This is the official submission document — it needs to be accurate to what's actually built (verify against the real code, don't assume the plan docs are 100% up to date, since a few things changed during the build — e.g. the tolerance band was added later, the LangGraph interrupt pattern was replaced with a re-run approach for the FastAPI/Next.js version).

Required sections, in this order
1. Title + one-line description

Project name, one sentence on what it does, the track (Track 2 — Autonomous Office of the CFO, Syndicate by Maximor).

2. The problem

2-4 sentences: what pain point this addresses, grounded in the same framing used in the demo (a vendor invoice comes in above the PO price — is it a real issue or an already-approved change never reflected on the PO). Reference the real-world mechanism (substitute item, fuel surcharge, contract renewal) and the cited stats (45-60 min per price-variance exception per Peakflo; ~62% of AP time on exceptions per Ardent Partners via Centime) — check data/SCENARIO_KEY.md and the slide content for the exact figures/attribution already used, and keep it consistent with those, not restated differently.

3. How it works (architecture)

Short prose + the pipeline diagram, described as: Invoice arrives → Extract (LLM) → Look up PO + resolution history (SQLite) → Decide (variance + tolerance band + memory check) → Auto-approve, or Flag → human resolves → writes to memory. Explicitly state that a flagged invoice does NOT pause a running process (no LangGraph interrupt across the API boundary) — the decision is computed and returned immediately as "pending review," and resolving it later is a separate API call that writes to the resolutions table directly. Be accurate here — check the actual current code in backend/src/graph/build_graph.py and backend/main.py before writing this, don't assume it matches an earlier planning doc.

4. Tech stack

List: LangGraph, FastAPI, Next.js, SQLite, Claude / Tensormux (GLM-4.7-Flash) for extraction and reasoning, Agent Orchestrator (used to build the project). One line each on what it's used for.

5. Project structure

A brief tree view of backend/ and frontend/, matching the actual current folder layout (verify against the real repo, not an old planning doc — the structure changed at least twice during the build: once for the LangGraph restructure, once for the backend/frontend split).

6. Setup instructions

Prerequisites: Python version used, Node.js version used, and any system dependency the PDF generation step needs (check what library was actually used — weasyprint or pdfkit/wkhtmltopdf — and note its system dependency if any).

Backend setup:

Clone the repo
cd backend
Create and activate a virtual environment (include the actual commands for both macOS/Linux and Windows)
pip install -r requirements.txt
Environment variables: create a .env file — list every environment variable actually read by the code (check backend/src/llm.py and anywhere else os.environ/os.getenv is called) — likely includes API keys for Claude and/or Tensormux. Provide an .env.example template as well if one doesn't already exist, and create it as part of this task if missing.
Generate the database and synthetic invoices: exact command to run scripts/generate_data.py (and scripts/generate_pdf_invoices.py if that's a separate script), noting this creates data/ppv_memory.db and populates data/invoices/ and data/invoices_pdf/
Start the backend: exact uvicorn command actually used (check main.py's app variable name and confirm the reload flag/port used in development)

Frontend setup:

cd frontend
npm install
Environment variables: if the frontend needs to know the backend's URL (e.g. NEXT_PUBLIC_API_URL), document it — check frontend/lib/api.ts for how the backend URL is currently configured (hardcoded vs. env var) and document accordingly; if it's currently hardcoded, note that as a known limitation rather than inventing an env var that doesn't exist
Start the frontend: npm run dev, note the port and that both backend and frontend need to be running simultaneously

Regenerating a clean demo state: note that re-running generate_data.py resets the database (clears any resolutions), useful for re-running the demo scenarios from scratch.

7. Which track, what agent workflow (required by the hackathon rules)

Explicitly state: Track 2, and describe the agent workflow built (extraction → lookup → decision → human-in-the-loop resolution → memory write), matching what's actually in the code.

8. What improved across iterations (required by the hackathon rules)

Briefly and honestly describe the real iteration history: started as a Streamlit prototype, moved to a FastAPI + Next.js fullstack version; the LangGraph interrupt-based human-in-the-loop was replaced with a re-run approach for the API version; a tolerance-band mechanism was added to decide_node after being identified as missing from the original design; PDF invoice support (real text-layer PDFs, no OCR) was added as an extension beyond plain text invoices.

9. Output explanation — what each invoice result means (this is the

section the user specifically asked for; write it carefully)

For each of the three possible outcomes a buyer sees on an invoice's detail page, explain clearly, in plain language a non-technical reader (an accountant, a judge, a Maximor engineer skimming this) can follow:

Auto-approved (exact match): "The invoice price matches the purchase order exactly — no variance, so no review is needed. [Reference INV-1001 or similar as a concrete example from the actual data, if still present in the repo.]"

Auto-approved (within tolerance band): "The variance is small enough (under the tolerance threshold — state the actual percentage used in decide_node, verified from the real code) that it's approved automatically, even without a prior human decision on file. [Reference INV-3003 or similar concrete example.]"

Flagged — needs buyer review: "The variance is above tolerance, and there's no matching prior resolution for this exact vendor and item at this price. The system shows the buyer exactly why it was flagged — the invoice price, the PO price, the variance percentage — so they can make an informed call. [Reference INV-1002 or similar.]"

Auto-approved via memory (citing a prior resolution): "This is the core mechanism: once a buyer resolves a flagged invoice with a stated reason, that resolution is remembered. If a later invoice comes in from the same vendor, for the same item, at the same price, it's auto-approved automatically — and the reasoning explicitly cites the earlier decision, by date and reason, so there's a clear audit trail of why. [Reference INV-1003 citing INV-1002's resolution, with the actual reasoning text pulled from a real run if possible.]"

Flagged despite similar vendor/item (guardrail case): "The memory mechanism is deliberately narrow — it only reuses a decision for the exact same vendor, item, and price. A different item from the same vendor, or a variance that goes well beyond what was previously approved, will still be flagged for a fresh decision. [Reference INV-1004 and INV-1005 as concrete examples of this guardrail.]"

For each of these, pull the ACTUAL vendor names, items, prices, and reasoning text from the real data in data/invoices/, data/SCENARIO_KEY.md, and ideally a real API response — do not invent example numbers; use what's actually in the repository so the README is verifiably accurate against the running project.

10. Demo / links


Validation before finishing
Confirm every command in the setup section actually works by running through it fresh (ideally in a clean clone or at least a fresh terminal session) — a broken README is worse than no README, since it's the first thing a judge tries
Confirm every environment variable listed is actually read somewhere in the code — don't list one that isn't used, and don't omit one that is
Confirm the project structure section matches the real current folder layout via ls/tree, not an old planning doc
Confirm the output-explanation section's example invoices and numbers are pulled from real, current data — cross-check against SCENARIO_KEY.md