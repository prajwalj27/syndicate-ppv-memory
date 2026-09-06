const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type InvoiceStep = {
  label: string;
  detail: string;
  done: boolean;
};

export type InvoiceStatus =
  | "auto_approved"
  | "pending_review"
  | "resolved"
  | "rejected";

export type Invoice = {
  id: number;
  invoice_filename: string;
  status: InvoiceStatus;
  created_at: string;
  vendor: string;
  item: string;
  invoice_unit_price: number;
  po_unit_price: number;
  variance_pct: number;
  reasoning: string;
  prior_resolution: Record<string, unknown> | null;
  extracted_data: Record<string, unknown>;
  po_record: Record<string, unknown>;
  steps: InvoiceStep[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status} ${body}`);
  }

  return res.json() as Promise<T>;
}

export function getInvoices(): Promise<Invoice[]> {
  return request<Invoice[]>("/invoices");
}

export function getInvoice(id: number): Promise<Invoice> {
  return request<Invoice>(`/invoices/${id}`);
}

export function triggerInvoice(filename: string): Promise<Invoice> {
  return request<Invoice>("/invoices/trigger", {
    method: "POST",
    body: JSON.stringify({ filename }),
  });
}

export function resolveInvoice(
  id: number,
  data: { resolver_name: string; resolved_price: number; reason: string }
): Promise<Invoice> {
  return request<Invoice>(`/invoices/${id}/resolve`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
