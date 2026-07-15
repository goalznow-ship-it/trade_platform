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

export function TerminalPage() {
  const { selectedSymbol, selectedTimeframe } = useMarketStore()
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null)
  const [explain, setExplain] = useState<ExplainData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [ai, ex] = await Promise.all([
          api.getAIAnalysis(selectedSymbol, selectedTimeframe).catch(() => null),
          api.getAIExplainability().catch(() => null),
        ])
        setAnalysis(ai)
        setExplain(ex)
      } catch {} finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [selectedSymbol, selectedTimeframe])

  return (
    <div className="h-full flex flex-col bg-[#0d1117]">
      <div className="flex-1 flex overflow-hidden">
        {/* Chart Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <AIChart analysis={analysis} explain={explain} />

          {/* Bottom Panel - AI Forecast + Summary */}
          <div className="border-t border-gray-800 bg-gray-950/80 p-3">
            <div className="max-w-5xl">
              <AIForecastPanel analysis={analysis} loading={loading} />
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
          <AIPredictionPanel analysis={analysis} loading={loading} />

          <div className="border-b border-gray-800">
            <div className="px-3 py-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wider bg-gray-900/50">
              Trade Decision
            </div>
          </div>
          <div className="p-3">
            <TradeDecisionCard analysis={analysis} explain={explain} loading={loading} />
          </div>
        </div>
      </div>
    </div>
  )
}
