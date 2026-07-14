"use client"

import { memo } from "react"
import { useMarketStore } from "@/store/market"
import { cn, confidenceColor } from "@/lib/utils"
import { Brain, AlertCircle } from "lucide-react"

const MarketRegimeBadge = memo(function MarketRegimeBadge({ label, active, color }: {
  label: string; active: boolean; color: string
}) {
  return (
    <div className={cn("flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-all duration-300",
      active
        ? `${color} text-white shadow-sm`
        : "bg-gray-800/30 text-gray-600")}>
      <div className={cn("w-1.5 h-1.5 rounded-full", active ? "bg-white/60" : "bg-gray-700")} />
      {label}
    </div>
  )
})

const ScoreBar = memo(function ScoreBar({ label, value, color }: {
  label: string; value: number; color: string
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-gray-500 w-20">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-500", color)}
          style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
      <span className={cn("text-[10px] font-mono font-medium w-8 text-right", color.replace("bg-", "text-"))}>
        {Math.round(value)}
      </span>
    </div>
  )
})

export function AIConfidencePanel() {
  const brain = useMarketStore((s) => s.brain)
  const isLive = useMarketStore((s) => s.isLive)

  const assessments = Object.entries(brain)
    .sort(([, a], [, b]) => (b?.overall_market_score ?? 0) - (a?.overall_market_score ?? 0))
    .slice(0, 3)

  if (!isLive && assessments.length === 0) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">AI Intelligence</h3>
          <Brain className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <div className="flex flex-col items-center justify-center py-6 text-gray-600">
          <AlertCircle className="w-6 h-6 text-gray-700 mb-2" />
          <span className="text-xs">Connecting to AI Brain...</span>
        </div>
      </div>
    )
  }

  const top = assessments[0]?.[1]
  if (!top) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">AI Intelligence</h3>
          <Brain className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <div className="flex flex-col items-center justify-center py-6 text-gray-600">
          <span className="text-xs">Analyzing market data...</span>
        </div>
      </div>
    )
  }

  const confidence = top.confidence ?? top.overall_market_score ?? 50
  const longProb = top.bull_probability ?? 50
  const shortProb = top.bear_probability ?? 50

  const regime = top.regime || (
    confidence >= 80 ? "Strong Trend" : confidence >= 60 ? "Trending" : confidence >= 40 ? "Neutral" : "Choppy"
  )
  const regimes = [
    { label: "Strong Trend", color: "bg-green-600", active: regime === "strong_bullish" || regime === "Strong Trend" },
    { label: "Trending", color: "bg-blue-600", active: regime === "bullish" || regime === "Trending" },
    { label: "Neutral", color: "bg-yellow-600", active: regime === "neutral" },
    { label: "Choppy", color: "bg-red-600", active: regime === "bearish" || regime === "strong_bearish" || regime === "Choppy" },
  ]

  const factors = top.contributing_factors || []

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain className="w-3.5 h-3.5 text-purple-400" />
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">AI Intelligence</h3>
        </div>
        {isLive && <span className="text-[9px] text-green-500">● LIVE</span>}
      </div>

      <div className="flex items-center gap-4 mb-3">
        <div className="relative w-16 h-16 flex items-center justify-center flex-shrink-0">
          <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="15.5" fill="none" stroke="#1f2937" strokeWidth="3" />
            <circle cx="18" cy="18" r="15.5" fill="none"
              stroke={confidence >= 85 ? "#22c55e" : confidence >= 70 ? "#3b82f6" : confidence >= 50 ? "#eab308" : "#ef4444"}
              strokeWidth="3"
              strokeDasharray={`${(confidence / 100) * 97.4} 97.4`}
              strokeLinecap="round"
              className="transition-all duration-700" />
          </svg>
          <span className={cn("absolute text-lg font-bold font-mono", confidenceColor(confidence))}>
            {Math.round(confidence)}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-sm font-semibold text-white">{assessments[0]?.[0]}</span>
            <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-semibold",
              top.bull_probability > top.bear_probability
                ? "bg-green-900/50 text-green-400"
                : "bg-red-900/50 text-red-400")}>
              {top.bull_probability > top.bear_probability ? "BULLISH" : "BEARISH"}
            </span>
          </div>
          <div className="flex items-center gap-4 text-[10px] text-gray-500">
            <span>Bull: {Math.round(longProb)}%</span>
            <span>Bear: {Math.round(shortProb)}%</span>
            <span>Crash: {Math.round(top.crash_probability || 0)}%</span>
            {top.alt_season_probability != null && (
              <span>Alt: {Math.round(top.alt_season_probability)}%</span>
            )}
          </div>
        </div>
      </div>

      <div className="flex gap-1 mb-3">
        {regimes.map((r) => (
          <MarketRegimeBadge key={r.label} {...r} />
        ))}
      </div>

      {(top.short_squeeze_probability || top.long_squeeze_probability) ? (
        <div className="text-[10px] text-gray-500 mb-2 flex gap-2">
          <span>Short squeeze: {Math.round(top.short_squeeze_probability || 0)}%</span>
          <span>Long squeeze: {Math.round(top.long_squeeze_probability || 0)}%</span>
        </div>
      ) : null}

      <ScoreBar label="Overall" value={top.overall_market_score || 50} color="bg-blue-500" />
      <ScoreBar label="Confidence" value={confidence} color="bg-purple-500" />

      {factors.length > 0 && (
        <div className="mt-2 space-y-0.5">
          {factors.slice(0, 3).map((f: string, i: number) => (
            <div key={i} className="text-[9px] text-gray-500 flex items-start gap-1">
              <span className="text-gray-700 mt-0.5">•</span>
              {f}
            </div>
          ))}
        </div>
      )}

      {assessments.length > 1 && (
        <div className="mt-2 pt-2 border-t border-gray-800">
          <div className="text-[9px] text-gray-600 mb-1">Other assessments</div>
          {assessments.slice(1).map(([sym, a]) => (
            <div key={sym} className="flex items-center justify-between text-[10px] text-gray-500">
              <span>{sym}</span>
              <span className={cn("font-mono", a.overall_market_score >= 70 ? "text-green-400" : "text-yellow-400")}>
                {Math.round(a.overall_market_score || 0)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
