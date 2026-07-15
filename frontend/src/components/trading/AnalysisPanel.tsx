"use client"

import { useEffect, useState } from "react"
import { useMarketStore } from "@/store/market"
import { api } from "@/lib/api"
import { Badge } from "@/components/ui/Badge"
import { cn, formatPrice } from "@/lib/utils"
import {
  Brain,
  TrendingUp,
  TrendingDown,
} from "lucide-react"

interface AnalysisData {
  confidence?: number
  prediction?: string
  risk_level?: string
  long_probability?: number
  short_probability?: number
  summary?: string
  scores?: Record<string, number>
  details?: {
    rsi?: number
    macd?: number
    support?: number
    resistance?: number
  }
}

interface SignalItem {
  direction: string
  signal_type: string
  confidence: number
  entry_price: number
  stop_loss: number
  take_profit_1: number
  reason: string
}

interface SignalsData {
  signals?: SignalItem[]
  confidence?: Record<string, number>
}

export function AnalysisPanel() {
  const { selectedSymbol } = useMarketStore()
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null)
  const [signals, setSignals] = useState<SignalsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function loadAnalysis() {
      setLoading(true)
      try {
        const [a, s] = await Promise.all([
          api.getAIAnalysis(selectedSymbol),
          api.getSignals(selectedSymbol),
        ])
        if (!cancelled) {
          setAnalysis(a)
          setSignals(s)
        }
      } catch (e) {
        console.error(e)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadAnalysis()
    const interval = setInterval(loadAnalysis, 30000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [selectedSymbol])

  if (loading) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        <Brain className="w-8 h-8 mx-auto mb-2 animate-pulse text-blue-500" />
        Analyzing market...
      </div>
    )
  }

  const ai = analysis || {}
  const sigs = signals?.signals || []

  return (
    <div className="p-3 space-y-3 overflow-auto h-full">
      {/* AI Score */}
      <div className="text-center p-4 rounded-xl bg-gradient-to-br from-blue-600/10 to-purple-600/10 border border-blue-500/20">
        <div className="text-3xl font-bold text-white mb-1">{ai.confidence || 0}%</div>
        <div className="text-xs text-gray-400">AI Confidence Score</div>
        <div className="flex justify-center gap-4 mt-2">
          <Badge variant={ai.prediction === "long" ? "success" : ai.prediction === "short" ? "danger" : "warning"}>
            {ai.prediction?.toUpperCase() || "NEUTRAL"}
          </Badge>
          <Badge variant={ai.risk_level === "low" ? "success" : ai.risk_level === "high" ? "danger" : "warning"}>
            Risk: {ai.risk_level?.toUpperCase()}
          </Badge>
        </div>
      </div>

      {/* Signal Probability */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-3 rounded-lg bg-green-900/10 border border-green-900/30">
          <div className="text-lg font-bold text-green-400">{ai.long_probability || 0}%</div>
          <div className="text-xs text-gray-400">Long Probability</div>
        </div>
        <div className="p-3 rounded-lg bg-red-900/10 border border-red-900/30">
          <div className="text-lg font-bold text-red-400">{ai.short_probability || 0}%</div>
          <div className="text-xs text-gray-400">Short Probability</div>
        </div>
      </div>

      {/* AI Summary */}
      {ai.summary && (
        <div className="text-xs text-gray-400 bg-gray-800/50 rounded-lg p-3 leading-relaxed">
          {ai.summary}
        </div>
      )}

      {/* Score Breakdown */}
      {ai.scores && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-gray-400">Score Breakdown</div>
          {Object.entries(ai.scores).map(([key, value]) => (
            <div key={key} className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-24 capitalize">{key.replace("_", " ")}</span>
              <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    (value as number) > 0 ? "bg-green-500" : (value as number) < 0 ? "bg-red-500" : "bg-gray-600"
                  )}
                  style={{ width: `${Math.abs((value as number) * 100)}%` }}
                />
              </div>
              <span className={cn(
                "text-xs font-mono w-10 text-right",
                (value as number) > 0 ? "text-green-400" : (value as number) < 0 ? "text-red-400" : "text-gray-500"
              )}>
                {((value as number) * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Active Signals */}
      {sigs.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-gray-400">Active Signals</div>
          {sigs.slice(0, 3).map((sig: SignalItem, i: number) => (
            <div
              key={i}
              className={cn(
                "p-3 rounded-lg border",
                sig.direction === "long"
                  ? "bg-green-900/10 border-green-900/30"
                  : "bg-red-900/10 border-red-900/30"
              )}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1">
                  {sig.direction === "long" ? (
                    <TrendingUp className="w-3 h-3 text-green-400" />
                  ) : (
                    <TrendingDown className="w-3 h-3 text-red-400" />
                  )}
                  <span className={cn(
                    "text-xs font-semibold",
                    sig.direction === "long" ? "text-green-400" : "text-red-400"
                  )}>
                    {sig.direction.toUpperCase()}
                  </span>
                  <span className="text-[10px] text-gray-500">{sig.signal_type}</span>
                </div>
                <span className="text-xs font-mono text-white">{sig.confidence}%</span>
              </div>
              <div className="flex justify-between text-[10px] text-gray-500">
                <span>Entry: ${sig.entry_price?.toFixed(2)}</span>
                <span>SL: ${sig.stop_loss?.toFixed(2)}</span>
                <span>TP: ${sig.take_profit_1?.toFixed(2)}</span>
              </div>
              <div className="text-[10px] text-gray-500 mt-1">{sig.reason}</div>
            </div>
          ))}
        </div>
      )}

      {/* Market Details */}
      {ai.details && (
        <div className="grid grid-cols-2 gap-2">
          <div className="text-center p-2 rounded bg-gray-800/50">
            <div className="text-[10px] text-gray-500">RSI</div>
            <div className="text-xs font-medium text-white">{ai.details.rsi?.toFixed(1) || "--"}</div>
          </div>
          <div className="text-center p-2 rounded bg-gray-800/50">
            <div className="text-[10px] text-gray-500">MACD</div>
            <div className={cn("text-xs font-medium", (ai.details.macd || 0) > 0 ? "text-green-400" : "text-red-400")}>
              {ai.details.macd?.toFixed(2) || "--"}
            </div>
          </div>
          <div className="text-center p-2 rounded bg-gray-800/50">
            <div className="text-[10px] text-gray-500">Support</div>
            <div className="text-xs font-medium text-white">{formatPrice(ai.details.support)}</div>
          </div>
          <div className="text-center p-2 rounded bg-gray-800/50">
            <div className="text-[10px] text-gray-500">Resistance</div>
            <div className="text-xs font-medium text-white">{formatPrice(ai.details.resistance)}</div>
          </div>
        </div>
      )}
    </div>
  )
}
