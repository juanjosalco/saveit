import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Category, Rule } from "../api/client";

export default function Rules() {
  const qc = useQueryClient();
  const rules = useQuery({ queryKey: ["rules"], queryFn: () => api.get<Rule[]>("/rules") });
  const cats = useQuery({ queryKey: ["categories"], queryFn: () => api.get<Category[]>("/categories") });
  const [pattern, setPattern] = useState("");
  const [matchType, setMatchType] = useState("contains");
  const [catId, setCatId] = useState<number>(0);
  const [priority, setPriority] = useState(100);

  const create = useMutation({
    mutationFn: (r: Omit<Rule, "id">) => api.post<Rule>("/rules", r),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["rules"] }); setPattern(""); },
  });
  const del = useMutation({
    mutationFn: (id: number) => api.del<{ ok: boolean }>(`/rules/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
  const recat = useMutation({
    mutationFn: () => api.post<{ updated: number }>("/rules/recategorize"),
    onSuccess: (r) => alert(`Recategorized ${r.updated} transactions`),
  });

  const catMap = new Map((cats.data ?? []).map((c) => [c.id, c]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Categorization Rules</h1>
        <button onClick={() => recat.mutate()} className="bg-slate-900 text-white px-3 py-2 rounded-md text-sm">
          Re-run on existing transactions
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-md p-4">
        <h2 className="font-semibold mb-2">Add rule</h2>
        <div className="flex flex-wrap items-end gap-2">
          <input className="border rounded px-2 py-1" placeholder="Pattern (e.g. STARBUCKS)" value={pattern} onChange={(e) => setPattern(e.target.value)} />
          <select className="border rounded px-2 py-1" value={matchType} onChange={(e) => setMatchType(e.target.value)}>
            <option value="contains">contains</option>
            <option value="regex">regex</option>
          </select>
          <select className="border rounded px-2 py-1" value={catId} onChange={(e) => setCatId(Number(e.target.value))}>
            <option value={0}>Category…</option>
            {cats.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <input type="number" className="border rounded px-2 py-1 w-24" value={priority} onChange={(e) => setPriority(Number(e.target.value))} />
          <button
            disabled={!pattern || !catId}
            onClick={() => create.mutate({ pattern, match_type: matchType, category_id: catId, priority })}
            className="bg-emerald-600 text-white px-3 py-1.5 rounded disabled:opacity-50"
          >Add</button>
        </div>
        <p className="text-xs text-slate-500 mt-2">Lower priority = runs first. Manual category overrides are preserved during re-run.</p>
      </div>

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="px-3 py-2">Priority</th>
              <th className="px-3 py-2">Pattern</th>
              <th className="px-3 py-2">Type</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {rules.data?.map((r) => (
              <tr key={r.id} className="border-t border-slate-100">
                <td className="px-3 py-1 tabular-nums">{r.priority}</td>
                <td className="px-3 py-1 font-mono">{r.pattern}</td>
                <td className="px-3 py-1">{r.match_type}</td>
                <td className="px-3 py-1">{catMap.get(r.category_id)?.name ?? "?"}</td>
                <td className="px-3 py-1 text-right">
                  <button onClick={() => del.mutate(r.id)} className="text-red-600 text-xs hover:underline">delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
