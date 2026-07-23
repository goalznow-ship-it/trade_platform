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
  signal?: {
    error?: string
    direction?: string
    confidence?: number
    stop_loss?: number
    take_profit_1?: number
    take_profit_2?: number
    take_profit_3?: number
  } | null
  loading?: boolean
}

function displayPrice(value?: number) {
  return value && value > 0 ? formatPrice(value) : "N/A"
}

export function AIForecastPanel({ analysis, signal, loading }: AIForecastPanelProps) {
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
  const currentPrice = analysis.current_price
  const hasDirectionalForecast = (isBullish || isBearish)
    && conf >= 70
    && !signal?.error
    && Boolean(signal?.take_profit_1)
  const targets = [
    signal?.take_profit_1,
    signal?.take_profit_2,
    signal?.take_profit_3,
  ].filter((target): target is number => Boolean(target && target > 0))

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
          <span className="text-xs font-bold text-white font-mono">{displayPrice(currentPrice)}</span>
        </div>

        {hasDirectionalForecast && currentPrice ? (
          <div className="ml-1 mt-1 space-y-1">
            {targets.map((target, i) => {
            const pct = ((target - currentPrice) / currentPrice * 100)
            return (
              <div key={i} className="flex items-center gap-2 pl-4 border-l-2 border-dashed border-gray-700/50 py-1.5">
                <div className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  isBullish ? "bg-green-400" : "bg-red-400"
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
                      TP{i + 1} {formatPrice(target)}
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
        ) : (
          <div className="mt-2 p-3 rounded border border-amber-900/30 bg-amber-900/10 text-xs text-amber-300">
            No directional forecast: signal is WAIT or confidence is below 70%.
          </div>
        )}
      </div>

      {/* Target Range */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded bg-gray-800/30 border border-gray-700/20">
          <div className="text-[9px] text-gray-500 uppercase tracking-wider">Expected Range</div>
          <div className="text-xs font-bold text-white font-mono mt-0.5">
            {hasDirectionalForecast && targets.length
              ? `${displayPrice(targets[0])} - ${displayPrice(targets[targets.length - 1])}`
              : "N/A"}
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
            {hasDirectionalForecast ? displayPrice(signal?.stop_loss) : "N/A"}
          </div>
        </div>
        <div className="p-2 rounded bg-gray-800/30 border border-gray-700/20">
          <div className="text-[9px] text-gray-500 uppercase tracking-wider">Probability</div>
          <div className={cn(
            "text-xs font-bold font-mono mt-0.5",
            isBullish ? "text-green-400" : isBearish ? "text-red-400" : "text-yellow-400"
          )}>
            {hasDirectionalForecast && typeof (isBullish ? analysis.long_probability : analysis.short_probability) === "number"
              ? `${(isBullish ? analysis.long_probability : analysis.short_probability)?.toFixed(0)}%`
              : "N/A"}
          </div>
        </div>
      </div>
    </div>
  )
}
