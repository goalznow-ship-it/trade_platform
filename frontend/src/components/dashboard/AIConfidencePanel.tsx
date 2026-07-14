"use client"

import { useEffect, useState, useCallback, memo } from "react"
import { api } from "@/lib/api"
import { cn, confidenceColor, ago } from "@/lib/utils"
import {
  Brain, TrendingUp, TrendingDown, BarChart3, AlertCircle, Gauge,
} from "lucide-react"

interface Signal {
  confidence?: number
  score?: number
  long_probability?: number
  short_probability?: number
  direction?: string
  trend_strength?: number
  volatility_score?: number
  liquidity_score?: number
  momentum_score?: number
  bias?: string
  reasons?: string[]
  reason?: string
  factors?: string[]
  ai_factors?: string[]
  symbol: string
  timeframe?: string
}

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
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<string>("")

  const load = useCallback(async () => {
    try {
      const data = await api.scanAllV2(0)
      const list = data?.signals || data || []
      setSignals(Array.isArray(list) ? list.slice(0, 3) : [])
      setLastFetch(new Date().toISOString())
      setError(null)
    } catch {
      setError("AI analysis unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(load, 0)
    const interval = setInterval(load, 60000)
    return () => {
      clearTimeout(timer)
      clearInterval(interval)
    }
  }, [load])

  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-3">
          <div className="h-3 w-24 bg-gray-800 rounded" />
          <div className="h-20 bg-gray-800 rounded" />
          <div className="h-12 bg-gray-800 rounded" />
        </div>
      </div>
    )
  }

  if (error && signals.length === 0) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">AI Intelligence</h3>
          <Brain className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <div className="flex items-center gap-2 text-yellow-400 text-xs">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          {error}
        </div>
      </div>
    )
  }

  const top = signals[0]
  const confidence = top?.confidence || top?.score || 0
  const longProb = top?.long_probability ?? (top?.direction === "long" ? confidence : 100 - confidence)
  const shortProb = top?.short_probability ?? (top?.direction === "short" ? confidence : 100 - confidence)

  const regime = confidence >= 80 ? "Strong Trend" : confidence >= 60 ? "Trending" : confidence >= 40 ? "Neutral" : "Choppy"
  const regimes = [
    { label: "Strong Trend", color: "bg-green-600", active: regime === "Strong Trend" },
    { label: "Trending", color: "bg-blue-600", active: regime === "Trending" },
    { label: "Neutral", color: "bg-yellow-600", active: regime === "Neutral" },
    { label: "Choppy", color: "bg-red-600", active: regime === "Choppy" },
  ]

  const trendStrength = top?.trend_strength ?? confidence
  const volatilityScore = top?.volatility_score ?? 50
  const liquidityScore = top?.liquidity_score ?? 70
  const momentumScore = top?.momentum_score ?? 50
  const bias = top?.bias || top?.direction || "neutral"

  const reasons = Array.isArray(top?.reasons) ? top.reasons : top?.reason ? [top.reason] : []
  const factors = top?.factors || top?.ai_factors || []

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain className="w-3.5 h-3.5 text-purple-400" />
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">AI Intelligence</h3>
        </div>
        {lastFetch && <span className="text-[9px] text-gray-600">{ago(lastFetch)}</span>}
      </div>

      {!top ? (
        <div className="flex flex-col items-center justify-center py-6 text-gray-600">
          <BarChart3 className="w-8 h-8 text-gray-700 mb-2" />
          <span className="text-xs">Analyzing market data</span>
        </div>
      ) : (
        <>
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
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-semibold text-white font-mono">{top.symbol}</span>
                <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded",
                  top.direction === "long" ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400")}>
                  {top.direction?.toUpperCase() || "NEUTRAL"}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <Gauge className="w-3 h-3 text-gray-600" />
                <span className="text-xs text-gray-500 font-medium capitalize">{bias} bias</span>
                <span className="text-[10px] text-gray-600">{top.timeframe || "1h"}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 mb-3">
            <div className="p-2.5 rounded-lg bg-gray-800/30">
              <div className="flex items-center gap-1 mb-1">
                <TrendingUp className="w-3 h-3 text-green-400" />
                <span className="text-[10px] text-gray-500">Bull Prob.</span>
              </div>
              <div className="text-base font-bold text-green-400 font-mono">{Math.round(longProb)}%</div>
              <div className="w-full h-1.5 bg-gray-700 rounded mt-1 overflow-hidden">
                <div className="h-full bg-green-500 rounded transition-all duration-500" style={{ width: `${longProb}%` }} />
              </div>
            </div>
            <div className="p-2.5 rounded-lg bg-gray-800/30">
              <div className="flex items-center gap-1 mb-1">
                <TrendingDown className="w-3 h-3 text-red-400" />
                <span className="text-[10px] text-gray-500">Bear Prob.</span>
              </div>
              <div className="text-base font-bold text-red-400 font-mono">{Math.round(shortProb)}%</div>
              <div className="w-full h-1.5 bg-gray-700 rounded mt-1 overflow-hidden">
                <div className="h-full bg-red-500 rounded transition-all duration-500" style={{ width: `${shortProb}%` }} />
              </div>
            </div>
          </div>

          <div className="mb-3">
            <span className="text-[10px] text-gray-500 mb-1.5 block">Market Regime</span>
            <div className="flex gap-1">
              {regimes.map((r) => (
                <MarketRegimeBadge key={r.label} {...r} />
              ))}
            </div>
          </div>

          <div className="space-y-1.5 mb-3">
            <ScoreBar label="Trend Strength" value={trendStrength} color={trendStrength >= 70 ? "bg-green-500" : trendStrength >= 40 ? "bg-blue-500" : "bg-yellow-500"} />
            <ScoreBar label="Volatility" value={volatilityScore} color={volatilityScore >= 70 ? "bg-red-500" : volatilityScore >= 40 ? "bg-yellow-500" : "bg-green-500"} />
            <ScoreBar label="Liquidity" value={liquidityScore} color="bg-cyan-500" />
            <ScoreBar label="Momentum" value={momentumScore} color={momentumScore >= 60 ? "bg-green-500" : "bg-blue-500"} />
          </div>

          {reasons.length > 0 && (
            <div className="mb-2">
              <span className="text-[10px] text-gray-500 mb-1 block">Key Factors</span>
              <div className="text-[10px] text-gray-400 leading-relaxed">
                {reasons.slice(0, 2).join(" · ")}
              </div>
            </div>
          )}

          {factors.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {factors.slice(0, 4).map((f: string, i: number) => (
                <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-gray-800/50 text-gray-500 border border-gray-700/30">
                  {f}
                </span>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
