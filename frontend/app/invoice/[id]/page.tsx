"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { use } from "react";
import {
  getInvoice,
  resolveInvoice,
  type Invoice,
  type InvoiceStatus,
} from "@/lib/api";

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

function ResolutionForm({
  invoiceId,
  onResolved,
}: {
  invoiceId: number;
  onResolved: (invoice: Invoice) => void;
}) {
  const [resolverName, setResolverName] = useState("");
  const [resolvedPrice, setResolvedPrice] = useState("");
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

  return (
    <form onSubmit={handleSubmit} className="mt-4 space-y-3 rounded border border-zinc-200 p-4">
      <h3 className="text-sm font-semibold text-zinc-900">Resolve invoice</h3>

      <div>
        <label className="block text-xs font-medium text-zinc-500">Resolver name</label>
        <input
          type="text"
          required
          value={resolverName}
          onChange={(e) => setResolverName(e.target.value)}
          className="mt-1 w-full rounded border border-zinc-300 px-3 py-2 text-sm"
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
          className="mt-1 w-full rounded border border-zinc-300 px-3 py-2 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-zinc-500">Reason</label>
        <textarea
          required
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="mt-1 w-full rounded border border-zinc-300 px-3 py-2 text-sm"
          rows={3}
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
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
      <Link href="/" className="text-sm text-zinc-500 underline-offset-2 hover:underline">
        ← Back to dashboard
      </Link>

      {loading && <p className="mt-6 text-zinc-500">Loading…</p>}
      {error && <p className="mt-6 text-sm text-red-600">{error}</p>}

      {invoice && (
        <>
          <div className="mt-4 flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-zinc-900">
              {(invoice.extracted_data?.invoice_number as string) ?? invoice.invoice_filename}
            </h1>
            <StatusBadge status={invoice.status} />
          </div>

          <div className="mt-6 grid grid-cols-2 gap-4 rounded border border-zinc-200 p-4 text-sm">
            <div>
              <div className="text-xs font-medium text-zinc-500">Vendor</div>
              <div className="mt-1 text-zinc-900">{invoice.vendor}</div>
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-500">Item</div>
              <div className="mt-1 text-zinc-900">{invoice.item}</div>
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-500">Invoice unit price</div>
              <div className="mt-1 text-zinc-900">${invoice.invoice_unit_price.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-500">PO unit price</div>
              <div className="mt-1 text-zinc-900">${invoice.po_unit_price.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-500">Variance</div>
              <div className="mt-1 text-zinc-900">{(invoice.variance_pct * 100).toFixed(1)}%</div>
            </div>
          </div>

          {invoice.status === "auto_approved" && priorResolution && (
            <div className="mt-6 rounded border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
              <span className="font-semibold">Prior resolution cited: </span>
              Consistent with prior approval on {priorResolution.date_resolved}: &ldquo;
              {priorResolution.reason}&rdquo;
            </div>
          )}

          <div className="mt-6">
            <h2 className="text-sm font-semibold text-zinc-900">Reasoning</h2>
            <p className="mt-2 rounded border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-800">
              {invoice.reasoning}
            </p>
          </div>

          <div className="mt-6">
            <h2 className="text-sm font-semibold text-zinc-900">Steps</h2>
            <ul className="mt-2 space-y-2">
              {invoice.steps.map((step, i) => (
                <li key={i} className="flex gap-3 rounded border border-zinc-200 p-3 text-sm">
                  <span className={step.done ? "text-green-600" : "text-zinc-400"}>
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
            <ResolutionForm invoiceId={invoice.id} onResolved={setInvoice} />
          )}
        </>
      )}
    </div>
  );
}
