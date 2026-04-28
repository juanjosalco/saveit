import { useState, useEffect } from "react";

export type RangeKey = "MTD" | "1M" | "3M" | "6M" | "1Y" | "ALL" | "CUSTOM";

export type Range = {
  key: RangeKey;
  start?: string;  // YYYY-MM-DD
  end?: string;
};

const STORAGE_KEY = "saveit.dashboardRange";

const PRESETS: { key: RangeKey; label: string }[] = [
  { key: "MTD", label: "This month" },
  { key: "1M", label: "1M" },
  { key: "3M", label: "3M" },
  { key: "6M", label: "6M" },
  { key: "1Y", label: "1Y" },
  { key: "ALL", label: "All" },
];

function fmt(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function computeRange(key: RangeKey, customStart?: string, customEnd?: string): { start?: string; end?: string } {
  const today = new Date();
  const end = fmt(today);
  switch (key) {
    case "MTD": {
      const s = new Date(today.getFullYear(), today.getMonth(), 1);
      return { start: fmt(s), end };
    }
    case "1M": return { start: fmt(new Date(Date.now() - 30 * 86_400_000)), end };
    case "3M": return { start: fmt(new Date(Date.now() - 90 * 86_400_000)), end };
    case "6M": return { start: fmt(new Date(Date.now() - 180 * 86_400_000)), end };
    case "1Y": return { start: fmt(new Date(Date.now() - 365 * 86_400_000)), end };
    case "ALL": return {};
    case "CUSTOM": return { start: customStart, end: customEnd };
  }
}

export function loadRange(): Range {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as Range;
  } catch {}
  return { key: "MTD" };
}

export function saveRange(r: Range) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(r)); } catch {}
}

export function rangeLabel(r: Range): string {
  if (r.key === "CUSTOM") return `${r.start || "?"} → ${r.end || "?"}`;
  const p = PRESETS.find((x) => x.key === r.key);
  return p?.label ?? r.key;
}

export default function RangePicker({
  value,
  onChange,
}: {
  value: Range;
  onChange: (r: Range) => void;
}) {
  const [showCustom, setShowCustom] = useState(value.key === "CUSTOM");
  const [start, setStart] = useState(value.start ?? "");
  const [end, setEnd] = useState(value.end ?? "");

  useEffect(() => {
    if (value.key === "CUSTOM") {
      setStart(value.start ?? "");
      setEnd(value.end ?? "");
    }
  }, [value]);

  function pick(key: RangeKey) {
    setShowCustom(false);
    onChange({ key });
  }

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
      <div className="inline-flex rounded-md shadow-sm border border-slate-200 bg-white overflow-hidden">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            onClick={() => pick(p.key)}
            className={`px-3 py-1.5 text-xs font-medium border-r last:border-r-0 border-slate-200 transition ${
              value.key === p.key ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            {p.label}
          </button>
        ))}
        <button
          onClick={() => setShowCustom((v) => !v)}
          className={`px-3 py-1.5 text-xs font-medium transition ${
            value.key === "CUSTOM" ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
          }`}
        >
          Custom
        </button>
      </div>

      {showCustom && (
        <div className="flex items-center gap-2 text-xs">
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="border rounded px-2 py-1" />
          <span className="text-slate-400">→</span>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="border rounded px-2 py-1" />
          <button
            onClick={() => onChange({ key: "CUSTOM", start, end })}
            className="px-2 py-1 bg-emerald-600 text-white rounded"
            disabled={!start || !end}
          >
            Apply
          </button>
        </div>
      )}

      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-slate-100 text-slate-600 border border-slate-200">
        {rangeLabel(value)}
      </span>
    </div>
  );
}
