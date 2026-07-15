"use client"

import { useMarketStore } from "@/store/market"
import { cn, formatPrice } from "@/lib/utils"
import {
  ArrowUpRight, ArrowDownRight,
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

interface AIForecastPanelProps {
  analysis?: AnalysisData | null
  loading?: boolean
}

export function AIForecastPanel({ analysis, loading }: AIForecastPanelProps) {
  const { selectedTimeframe } = useMarketStore()

  if (loading) {
    return (
      <div className="p-3 bg-gray-900/50 rounded-lg border border-gray-800">
        <div className="animate-pulse space-y-2">
          <div className="h-4 w-32 bg-gray-800 rounded" />
          <div className="h-16 bg-gray-800 rounded" />
          <div className="h-8 bg-gray-800 rounded" />
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="p-3 bg-gray-900/50 rounded-lg border border-gray-800 text-center">
        <div className="text-xs text-gray-600">Select a symbol to view AI forecast</div>
      </div>
    )
  }

  const isBullish = analysis.prediction === "long"
  const isBearish = analysis.prediction === "short"
  const conf = analysis.confidence || 0
  const currentPrice = analysis.current_price || analysis.details?.support || 0
  const move = currentPrice * 0.02

  const targets = isBullish
    ? [currentPrice + move * 0.5, currentPrice + move, currentPrice + move * 1.8]
    : [currentPrice - move * 0.5, currentPrice - move, currentPrice - move * 1.8]

  return (
    <div className="p-3 bg-gray-900/50 rounded-lg border border-gray-800 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">AI Forecast</span>
          <span className="text-[10px] text-gray-500">
            Next {selectedTimeframe === "1d" ? "Day" : selectedTimeframe === "4h" ? "4 Hours" : "1 Hour"}
          </span>
        </div>
        <div className={cn(
          "text-[10px] font-bold px-1.5 py-0.5 rounded",
          conf >= 80 ? "bg-green-900/50 text-green-400" :
          conf >= 60 ? "bg-yellow-900/50 text-yellow-400" :
          "bg-red-900/50 text-red-400"
        )}>
          {conf}% confidence
        </div>
      </div>

      {/* Forecast Path Visualization */}
      <div className="relative">
        {/* Current Price */}
        <div className="flex items-center justify-between p-2 rounded bg-gray-800/40 border border-gray-700/30">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-blue-400" />
            <span className="text-[10px] text-gray-500">Current</span>
          </div>
          <span className="text-xs font-bold text-white font-mono">{formatPrice(currentPrice)}</span>
        </div>

        {/* Price Path */}
        <div className="ml-1 mt-1 space-y-1">
          {targets.map((target, i) => {
            const isAbove = target > currentPrice
            const pct = ((target - currentPrice) / currentPrice * 100)
            return (
              <div key={i} className="flex items-center gap-2 pl-4 border-l-2 border-dashed border-gray-700/50 py-1.5">
                <div className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  isBullish && isAbove ? "bg-green-400" :
                  isBearish && !isAbove ? "bg-red-400" : "bg-gray-600"
                )} />
                <div className="flex items-center justify-between flex-1">
                  <div className="flex items-center gap-1">
                    {isBullish ? (
                      <ArrowUpRight className="w-3 h-3 text-green-400" />
                    ) : (
                      <ArrowDownRight className="w-3 h-3 text-red-400" />
                    )}
                    <span className={cn(
                      "text-[11px] font-mono font-medium",
                      isBullish ? "text-green-400" : "text-red-400"
                    )}>
                      {formatPrice(target)}
                    </span>
                  </div>
                  <span className={cn(
                    "text-[10px] font-mono",
                    pct > 0 ? "text-green-400/70" : "text-red-400/70"
                  )}>
                    {pct > 0 ? "+" : ""}{pct.toFixed(1)}%
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Target Range */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded bg-gray-800/30 border border-gray-700/20">
          <div className="text-[9px] text-gray-500 uppercase tracking-wider">Expected Range</div>
          <div className="text-xs font-bold text-white font-mono mt-0.5">
            {formatPrice(targets[0])} - {formatPrice(targets[targets.length - 1])}
          </div>
        </div>
        <div className="p-2 rounded bg-gray-800/30 border border-gray-700/20">
          <div className="text-[9px] text-gray-500 uppercase tracking-wider">Time Horizon</div>
          <div className="text-xs font-bold text-white font-mono mt-0.5">
            {selectedTimeframe === "1d" ? "24H" : selectedTimeframe === "4h" ? "4H" : "1H"}
          </div>
        </div>
        <div className="p-2 rounded bg-gray-800/30 border border-gray-700/20">
          <div className="text-[9px] text-gray-500 uppercase tracking-wider">Invalidation</div>
          <div className="text-xs font-bold text-red-400 font-mono mt-0.5">
            {formatPrice(isBullish ? currentPrice * 0.97 : currentPrice * 1.03)}
          </div>
        </div>
        <div className="p-2 rounded bg-gray-800/30 border border-gray-700/20">
          <div className="text-[9px] text-gray-500 uppercase tracking-wider">Probability</div>
          <div className={cn(
            "text-xs font-bold font-mono mt-0.5",
            isBullish ? "text-green-400" : isBearish ? "text-red-400" : "text-yellow-400"
          )}>
            {isBullish ? analysis.long_probability?.toFixed(0) : isBearish ? analysis.short_probability?.toFixed(0) : 50}%
          </div>
        </div>
      </div>
    </div>
  )
}
