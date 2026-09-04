"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type MLStatusData = {
  is_ready: boolean;
  last_train_at: string | null;
  needs_retrain: boolean;
  feature_version: string;
  weights: Record<string, number>;
  models_loaded: { xgboost: boolean; lightgbm: boolean; transformer: boolean };
  model_metrics: Record<string, any>;
};

export default function MLStatus() {
  const [status, setStatus] = useState<MLStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    try {
      const data = await api.mlStatus();
      setStatus(data);
    } catch (e: any) {
      setErr(e?.message || "Failed to load status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  const handleRetrain = async () => {
    setRetraining(true);
    try {
      await api.mlRetrain();
      setTimeout(load, 2000);
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(() => setRetraining(false), 3000);
    }
  };

  if (loading) {
    return (
      <div className="rounded-lg border border-cyan-900/40 bg-[#0f1525] p-4 text-gray-400 text-sm">
        Loading ML engine status...
      </div>
    );
  }

  if (err || !status) {
    return (
      <div className="rounded-lg border border-red-900/40 bg-red-950/30 p-4 text-red-300 text-sm">
        {err || "ML engine unavailable"}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-cyan-900/40 bg-[#0f1525] p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span
            className={`h-3 w-3 rounded-full ${
              status.is_ready ? "bg-emerald-400 shadow-lg shadow-emerald-500/50" : "bg-amber-400"
            }`}
          />
          <span className="text-sm font-semibold text-gray-200">
            {status.is_ready ? "ML Engine Online" : "ML Engine Not Trained"}
          </span>
          <span className="text-xs text-gray-500">v{status.feature_version}</span>
        </div>
        <button
          onClick={handleRetrain}
          disabled={retraining}
          className="px-3 py-1.5 text-xs rounded bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 transition"
        >
          {retraining ? "Retraining..." : "Retrain Models"}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <ModelBadge name="XGBoost" ready={status.models_loaded.xgboost} weight={status.weights.xgboost} />
        <ModelBadge name="LightGBM" ready={status.models_loaded.lightgbm} weight={status.weights.lightgbm} />
        <ModelBadge name="Transformer" ready={status.models_loaded.transformer} weight={status.weights.transformer} />
        <div className="rounded bg-[#0a0f1c] border border-gray-800 p-3">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Last Train</div>
          <div className="text-sm text-gray-200 mt-1">
            {status.last_train_at
              ? new Date(status.last_train_at).toLocaleString()
              : "—"}
          </div>
        </div>
      </div>

      {status.needs_retrain && (
        <div className="mt-3 text-xs text-amber-400 bg-amber-950/30 border border-amber-900/40 rounded px-3 py-2">
          ⚠ Models older than 24h. Retrain recommended for accuracy.
        </div>
      )}
    </div>
  );
}

function ModelBadge({ name, ready, weight }: { name: string; ready: boolean; weight: number }) {
  return (
    <div
      className={`rounded border p-3 ${
        ready
          ? "bg-emerald-950/20 border-emerald-900/40"
          : "bg-[#0a0f1c] border-gray-800"
      }`}
    >
      <div className="text-[10px] text-gray-500 uppercase tracking-wider">{name}</div>
      <div className="text-sm font-semibold mt-1 flex items-center justify-between">
        <span className={ready ? "text-emerald-300" : "text-gray-500"}>
          {ready ? "ready" : "missing"}
        </span>
        <span className="text-xs text-gray-400">w: {(weight * 100).toFixed(0)}%</span>
      </div>
    </div>
  );
}
