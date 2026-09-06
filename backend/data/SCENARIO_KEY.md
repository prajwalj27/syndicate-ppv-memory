# Scenario Key — Ground Truth Verdicts

One correct final verdict per invoice, independent of which eval pass it's
evaluated in (see `eval/mini_eval.py`, `eval/mini_eval_extended.py`,
docs/BUILD_PLAN.md Step 5).

| Invoice  | Expected Verdict | Rationale |
|----------|-------------------|-----------|
| INV-1001 | `auto_approve` | Exact match to PO-4001 ($180). |
| INV-1002 | `auto_approve` | Legitimate substitution-driven price increase ($190 vs $180 PO); correct end-state once resolved. |
| INV-1003 | `auto_approve` | Repeat of the same vendor/item/price as INV-1002; should reuse that resolution. |
| INV-1004 | `flag` | Different vendor/item (standing desk), no precedent, genuinely needs a human. |
| INV-1005 | `flag` | Same vendor/item as INV-1002 but a larger, unresolved variance (13.9% vs the ~5.5% that was approved) — new information, correctly still escalated. |
| INV-2001 | `auto_approve` | Exact match to PO-5001 ($2200). |
| INV-2002 | `auto_approve` | Fuel surcharge price increase ($2321 vs $2200 PO, +5.5%, above the 2% tolerance); correct end-state once resolved. |
| INV-2003 | `auto_approve` | Repeat of the same vendor/item/price as INV-2002; should reuse that resolution. |
| INV-2004 | `flag` | Different item (monthly warehousing fee, not freight shipping) for the same vendor as INV-2002/2003, no precedent for this item, and its own variance (+5.6%) is above tolerance — proves memory doesn't over-generalize across items for the same vendor. |
| INV-3001 | `auto_approve` | Exact match to PO-6001 ($3000). |
| INV-3002 | `auto_approve` | Retainer rate increase ($3063 vs $3000 PO, +2.1%, just above the 2% tolerance); correct end-state once resolved. |
| INV-3003 | `auto_approve` | Variance ($3054 vs $3000 PO, +1.8%) is within the 2% auto-approval tolerance band; approved on tolerance alone, no prior resolution needed. |
