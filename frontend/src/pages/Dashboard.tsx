import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line,
} from "recharts";
import { api } from "../api/client";
import RangePicker, { Range, computeRange, loadRange, saveRange } from "../components/RangePicker";

type CatRow = { category_id: number | null; category_name: string; color: string; amount: number; count: number };
type TimeRow = { period: string; amount: number };
type MerchRow = { merchant: string; amount: number; count: number };
type CurrencyTotals = { currency: string; transaction_count: number; total_spend: number; total_refunds: number; net_spend: number };
type Summary = { transaction_count: number; total_spend: number; total_refunds: number; net_spend: number; by_currency: CurrencyTotals[] };

const CURRENCY_SYMBOL: Record<string, string> = { USD: "$", MXN: "$", EUR: "€", GBP: "£" };
function fmt(amount: number, currency = "USD"): string {
  const sym = CURRENCY_SYMBOL[currency] || "";
  return `${sym}${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${currency !== "USD" ? ` ${currency}` : ""}`;
}

function buildQS(range: Range): string {
  const r = computeRange(range.key, range.start, range.end);
  const p = new URLSearchParams();
  if (r.start) p.set("start", r.start);
  if (r.end) p.set("end", r.end);
  return p.toString();
}

export default function Dashboard() {
  const [range, setRange] = useState<Range>(() => loadRange());
  useEffect(() => { saveRange(range); }, [range]);

  const qs = buildQS(range);

  const summary = useQuery({ queryKey: ["sum", qs], queryFn: () => api.get<Summary>(`/analytics/summary?${qs}`) });
  const top = useQuery({ queryKey: ["top", qs], queryFn: () => api.get<MerchRow[]>(`/analytics/top-merchants?limit=10&${qs}`) });
  const byCat = useQuery({ queryKey: ["cat", qs], queryFn: () => api.get<CatRow[]>(`/analytics/by-category?${qs}`) });
  const overTime = useQuery({ queryKey: ["time", qs], queryFn: () => api.get<TimeRow[]>(`/analytics/over-time?granularity=month&${qs}`) });

  const isEmpty = (summary.data?.transaction_count ?? 0) === 0 && !summary.isLoading;
  const maxTop = Math.max(1, ...(top.data?.map((m) => m.amount) ?? [0]));

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <RangePicker value={range} onChange={setRange} />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Stat label="Total Spend" value={summary.data ? fmt(summary.data.total_spend) : null} loading={summary.isLoading} />
        <Stat label="Transactions" value={summary.data?.transaction_count} loading={summary.isLoading} />
        <Stat label="Refunds" value={summary.data ? fmt(summary.data.total_refunds) : null} loading={summary.isLoading} />
        <Stat label="Net Spend" value={summary.data ? fmt(summary.data.net_spend) : null} loading={summary.isLoading} accent />
      </div>

      {summary.data && summary.data.by_currency.length > 1 && (
        <div className="bg-white border border-slate-200 rounded-md p-4">
          <h2 className="font-semibold mb-2 text-sm text-slate-700">By currency</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {summary.data.by_currency.map((c) => (
              <div key={c.currency} className="flex items-baseline justify-between border border-slate-200 rounded-md px-3 py-2">
                <div>
                  <span className="inline-block text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono mr-2">{c.currency}</span>
                  <span className="text-xs text-slate-500">{c.transaction_count} txns</span>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold tabular-nums">{fmt(c.net_spend, c.currency)}</div>
                  <div className="text-xs text-slate-400">spend {fmt(c.total_spend, c.currency)}</div>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-2">Note: top stats above sum amounts as nominal numbers across currencies. Use this breakdown for accurate per-currency totals.</p>
        </div>
      )}

      {isEmpty ? (
        <EmptyState />
      ) : (
        <>
          <Card title="Top Merchants">
            {top.isLoading ? (
              <Skeleton h={220} />
            ) : top.data && top.data.length > 0 ? (
              <ul className="divide-y divide-slate-100">
                {top.data.map((m, i) => (
                  <li key={m.merchant} className="py-2 flex items-center gap-3">
                    <div className="w-6 text-right text-slate-400 text-sm tabular-nums">{i + 1}</div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{m.merchant}</div>
                      <div className="h-1.5 bg-slate-100 rounded-full mt-1 overflow-hidden">
                        <div className="h-full bg-slate-900" style={{ width: `${(m.amount / maxTop) * 100}%` }} />
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold tabular-nums">${m.amount.toFixed(2)}</div>
                      <div className="text-xs text-slate-400">{m.count} txn{m.count > 1 ? "s" : ""}</div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-slate-500 text-sm">No merchants in this range.</p>
            )}
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card title="Spend by Category">
              {byCat.isLoading ? <Skeleton h={300} /> : (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={byCat.data ?? []} dataKey="amount" nameKey="category_name" outerRadius={110} label={(e: any) => e.category_name}>
                      {(byCat.data ?? []).map((c, i) => <Cell key={i} fill={c.color} />)}
                    </Pie>
                    <Tooltip formatter={(v: number) => `$${v.toFixed(2)}`} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </Card>

            <Card title="Categories Ranked">
              {byCat.isLoading ? <Skeleton h={300} /> : (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={byCat.data ?? []} layout="vertical" margin={{ left: 80 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="category_name" width={100} />
                    <Tooltip formatter={(v: number) => `$${v.toFixed(2)}`} />
                    <Bar dataKey="amount">
                      {(byCat.data ?? []).map((c, i) => <Cell key={i} fill={c.color} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>

          <Card title="Spend Over Time (monthly)">
            {overTime.isLoading ? <Skeleton h={280} /> : (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={overTime.data ?? []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="period" />
                  <YAxis />
                  <Tooltip formatter={(v: number) => `$${v.toFixed(2)}`} />
                  <Line type="monotone" dataKey="amount" stroke="#0f172a" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, loading, accent }: { label: string; value: any; loading?: boolean; accent?: boolean }) {
  return (
    <div className={`p-4 rounded-md border ${accent ? "bg-slate-900 text-white border-slate-900" : "bg-white border-slate-200"}`}>
      <div className={`text-xs uppercase tracking-wide ${accent ? "text-slate-300" : "text-slate-500"}`}>{label}</div>
      <div className="text-2xl font-bold mt-1 min-h-[2rem]">
        {loading ? <span className="inline-block w-20 h-6 rounded bg-slate-200/60 animate-pulse" /> : value ?? "—"}
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white p-4 rounded-md border border-slate-200">
      <h2 className="font-semibold mb-3">{title}</h2>
      {children}
    </div>
  );
}

function Skeleton({ h }: { h: number }) {
  return <div className="w-full rounded-md bg-slate-100 animate-pulse" style={{ height: h }} />;
}

function EmptyState() {
  return (
    <div className="bg-white border border-dashed border-slate-300 rounded-md p-12 text-center">
      <div className="text-3xl mb-2">🪙</div>
      <h2 className="font-semibold text-slate-800">No spending in this range</h2>
      <p className="text-sm text-slate-500 mt-1">
        Try widening the date range, or upload more statements from the Upload page.
      </p>
    </div>
  );
}
