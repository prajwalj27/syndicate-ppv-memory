"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { use } from "react";
import { getInvoice, resolveInvoice, type Invoice } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

function ResolutionForm({
  invoiceId,
  defaultPrice,
  onResolved,
}: {
  invoiceId: number;
  defaultPrice: number;
  onResolved: (invoice: Invoice) => void;
}) {
  const [resolverName, setResolverName] = useState("Prajwal Jaiswal");
  const [resolvedPrice, setResolvedPrice] = useState(String(defaultPrice));
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const updated = await resolveInvoice(invoiceId, {
        resolver_name: resolverName,
        resolved_price: parseFloat(resolvedPrice),
        reason,
      });
      onResolved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve invoice");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "mt-1 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100";

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-8 space-y-4 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm"
    >
      <h3 className="text-xs font-medium uppercase tracking-wide text-zinc-500">Resolve invoice</h3>

      <div>
        <label className="block text-xs font-medium text-zinc-500">Resolver name</label>
        <input
          type="text"
          required
          value={resolverName}
          onChange={(e) => setResolverName(e.target.value)}
          className={inputClass}
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-zinc-500">Resolved price</label>
        <input
          type="number"
          step="0.01"
          required
          value={resolvedPrice}
          onChange={(e) => setResolvedPrice(e.target.value)}
          className={inputClass}
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-zinc-500">Reason</label>
        <textarea
          required
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className={inputClass}
          rows={3}
        />
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Submitting…" : "Submit resolution"}
      </button>
    </form>
  );
}

export default function InvoiceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const invoiceId = Number(id);

  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    getInvoice(invoiceId)
      .then((data) => {
        if (!ignore) setInvoice(data);
      })
      .catch((err) => {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Failed to load invoice");
        }
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [invoiceId]);

  const priorResolution = invoice?.prior_resolution as
    | { date_resolved?: string; reason?: string; resolved_by?: string }
    | null
    | undefined;

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-10">
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-zinc-500 transition hover:text-zinc-900"
      >
        ← Back to dashboard
      </Link>

      {loading && <p className="mt-6 text-zinc-400">Loading…</p>}
      {error && (
        <p className="mt-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
          {error}
        </p>
      )}

      {invoice && (
        <>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
              {(invoice.extracted_data?.invoice_number as string) ?? invoice.invoice_filename}
            </h1>
            <StatusBadge status={invoice.status} />
          </div>

          <div className="mt-6 grid grid-cols-2 gap-x-4 gap-y-5 rounded-xl border border-zinc-200 bg-white p-5 text-sm shadow-sm sm:grid-cols-3">
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">Vendor</div>
              <div className="mt-1 text-zinc-900">{invoice.vendor}</div>
            </div>
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">Item</div>
              <div className="mt-1 text-zinc-900">{invoice.item}</div>
            </div>
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">Invoice unit price</div>
              <div className="mt-1 tabular-nums text-zinc-900">${invoice.invoice_unit_price.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">PO unit price</div>
              <div className="mt-1 tabular-nums text-zinc-900">${invoice.po_unit_price.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">Variance</div>
              <div className="mt-1 font-medium tabular-nums text-zinc-900">{(invoice.variance_pct * 100).toFixed(1)}%</div>
            </div>
          </div>

          {invoice.status === "auto_approved" && priorResolution && (
            <div className="mt-6 rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
              <span className="font-semibold">Prior resolution cited: </span>
              Consistent with prior approval on {priorResolution.date_resolved}: &ldquo;
              {priorResolution.reason}&rdquo;
            </div>
          )}

          <div className="mt-8">
            <h2 className="text-xs font-medium uppercase tracking-wide text-zinc-500">Reasoning</h2>
            <p className="mt-2 rounded-xl border border-zinc-200 bg-white p-4 text-sm leading-relaxed text-zinc-700 shadow-sm">
              {invoice.reasoning}
            </p>
          </div>

          <div className="mt-8">
            <h2 className="text-xs font-medium uppercase tracking-wide text-zinc-500">Steps</h2>
            <ul className="mt-2 space-y-2">
              {invoice.steps.map((step, i) => (
                <li
                  key={i}
                  className="flex gap-3 rounded-xl border border-zinc-200 bg-white p-3.5 text-sm shadow-sm"
                >
                  <span
                    className={`mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full text-xs font-semibold ${
                      step.done
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-zinc-100 text-zinc-400"
                    }`}
                  >
                    {step.done ? "✓" : "○"}
                  </span>
                  <div>
                    <div className="font-medium text-zinc-900">{step.label}</div>
                    <div className="text-zinc-500">{step.detail}</div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {invoice.status === "pending_review" && (
            <ResolutionForm
              invoiceId={invoice.id}
              defaultPrice={invoice.invoice_unit_price}
              onResolved={setInvoice}
            />
          )}
        </>
      )}
    </div>
  );
}
