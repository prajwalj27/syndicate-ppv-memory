"""Synthetic data generator for PPV Memory.

Creates the SQLite database (purchase_orders + empty resolutions table)
and a set of plain-text invoice files used to demo purchase price
variance detection and the resolution-memory workflow.

Safe to re-run: recreates the DB and invoice files from scratch each time.
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "ppv_memory.db")
INVOICES_DIR = os.path.join(DATA_DIR, "invoices")

VENDOR_ADDRESS = "220 Industrial Pkwy, Newark, NJ 07102"

PURCHASE_ORDERS = [
    {
        "po_number": "PO-4001",
        "vendor": "Meridian Office Supply",
        "item": "Ergonomic Office Chair (Model ErgoFlex-200)",
        "quantity": 20,
        "unit_price": 180.00,
        "date_issued": "2026-07-01",
    },
    {
        "po_number": "PO-4002",
        "vendor": "Meridian Office Supply",
        "item": "Standing Desk (Model RiseUp-Pro)",
        "quantity": 5,
        "unit_price": 350.00,
        "date_issued": "2026-07-05",
    },
    {
        "po_number": "PO-5001",
        "vendor": "Brightline Logistics",
        "item": "Freight Shipping — Standard Route",
        "quantity": 1,
        "unit_price": 2200.00,
        "date_issued": "2026-07-08",
    },
    {
        "po_number": "PO-5002",
        "vendor": "Brightline Logistics",
        "item": "Warehousing Fee — Monthly",
        "quantity": 1,
        "unit_price": 450.00,
        "date_issued": "2026-07-10",
    },
    {
        "po_number": "PO-6001",
        "vendor": "Crestpoint IT Services",
        "item": "Managed IT Support — Monthly Retainer",
        "quantity": 1,
        "unit_price": 3000.00,
        "date_issued": "2026-07-12",
    },
]

INVOICES = [
    {
        "invoice_number": "INV-1001",
        "invoice_date": "2026-07-15",
        "po_number": "PO-4001",
        "quantity": 20,
        "unit_price": 180.00,
        "note": None,
    },
    {
        "invoice_number": "INV-1002",
        "invoice_date": "2026-07-22",
        "po_number": "PO-4001",
        "quantity": 20,
        "unit_price": 190.00,
        "note": (
            "Note: Original ErgoFlex-200 model was on backorder; "
            "substituted with ErgoFlex-200S at time of shipment."
        ),
    },
    {
        "invoice_number": "INV-1003",
        "invoice_date": "2026-08-10",
        "po_number": "PO-4001",
        "quantity": 15,
        "unit_price": 190.00,
        "note": None,
    },
    {
        "invoice_number": "INV-1004",
        "invoice_date": "2026-08-12",
        "po_number": "PO-4002",
        "quantity": 5,
        "unit_price": 370.00,
        "note": None,
    },
    {
        "invoice_number": "INV-1005",
        "invoice_date": "2026-08-28",
        "po_number": "PO-4001",
        "quantity": 20,
        "unit_price": 205.00,
        "note": None,
    },
    {
        "invoice_number": "INV-2001",
        "invoice_date": "2026-07-15",
        "po_number": "PO-5001",
        "quantity": 1,
        "unit_price": 2200.00,
        "note": None,
    },
    {
        "invoice_number": "INV-2002",
        "invoice_date": "2026-07-22",
        "po_number": "PO-5001",
        "quantity": 1,
        "unit_price": 2321.00,
        "note": (
            "Note: Fuel surcharge applied at time of shipment; not reflected "
            "in original PO."
        ),
    },
    {
        "invoice_number": "INV-2003",
        "invoice_date": "2026-08-10",
        "po_number": "PO-5001",
        "quantity": 1,
        "unit_price": 2321.00,
        "note": None,
    },
    {
        "invoice_number": "INV-2004",
        "invoice_date": "2026-08-15",
        "po_number": "PO-5002",
        "quantity": 1,
        "unit_price": 475.00,
        "note": None,
    },
    {
        "invoice_number": "INV-3001",
        "invoice_date": "2026-07-19",
        "po_number": "PO-6001",
        "quantity": 1,
        "unit_price": 3000.00,
        "note": None,
    },
    {
        "invoice_number": "INV-3002",
        "invoice_date": "2026-07-26",
        "po_number": "PO-6001",
        "quantity": 1,
        "unit_price": 3063.00,
        "note": None,
    },
    {
        "invoice_number": "INV-3003",
        "invoice_date": "2026-08-11",
        "po_number": "PO-6001",
        "quantity": 1,
        "unit_price": 3054.00,
        "note": None,
    },
]


def setup_database():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE purchase_orders (
            po_number TEXT PRIMARY KEY,
            vendor TEXT NOT NULL,
            item TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            date_issued TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE resolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT NOT NULL,
            item TEXT NOT NULL,
            resolved_price REAL NOT NULL,
            resolved_by TEXT NOT NULL,
            reason TEXT NOT NULL,
            date_resolved TEXT NOT NULL
        )
        """
    )

    for po in PURCHASE_ORDERS:
        cur.execute(
            """
            INSERT INTO purchase_orders
                (po_number, vendor, item, quantity, unit_price, date_issued)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                po["po_number"],
                po["vendor"],
                po["item"],
                po["quantity"],
                po["unit_price"],
                po["date_issued"],
            ),
        )

    conn.commit()
    conn.close()


def generate_invoices():
    if os.path.exists(INVOICES_DIR):
        for name in os.listdir(INVOICES_DIR):
            os.remove(os.path.join(INVOICES_DIR, name))
    else:
        os.makedirs(INVOICES_DIR, exist_ok=True)

    po_by_number = {po["po_number"]: po for po in PURCHASE_ORDERS}

    for inv in INVOICES:
        po = po_by_number[inv["po_number"]]
        vendor = po["vendor"]
        item = po["item"]
        quantity = inv["quantity"]
        unit_price = inv["unit_price"]
        line_total = quantity * unit_price
        subtotal = line_total
        total = subtotal

        lines = [
            "INVOICE",
            f"Invoice Number: {inv['invoice_number']}",
            f"Invoice Date: {inv['invoice_date']}",
            f"Vendor: {vendor}",
            f"Vendor Address: {VENDOR_ADDRESS}",
            f"PO Reference: {inv['po_number']}",
            "",
            "Line Items:",
            f"- {item} x {quantity} @ ${unit_price:.2f} = ${line_total:.2f}",
            "",
            f"Subtotal: ${subtotal:.2f}",
            "Tax: $0.00",
            f"Total Due: ${total:.2f}",
            "Payment Terms: Net 30",
            f"Remit To: {vendor}, Accounts Receivable",
        ]

        if inv["note"]:
            lines.append(inv["note"])

        content = "\n".join(lines) + "\n"

        file_path = os.path.join(INVOICES_DIR, f"{inv['invoice_number']}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


def print_summary():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM purchase_orders")
    po_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM resolutions")
    resolution_count = cur.fetchone()[0]
    conn.close()

    invoice_count = len(
        [f for f in os.listdir(INVOICES_DIR) if f.endswith(".txt")]
    )

    print("PPV Memory synthetic data generation complete.")
    print(f"  Purchase orders created: {po_count}")
    print(f"  Invoice files generated: {invoice_count} (in {INVOICES_DIR})")
    print(
        f"  Resolutions table exists and is empty: "
        f"{'yes' if resolution_count == 0 else 'no'} "
        f"({resolution_count} rows)"
    )
    print(f"  Database written to: {DB_PATH}")


def main():
    setup_database()
    generate_invoices()
    print_summary()


if __name__ == "__main__":
    main()
