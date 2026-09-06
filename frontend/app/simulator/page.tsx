"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL, triggerInvoice, type InvoiceStatus } from "@/lib/api";
import { STATUS_LABELS } from "@/components/StatusBadge";

type InvoiceSummary = {
  vendor: string;
  item: string;
  quantity: number;
  unitPrice: number;
  poReference: string;
};

const INVOICE_SUMMARIES: Record<string, InvoiceSummary> = {
  "INV-1001": {
    vendor: "Meridian Office Supply",
    item: "Ergonomic Office Chair (Model ErgoFlex-200)",
    quantity: 20,
    unitPrice: 180.0,
    poReference: "PO-4001",
  },
  "INV-1002": {
    vendor: "Meridian Office Supply",
    item: "Ergonomic Office Chair (substituted ErgoFlex-200S)",
    quantity: 20,
    unitPrice: 190.0,
    poReference: "PO-4001",
  },
  "INV-1003": {
    vendor: "Meridian Office Supply",
    item: "Ergonomic Office Chair (Model ErgoFlex-200)",
    quantity: 15,
    unitPrice: 190.0,
    poReference: "PO-4001",
  },
  "INV-1004": {
    vendor: "Meridian Office Supply",
    item: "Standing Desk (Model RiseUp-Pro)",
    quantity: 5,
    unitPrice: 370.0,
    poReference: "PO-4002",
  },
  "INV-1005": {
    vendor: "Meridian Office Supply",
    item: "Ergonomic Office Chair (Model ErgoFlex-200)",
    quantity: 20,
    unitPrice: 205.0,
    poReference: "PO-4001",
  },
  "INV-2001": {
    vendor: "Brightline Logistics",
    item: "Freight Shipping — Standard Route",
    quantity: 1,
    unitPrice: 2200.0,
    poReference: "PO-5001",
  },
  "INV-2002": {
    vendor: "Brightline Logistics",
    item: "Freight Shipping — Standard Route",
    quantity: 1,
    unitPrice: 2321.0,
    poReference: "PO-5001",
  },
  "INV-2003": {
    vendor: "Brightline Logistics",
    item: "Freight Shipping — Standard Route",
    quantity: 1,
    unitPrice: 2321.0,
    poReference: "PO-5001",
  },
  "INV-2004": {
    vendor: "Brightline Logistics",
    item: "Warehousing Fee — Monthly",
    quantity: 1,
    unitPrice: 475.0,
    poReference: "PO-5002",
  },
  "INV-3001": {
    vendor: "Crestpoint IT Services",
    item: "Managed IT Support — Monthly Retainer",
    quantity: 1,
    unitPrice: 3000.0,
    poReference: "PO-6001",
  },
  "INV-3002": {
    vendor: "Crestpoint IT Services",
    item: "Managed IT Support — Monthly Retainer",
    quantity: 1,
    unitPrice: 3063.0,
    poReference: "PO-6001",
  },
  "INV-3003": {
    vendor: "Crestpoint IT Services",
    item: "Managed IT Support — Monthly Retainer",
    quantity: 1,
    unitPrice: 3054.0,
    poReference: "PO-6001",
  },
};

const SCENARIO_NOTES: Record<string, string> = {
  "INV-1001":
    "Baseline invoice — the price matches PO-4001 exactly ($180). A clean control case with no variance.",
  "INV-1002":
    "First-time price variance for this vendor/item — a mid-shipment product substitution pushed the price up ($190 vs $180 PO). No prior resolution exists yet for this pair.",
  "INV-1003":
    "Repeat of the same vendor/item/price as INV-1002, arriving after that invoice would already have been resolved — tests whether a prior resolution gets reused instead of re-flagging.",
  "INV-1004":
    "A different item (standing desk) from the same vendor, with no purchase history or precedent — a genuinely novel case that needs human judgment.",
  "INV-1005":
    "Same vendor/item as INV-1002, but a much larger variance (13.9% vs. the ~5.5% previously seen) — new information that shouldn't be waved through by the earlier precedent.",
  "INV-2001":
    "Baseline invoice for a second vendor — the price matches PO-5001 exactly ($2200).",
  "INV-2002":
    "A fuel surcharge pushes the price up ($2321 vs $2200 PO, +5.5%, above the 2% tolerance band) — first variance seen for this vendor/item, no prior resolution yet.",
  "INV-2003":
    "Repeat of the same vendor/item/price as INV-2002 — tests whether a prior resolution gets reused.",
  "INV-2004":
    "A different item (monthly warehousing fee) for the same vendor as INV-2002/2003, with its own variance (+5.6%) — tests that memory doesn't over-generalize a resolution across items for the same vendor.",
  "INV-3001":
    "Baseline invoice for a third vendor — the price matches PO-6001 exactly ($3000).",
  "INV-3002":
    "A retainer rate increase ($3063 vs $3000 PO, +2.1%) — just above the 2% auto-approval tolerance band, and the first variance seen for this vendor/item.",
  "INV-3003":
    "Variance ($3054 vs $3000 PO, +1.8%) falls inside the 2% tolerance band — tests the auto-approval tolerance threshold directly, independent of resolution history.",
};

const INVOICE_NUMBERS = Object.keys(INVOICE_SUMMARIES);

type FileFormat = "txt" | "pdf";

function invoiceNumberOf(filename: string): string {
  return filename.replace(/\.(txt|pdf)$/i, "");
}

function formatOf(filename: string): FileFormat {
  return filename.toLowerCase().endsWith(".pdf") ? "pdf" : "txt";
}

