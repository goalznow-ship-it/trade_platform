"use client"

import { cn } from "@/lib/utils"
import {
  Brain, TrendingUp, TrendingDown, Activity,
  BarChart3, Volume2, Shield,
} from "lucide-react"

interface AnalysisDetails {
  rsi?: number
  macd?: number
  support?: number
  resistance?: number
  [key: string]: unknown
}

interface AnalysisData {
  prediction?: string
  confidence?: number
  long_probability?: number
  short_probability?: number
  risk_level?: string
  scores?: Record<string, number>
  details?: AnalysisDetails
  summary?: string
  current_price?: number
  [key: string]: unknown
}

interface AIPredictionPanelProps {
  analysis?: AnalysisData | null
  loading?: boolean
}

export function AIPredictionPanel({ analysis, loading }: AIPredictionPanelProps) {
  if (loading) {
    return (
      <div className="p-4 space-y-3">
        <div className="animate-pulse space-y-3">
          <div className="h-24 bg-gray-800 rounded-xl" />
          <div className="h-20 bg-gray-800 rounded-xl" />
          <div className="h-32 bg-gray-800 rounded-xl" />
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="p-4 text-center text-gray-600 text-sm">
        <Brain className="w-8 h-8 mx-auto mb-2 text-gray-700" />
        Select a symbol and timeframe to view AI analysis
      </div>
    )
  }

  const isBullish = analysis.prediction === "long"
  const isBearish = analysis.prediction === "short"
  const isNeutral = analysis.prediction === "neutral"
  const conf = analysis.confidence || 0
  const risk = analysis.risk_level || "unknown"
  const scores = analysis.scores || {}
  const details = analysis.details || {}

  const factorItems = [
    { key: "trend", label: "Trend", score: scores.trend, icon: TrendingUp },
    { key: "momentum", label: "Momentum", score: scores.momentum, icon: Activity },
    { key: "volume", label: "Volume", score: scores.volume, icon: Volume2 },
    { key: "liquidity", label: "Liquidity", score: scores.liquidity, icon: BarChart3 },
    { key: "smc", label: "Smart Money", score: scores.smc, icon: Shield },
    { key: "risk", label: "Risk Quality", score: scores.risk, icon: TrendingDown },
  ]

  return (
    <div className="p-4 space-y-3">
      {/* Prediction Header */}
      <div className={cn(
        "p-4 rounded-xl border text-center",
        isBullish && "bg-green-900/10 border-green-500/30",
        isBearish && "bg-red-900/10 border-red-500/30",
        isNeutral && "bg-yellow-900/10 border-yellow-500/30",
      )}>
        <div className="text-xs text-gray-500 mb-1">AI Market Direction</div>
        <div className={cn(
          "text-xl font-bold",
          isBullish && "text-green-400",
          isBearish && "text-red-400",
          isNeutral && "text-yellow-400",
        )}>
          {isBullish ? "BULLISH" : isBearish ? "BEARISH" : "NEUTRAL"}
        </div>
        <div className="flex justify-center gap-6 mt-3">
          <div>
            <div className="text-lg font-bold text-green-400 font-mono">{analysis.long_probability?.toFixed(0) || 0}%</div>
            <div className="text-[10px] text-gray-500">LONG</div>
          </div>
          <div className="w-px bg-gray-700" />
          <div>
            <div className="text-lg font-bold text-red-400 font-mono">{analysis.short_probability?.toFixed(0) || 0}%</div>
            <div className="text-[10px] text-gray-500">SHORT</div>
          </div>
        </div>
        <div className="mt-3 flex justify-center gap-2">
          <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full",
            conf >= 80 ? "bg-green-900/50 text-green-400" :
            conf >= 60 ? "bg-yellow-900/50 text-yellow-400" :
            "bg-red-900/50 text-red-400"
          )}>
            {conf}% confidence
          </span>
          <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full",
            risk === "low" ? "bg-green-900/50 text-green-400" :
            risk === "medium" ? "bg-yellow-900/50 text-yellow-400" :
            "bg-red-900/50 text-red-400"
          )}>
            Risk: {risk.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Factor Scores */}
      <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Factor Analysis</h3>
        <div className="space-y-2">
          {factorItems.map((f) => {
            const hasScore = typeof f.score === "number" && Number.isFinite(f.score)
            const s = hasScore ? f.score as number : 0
            const pct = Math.min(100, Math.abs(s) * 100)
            return (
              <div key={f.key}>
                <div className="flex items-center justify-between text-xs mb-0.5">
                  <div className="flex items-center gap-1">
                    <f.icon className={cn("w-3 h-3", s > 0 ? "text-green-400" : s < 0 ? "text-red-400" : "text-gray-500")} />
                    <span className="text-gray-400">{f.label}</span>
                  </div>
                  <span className={cn("font-mono font-medium", s > 0 ? "text-green-400" : s < 0 ? "text-red-400" : "text-gray-500")}>
                    {hasScore ? `${(s * 100).toFixed(0)}%` : "N/A"}
                  </span>
                </div>
                <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all", s > 0 ? "bg-green-500" : s < 0 ? "bg-red-500" : "bg-gray-600")}
                    style={{ width: hasScore ? `${pct}%` : "0%" }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Key Levels */}
      {details.support || details.resistance ? (
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Key Levels</h3>
          <div className="grid grid-cols-2 gap-2">
            <div className="p-2 rounded-lg bg-gray-800/30">
              <div className="text-[10px] text-gray-500">Support</div>
              <div className="text-sm font-bold text-green-400 font-mono">${details.support?.toFixed(2) || "--"}</div>
            </div>
            <div className="p-2 rounded-lg bg-gray-800/30">
              <div className="text-[10px] text-gray-500">Resistance</div>
              <div className="text-sm font-bold text-red-400 font-mono">${details.resistance?.toFixed(2) || "--"}</div>
            </div>
            <div className="p-2 rounded-lg bg-gray-800/30">
              <div className="text-[10px] text-gray-500">RSI</div>
              <div className={cn("text-sm font-bold font-mono", (details.rsi || 0) > 70 ? "text-red-400" : (details.rsi || 0) < 30 ? "text-green-400" : "text-white")}>
                {details.rsi?.toFixed(1) || "--"}
              </div>
            </div>
            <div className="p-2 rounded-lg bg-gray-800/30">
              <div className="text-[10px] text-gray-500">MACD</div>
              <div className={cn("text-sm font-bold font-mono", (details.macd || 0) > 0 ? "text-green-400" : "text-red-400")}>
                {details.macd?.toFixed(2) || "--"}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {/* Summary */}
      {analysis.summary && (
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <div className="flex items-center gap-1 mb-1">
            <Brain className="w-3 h-3 text-purple-400" />
            <span className="text-[10px] text-gray-500 uppercase tracking-wider">AI Summary</span>
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">{analysis.summary}</p>
        </div>
      )}
    </div>
  )
}
