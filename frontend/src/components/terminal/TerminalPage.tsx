"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { useMarketStore } from "@/store/market"
import { AIChart } from "@/components/terminal/AIChart"
import { AIPredictionPanel } from "@/components/terminal/AIPredictionPanel"
import { TradeDecisionCard } from "@/components/terminal/TradeDecisionCard"
import { AIForecastPanel } from "@/components/terminal/AIForecastPanel"

interface AnalysisData {
  prediction?: string
  confidence?: number
  long_probability?: number
  short_probability?: number
  risk_level?: string
  scores?: Record<string, number>
  details?: Record<string, unknown>
  summary?: string
  current_price?: number
  [key: string]: unknown
}

interface ExplainData {
  reasons?: string[]
  warnings?: string[]
  suggestions?: Record<string, unknown>
  key_levels?: Record<string, unknown>
  [key: string]: unknown
}

interface InstitutionalSignal {
  error?: string
  direction?: string
  confidence?: number
  current_price?: number
  invalidation?: string
  reasons?: string[]
  stop_loss?: number
  take_profit_1?: number
  take_profit_2?: number
  take_profit_3?: number
  entry_zone?: { min?: number; max?: number; mid?: number }
  indicators?: Record<string, unknown>
  institutional_score?: {
    abs_score?: number
    long_probability?: number
    short_probability?: number
    risk_level?: string
    scores?: Record<string, number>
    weights?: Record<string, number>
    details?: Record<string, unknown>
  }
  execution?: { rejection_reasons?: string[]; approved?: boolean }
  position_sizing?: { leverage?: number; position_size?: number }
}

export function TerminalPage() {
  const { selectedSymbol, selectedTimeframe, tickers } = useMarketStore()
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null)
  const [explain, setExplain] = useState<ExplainData | null>(null)
  const [signal, setSignal] = useState<InstitutionalSignal | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const institutional = await api
          .getInstitutionalSignal(selectedSymbol, selectedTimeframe)
          .catch(() => null)
        setSignal(institutional)
        if (institutional) {
          const direction = institutional.direction
          const score = institutional.institutional_score
          const factorScores: Record<string, number> = {}
          for (const [key, value] of Object.entries(score?.scores || {})) {
            const weight = score?.weights?.[key]
            if (typeof value === "number" && typeof weight === "number" && weight > 0) {
              factorScores[key] = value / weight
            }
          }
          setAnalysis({
            prediction: institutional.error ? "neutral" : direction,
            confidence: institutional.confidence ?? score?.abs_score,
            current_price: institutional.current_price,
            long_probability: score?.long_probability,
            short_probability: score?.short_probability,
            risk_level: score?.risk_level,
            scores: factorScores,
            details: {
              ...(score?.details || {}),
              ...(institutional.indicators || {}),
              macd: institutional.indicators?.macd_histogram,
            },
          })
          setExplain(institutional.error ? null : {
            reasons: institutional.reasons || [],
            warnings: [
              institutional.invalidation,
              ...(institutional.execution?.rejection_reasons || []),
            ].filter(Boolean),
            suggestions: {
              entry: institutional.entry_zone?.mid,
              stop_loss: institutional.stop_loss,
              take_profit: institutional.take_profit_1,
              take_profit_2: institutional.take_profit_2,
              take_profit_3: institutional.take_profit_3,
              suggested_leverage: institutional.position_sizing?.leverage,
              position_size: institutional.position_sizing?.position_size,
            },
            key_levels: {
              support: institutional.entry_zone?.min,
              resistance: institutional.entry_zone?.max,
            },
          })
        } else {
          setAnalysis(null)
          setExplain(null)
        }
      } catch {} finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [selectedSymbol, selectedTimeframe])

  const ticker = tickers[selectedSymbol]
    || tickers[selectedSymbol.replace("/", "")]
    || tickers[selectedSymbol.replace("/", "-")]
  const livePrice = ticker?.price && ticker.price > 0
    ? ticker.price
    : signal?.current_price
  const displayedAnalysis = analysis
    ? { ...analysis, current_price: livePrice }
    : analysis

  return (
    <div className="h-full flex flex-col bg-[#0d1117]">
      <div className="flex-1 flex overflow-hidden">
        {/* Chart Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <AIChart analysis={displayedAnalysis} explain={explain} signal={signal} livePrice={livePrice} />

          {/* Bottom Panel - AI Forecast + Summary */}
          <div className="border-t border-gray-800 bg-gray-950/80 p-3">
            <div className="max-w-5xl">
              <AIForecastPanel analysis={displayedAnalysis} signal={signal} loading={loading} />
            </div>
          </div>
        </div>

        {/* Right Panel - AI Prediction + Decision */}
        <div className="w-80 lg:w-96 border-l border-gray-800 overflow-y-auto flex-shrink-0">
          <div className="border-b border-gray-800">
            <div className="px-3 py-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wider bg-gray-900/50">
              AI Prediction Engine
            </div>
          </div>
          <AIPredictionPanel analysis={displayedAnalysis} loading={loading} />

          <div className="border-b border-gray-800">
            <div className="px-3 py-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wider bg-gray-900/50">
              Trade Decision
            </div>
          </div>
          <div className="p-3">
            <TradeDecisionCard analysis={displayedAnalysis} explain={explain} livePrice={livePrice} loading={loading} />
          </div>
        </div>
      </div>
    </div>
  )
}
