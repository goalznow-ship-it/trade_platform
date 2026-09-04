"use client";

import { useEffect, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import MLPanel from "@/components/ml/MLPanel";
import MLStatus from "@/components/ml/MLStatus";
import MLPredictionCard from "@/components/ml/MLPredictionCard";

const DEFAULT_SYMBOLS = [
  "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
  "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "LINK/USDT", "TRX/USDT",
];

export default function MLPage() {
  return (
    <AuthGuard>
      <MLDashboard />
    </AuthGuard>
  );
}

function MLDashboard() {
  return (
    <div className="min-h-screen bg-[#0a0e1a] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <header>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
            ML Signal Engine
          </h1>
          <p className="text-gray-400 mt-2">
            Phase 21 · Multi-model ensemble (XGBoost + LightGBM + Transformer) ·
            Confidence-weighted predictions · 15m forward horizon
          </p>
        </header>

        <MLStatus />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <MLPanel symbols={DEFAULT_SYMBOLS} />
          </div>
          <div>
            <MLPredictionCard />
          </div>
        </div>
      </div>
    </div>
  );
}
