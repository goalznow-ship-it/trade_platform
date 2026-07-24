"use client"

import { useMarketStore } from "@/store/market"
import { cn, formatPrice } from "@/lib/utils"
import {
  ArrowUpRight, ArrowDownRight, Clock, AlertTriangle,
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
    invalidation?: string
    entry_zone?: { min?: number; max?: number; mid?: number }
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
        <div className="animate-pulse flex gap-4">
          <div className="h-4 w-24 bg-gray-800 rounded" />
          <div className="h-4 w-16 bg-gray-800 rounded" />
          <div className="h-4 w-20 bg-gray-800 rounded" />
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="p-3 bg-gray-900/50 rounded-lg border border-gray-800 text-center">
        <div className="text-xs text-gray-600">Simvol seçin — AI proqnozu görünəcək</div>
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
    <div className="bg-gray-900/50 rounded-lg border border-gray-800">
      {/* Header - compact */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-800/50">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold text-gray-300 uppercase tracking-wider">AI Proqnoz</span>
          <span className="text-[9px] text-gray-600">
            <Clock className="w-2.5 h-2.5 inline mr-0.5" />
            {selectedTimeframe === "1d" ? "24H" : selectedTimeframe === "4h" ? "4H" : selectedTimeframe === "1h" ? "1H" : selectedTimeframe}
          </span>
        </div>
        <div className={cn(
          "text-[9px] font-bold px-1.5 py-0.5 rounded",
          conf >= 80 ? "bg-green-900/50 text-green-400" :
          conf >= 60 ? "bg-yellow-900/50 text-yellow-400" : "text-gray-500"
        )}>
          {conf.toFixed(0)}% etibar
        </div>
      </div>

      {/* Body - compact grid */}
      <div className="flex items-center gap-4 p-2.5">
        {/* Direction + Price path */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-gray-500">Cari:</span>
            <span className="font-bold text-white font-mono">{displayPrice(currentPrice)}</span>
          </div>
          {hasDirectionalForecast && currentPrice ? (
            <div className="flex items-center gap-1">
              {targets.map((target, i) => {
                const pct = ((target - currentPrice) / currentPrice * 100)
                return (
                  <div key={i} className={cn(
                    "flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-mono",
                    isBullish ? "bg-green-900/20 text-green-400" : "bg-red-900/20 text-red-400"
                  )}>
                    {isBullish ? <ArrowUpRight className="w-2.5 h-2.5" /> : <ArrowDownRight className="w-2.5 h-2.5" />}
                    MH{i + 1} {displayPrice(target)}
                    <span className="ml-0.5 opacity-60">({pct > 0 ? "+" : ""}{pct.toFixed(1)}%)</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <span className="text-[10px] text-amber-400 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Etibarlı proyeksiya üçün breakout təsdiqi gözlənilir
            </span>
          )}
        </div>

        {/* Stats - compact */}
        <div className="flex items-center gap-3 text-[10px] flex-shrink-0">
          <div className="text-center px-2 py-1 rounded bg-gray-800/30">
            <div className="text-gray-500">Range</div>
            <div className="font-bold text-white font-mono">
              {hasDirectionalForecast && targets.length
                ? `${displayPrice(targets[0])}–${displayPrice(targets[targets.length - 1])}`
                : "N/A"}
            </div>
          </div>
          <div className="text-center px-2 py-1 rounded bg-gray-800/30">
            <div className="text-gray-500">Invalidasiya</div>
            <div className="font-bold text-red-400 font-mono">
              {hasDirectionalForecast ? displayPrice(signal?.stop_loss) : "N/A"}
            </div>
          </div>
          <div className="text-center px-2 py-1 rounded bg-gray-800/30">
            <div className="text-gray-500">Ehtimal</div>
            <div className={cn("font-bold", isBullish ? "text-green-400" : isBearish ? "text-red-400" : "text-yellow-400")}>
              {hasDirectionalForecast
                ? `${((isBullish ? analysis.long_probability : analysis.short_probability) || 50).toFixed(0)}%`
                : "N/A"}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
