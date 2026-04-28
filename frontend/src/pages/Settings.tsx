import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, AzureSettings } from "../api/client";

export default function Settings() {
  const qc = useQueryClient();
  const [endpoint, setEndpoint] = useState("");
  const [key, setKey] = useState("");
  const [savedNote, setSavedNote] = useState<string | null>(null);

  const azure = useQuery({
    queryKey: ["settings", "azure"],
    queryFn: () => api.get<AzureSettings>("/settings/azure"),
  });

  useEffect(() => {
    if (azure.data) {
      setEndpoint(azure.data.endpoint || "");
      setKey(azure.data.key_masked || "");
    }
  }, [azure.data]);

  const save = useMutation({
    mutationFn: (body: { endpoint: string; key: string }) =>
      api.put<AzureSettings>("/settings/azure", body),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      setEndpoint(r.endpoint);
      setKey(r.key_masked);
      setSavedNote(r.configured ? "Saved. Azure DI is configured." : "Saved (incomplete).");
      setTimeout(() => setSavedNote(null), 3500);
    },
  });

  const keyIsMasked = !!azure.data && key === azure.data.key_masked;

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      <div className="bg-white border border-slate-200 rounded-md p-5">
        <h2 className="font-semibold">Azure Document Intelligence</h2>
        <p className="text-sm text-slate-600 mt-1">
          Required to parse <strong>Santander</strong> (image-based) statements.
          Credentials are stored locally in your SQLite database — never sent
          anywhere except to your Azure resource.
        </p>

        <div className="mt-4 space-y-3">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Endpoint</span>
            <input
              type="url"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              placeholder="https://your-resource.cognitiveservices.azure.com/"
              className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-md text-sm font-mono"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">API Key</span>
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              onFocus={() => { if (keyIsMasked) setKey(""); }}
              placeholder="paste your key (will be hidden after saving)"
              className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-md text-sm font-mono"
            />
            {keyIsMasked && (
              <span className="text-xs text-slate-500">A key is already saved. Focus this field to replace it.</span>
            )}
          </label>

          <div className="flex items-center gap-3">
            <button
              onClick={() => save.mutate({ endpoint, key: keyIsMasked ? "" : key })}
              disabled={save.isPending}
              className="bg-slate-900 text-white px-4 py-2 rounded-md text-sm hover:bg-slate-700 disabled:opacity-50"
            >
              {save.isPending ? "Saving…" : "Save"}
            </button>
            <span className={`text-sm ${azure.data?.configured ? "text-emerald-700" : "text-slate-500"}`}>
              {azure.data?.configured ? "✓ Configured" : "Not configured"}
            </span>
            {savedNote && <span className="text-sm text-slate-600">{savedNote}</span>}
          </div>
        </div>

        <div className="mt-5 text-xs text-slate-500 space-y-1">
          <p><strong>How to get these:</strong></p>
          <ol className="list-decimal list-inside space-y-0.5">
            <li>Sign in to the <a className="text-blue-600 hover:underline" href="https://portal.azure.com" target="_blank" rel="noreferrer">Azure portal</a>.</li>
            <li>Create a <em>Document Intelligence</em> resource (Free F0 tier works for testing).</li>
            <li>Open the resource → <em>Keys and Endpoint</em>.</li>
            <li>Copy the <em>Endpoint</em> URL and <em>KEY 1</em> here.</li>
          </ol>
          <p className="mt-2">Tip: you can also set <code>FINAPP_AZURE_DI_ENDPOINT</code> and <code>FINAPP_AZURE_DI_KEY</code> as environment variables — they override anything saved here.</p>
        </div>
      </div>
    </div>
  );
}
