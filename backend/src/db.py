"""Shared SQLite helpers for data/ppv_memory.db.

Minimal query helpers needed by src/graph/nodes.py's lookup_node. See
docs/BUILD_PLAN.md (Step 2c) and scripts/generate_data.py for the schema.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ppv_memory.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoice_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_filename TEXT NOT NULL,
            status TEXT NOT NULL,
            state_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
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


def insert_resolution(
    vendor: str,
    item: str,
    resolved_price: float,
    resolved_by: str,
    reason: str,
    date_resolved: str,
) -> None:
    """Insert a new resolution row for a vendor+item."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO resolutions (vendor, item, resolved_price, resolved_by, reason, date_resolved)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (vendor, item, resolved_price, resolved_by, reason, date_resolved),
        )


def reset_resolutions() -> None:
    """Delete all rows from the resolutions table, for a clean demo run."""
    with _connect() as conn:
        conn.execute("DELETE FROM resolutions")


def insert_invoice_record(invoice_filename: str, status: str, state: dict[str, Any], created_at: str) -> int:
    """Store a triggered invoice's graph state as a new invoice_records row.

    Returns the new row's autoincrement id.
    """
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO invoice_records (invoice_filename, status, state_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (invoice_filename, status, json.dumps(state), created_at),
        )
        return cursor.lastrowid


def get_invoice_record(record_id: int) -> dict[str, Any] | None:
    """Fetch one invoice_records row by id, with state_json parsed, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM invoice_records WHERE id = ?",
            (record_id,),
        ).fetchone()
    if row is None:
        return None
    record = dict(row)
    record["state"] = json.loads(record.pop("state_json"))
    return record


def list_invoice_records() -> list[dict[str, Any]]:
    """Fetch all invoice_records rows, with state_json parsed, oldest first."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM invoice_records ORDER BY id").fetchall()
    records = []
    for row in rows:
        record = dict(row)
        record["state"] = json.loads(record.pop("state_json"))
        records.append(record)
    return records


def update_invoice_record(record_id: int, status: str, state: dict[str, Any]) -> None:
    """Update an invoice_records row's status and state_json in place."""
    with _connect() as conn:
        conn.execute(
            "UPDATE invoice_records SET status = ?, state_json = ? WHERE id = ?",
            (status, json.dumps(state), record_id),
        )
