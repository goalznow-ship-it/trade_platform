"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Feature = { feature: string; importance: number };

export default function MLPredictionCard() {
  const [features, setFeatures] = useState<Feature[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.mlFeatureImportance()
      .then((data) => {
        const out: Feature[] = [];
        Object.entries(data || {}).forEach(([model, list]: [string, any]) => {
          (list as Feature[]).slice(0, 8).forEach((f) =>
            out.push({ feature: `${model}: ${f.feature}`, importance: f.importance })
          );
        });
        out.sort((a, b) => b.importance - a.importance);
        setFeatures(out.slice(0, 15));
      })
      .catch((e) => setErr(e?.message || "Failed to load feature importance"));
  }, []);

  return (
    <div className="rounded-lg border border-cyan-900/40 bg-[#0f1525] p-5">
      <h2 className="text-lg font-semibold text-gray-100 mb-1">Top Features</h2>
      <p className="text-xs text-gray-500 mb-4">
        What the models rely on most right now
      </p>

      {err && (
        <div className="text-xs text-amber-400 bg-amber-950/30 rounded p-2 mb-3">{err}</div>
      )}

      {features.length === 0 ? (
        <div className="rounded bg-[#0a0f1c] p-6 text-center text-gray-500 text-sm">
          Train models to see top features
        </div>
      ) : (
        <div className="space-y-1.5">
          {features.map((f, i) => (
            <div key={i} className="text-xs">
              <div className="flex justify-between text-gray-400 mb-0.5">
                <span className="truncate font-mono">{f.feature}</span>
                <span>{(f.importance * 100).toFixed(1)}</span>
              </div>
              <div className="relative h-1.5 bg-gray-900 rounded overflow-hidden">
                <div
                  className="absolute top-0 left-0 h-full bg-cyan-500"
                  style={{ width: `${Math.min(100, f.importance * 5)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
