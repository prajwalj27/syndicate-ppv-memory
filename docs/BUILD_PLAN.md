# PPV Memory — Build Plan, Step 2 Onward (LangGraph Revision)

**Context:** Step 1 (synthetic data generator) is merged. A standalone extraction 
script also already exists — it reads an invoice text file, calls an LLM, and 
`json.dumps()`s the extracted fields to console. This plan folds that existing 
extraction logic into a LangGraph pipeline rather than rebuilding it, and covers 
everything from there through the mini-eval.

---

## STEP 2 — Wrap existing extraction as a graph node, add lookup + decision nodes

**2a. Locate and adapt the existing extraction code**
Find the function in the current extraction script that performs the actual LLM 
call and produces the field dict (vendor, item, po_reference, quantity, 
unit_price, invoice_number, invoice_date) — this is the logic sitting just before 
the `json.dumps()`/`print()` call. Refactor so that function **returns the dict** 
instead of (or in addition to) printing it. Move this function into 
`src/graph/nodes.py` as the body of `extract_node`, or have `extract_node` import 
and call it from wherever it already lives — whichever requires less rewriting. 
Do not re-implement extraction from scratch; reuse the working prompt/logic as-is.

**2b. Define the graph state**
Create `src/graph/state.py` with a TypedDict:
```
invoice_file: str
extracted_data: dict | None
po_record: dict | None
variance_pct: float | None
prior_resolution: dict | None
decision: str | None
reasoning: str | None
human_resolution: dict | None
```

**2c. Build the three initial nodes in `src/graph/nodes.py`**
- `extract_node(state)`: calls the adapted extraction function on `state.invoice_file`, 
  sets `extracted_data`.
- `lookup_node(state)`: using `extracted_data["po_reference"]`, queries the 
  `purchase_orders` table for the matching PO. Queries the `resolutions` table for 
  any row matching this vendor+item. Calculates 
  `variance_pct = (invoice_unit_price - po_unit_price) / po_unit_price`. Sets 
  `po_record`, `prior_resolution`, `variance_pct`.
- `decide_node(state)`: applies this logic —
  - If `prior_resolution` exists and its `resolved_price` matches (or is very 
    close to) the invoice price → `decision = "auto_approve"`, reasoning cites the 
    prior resolution's date and reason.
  - Else if `variance_pct == 0` → `decision = "auto_approve"`, reasoning states 
    exact match to PO.
  - Else → `decision = "flag"`, reasoning states vendor, item, invoice price, PO 
    price, variance %, and "no prior resolution on file."

**2d. Wire the graph in `src/graph/build_graph.py`**
`extract_node -> lookup_node -> decide_node`. From `decide_node`, add a 
conditional edge: if `decision == "auto_approve"` → `END`; if `decision == "flag"` 
→ `human_review_node` (built in Step 3 — define the edge now, node comes next).

**2e. Test**
Run all 5 invoices from `data/invoices/` through the graph up through 
`decide_node`. Print the resulting state for each, especially `decision` and 
`reasoning`. Confirm output matches `data/SCENARIO_KEY.md` expectations (INV-1001 
auto-approves; INV-1002, 1004, 1005 flag; INV-1003 will also flag at this stage, 
since memory isn't populated yet — that's expected until Step 3/4 are wired in).

---

## STEP 3 — Human-in-the-loop node + resolution memory write

**3a. Build `human_review_node` using LangGraph's `interrupt()`**
When the graph reaches this node for a flagged invoice, it pauses and surfaces: 
vendor, item, invoice price, PO price, variance %, `reasoning`, and 
`prior_resolution` (if any, for context). This is what the review queue UI 
(Step 4) will read and display.

**3b. Build `record_resolution_node`**
Runs after the graph is resumed with a human's input 
(`approved: bool, resolved_price: float, resolver_name: str, reason: str`):
- If approved: inserts a new row into `resolutions` (vendor, item, resolved_price, 
  resolver_name, reason, `date_resolved` = today).
- Sets `decision = "resolved"`.
- Appends the human's reason to `reasoning`, so the final reasoning shows the full 
  history: why it was flagged, and how it was resolved.

**3c. Wire `record_resolution_node -> END`.**

**3d. Test**
Manually resume an interrupted run for INV-1002 with a test approval 
(`resolved_price=190.00, reason="Approved — substitute model due to unavailability, 
this is now the standard price for this vendor/item"`). Confirm a new row appears 
in `resolutions` matching this. Re-run the graph on INV-1003 and confirm it now 
hits the memory-match path in `decide_node` and auto-approves, citing the INV-1002 
resolution.

---

## STEP 4 — Review queue (Streamlit UI wired to the graph)

Build a Streamlit app (`app/review_queue.py`) that:
- Imports the compiled graph from `src/graph/build_graph.py`.
- Runs the graph for each invoice in `data/invoices/`, **in order** (INV-1001 
  through INV-1005), so resolving INV-1002 happens before INV-1003 is processed.
- Displays auto-approved invoices in an "Auto-Approved" list with their reasoning.
- Displays flagged/interrupted invoices in a "Needs Review" list, showing 
  reasoning, with an approve button and a required text input for the resolver's 
  reason.
- On approve, resumes the graph's interrupted state with the human's input 
  (LangGraph's `Command(resume=...)` pattern), triggering `record_resolution_node`.
- Refreshes the display after resuming so the resolved invoice moves out of 
  "Needs Review" and into a resolved/approved view.
- Frame this as **"buyer review,"** not generic AP review, in the UI copy.

---

## STEP 5 — Mini-eval

Build `eval/mini_eval.py`, importing the same compiled graph. Run all 5 invoices 
through the full graph twice:
1. **Without memory**: clear the `resolutions` table first. For any interrupt, 
   auto-resume with a stand-in "leave flagged, do not approve" response so the run 
   completes without a live human. Record each invoice's decision.
2. **With memory**: pre-populate `resolutions` with the INV-1002 resolution 
   (simulating the human step having already happened), then run again.

Print a before/after comparison table: for each invoice, the decision in each run, 
and whether it matches the expected outcome in `data/SCENARIO_KEY.md`. This is 
your measurable "it learns" evidence for the demo.

---

## Updated project structure (reflects Step 2's actual folding-in of existing code)

```
ppv-memory/
├── PLAN.md
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── ppv_memory.db
│   ├── invoices/ (INV-1001.txt ... INV-1005.txt)
│   └── SCENARIO_KEY.md
├── scripts/
│   └── generate_data.py
├── src/
│   ├── graph/
│   │   ├── state.py
│   │   ├── nodes.py        # extract_node (wraps existing extraction logic),
│   │   │                   # lookup_node, decide_node, human_review_node,
│   │   │                   # record_resolution_node
│   │   └── build_graph.py  # wires nodes + edges, exposes compiled `graph`
│   ├── db.py
│   └── llm.py
├── app/
│   └── review_queue.py     # imports compiled graph, drives it via Streamlit
├── eval/
│   └── mini_eval.py        # imports compiled graph, runs with/without memory
└── tests/
    └── test_graph.py
```

## Build order
Process Steps 2 → 3 → 4 → 5 sequentially, merging each before starting the next — 
each depends on the prior step's output. Start with Step 2 now.