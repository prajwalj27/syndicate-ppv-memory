"""Shared SQLite helpers for data/ppv_memory.db.

Minimal query helpers needed by src/graph/nodes.py's lookup_node. See
docs/BUILD_PLAN.md (Step 2c) and scripts/generate_data.py for the schema.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ppv_memory.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_po(po_number: str) -> dict[str, Any] | None:
    """Fetch a purchase order by po_number, or None if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM purchase_orders WHERE po_number = ?",
            (po_number,),
        ).fetchone()
    return dict(row) if row else None


def get_latest_resolution(vendor: str, item: str) -> dict[str, Any] | None:
    """Fetch the most recent resolution for a vendor+item, or None."""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM resolutions
            WHERE vendor = ? AND item = ?
            ORDER BY date_resolved DESC
            LIMIT 1
            """,
            (vendor, item),
        ).fetchone()
    return dict(row) if row else None
