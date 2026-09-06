# PPV Memory — Fullstack (FastAPI + Next.js) Build Plan

**Context:** Core LangGraph pipeline is complete, tested, and passing the mini-eval 
(3/5 without memory, 5/5 with memory). A working Streamlit prototype exists. This 
plan replaces the Streamlit layer with a FastAPI backend + Next.js dashboard 
frontend, using the "re-run rather than pause/resume" approach (see prior 
discussion) to avoid LangGraph's interrupt/resume crossing a network boundary. 
No changes to `extract_node`, `lookup_node`, or `decide_node`'s internal logic — 
this plan only restructures where the pipeline is called from and how a flagged 
invoice gets resolved.

**Time-box discipline:** ~17 hours remained at the point this was planned, with 
README, demo scripting, recording, and Devpost submission still ahead. Each step 
below has a rough time budget. If Step 2 or 3 blows its budget significantly, 
fall back to the existing working Streamlit version rather than continuing.

---

## STEP 1 — Restructure the repo (mechanical move, ~30-45 min)

Move existing code into a `backend/` folder without changing any logic:

- `src/` → `backend/src/`
- `data/` → `backend/data/`
- `scripts/` → `backend/scripts/`
- `eval/` → `backend/eval/`
- `requirements.txt` → `backend/requirements.txt`
- Update any relative imports/paths inside these files that assumed repo-root 
  execution (e.g. `data/ppv_memory.db` paths may need to become relative to 
  `backend/`, or resolved via an absolute path helper)

Create an empty `frontend/` folder at the repo root, sibling to `backend/`.

**Validate before proceeding:** run the existing mini-eval 
(`backend/eval/mini_eval.py`) from within `backend/` and confirm it still passes 
5/5 with memory, exactly as before the move. If imports or paths break, fix them 
now — this is the cheapest point to catch it.

**Do this step yourself or as a single, tightly-scoped AO task** — explicitly 
instruct: "move files only, do not rewrite any logic inside `nodes.py`, 
`build_graph.py`, `db.py`, or `llm.py`."

---

## STEP 2 — Modify the graph: remove the mid-graph interrupt (~30 min)

In `backend/src/graph/build_graph.py`, change the wiring so the graph ends after 
`decide_node`, regardless of decision:

```
extract_node -> lookup_node -> decide_node -> END
```

Remove the conditional edge to `human_review_node`. The graph itself never 
pauses — it always runs start-to-finish and returns a complete state, including 
`decision` ("auto_approve" or "flag") and `reasoning`.

`human_review_node`'s existing logic (surfacing what a flagged invoice needs) and 
`record_resolution_node`'s existing logic (writing to the `resolutions` table) 
are **kept as plain functions** in `nodes.py` — just no longer wired as graph 
edges. They'll be called directly by the API layer in Step 3.

**Validate:** run the graph manually against INV-1002 (a flag case) and confirm 
it now returns a complete result immediately, with `decision: "flag"`, instead 
of pausing.

---

## STEP 3 — Build the FastAPI backend (~2-2.5 hrs)

Create `backend/main.py` with three endpoints:

**`POST /invoices/trigger`**
- Input: an invoice filename (from `backend/data/invoices/`) or raw invoice text
- Runs the invoice through the graph (`extract_node -> lookup_node -> decide_node`)
- If `decision == "auto_approve"`: store result as resolved/approved (a simple 
  table, e.g. `invoice_status`, tracking id, status, reasoning, steps)
- If `decision == "flag"`: store result with status `"pending_review"`
- Returns the full result including the `steps` array (see Step 3b)

**`GET /invoices`**
- Returns all processed invoices with: id, vendor, item, status 
  (auto_approved / pending_review / resolved), variance %, reasoning summary
- This feeds the dashboard table (Step 4)

**`GET /invoices/{id}`**
- Returns full detail for one invoice: all extracted fields, PO comparison, 
  variance, reasoning, prior resolution (if any), and the `steps` array
- This feeds the invoice detail page (Step 5)

**`POST /invoices/{id}/resolve`**
- Input: `resolver_name`, `resolved_price`, `reason`
- Calls the existing `record_resolution_node` logic directly (not through the 
  graph) to write a new row into `resolutions`
- Updates the invoice's stored status to `"resolved"`
- Returns the updated invoice record

**3b. Add the `steps` field to every invoice response** (per earlier discussion):
Reshape the graph's final state into an ordered list for display — no new 
computation, just formatting what's already in state:
```json
"steps": [
  {"label": "Extracted invoice data", "detail": "Vendor: ..., Item: ..., Price: $...", "done": true},
  {"label": "Looked up PO ...", "detail": "PO price: $...", "done": true},
  {"label": "Checked resolution history", "detail": "Found prior resolution / None found", "done": true},
  {"label": "Calculated variance", "detail": "+X.X%", "done": true},
  {"label": "Decision", "detail": "Auto-approved / Flagged for review", "done": true}
]
```

**3c. CORS setup:** enable CORS for `localhost:3000` (Next.js dev default) so the 
frontend can call these endpoints during development.

**Validate before proceeding:** use `curl` or FastAPI's built-in `/docs` (Swagger 
UI) to manually test all 4 endpoints against your 5 synthetic invoices, in order. 
Confirm: INV-1001 auto-approves; INV-1002 flags; resolving INV-1002 writes to 
`resolutions`; INV-1003 (triggered *after* resolving INV-1002) auto-approves 
citing the prior resolution — this is your core thesis, now working over HTTP. 
**Do not proceed to frontend work until this sequence is confirmed correct.**

