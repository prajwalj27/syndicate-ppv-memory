import type { InvoiceStatus } from "@/lib/api";

export const STATUS_BADGE_CLASSES: Record<InvoiceStatus, string> = {
  auto_approved: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  pending_review: "bg-amber-50 text-amber-700 ring-amber-600/20",
  resolved: "bg-sky-50 text-sky-700 ring-sky-600/20",
  rejected: "bg-rose-50 text-rose-700 ring-rose-600/20",
};

export const STATUS_DOT_CLASSES: Record<InvoiceStatus, string> = {
  auto_approved: "bg-emerald-500",
  pending_review: "bg-amber-500",
  resolved: "bg-sky-500",
  rejected: "bg-rose-500",
};

export const STATUS_LABELS: Record<InvoiceStatus, string> = {
  auto_approved: "Auto-Approved",
  pending_review: "Pending Review",
  resolved: "Resolved",
  rejected: "Rejected",
};

export function StatusBadge({ status }: { status: InvoiceStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${STATUS_BADGE_CLASSES[status]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT_CLASSES[status]}`} />
      {STATUS_LABELS[status]}
    </span>
  );
}
