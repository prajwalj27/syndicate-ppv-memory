"""PDF invoice generator for PPV Memory.

Renders the same synthetic invoice scenarios used by generate_data.py
(see that module for the source-of-truth values) into PDF files via a
Jinja2 HTML template and WeasyPrint, so the extraction pipeline can be
exercised against PDF invoices alongside the existing .txt ones.

Safe to re-run: recreates data/invoices_pdf/*.pdf from scratch each time.

Usage:
    python scripts/generate_pdf_invoices.py
"""

import os

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from generate_data import INVOICES, PURCHASE_ORDERS, VENDOR_ADDRESS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
DATA_DIR = os.path.join(BASE_DIR, "data")
PDF_INVOICES_DIR = os.path.join(DATA_DIR, "invoices_pdf")


def generate_pdf_invoices():
    if os.path.exists(PDF_INVOICES_DIR):
        for name in os.listdir(PDF_INVOICES_DIR):
            os.remove(os.path.join(PDF_INVOICES_DIR, name))
    else:
        os.makedirs(PDF_INVOICES_DIR, exist_ok=True)

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("invoice_template.html")

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

        html = template.render(
            vendor=vendor,
            vendor_address=VENDOR_ADDRESS,
            invoice_number=inv["invoice_number"],
            invoice_date=inv["invoice_date"],
            po_number=inv["po_number"],
            item=item,
            quantity=quantity,
            unit_price=f"{unit_price:.2f}",
            line_total=f"{line_total:.2f}",
            subtotal=f"{subtotal:.2f}",
            tax="0.00",
            total=f"{total:.2f}",
            note=inv["note"],
            remit_to=f"{vendor}, Accounts Receivable",
            terms="Net 30",
        )

        file_path = os.path.join(PDF_INVOICES_DIR, f"{inv['invoice_number']}.pdf")
        HTML(string=html, base_url=TEMPLATES_DIR).write_pdf(file_path)


def print_summary():
    pdf_count = len(
        [f for f in os.listdir(PDF_INVOICES_DIR) if f.endswith(".pdf")]
    )
    print("PPV Memory PDF invoice generation complete.")
    print(f"  PDF invoice files generated: {pdf_count} (in {PDF_INVOICES_DIR})")


def main():
    generate_pdf_invoices()
    print_summary()


if __name__ == "__main__":
    main()
