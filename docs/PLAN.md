# PPV Memory — Implementation Plan
### A Purchase Price Variance (PPV) agent | Syndicate by Maximor Hackathon — Track 2: Autonomous Office of the CFO

**Project name: PPV Memory** — plain and unambiguous about what it does: it's an agent for Purchase Price Variance handling that remembers past buyer resolutions and applies them automatically to matching future cases.

**STATUS: Problem locked in.** After exploring invoice processing broadly, then weighing price-variance vs. duplicate-invoice detection, this plan commits to **purchase price variance (PPV) handling with a human-resolution learning loop** as the single, deep scenario to build and demo.

---

## 1. The Problem — Stated Plainly

**The pain point:** When a recurring vendor's invoice arrives priced above what the purchase order (PO) says, someone has to manually decide: is this a real problem, or a legitimate change that was already approved but never reflected in the PO? Right now, that judgment gets made fresh every time, by whoever happens to review it, with no memory of what was decided last time for that vendor/item.

**Why this is real** (not invented — grounded in actual industry mechanics found during research):
- A very common real-world mechanism: a buyer verbally/informally approves a substitute item or a price change (e.g. original item unavailable, approved a pricier substitute) — but nobody updates the PO to reflect it. The next invoice at the new price then reads as a "variance" even though it's already been legitimately resolved once.
- Industry data: price variance is a meaningful share of all AP exceptions (cited around 8-12%), taking ~20-30 minutes to resolve manually per instance.
- Real tolerance-banding used in practice (a reasonable structure to mirror, not invent from scratch): **under 2% auto-approve, 2-5% routes to the AP/purchasing manager, above 5% (or any quantity mismatch) routes to a controller.**
- Critically: a price variance is properly resolved by **the buyer/procurement person who negotiated the deal** — not a generic AP clerk — because they're the one who knows *why* the price changed. Your review queue should reflect this (route to "the buyer," not generic "reviewer").
- Industry framing (Peakflo) directly validates the shift you're building: legacy automation is rigid ("if variance exceeds 5%, route to manager"); modern agentic systems instead learn acceptable variance patterns from historical data and autonomously approve invoices resembling previously approved exceptions. This is your project's thesis, already articulated by the industry — a good, honest line to use in the demo.

**One-line pitch:** "When a vendor's invoice comes in above the PO price, someone always has to decide: is this normal, already-approved drift, or a real problem? My agent remembers what a buyer decided last time and only interrupts a human when something is genuinely new."

---

## 2. Judging Context (why this scenario, specifically)

### Official Track 2 rubric (from organizers)
Judged on: genuine pain-point relevance, intuitiveness of the human-judgment modeling, depth of thought for this specific workflow, and real-world groundedness — not novelty of tech stack.

**Organizer build guidance:**
- Plan and rehearse the demo — don't build it last-minute. **3 minutes is very little time.**
- Skip anything not core to the idea (no auth/login/2FA/etc.).
- Spend more time planning the idea than building.
- Reference material provided: Anthropic's "Demystifying evals for AI agents" and "Writing tools for agents," Claude's managed-agents docs, Maximor's own YouTube/site.

### Insider feedback (Maximor engineer, met in person at the NYC venue)
- Go deep on one real problem, not broad feature coverage — no "vibe-coded" pipelines.
- The demo is the most important deliverable; 3 minutes forces radical focus.
- **The single most emphasized point**: the agent must learn from how a human resolves an exception and apply that resolution automatically to matching future cases. This is the centerpiece of the whole build, not a nice-to-have.

### Two build techniques adopted from Anthropic's reference material
- **Design tools around the workflow, not the API.** One consolidated tool, e.g. `evaluate_invoice_against_vendor_history(invoice_id)`, that returns PO match + variance + prior resolutions in one call — mirroring how a buyer actually pulls context together — rather than several thin lookup tools the agent has to chain itself.
- **Build a tiny eval, not just a demo.** 3-5 invoice scenarios with a known "correct" verdict, run once *without* the memory feature and once *with* it, gives a real, measurable before/after claim ("without memory: 3/5 correctly resolved; with memory: 5/5") — more credible than asserting "it learns."

---

## 3. End-to-End Workflow

1. **Invoice arrives** (folder upload — simplest intake for demo) with a price above its PO
2. **Agent evaluates**: pulls the PO, calculates variance %, checks memory for this vendor+item combination
3. **First time seeing this vendor/item variance** → flags it, routes to **the buyer who placed the original PO** (not generic AP review), with specific reasoning: *"Invoice price $190/unit vs. PO price $180/unit for [item], 5.5% over threshold. No prior resolution on file for this vendor/item."*
4. **Buyer resolves it** with a real, one-line reason (e.g. "Approved — substitute model due to unavailability, this is now the standard price for this vendor/item")
5. **Agent stores the resolution**, keyed to vendor + item (or vendor + item + price band)
6. **A later invoice** from the same vendor for the same item at the same (now-approved) price arrives → agent auto-approves, citing the prior resolution in its reasoning: *"Consistent with prior approval on [date]: 'substitute model due to unavailability.' Auto-approved, no review needed."*
7. **A genuinely new variance** (different item, or a further price increase beyond what was approved) → flags again, since it's new information, not something already resolved

