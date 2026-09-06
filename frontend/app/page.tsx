"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getInvoices, triggerInvoice, type Invoice, type InvoiceStatus } from "@/lib/api";

const KNOWN_INVOICE_FILES = [
  "INV-1001.txt",
  "INV-1002.txt",
  "INV-1003.txt",
  "INV-1004.txt",
  "INV-1005.txt",
];

const STATUS_BADGE_CLASSES: Record<InvoiceStatus, string> = {
  auto_approved: "bg-green-100 text-green-800",
  pending_review: "bg-yellow-100 text-yellow-800",
  resolved: "bg-blue-100 text-blue-800",
  rejected: "bg-red-100 text-red-800",
};

const STATUS_LABELS: Record<InvoiceStatus, string> = {
  auto_approved: "Auto-Approved",
  pending_review: "Pending Review",
  resolved: "Resolved",
  rejected: "Rejected",
};

function StatusBadge({ status }: { status: InvoiceStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

export default function Home() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState(KNOWN_INVOICE_FILES[0]);
  const [triggering, setTriggering] = useState(false);

  async function loadInvoices() {
    setError(null);
    try {
      const data = await getInvoices();
      setInvoices(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load invoices");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let ignore = false;

    getInvoices()
      .then((data) => {
        if (!ignore) setInvoices(data);
      })
      .catch((err) => {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Failed to load invoices");
        }
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, []);

  async function handleTrigger() {
    setTriggering(true);
    setError(null);
    try {
      await triggerInvoice(selectedFile);
      await loadInvoices();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to trigger invoice");
    } finally {
      setTriggering(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-zinc-900">PPV Memory Dashboard</h1>

      <div className="mt-6 flex items-center gap-3">
        <select
          value={selectedFile}
          onChange={(e) => setSelectedFile(e.target.value)}
          className="rounded border border-zinc-300 px-3 py-2 text-sm"
        >
          {KNOWN_INVOICE_FILES.map((file) => (
            <option key={file} value={file}>
              {file}
            </option>
          ))}
        </select>
        <button
          onClick={handleTrigger}
          disabled={triggering}
          className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {triggering ? "Triggering…" : "Trigger new invoice"}
        </button>
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      <div className="mt-8 overflow-hidden rounded border border-zinc-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-zinc-50 text-zinc-500">
            <tr>
              <th className="px-4 py-2 font-medium">Invoice #</th>
              <th className="px-4 py-2 font-medium">Vendor</th>
              <th className="px-4 py-2 font-medium">Item</th>
              <th className="px-4 py-2 font-medium">Variance %</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-zinc-500">
                  Loading…
                </td>
              </tr>
            ) : invoices.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-zinc-500">
                  No invoices yet. Trigger one above.
                </td>
              </tr>
            ) : (
              invoices.map((invoice) => (
                <tr key={invoice.id} className="hover:bg-zinc-50">
                  <td className="px-4 py-2">
                    <Link
                      href={`/invoice/${invoice.id}`}
                      className="font-medium text-zinc-900 underline-offset-2 hover:underline"
                    >
                      {(invoice.extracted_data?.invoice_number as string) ?? invoice.invoice_filename}
                    </Link>
                  </td>
                  <td className="px-4 py-2">{invoice.vendor}</td>
                  <td className="px-4 py-2">{invoice.item}</td>
                  <td className="px-4 py-2">{(invoice.variance_pct * 100).toFixed(1)}%</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={invoice.status} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
