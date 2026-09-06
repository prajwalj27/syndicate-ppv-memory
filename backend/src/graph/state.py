"""Shared graph state definition for the PPV Memory pipeline.

See docs/BUILD_PLAN.md (Step 2b) for the full graph design.
"""

from __future__ import annotations

from typing import TypedDict


class PPVState(TypedDict):
    invoice_file: str
    extracted_data: dict | None
    po_record: dict | None
    variance_pct: float | None
    prior_resolution: dict | None
    decision: str | None
    reasoning: str | None
    human_resolution: dict | None