---

## STEP 4 — Build the Next.js dashboard (main page) (~1.5-2 hrs)

Set up a basic Next.js app in `frontend/` (`npx create-next-app@latest`, minimal 
config, no need for extra libraries beyond fetch).

`frontend/app/page.tsx` — the dashboard:
- On load, calls `GET /invoices` and renders a simple table
- Columns: Invoice #, Vendor, Item, Variance %, Status (with a simple colored 
  badge: green = auto-approved, yellow = pending review, blue = resolved)
- Each row is clickable, navigating to `/invoice/[id]`
- A "Trigger new invoice" control (dropdown or button list of the 5 synthetic 
  invoice filenames) that calls `POST /invoices/trigger` — this is your 
  "simulate an invoice arriving" mechanism from the earlier discussion

`frontend/lib/api.ts` — thin fetch wrapper (`getInvoices()`, `getInvoice(id)`, 
`triggerInvoice(filename)`, `resolveInvoice(id, data)`) pointing at your FastAPI 
backend's URL.

**Validate:** run both servers (`uvicorn backend.main:app --reload` and 
`npm run dev` in `frontend/`), load the dashboard, confirm the table populates 
and the trigger button actually calls the backend and updates the table.

---

## STEP 5 — Build the invoice detail page (~1-1.5 hrs)

`frontend/app/invoice/[id]/page.tsx`:
- Calls `GET /invoices/{id}` on load
- Displays: vendor, item, invoice price vs. PO price, variance %
- Renders the `steps` array as a simple vertical checklist (per the earlier 
  "agent steps" discussion) — label + detail per step, no animation, static 
  render since processing is already complete by the time this page loads
- Displays the reasoning text prominently
- If status is `"pending_review"`: shows a resolution form (resolver name, 
  resolved price, reason — text inputs + submit button) that calls 
  `POST /invoices/{id}/resolve`, then refreshes to show the resolved state
- If status is `"auto_approved"` and a prior resolution was cited: shows that 
  citation clearly (e.g. "Consistent with prior approval on [date]: '[reason]'")

**Validate:** click through the full demo sequence in the browser — trigger 
INV-1002, see it flagged, open its detail page, see the steps + reasoning, 
resolve it, confirm it updates, then trigger INV-1003 and confirm it 
auto-approves citing the resolution. This is the complete Step 4 demo arc from 
the original plan, now running through the real frontend/backend stack.

---

## STEP 6 — Final polish pass (~30-45 min, time permitting)

Only after Steps 1-5 are fully working and validated:
- Basic styling pass (spacing, font, color consistency) — not a redesign, just 
  making sure it doesn't look unstyled
- Confirm the "Needs Review" vs "Auto-Approved" distinction is visually obvious 
  at a glance on the dashboard (this matters more for the demo than any other 
  visual detail)
- Double check the notification framing ("🔔 N invoices pending review" badge/
  banner on the dashboard) if time allows — this was the other cheap addition 
  discussed earlier for grounding the "how does a human get notified" question

**Do not start this step if Steps 1-5 together have already consumed more than 
~6 hours** — at that point, prioritize README, demo script, and recording over 
further polish.

---

## Fallback checkpoint

After Step 3 (backend complete and validated over curl/Swagger), you have a 
genuine decision point: if frontend work (Steps 4-5) is going well and on 
budget, continue. If Step 3 itself ran significantly over budget, or you're 
more than ~10 hours from the deadline at this point with README/demo/submission 
still ahead, stop here and fall back to the already-working Streamlit version — 
it demonstrates the identical core thesis and is a completely safe, submittable 
project on its own.

---

## Updated project structure (final state)

```
ppv-memory/
├── PLAN.md
├── README.md
├── .gitignore
│
├── backend/
│   ├── requirements.txt
│   ├── main.py                    # FastAPI app — 4 endpoints
│   ├── data/
│   │   ├── ppv_memory.db
│   │   ├── invoices/ (INV-1001.txt ... INV-1005.txt)
│   │   └── SCENARIO_KEY.md
│   ├── scripts/
│   │   └── generate_data.py
│   ├── src/
│   │   ├── graph/
│   │   │   ├── state.py
│   │   │   ├── nodes.py           # extract_node, lookup_node, decide_node,
│   │   │   │                      # human_review_node (plain fn now),
│   │   │   │                      # record_resolution_node (plain fn now)
│   │   │   └── build_graph.py     # extract -> lookup -> decide -> END
│   │   ├── db.py
│   │   └── llm.py
│   └── eval/
│       └── mini_eval.py
│
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── app/
    │   ├── page.tsx                # dashboard table + trigger control
    │   ├── invoice/[id]/page.tsx   # detail view: steps, reasoning, resolution form
    │   └── layout.tsx
    └── lib/
        └── api.ts
```

## Build order summary
1. Restructure (move files, no logic change) → validate eval still passes
2. Simplify graph (remove interrupt) → validate flag returns immediately
3. FastAPI backend, 4 endpoints + steps field → validate full sequence via curl/Swagger
4. Next.js dashboard page → validate table + trigger
5. Next.js detail page + resolution form → validate full demo arc end-to-end
6. Polish (time-boxed, optional)

**Fallback checkpoint after Step 3**: continue only if on budget; otherwise revert to Streamlit.