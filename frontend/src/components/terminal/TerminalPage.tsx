"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { useMarketStore } from "@/store/market"
import { AIChart } from "@/components/terminal/AIChart"
import { AIPredictionPanel } from "@/components/terminal/AIPredictionPanel"
import { TradeDecisionCard } from "@/components/terminal/TradeDecisionCard"

export function TerminalPage() {
  const { selectedSymbol, selectedTimeframe } = useMarketStore()
  const [analysis, setAnalysis] = useState<any>(null)
  const [explain, setExplain] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [ai, ex] = await Promise.all([
          api.getAIAnalysis(selectedSymbol, selectedTimeframe).catch(() => null),
          api.getAIExplainability(selectedSymbol, selectedTimeframe).catch(() => null),
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
        </div>

        {/* Right Panel - AI Prediction + Decision */}
        <div className="w-80 lg:w-96 border-l border-gray-800 overflow-y-auto flex-shrink-0">
          <div className="border-b border-gray-800">
            <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider bg-gray-900/50">
              AI Prediction Engine
            </div>
          </div>
          <AIPredictionPanel analysis={analysis} loading={loading} />

          <div className="border-b border-gray-800">
            <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider bg-gray-900/50">
              Trade Decision
            </div>
          </div>
          <div className="p-4">
            <TradeDecisionCard analysis={analysis} explain={explain} loading={loading} />
          </div>
        </div>
      </div>
    </div>
  )
}
