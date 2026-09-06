# Scenario Key — Ground Truth Verdicts

One correct final verdict per invoice, independent of which eval pass it's
evaluated in (see `eval/mini_eval.py`, docs/BUILD_PLAN.md Step 5).

| Invoice  | Expected Verdict | Rationale |
|----------|-------------------|-----------|
| INV-1001 | `auto_approve` | Exact match to PO-4001 ($180). |
| INV-1002 | `auto_approve` | Legitimate substitution-driven price increase ($190 vs $180 PO); correct end-state once resolved. |
| INV-1003 | `auto_approve` | Repeat of the same vendor/item/price as INV-1002; should reuse that resolution. |
| INV-1004 | `flag` | Different vendor/item (standing desk), no precedent, genuinely needs a human. |
| INV-1005 | `flag` | Same vendor/item as INV-1002 but a larger, unresolved variance (13.9% vs the ~5.5% that was approved) — new information, correctly still escalated. |
