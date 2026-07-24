"use client"

import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus, Activity, BarChart3, Volume2, Zap, Shield } from "lucide-react"

interface Props {
  timeframes: Record<string, unknown>
  scores: Record<string, unknown>
  alignment: Record<string, unknown>
  sr: Record<string, unknown>
}

function scoreValue(s: Record<string, unknown>, key: string): number {
  const v = s[key]
  return typeof v === "number" ? v : 0
}

function strVal(v: unknown): string {
  if (v == null) return "N/A"
  return String(v)
}

export function SKHYAnalysisPanel({ timeframes, scores, alignment, sr }: Props) {
  const tfList = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

  const scoreItems = [
    { label: "Trend", key: "trend_score", icon: TrendingUp },
    { label: "Structure", key: "structure_score", icon: BarChart3 },
    { label: "Momentum", key: "momentum_score", icon: Zap },
    { label: "Volume", key: "volume_score", icon: Volume2 },
    { label: "Liquidity", key: "liquidity_score", icon: Activity },
    { label: "Pattern", key: "pattern_score", icon: BarChart3 },
    { label: "Futures", key: "futures_score", icon: BarChart3 },
    { label: "OrderFlow", key: "orderflow_score", icon: Activity },
    { label: "MTF", key: "multitimeframe_score", icon: BarChart3 },
    { label: "Risk", key: "risk_score", icon: Shield },
  ]

  return (
    <div className="border-b border-gray-800/60">
      <div className="p-3 space-y-2">
        <div className="flex items-center gap-1.5 text-[11px] text-gray-400 font-semibold uppercase tracking-wider">
          <Shield className="w-3 h-3 text-blue-400" /> Scoring
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          {scoreItems.map((s) => (
            <div key={s.key} className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/30">
              <div className="flex items-center gap-1">
                <s.icon className="w-2.5 h-2.5 text-gray-500" />
                <span className="text-[10px] text-gray-400">{s.label}</span>
              </div>
              <span className={cn("text-[10px] font-mono font-bold", getScoreColor(scoreValue(scores, s.key)))}>
                {scoreValue(scores, s.key)}
              </span>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between px-2 py-1.5 rounded bg-gray-800/40">
          <span className="text-xs font-semibold text-gray-300">Overall</span>
          <div className="flex items-center gap-2">
            <span className={cn("text-sm font-bold font-mono", getScoreColor(scoreValue(scores, "overall")))}>
              {scoreValue(scores, "overall")}
            </span>
            <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-semibold", getStatusBadge(strVal(scores.status)))}>
              {strVal(scores.status)}
            </span>
          </div>
        </div>
      </div>

      {alignment && (
        <div className="px-3 pb-2">
          <div className={cn("flex items-center gap-1.5 text-[11px] px-2 py-1 rounded",
            alignment.status === "ALIGNED" ? "bg-green-500/10 text-green-400" :
            alignment.status === "CONFLICTING" ? "bg-red-500/10 text-red-400" : "bg-yellow-500/10 text-yellow-400")}>
            {alignment.status === "ALIGNED" ? <TrendingUp className="w-3 h-3" /> :
             alignment.status === "CONFLICTING" ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
            MTF: {strVal(alignment.status)} ({typeof alignment.confidence === "number" ? alignment.confidence : 0}%)
          </div>
          {Array.isArray(alignment.conflicts) && alignment.conflicts.length > 0 && (
            <div className="mt-1 space-y-0.5">
              {alignment.conflicts.slice(0, 2).map((c: string, i: number) => (
                <div key={i} className="text-[10px] text-red-400/80 px-2">⚠ {c}</div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="px-3 pb-3">
        <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-1.5">Timeframes</div>
        <div className="overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800/40">
                <th className="text-left py-1 pr-2">TF</th>
                <th className="text-left py-1 pr-2">Signal</th>
                <th className="text-left py-1 pr-2">Trend</th>
                <th className="text-right py-1 pr-2">Bull</th>
                <th className="text-right py-1 pr-2">Bear</th>
                <th className="text-right py-1 pr-2">BOS</th>
              </tr>
            </thead>
            <tbody>
              {tfList.map((tf) => {
                const d = timeframes[tf] as Record<string, unknown> | undefined
                if (!d || d.error) return null
                return (
                  <tr key={tf} className="border-b border-gray-800/20 hover:bg-gray-800/10">
                    <td className="py-1 pr-2 font-mono text-gray-300">{tf}</td>
                    <td className="py-1 pr-2">
                      <span className={cn("font-semibold", getSignalColor(strVal(d.signal)))}>
                        {strVal(d.signal)}
                      </span>
                    </td>
                    <td className="py-1 pr-2">
                      <span className={cn("flex items-center gap-0.5", 
                        d.trend === "bullish" ? "text-green-400" : d.trend === "bearish" ? "text-red-400" : "text-gray-500")}>
                        {d.trend === "bullish" ? <TrendingUp className="w-2.5 h-2.5" /> :
                         d.trend === "bearish" ? <TrendingDown className="w-2.5 h-2.5" /> : <Minus className="w-2.5 h-2.5" />}
                        {strVal(d.trend)}
                      </span>
                    </td>
                    <td className="py-1 pr-2 text-right text-green-400 font-mono">{typeof d.bullish_score === "number" ? d.bullish_score : "-"}</td>
                    <td className="py-1 pr-2 text-right text-red-400 font-mono">{typeof d.bearish_score === "number" ? d.bearish_score : "-"}</td>
                    <td className="py-1 pr-2 text-right font-mono text-gray-400">{typeof d.bos === "number" ? d.bos : 0}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {sr && typeof sr.nearest_support === "number" && (
        <div className="px-3 pb-3">
          <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-1.5">S/R Levels</div>
          <div className="space-y-1 text-[10px]">
            <div className="flex justify-between px-2 py-1 rounded bg-red-500/5">
              <span className="text-red-400">Resistance</span>
              <span className="font-mono text-gray-300">${Number(sr.nearest_resistance).toFixed(2)}</span>
            </div>
            <div className="flex justify-between px-2 py-1 rounded bg-green-500/5">
              <span className="text-green-400">Support</span>
              <span className="font-mono text-gray-300">${Number(sr.nearest_support).toFixed(2)}</span>
            </div>
            <div className="flex justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-500">Strongest R</span>
              <span className="font-mono text-gray-400">${Number(sr.strongest_resistance).toFixed(2)}</span>
            </div>
            <div className="flex justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-500">Strongest S</span>
              <span className="font-mono text-gray-400">${Number(sr.strongest_support).toFixed(2)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function getScoreColor(v: number): string {
  if (v >= 80) return "text-green-400"
  if (v >= 60) return "text-blue-400"
  if (v >= 40) return "text-yellow-400"
  return "text-red-400"
}

function getStatusBadge(status: string): string {
  switch (status) {
    case "STRONG_TRADE_READY": return "bg-green-500/20 text-green-400 border border-green-500/30"
    case "TRADE_READY": return "bg-blue-500/20 text-blue-400 border border-blue-500/30"
    case "WATCHLIST": return "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30"
    default: return "bg-gray-500/20 text-gray-400 border border-gray-500/30"
  }
}

function getSignalColor(signal: string): string {
  switch (signal) {
    case "STRONG_LONG": return "text-green-400"
    case "LONG": return "text-green-300"
    case "STRONG_SHORT": return "text-red-400"
    case "SHORT": return "text-red-300"
    default: return "text-gray-500"
  }
}
