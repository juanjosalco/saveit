import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Account, Category, Transaction } from "../api/client";

export default function Transactions() {
  const qc = useQueryClient();
  const [accountId, setAccountId] = useState<string>("");
  const [categoryId, setCategoryId] = useState<string>("");
  const [start, setStart] = useState<string>("");
  const [end, setEnd] = useState<string>("");

  const accounts = useQuery({ queryKey: ["accounts"], queryFn: () => api.get<Account[]>("/accounts") });
  const categories = useQuery({ queryKey: ["categories"], queryFn: () => api.get<Category[]>("/categories") });
  const params = new URLSearchParams();
  if (accountId) params.set("account_id", accountId);
  if (categoryId) params.set("category_id", categoryId);
  if (start) params.set("start", start);
  if (end) params.set("end", end);

  const txns = useQuery({
    queryKey: ["txns", params.toString()],
    queryFn: () => api.get<Transaction[]>(`/transactions?${params.toString()}`),
  });

  const update = useMutation({
    mutationFn: ({ id, category_id }: { id: number; category_id: number }) =>
      api.patch<Transaction>(`/transactions/${id}`, { category_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["txns"] }),
  });

  const catMap = new Map((categories.data ?? []).map((c) => [c.id, c]));
  const acctMap = new Map((accounts.data ?? []).map((a) => [a.id, a]));

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Transactions</h1>
      <div className="flex flex-wrap gap-3 bg-white p-3 rounded-md border border-slate-200">
        <select value={accountId} onChange={(e) => setAccountId(e.target.value)} className="border rounded px-2 py-1">
          <option value="">All accounts</option>
          {accounts.data?.map((a) => <option key={a.id} value={a.id}>{a.issuer.toUpperCase()} •••{a.last4}</option>)}
        </select>
        <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className="border rounded px-2 py-1">
          <option value="">All categories</option>
          {categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="border rounded px-2 py-1" />
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="border rounded px-2 py-1" />
        <button onClick={() => { setAccountId(""); setCategoryId(""); setStart(""); setEnd(""); }} className="px-3 py-1 text-sm bg-slate-200 rounded hover:bg-slate-300">
          Clear
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Account</th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {txns.data?.map((t) => {
              const acct = acctMap.get(t.account_id);
              return (
                <tr key={t.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2 whitespace-nowrap">{t.txn_date}</td>
                  <td className="px-3 py-2">{acct ? `${acct.issuer.toUpperCase()} •••${acct.last4}` : "?"}</td>
                  <td className="px-3 py-2">{t.description_clean || t.description_raw}</td>
                  <td className="px-3 py-2">
                    <select
                      value={t.category_id ?? ""}
                      onChange={(e) => update.mutate({ id: t.id, category_id: Number(e.target.value) })}
                      className="border rounded px-1 py-0.5 text-xs"
                      style={{ borderColor: catMap.get(t.category_id ?? -1)?.color }}
                    >
                      <option value="">—</option>
                      {categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                    {t.manual_category_override && <span className="ml-1 text-xs text-slate-400">(manual)</span>}
                  </td>
                  <td className={`px-3 py-2 text-right tabular-nums ${t.amount < 0 ? "text-emerald-600" : ""}`}>
                    {t.amount < 0 ? "-" : ""}${Math.abs(t.amount).toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {txns.isLoading && <div className="p-4 text-slate-500">Loading…</div>}
        {txns.data?.length === 0 && <div className="p-4 text-slate-500">No transactions. Upload a statement to get started.</div>}
      </div>
    </div>
  );
}