type LoadedDoc =
  | { filename: string; text: string; error?: undefined }
  | { filename: string; text?: undefined; error: string };

export default function SimulatorPage() {
  const [selectedFilename, setSelectedFilename] = useState(`${INVOICE_NUMBERS[0]}.txt`);
  const [loadedDoc, setLoadedDoc] = useState<LoadedDoc | null>(null);

  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [sendResult, setSendResult] = useState<{ filename: string; status: InvoiceStatus } | null>(
    null
  );

  const invoiceNumber = invoiceNumberOf(selectedFilename);
  const format = formatOf(selectedFilename);
  const summary = INVOICE_SUMMARIES[invoiceNumber];
  const notes = SCENARIO_NOTES[invoiceNumber];

  const documentLoading = format === "txt" && loadedDoc?.filename !== selectedFilename;
  const documentText = loadedDoc?.filename === selectedFilename ? loadedDoc.text ?? null : null;
  const documentError = loadedDoc?.filename === selectedFilename ? loadedDoc.error ?? null : null;

  useEffect(() => {
    if (format !== "txt") {
      return;
    }

    let ignore = false;

    fetch(`${API_BASE_URL}/static/invoices/${selectedFilename}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${selectedFilename}: ${res.status}`);
        return res.text();
      })
      .then((text) => {
        if (!ignore) setLoadedDoc({ filename: selectedFilename, text });
      })
      .catch((err) => {
        if (!ignore) {
          const message = err instanceof Error ? err.message : "Failed to load document";
          setLoadedDoc({ filename: selectedFilename, error: message });
        }
      });

    return () => {
      ignore = true;
    };
  }, [selectedFilename, format]);

  function handleSelect(filename: string) {
    setSelectedFilename(filename);
    setSendResult(null);
    setSendError(null);
  }

  async function handleSend() {
    setSending(true);
    setSendError(null);
    setSendResult(null);
    const txtFilename = `${invoiceNumber}.txt`;
    try {
      const invoice = await triggerInvoice(txtFilename);
      setSendResult({ filename: txtFilename, status: invoice.status });
    } catch (err) {
      setSendError(err instanceof Error ? err.message : "Failed to send invoice");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
          Vendor Invoice Simulator
        </h1>
        <p className="text-sm text-zinc-500">
          Stand-in for the external system that sends invoices into PPV Memory. Pick a
          document, review it, and send it into the pipeline.
        </p>
      </header>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* LEFT: control panel */}
        <section className="flex flex-col gap-4">
          <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
            <label
              htmlFor="invoice-file"
              className="block text-xs font-medium uppercase tracking-wide text-zinc-500"
            >
              Invoice file
            </label>
            <select
              id="invoice-file"
              value={selectedFilename}
              onChange={(e) => handleSelect(e.target.value)}
              className="mt-2 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
            >
              {INVOICE_NUMBERS.map((num) => (
                <optgroup key={num} label={`${num} (${INVOICE_SUMMARIES[num].vendor})`}>
                  <option value={`${num}.txt`}>Text (.txt)</option>
                  <option value={`${num}.pdf`}>PDF (.pdf)</option>
                </optgroup>
              ))}
            </select>

            <button
              onClick={handleSend}
              disabled={sending}
              className="mt-3 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {sending ? "Sending…" : "Send Invoice"}
            </button>

            {sendResult && (
              <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                Sent — {sendResult.filename} is now{" "}
                {STATUS_LABELS[sendResult.status].toLowerCase()}.
              </p>
            )}
            {sendError && (
              <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {sendError}
              </p>
            )}
          </div>

          {summary && (
            <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
              <h2 className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                Invoice summary
              </h2>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-zinc-500">Vendor</dt>
                  <dd className="mt-0.5 text-zinc-900">{summary.vendor}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-zinc-500">PO reference</dt>
                  <dd className="mt-0.5 text-zinc-900">{summary.poReference}</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-xs uppercase tracking-wide text-zinc-500">Item</dt>
                  <dd className="mt-0.5 text-zinc-900">{summary.item}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-zinc-500">Quantity</dt>
                  <dd className="mt-0.5 tabular-nums text-zinc-900">{summary.quantity}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-zinc-500">Unit price</dt>
                  <dd className="mt-0.5 tabular-nums text-zinc-900">
                    ${summary.unitPrice.toFixed(2)}
                  </dd>
                </div>
              </dl>
            </div>
          )}

          {notes && (
            <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 shadow-sm">
              <h2 className="text-xs font-medium uppercase tracking-wide text-indigo-500">
                Scenario notes
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-indigo-900">{notes}</p>
            </div>
          )}
        </section>

        {/* RIGHT: document view */}
        <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
          <h2 className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            Document preview — {selectedFilename}
          </h2>

          <div className="mt-3">
            {format === "pdf" ? (
              <iframe
                key={selectedFilename}
                src={`${API_BASE_URL}/static/invoices_pdf/${selectedFilename}`}
                title={selectedFilename}
                className="h-[600px] w-full rounded-lg border border-zinc-200"
              />
            ) : documentLoading ? (
              <p className="py-10 text-center text-sm text-zinc-400">Loading…</p>
            ) : documentError ? (
              <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {documentError}
              </p>
            ) : (
              <pre className="max-h-[600px] overflow-auto whitespace-pre-wrap rounded-lg border border-zinc-200 bg-zinc-50 p-4 font-mono text-sm leading-relaxed text-zinc-800">
                {documentText}
              </pre>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
