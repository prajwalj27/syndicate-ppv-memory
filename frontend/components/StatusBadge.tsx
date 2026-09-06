import type { InvoiceStatus } from "@/lib/api";

export const STATUS_BADGE_CLASSES: Record<InvoiceStatus, string> = {
  auto_approved: "bg-green-100 text-green-800",
  pending_review: "bg-yellow-100 text-yellow-800",
  resolved: "bg-blue-100 text-blue-800",
  rejected: "bg-red-100 text-red-800",
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
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
