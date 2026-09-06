"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getInvoices, triggerInvoice, type Invoice } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

const KNOWN_INVOICE_FILES = [
  "INV-1001.txt",
  "INV-1002.txt",
  "INV-1003.txt",
  "INV-1004.txt",
  "INV-1005.txt",
];

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

  const pendingCount = invoices.filter((inv) => inv.status === "pending_review").length;

  const sortedInvoices = [...invoices].sort((a, b) => {
    const aPending = a.status === "pending_review" ? 0 : 1;
    const bPending = b.status === "pending_review" ? 0 : 1;
    return aPending - bPending;
  });

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
          Invoice Dashboard
        </h1>
        <p className="text-sm text-zinc-500">
          Review purchase price variances and resolve flagged invoices.
        </p>
      </header>

      <section className="mt-6 grid gap-4 sm:grid-cols-3">
        <div
          className={`rounded-xl border p-4 shadow-sm sm:col-span-2 ${
            pendingCount > 0
              ? "border-amber-200 bg-amber-100"
              : "border-zinc-200 bg-white"
          }`}
        >
          <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            Review queue
          </div>
          <div
            className={`mt-1 flex items-center gap-2 text-lg font-semibold ${
              pendingCount > 0 ? "text-amber-900" : "text-zinc-900"
            }`}
          >
            {pendingCount > 0 ? (
              <>
                <span
                  className="flex h-2 w-2 rounded-full bg-amber-500"
                  aria-hidden
                />
                {pendingCount} invoice{pendingCount === 1 ? "" : "s"} pending review
              </>
            ) : (
              "All caught up — nothing pending review"
            )}
          </div>
        </div>

        <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            Total invoices
          </div>
          <div className="mt-1 text-lg font-semibold text-zinc-900">
            {loading ? "—" : invoices.length}
          </div>
        </div>
      </section>

      <section className="mt-6 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
        <h2 className="text-xs font-medium uppercase tracking-wide text-zinc-500">
          Trigger new invoice
        </h2>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <select
            value={selectedFile}
            onChange={(e) => setSelectedFile(e.target.value)}
            className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
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
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {triggering ? "Triggering…" : "Trigger new invoice"}
          </button>
        </div>
      </section>

      {error && (
        <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
          {error}
        </p>
      )}

      <section className="mt-6">
        <h2 className="text-xs font-medium uppercase tracking-wide text-zinc-500">
          Invoices
        </h2>
        <div className="mt-2 overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-200 bg-zinc-50/80 text-xs uppercase tracking-wide text-zinc-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Invoice #</th>
                  <th className="px-4 py-3 font-medium">Vendor</th>
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 font-medium">Variance %</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-zinc-400">
                      Loading…
                    </td>
                  </tr>
                ) : sortedInvoices.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-zinc-400">
                      No invoices yet. Trigger one above.
                    </td>
                  </tr>
                ) : (
                  sortedInvoices.map((invoice) => (
                    <tr
                      key={invoice.id}
                      className={
                        invoice.status === "pending_review"
                          ? "bg-amber-100/50 transition hover:bg-amber-100"
                          : "transition hover:bg-zinc-50"
                      }
                    >
                      <td className="px-4 py-3">
                        <Link
                          href={`/invoice/${invoice.id}`}
                          className="font-medium text-indigo-600 underline-offset-2 hover:underline"
                        >
                          {(invoice.extracted_data?.invoice_number as string) ?? invoice.invoice_filename}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-zinc-700">{invoice.vendor}</td>
                      <td className="px-4 py-3 text-zinc-700">{invoice.item}</td>
                      <td className="px-4 py-3 font-medium tabular-nums text-zinc-900">
                        {(invoice.variance_pct * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={invoice.status} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
