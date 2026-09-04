"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Prediction = {
  symbol: string;
  direction: -1 | 0 | 1;
  direction_label: "sell" | "hold" | "buy";
  confidence: number;
  agreement: number;
  proba: { sell: number; hold: number; buy: number };
  per_model: Record<string, { sell: number; hold: number; buy: number }>;
  timestamp: string;
};

export default function MLPanel({ symbols }: { symbols: string[] }) {
  const [results, setResults] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [tf, setTf] = useState<"15m" | "1h" | "4h">("15m");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const load = async () => {
    try {
      setLoading(true);
      const data = await api.mlPredictBatch(symbols, tf);
      setResults(data.results || []);
      setErr(null);
    } catch (e: any) {
      setErr(e?.message || "Failed to fetch predictions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [tf]);

  useEffect(() => {
    if (!autoRefresh) return;
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [autoRefresh, tf]);

  return (
    <div className="rounded-lg border border-cyan-900/40 bg-[#0f1525] p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-100">Live ML Predictions</h2>
        <div className="flex items-center gap-2">
          <select
            value={tf}
            onChange={(e) => setTf(e.target.value as any)}
            className="bg-[#0a0f1c] border border-gray-800 text-sm rounded px-2 py-1"
          >
            <option value="15m">15m</option>
            <option value="1h">1H</option>
            <option value="4h">4H</option>
          </select>
          <button
            onClick={load}
            className="px-3 py-1 text-xs rounded bg-cyan-600 hover:bg-cyan-500 transition"
          >
            Refresh
          </button>
        </div>
      </div>

      {err && (
        <div className="rounded border border-amber-900/40 bg-amber-950/30 p-3 mb-3 text-amber-200 text-sm">
          ⚠ {err}
        </div>
      )}

      {loading && results.length === 0 ? (
        <div className="space-y-2">
          {symbols.slice(0, 5).map((s) => (
            <div key={s} className="h-20 rounded bg-[#0a0f1c] animate-pulse" />
          ))}
        </div>
      ) : results.length === 0 ? (
        <div className="rounded bg-[#0a0f1c] p-8 text-center text-gray-500 text-sm">
          No predictions yet. Train the models first via the "Retrain" button above.
        </div>
      ) : (
        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {results
            .sort((a, b) => b.confidence - a.confidence)
            .map((p) => (
              <PredictionRow key={p.symbol} p={p} />
            ))}
        </div>
      )}
    </div>
  );
}

function PredictionRow({ p }: { p: Prediction }) {
  const isBuy = p.direction === 1;
  const isSell = p.direction === -1;
  const dirColor = isBuy
    ? "text-emerald-400"
    : isSell
    ? "text-rose-400"
    : "text-gray-400";
  const barColor = isBuy
    ? "bg-emerald-500"
    : isSell
    ? "bg-rose-500"
    : "bg-gray-500";

  return (
    <div className="rounded border border-gray-800 bg-[#0a0f1c] p-3 hover:border-cyan-700/40 transition">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className="font-mono font-semibold text-gray-100">{p.symbol}</span>
          <span className={`text-sm font-semibold uppercase ${dirColor}`}>
            {p.direction_label}
          </span>
          {p.agreement > 0.8 && (
            <span className="text-[10px] text-emerald-400 bg-emerald-950/30 px-1.5 py-0.5 rounded">
              STRONG AGREEMENT
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500">
          conf: <span className="text-gray-200 font-mono">{(p.confidence * 100).toFixed(1)}%</span>
        </div>
      </div>

      <div className="relative h-2 bg-gray-900 rounded overflow-hidden">
        <div
          className={`absolute top-0 left-0 h-full ${barColor} transition-all`}
          style={{ width: `${p.confidence * 100}%` }}
        />
      </div>

      <div className="grid grid-cols-3 gap-2 mt-2 text-[10px] text-gray-500">
        <div>
          sell: <span className="text-rose-300 font-mono">{(p.proba.sell * 100).toFixed(0)}%</span>
        </div>
        <div className="text-center">
          hold: <span className="text-gray-300 font-mono">{(p.proba.hold * 100).toFixed(0)}%</span>
        </div>
        <div className="text-right">
          buy: <span className="text-emerald-300 font-mono">{(p.proba.buy * 100).toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
}
