"use client"

import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus, Activity, BarChart3, Volume2, Zap, Shield, Brain, AlertTriangle } from "lucide-react"

interface Props {
  timeframes: Record<string, unknown>
  scores: Record<string, unknown>
  alignment: Record<string, unknown>
  sr: Record<string, unknown>
  analysis: Record<string, unknown> | null
}

function scoreValue(s: Record<string, unknown>, key: string): number {
  const v = s[key]
  return typeof v === "number" ? v : 0
}

function strVal(v: unknown): string {
  if (v == null) return "N/A"
  return String(v)
}

function numVal(v: unknown): number {
  return typeof v === "number" ? v : 0
}

export function SKHYAnalysisPanel({ timeframes, scores, alignment, sr, analysis }: Props) {
  const tfList = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

  const scoreItems = [
    { label: "Trend", key: "trend_score", icon: TrendingUp },
    { label: "Struktur", key: "structure_score", icon: BarChart3 },
    { label: "Momentum", key: "momentum_score", icon: Zap },
    { label: "Həcm", key: "volume_score", icon: Volume2 },
    { label: "Likvidite", key: "liquidity_score", icon: Activity },
    { label: "Pattern", key: "pattern_score", icon: BarChart3 },
    { label: "Fyuçers", key: "futures_score", icon: BarChart3 },
    { label: "OrderFlow", key: "orderflow_score", icon: Activity },
    { label: "MTF", key: "multitimeframe_score", icon: BarChart3 },
    { label: "Risk", key: "risk_score", icon: Shield },
  ]

  const explanation = strVal(analysis?.explanation_az)
  const triggers = (analysis?.triggers || {}) as Record<string, unknown>
  const ltPrice = numVal(triggers.long_trigger_price)
  const stPrice = numVal(triggers.short_trigger_price)
  const longConditions = triggers.long_trigger_conditions as string[] | undefined
  const shortConditions = triggers.short_trigger_conditions as string[] | undefined
  const bullishInvalidation = numVal(triggers.bullish_invalidation)
  const bearishInvalidation = numVal(triggers.bearish_invalidation)

  return (
    <div className="border-b border-gray-800/60">
      {/* Hazırda nə baş verir? */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="flex items-center gap-1.5 text-[11px] text-blue-400 font-semibold uppercase tracking-wider mb-2">
          <Brain className="w-3 h-3" /> Hazırda nə baş verir?
        </div>
        <div className="text-[10px] text-gray-400 leading-relaxed">
          {explanation || "Məlumat hazırlanır..."}
        </div>
      </div>

      {/* LONG nə vaxt aktivləşər? */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="flex items-center gap-1.5 text-[11px] text-green-400 font-semibold uppercase tracking-wider mb-2">
          <TrendingUp className="w-3 h-3" /> ALIŞ (LONG) nə vaxt aktivləşər?
        </div>
        <div className="text-[10px] text-gray-400 space-y-1">
          {longConditions && longConditions.length > 0 ? (
            longConditions.slice(0, 4).map((c, i) => (
              <div key={i} className="flex items-start gap-1">
                <span className="text-green-500/60 mt-0.5">•</span>
                <span>{c}</span>
              </div>
            ))
          ) : (
            <span>ALIŞ üçün hələ şərtlər formalaşmayıb</span>
          )}
          {ltPrice > 0 && (
            <div className="mt-1 text-[11px] font-mono text-green-400">
              Giriş: ${ltPrice.toFixed(2)}
            </div>
          )}
          {bullishInvalidation > 0 && (
            <div className="flex items-center gap-1 text-[10px] text-red-400/70">
              <AlertTriangle className="w-2.5 h-2.5" />
              Ləğv: ${bullishInvalidation.toFixed(2)} altında
            </div>
          )}
        </div>
      </div>

      {/* SHORT nə vaxt aktivləşər? */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="flex items-center gap-1.5 text-[11px] text-red-400 font-semibold uppercase tracking-wider mb-2">
          <TrendingDown className="w-3 h-3" /> SATIŞ (SHORT) nə vaxt aktivləşər?
        </div>
        <div className="text-[10px] text-gray-400 space-y-1">
          {shortConditions && shortConditions.length > 0 ? (
            shortConditions.slice(0, 4).map((c, i) => (
              <div key={i} className="flex items-start gap-1">
                <span className="text-red-500/60 mt-0.5">•</span>
                <span>{c}</span>
              </div>
            ))
          ) : (
            <span>SATIŞ üçün hələ şərtlər formalaşmayıb</span>
          )}
          {stPrice > 0 && (
            <div className="mt-1 text-[11px] font-mono text-red-400">
              Giriş: ${stPrice.toFixed(2)}
            </div>
          )}
          {bearishInvalidation > 0 && (
            <div className="flex items-center gap-1 text-[10px] text-red-400/70">
              <AlertTriangle className="w-2.5 h-2.5" />
              Ləğv: ${bearishInvalidation.toFixed(2)} üzərində
            </div>
          )}
        </div>
      </div>

      {/* Scoring */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="flex items-center gap-1.5 text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-2">
          <Shield className="w-3 h-3 text-blue-400" /> Bal Sistemi
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
        <div className="flex items-center justify-between px-2 py-1.5 mt-1 rounded bg-gray-800/40">
          <span className="text-xs font-semibold text-gray-300">Ümumi</span>
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

      {/* MTF Alignment */}
      {alignment && (
        <div className="p-3 border-b border-gray-800/40">
          <div className={cn("flex items-center gap-1.5 text-[11px] px-2 py-1 rounded",
            alignment.status === "ALIGNED" ? "bg-green-500/10 text-green-400" :
            alignment.status === "CONFLICTING" ? "bg-red-500/10 text-red-400" : "bg-yellow-500/10 text-yellow-400")}>
            {alignment.status === "ALIGNED" ? <TrendingUp className="w-3 h-3" /> :
             alignment.status === "CONFLICTING" ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
            MTF Uyğunluq: {strVal(alignment.status)} ({typeof alignment.confidence === "number" ? alignment.confidence : 0}%)
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

      {/* Timeframe Table */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-1.5">Zaman Çərçivələri</div>
        <div className="overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800/40">
                <th className="text-left py-1 pr-2">TF</th>
                <th className="text-left py-1 pr-2">Siqnal</th>
                <th className="text-left py-1 pr-2">Trend</th>
                <th className="text-right py-1 pr-2">Alış</th>
                <th className="text-right py-1 pr-2">Satış</th>
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
                        {d.trend === "bullish" ? "Yüksələn" : d.trend === "bearish" ? "Enən" : "Neytral"}
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

      {/* Ən yaxın risk nədir? */}
      <div className="p-3">
        <div className="flex items-center gap-1.5 text-[11px] text-yellow-400 font-semibold uppercase tracking-wider mb-2">
          <AlertTriangle className="w-3 h-3" /> Ən yaxın risk nədir?
        </div>
        <div className="text-[10px] text-gray-400 space-y-1">
          {sr && numVal(sr.nearest_support) > 0 && (
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20">
              <span>Dəstək səviyyəsi</span>
              <span className="font-mono text-green-400">${numVal(sr.nearest_support).toFixed(2)}</span>
            </div>
          )}
          {sr && numVal(sr.nearest_resistance) > 0 && (
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20">
              <span>Müqavimət səviyyəsi</span>
              <span className="font-mono text-red-400">${numVal(sr.nearest_resistance).toFixed(2)}</span>
            </div>
          )}
          {sr && numVal(sr.distance_to_support) > 0 && (
            <div className="text-[9px] text-gray-500 px-2">
              Dəstəyə məsafə: ${numVal(sr.distance_to_support).toFixed(2)} | Müqavimətə məsafə: ${numVal(sr.distance_to_resistance).toFixed(2)}
            </div>
          )}
          <div className="flex items-center gap-1 px-2 py-1 text-yellow-400/60">
            <AlertTriangle className="w-2.5 h-2.5" />
            <span className="text-[9px]">
              {bullishInvalidation > 0 ? `ALIŞ ləğvi: $${bullishInvalidation.toFixed(2)}` : ""}
              {bullishInvalidation > 0 && bearishInvalidation > 0 ? " | " : ""}
              {bearishInvalidation > 0 ? `SATIŞ ləğvi: $${bearishInvalidation.toFixed(2)}` : ""}
            </span>
          </div>
        </div>
      </div>
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