### Demo script — 3 minutes, single scenario
1. (~20s) State the problem: "When a vendor's invoice comes in above the PO price, someone has to decide if it's a real problem or already-approved drift — and that decision gets made fresh every time, with no memory."
2. (~40s) Show the invoice come in, get flagged, with the agent's specific reasoning displayed (item, amounts, %, "no prior resolution on file")
3. (~40s) Show the buyer resolve it in the review queue with a one-line real reason
4. (~40s) Show a new invoice, same vendor/item/price → agent auto-approves, explicitly citing the prior resolution as justification
5. (~20s) Brief close on the AO Kanban / build process — required for judging, keep it short so it doesn't eat into the core scenario
**Rehearse to fit in 3 minutes before the deadline.** Cut anything that doesn't serve this exact arc.

---

## 4. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Orchestration framework | **LangGraph** | Native fit for a linear pipeline with a human-review branch; interrupts are a first-class primitive |
| LLM | **Claude (Sonnet)** via API, or **Tensormux (GLM-4.7-Flash)** for high-volume calls | Tensormux is free for the hackathon (50M tokens, OpenAI-compatible endpoint) — good for extraction/bulk calls; reserve Claude for the highest-stakes reasoning (the final decision/reasoning shown to the human) |
| Backend | **Python + FastAPI** | Fast to expose pipeline as endpoints; AO workers default to this well |
| Data store | **SQLite** | Zero setup; enough for mock POs, vendor/item resolution history, review decisions |
| Document parsing | **PyPDF/pdfplumber** for PDFs; plain parsing for text/email | Not solving OCR — demonstrating a workflow |
| Review queue UI | **Streamlit** (or simple React page) | Working reviewer UI (flagged invoice + reasoning + approve/override) in under an hour |

**Fallback rule:** if LangGraph setup eats more than 2-3 hours without results, drop to a plain Python pipeline (functions calling functions). A working plain-Python demo beats an unfinished LangGraph one.

**Tool design:** one consolidated tool, e.g. `evaluate_invoice_against_vendor_history(invoice_id)`, returning PO match + variance % + any prior resolution for this vendor/item — not separate thin tools the agent has to chain.

---

## 5. Feature List & Build Order

### Must-have (build first, in this order)
1. Synthetic invoice + PO generator — small set (~6-10 pairs) specifically crafted around price variance: some within tolerance, some over, some repeats of an already-resolved vendor/item combo
2. Extraction step (invoice → structured JSON: vendor, item, PO#, unit price, quantity)
3. Mock PO database + vendor/item resolution-history store (SQLite)
4. Variance calculation + decision step (auto-approve / flag / reject, using the 2% / 2-5% / 5%+ tolerance bands as a starting structure) with plain-language reasoning
5. **Vendor/item resolution memory** — the centerpiece: when a human resolves a flagged variance, store the resolution; check this memory before flagging future invoices for the same vendor/item
6. Review queue (shows flagged invoice, reasoning, prior history if any, approve/override) — framed as "buyer review," not generic AP review
7. **Mini-eval**: 3-5 scenarios with known-correct verdicts, run with/without the memory feature, to get a real before/after number for the demo

### Explicitly skip
No auth, login, 2FA, or user-management scaffolding — organizers said skip anything not core to the idea.

### Stretch (only if core is solid and rehearsed, roughly in order)
- Audit-trail-styled reasoning output (each decision written as a short compliance-style note)
- Vendor communication drafting (auto-draft, don't send, a clarifying email to the vendor for a flagged variance)
- Confidence-calibrated auto-approval (show a confidence score, let the buyer adjust the auto-approve threshold live)
- Cross-invoice pattern detection (flag a vendor trending upward across several invoices, not just one)

---

## 6. Wrap-up (do not skip)
- Public GitHub repo with README (what it does, how to run it, which track, what agent workflow, what improved across iterations, demo/live links)
- Demo video showing the pipeline running end-to-end **and** the AO Kanban/sessions used during the build
- Devpost submission before deadline (Discord post does not count as submission)

---

## 7. Networking Note
Maximor's own product already covers this exact workflow at production scale (AP is one of their live modules; their stated approach handles ~98% of work automatically, with the remaining ~2% as exceptions routed to humans and learned from). Frame this project honestly: not a claim to have out-built them, but a small, transparent, well-grounded demonstration of understanding their exact problem space — and a good opening for a real technical conversation with their team.