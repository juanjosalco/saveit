import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, UploadResult, StatementSummary, ResetResult } from "../api/client";

export default function Upload() {
  const qc = useQueryClient();
  const [results, setResults] = useState<UploadResult[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);

  const statements = useQuery({
    queryKey: ["statements"],
    queryFn: () => api.get<StatementSummary[]>("/statements"),
  });

  const upload = useMutation({
    mutationFn: (file: File) => api.upload<UploadResult>("/statements/upload", file),
    onSuccess: (r) => {
      setResults((rs) => [r, ...rs]);
      qc.invalidateQueries({ queryKey: ["statements"] });
      qc.invalidateQueries({ queryKey: ["sum"] });
      qc.invalidateQueries({ queryKey: ["cat"] });
      qc.invalidateQueries({ queryKey: ["top"] });
      qc.invalidateQueries({ queryKey: ["time"] });
      qc.invalidateQueries({ queryKey: ["txns"] });
      qc.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (e: Error, f) => setErrors((es) => [`${f.name}: ${e.message}`, ...es]),
  });

  const del = useMutation({
    mutationFn: (id: number) => api.del<{ ok: boolean }>(`/statements/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["statements"] });
      qc.invalidateQueries();
    },
  });

  const reset = useMutation({
    mutationFn: () => api.post<ResetResult>("/admin/reset"),
    onSuccess: (r) => {
      setResults([]);
      setErrors([]);
      setConfirmReset(false);
      qc.invalidateQueries();
      alert(
        `Wiped:\n• ${r.transactions_deleted} transactions\n• ${r.statements_deleted} statements\n• ${r.accounts_deleted} accounts\n• ${r.pdfs_deleted} archived PDFs\n\nCategories & rules preserved.`
      );
    },
  });

  function handleFiles(files: FileList | null) {
    if (!files) return;
    Array.from(files).filter((f) => f.name.toLowerCase().endsWith(".pdf")).forEach((f) => upload.mutate(f));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Upload Statements</h1>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
        className={`border-2 border-dashed rounded-lg p-12 text-center transition ${dragOver ? "border-slate-900 bg-slate-100" : "border-slate-300 bg-white"}`}
      >
        <p className="text-slate-600 mb-4">Drag & drop one or more PDF statements here</p>
        <label className="inline-block bg-slate-900 text-white px-4 py-2 rounded-md cursor-pointer hover:bg-slate-700">
          Or browse
          <input type="file" accept="application/pdf" multiple className="hidden" onChange={(e) => handleFiles(e.target.files)} />
        </label>
        <p className="text-xs text-slate-500 mt-3">Supported: American Express, Chase, Santander Mexico (requires Azure DI — <a className="text-blue-600 hover:underline" href="/settings">configure on Settings</a>)</p>
      </div>

      {upload.isPending && <p className="text-slate-500">Parsing…</p>}

      {results.length > 0 && (
        <div>
          <h2 className="font-semibold mb-2">Upload results (this session)</h2>
          <div className="space-y-2">
            {results.map((r, i) => (
              <div key={i} className={`p-3 rounded border ${r.duplicate ? "bg-amber-50 border-amber-200" : "bg-emerald-50 border-emerald-200"}`}>
                <div className="font-medium">{r.issuer.toUpperCase()} •••{r.last4} {r.duplicate && "(duplicate)"}</div>
                <div className="text-sm text-slate-600">
                  Period: {r.period_start ?? "?"} → {r.period_end ?? "?"} • Added: {r.transactions_added} • Skipped (dup): {r.transactions_skipped}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {errors.length > 0 && (
        <div>
          <h2 className="font-semibold mb-2 text-red-700">Errors</h2>
          <ul className="space-y-1 text-sm text-red-700">
            {errors.map((e, i) => <li key={i}>• {e}</li>)}
          </ul>
        </div>
      )}

      {/* Uploaded Statements archive */}
      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
          <h2 className="font-semibold">Uploaded Statements ({statements.data?.length ?? 0})</h2>
          <button
            onClick={() => setConfirmReset(true)}
            className="text-xs px-3 py-1.5 rounded bg-red-50 text-red-700 border border-red-200 hover:bg-red-100"
          >
            Reset everything
          </button>
        </div>

        {statements.isLoading ? (
          <div className="p-4 text-slate-500 text-sm">Loading…</div>
        ) : (statements.data?.length ?? 0) === 0 ? (
          <div className="p-6 text-center text-sm text-slate-500">
            No statements uploaded yet. Drop PDFs above to get started.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-slate-500 bg-slate-50">
              <tr>
                <th className="px-3 py-2">Account</th>
                <th className="px-3 py-2">Period</th>
                <th className="px-3 py-2">Filename</th>
                <th className="px-3 py-2 text-right">Txns</th>
                <th className="px-3 py-2 text-right">Total</th>
                <th className="px-3 py-2">Uploaded</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {statements.data!.map((s) => (
                <tr key={s.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span className="font-medium">{s.account.issuer.toUpperCase()}</span>
                    <span className="text-slate-400"> •••{s.account.last4}</span>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-slate-600">
                    {s.period_start ?? "?"} → {s.period_end ?? "?"}
                  </td>
                  <td className="px-3 py-2 max-w-xs truncate" title={s.source_filename}>{s.source_filename}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{s.transaction_count}</td>
                  <td className="px-3 py-2 text-right tabular-nums">${s.total_amount.toFixed(2)}</td>
                  <td className="px-3 py-2 whitespace-nowrap text-slate-500 text-xs">
                    {new Date(s.uploaded_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    {s.has_pdf ? (
                      <a
                        href={api.fileUrl(`/statements/${s.id}/file`)}
                        className="text-xs text-blue-600 hover:underline mr-3"
                        download={s.source_filename}
                      >Download</a>
                    ) : (
                      <span className="text-xs text-slate-400 mr-3" title="Original PDF not available (uploaded before archiving)">no PDF</span>
                    )}
                    <button
                      onClick={() => {
                        if (confirm(`Delete "${s.source_filename}" and its ${s.transaction_count} transactions?`)) {
                          del.mutate(s.id);
                        }
                      }}
                      className="text-xs text-red-600 hover:underline"
                    >Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Confirm reset modal */}
      {confirmReset && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setConfirmReset(false)}>
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-red-700">Reset everything?</h3>
            <p className="text-sm text-slate-600 mt-2">
              This will permanently delete:
            </p>
            <ul className="text-sm text-slate-700 mt-2 list-disc list-inside space-y-0.5">
              <li>All transactions</li>
              <li>All statements</li>
              <li>All accounts</li>
              <li>All archived PDF files</li>
            </ul>
            <p className="text-sm text-slate-500 mt-3">
              Categories and rules will be <strong>kept</strong>. This cannot be undone.
            </p>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setConfirmReset(false)} className="px-3 py-1.5 rounded border border-slate-300 text-sm">Cancel</button>
              <button
                onClick={() => reset.mutate()}
                disabled={reset.isPending}
                className="px-3 py-1.5 rounded bg-red-600 text-white text-sm hover:bg-red-700 disabled:opacity-50"
              >{reset.isPending ? "Wiping…" : "Yes, reset everything"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
