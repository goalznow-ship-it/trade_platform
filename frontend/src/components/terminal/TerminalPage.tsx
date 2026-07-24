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
  factor_scores?: Record<string, number>
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
    factor_scores?: Record<string, number>
  }
  execution?: { rejection_reasons?: string[]; approved?: boolean }
  position_sizing?: { leverage?: number; position_size?: number }
}

export function TerminalPage() {
  const { selectedSymbol, selectedTimeframe, tickers } = useMarketStore()
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null)
  const [explain, setExplain] = useState<ExplainData | null>(null)
  const [signal, setSignal] = useState<InstitutionalSignal | null>(null)
  const [aiAnalysis, setAiAnalysis] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [institutional, ai, mtfResult] = await Promise.all([
          api.getInstitutionalSignal(selectedSymbol, selectedTimeframe).catch(() => null),
          api.getPatternAnalysis(selectedSymbol, selectedTimeframe).catch(() => null),
          api.getMultiTimeframe(selectedSymbol).catch(() => null),
        ])
        setSignal(institutional)
        if (ai && mtfResult && typeof ai === "object") {
          (ai as Record<string, unknown>).multi_timeframe_alignment = mtfResult?.alignment || mtfResult?.aggregated
            ? {
                major_aligned: mtfResult.alignment?.major_aligned ?? mtfResult.aggregated?.major_aligned ?? false,
                aligned_tfs: mtfResult.aggregated?.timeframe_count ?? 0,
                aggregate_direction: mtfResult.aggregated?.direction ?? mtfResult.alignment?.aggregate_direction ?? "neutral",
              }
            : undefined
        }
        setAiAnalysis(ai)

        if (institutional) {
          const direction = institutional.direction
          const score = institutional.institutional_score
          const details = score?.details || {}
          const factorScores: Record<string, number> = {}
          for (const [key, value] of Object.entries(score?.scores || {})) {
            const weight = score?.weights?.[key]
            if (typeof value === "number" && typeof weight === "number" && weight > 0) {
              factorScores[key] = (value / weight) * 100
            }
          }
          const ff = score?.factor_scores
          if (ff) {
            for (const [key, value] of Object.entries(ff)) {
              if (typeof value === "number") factorScores[key] = value
            }
          }
          const aiConf = ai?.confidence || institutional.confidence || score?.abs_score
          const aiDir = ai?.combined_direction || direction

          setAnalysis({
            prediction: institutional.error ? "neutral" : (aiDir as string),
            confidence: typeof aiConf === "number" ? aiConf : 50,
            current_price: institutional.current_price,
            long_probability: score?.long_probability ?? ai?.long_probability ?? 50,
            short_probability: score?.short_probability ?? ai?.short_probability ?? 50,
            risk_level: score?.risk_level || "medium",
            scores: factorScores,
            factor_scores: factorScores,
            details: {
              ...(details || {}),
              ...(institutional.indicators || {}),
              macd: institutional.indicators?.macd_histogram,
            },
            summary: ai?.components?.elliott_wave
              ? `Elliott Wave: ${(ai.components.elliott_wave as Record<string, unknown>).count === "impulse" ? "İmpuls dalğası" : "Korrektiv dalğa"}. ${(ai.components.candlestick_patterns as Record<string, unknown>)?.total_count || 0} şam naxışı aşkarlandı.`
              : undefined,
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
        } else if (ai && !ai.error) {
          const aiDir = (ai.combined_direction as string) || "neutral"
          const aiConf = ai.confidence as number || 50
          const score = ai.institutional_score as Record<string, unknown> || {}
          const scores = score.scores as Record<string, number> || {}
          const weights = score.weights as Record<string, number> || {}
          const factorScores: Record<string, number> = {}
          for (const [key, value] of Object.entries(scores)) {
            const weight = weights[key]
            if (typeof value === "number" && typeof weight === "number" && weight > 0) {
              factorScores[key] = (value / weight) * 100
            }
          }
          const ff = score.factor_scores as Record<string, number> | undefined
          if (ff) {
            for (const [key, value] of Object.entries(ff)) {
              if (typeof value === "number") factorScores[key] = value
            }
          }
          setAnalysis({
            prediction: aiDir,
            confidence: typeof aiConf === "number" ? aiConf : 50,
            current_price: ai.current_price as number || 0,
            long_probability: (score.long_probability as number) ?? 50,
            short_probability: (score.short_probability as number) ?? 50,
            risk_level: (score.risk_level as string) || "medium",
            scores: factorScores,
            factor_scores: factorScores,
            details: (score.details as Record<string, unknown>) || {},
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
    : signal?.current_price || (aiAnalysis?.current_price as number)
  const displayedAnalysis = analysis
    ? { ...analysis, current_price: livePrice }
    : analysis

  return (
    <div className="h-full flex flex-col bg-[#0d1117]">
      <div className="flex-1 flex overflow-hidden">
        {/* Chart Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <AIChart
            analysis={displayedAnalysis}
            explain={explain}
            signal={signal as Record<string, unknown> | null | undefined}
            livePrice={livePrice}
            aiAnalysis={aiAnalysis as Record<string, unknown> as AIChartProps["aiAnalysis"]}
          />

          {/* Bottom Panel - AI Forecast (compact) */}
          <div className="border-t border-gray-800 bg-gray-950/80 px-3 py-1.5">
            <AIForecastPanel analysis={displayedAnalysis} signal={signal} loading={loading} />
          </div>
        </div>

        {/* Right Panel - AI Prediction + Decision */}
        <div className="w-80 lg:w-96 border-l border-gray-800 overflow-y-auto flex-shrink-0">
          <div className="border-b border-gray-800">
            <div className="px-3 py-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wider bg-gray-900/50">
              AI Analiz Mühərriki
            </div>
          </div>
          <AIPredictionPanel
            analysis={displayedAnalysis}
            aiAnalysis={aiAnalysis as Record<string, unknown> as AIAnalysisExtendedProps["aiAnalysis"]}
            loading={loading}
          />

          <div className="border-b border-gray-800">
            <div className="px-3 py-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wider bg-gray-900/50">
              Ticarət Qərarı
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

// Temp type for the cast
interface AIChartProps {
  aiAnalysis?: Record<string, unknown> | null
}
interface AIAnalysisExtendedProps {
  aiAnalysis?: Record<string, unknown> | null
}
