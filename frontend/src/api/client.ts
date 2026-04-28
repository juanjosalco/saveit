const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, init);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  get:    <T,>(p: string) => req<T>(p),
  post:   <T,>(p: string, body?: unknown) =>
            req<T>(p, { method: "POST", headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined }),
  patch:  <T,>(p: string, body: unknown) =>
            req<T>(p, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  put:    <T,>(p: string, body: unknown) =>
            req<T>(p, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  del:    <T,>(p: string) => req<T>(p, { method: "DELETE" }),
  upload: <T,>(p: string, file: File) => {
    const fd = new FormData(); fd.append("file", file);
    return req<T>(p, { method: "POST", body: fd });
  },
  fileUrl: (p: string) => BASE + p,
};

export type Category = { id: number; name: string; color: string };
export type Account = { id: number; issuer: string; last4: string; nickname?: string | null; base_currency?: string };
export type Transaction = {
  id: number; account_id: number; statement_id: number;
  txn_date: string; description_raw: string; description_clean: string;
  amount: number; currency: string;
  category_id: number | null; is_payment: boolean; is_refund: boolean;
  manual_category_override: boolean;
};
export type Rule = { id: number; pattern: string; match_type: string; category_id: number; priority: number };
export type UploadResult = {
  statement_id: number; account_id: number; issuer: string; last4: string;
  period_start: string | null; period_end: string | null;
  transactions_added: number; transactions_skipped: number; duplicate: boolean;
};
export type StatementSummary = {
  id: number;
  account_id: number;
  account: { id: number; issuer: string; last4: string; base_currency?: string };
  period_start: string | null;
  period_end: string | null;
  uploaded_at: string;
  source_filename: string;
  has_pdf: boolean;
  transaction_count: number;
  total_amount: number;
};
export type ResetResult = {
  transactions_deleted: number;
  statements_deleted: number;
  accounts_deleted: number;
  pdfs_deleted: number;
  config_preserved: boolean;
};
export type CurrencyTotals = {
  currency: string;
  transaction_count: number;
  total_spend: number;
  total_refunds: number;
  net_spend: number;
};
export type AzureSettings = { endpoint: string; key_masked: string; configured: boolean };
