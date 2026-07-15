"use client"

import { cn } from "@/lib/utils"
import {
  AlertTriangle,
  ArrowUpRight, ArrowDownRight, Minus,
} from "lucide-react"

interface SuggestionsData {
  entry?: number
  stop_loss?: number
  take_profit?: number
  suggested_leverage?: number
  position_size?: number
  [key: string]: unknown
}

interface ExplainData {
  reasons?: string[]
  warnings?: string[]
  suggestions?: SuggestionsData
  key_levels?: Record<string, unknown>
  [key: string]: unknown
}

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

interface TradeDecisionCardProps {
  analysis?: AnalysisData | null
  explain?: ExplainData | null
  loading?: boolean
}

export function TradeDecisionCard({ analysis, explain, loading }: TradeDecisionCardProps) {
  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-3">
          <div className="h-16 bg-gray-800 rounded-lg" />
          <div className="h-12 bg-gray-800 rounded-lg" />
          <div className="h-20 bg-gray-800 rounded-lg" />
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50 text-center">
        <AlertTriangle className="w-6 h-6 mx-auto mb-1 text-gray-600" />
        <div className="text-xs text-gray-500">No analysis data available</div>
      </div>
    )
  }

  const isBullish = analysis.prediction === "long"
  const isBearish = analysis.prediction === "short"
  const conf = analysis.confidence || 0
  const reasons = explain?.reasons || []
  const warnings = explain?.warnings || []
  const suggestions = explain?.suggestions || {}

  const decision = isBullish ? "BUY" : isBearish ? "SELL" : "WAIT"
  const decisionColor = isBullish ? "green" : isBearish ? "red" : "yellow"
  const DecisionIcon = isBullish ? ArrowUpRight : isBearish ? ArrowDownRight : Minus

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50 space-y-3">
      {/* Decision Badge */}
      <div className={cn(
        "p-3 rounded-xl text-center border",
        decisionColor === "green" && "bg-green-900/10 border-green-500/30",
        decisionColor === "red" && "bg-red-900/10 border-red-500/30",
        decisionColor === "yellow" && "bg-yellow-900/10 border-yellow-500/30",
      )}>
        <div className="flex items-center justify-center gap-2">
          <DecisionIcon className={cn("w-5 h-5",
            decisionColor === "green" && "text-green-400",
            decisionColor === "red" && "text-red-400",
            decisionColor === "yellow" && "text-yellow-400",
          )} />
          <span className={cn("text-lg font-bold",
            decisionColor === "green" && "text-green-400",
            decisionColor === "red" && "text-red-400",
            decisionColor === "yellow" && "text-yellow-400",
          )}>
            AI RECOMMENDATION: {decision}
          </span>
        </div>
        <div className={cn("text-xs mt-1 font-medium",
          decisionColor === "green" && "text-green-400/70",
          decisionColor === "red" && "text-red-400/70",
          decisionColor === "yellow" && "text-yellow-400/70",
        )}>
          Confidence: {conf}% | {analysis.long_probability?.toFixed(0) || 0}% Long / {analysis.short_probability?.toFixed(0) || 0}% Short
        </div>
      </div>

      {/* Suggested Levels */}
      {(suggestions.stop_loss || suggestions.take_profit) && (
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 rounded-lg bg-gray-800/30">
            <div className="text-[10px] text-gray-500 mb-0.5">Suggested Entry</div>
            <div className="text-sm font-bold text-white font-mono">
              ${Number(explain?.key_levels?.support || analysis.details?.support || 0).toFixed(2)}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-red-900/20 border border-red-900/30">
            <div className="text-[10px] text-red-400 mb-0.5">Stop Loss</div>
            <div className="text-sm font-bold text-red-400 font-mono">
              ${(suggestions.stop_loss || 0).toFixed(2)}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-green-900/20 border border-green-900/30">
            <div className="text-[10px] text-green-400 mb-0.5">Take Profit 1</div>
            <div className="text-sm font-bold text-green-400 font-mono">
              ${(suggestions.take_profit || 0).toFixed(2)}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-green-900/10 border border-green-900/20">
            <div className="text-[10px] text-green-400/70 mb-0.5">Take Profit 2</div>
            <div className="text-sm font-bold text-green-400/70 font-mono">
              ${((suggestions.take_profit || 0) * 1.03).toFixed(2)}
            </div>
          </div>
        </div>
      )}

      {/* Position Sizing */}
      {suggestions.suggested_leverage && (
        <div className="flex gap-2 text-xs">
          <div className="flex-1 p-2 rounded-lg bg-gray-800/30 text-center">
            <div className="text-gray-500">Leverage</div>
            <div className="text-white font-bold">{suggestions.suggested_leverage}x</div>
          </div>
          {suggestions.position_size && (
            <div className="flex-1 p-2 rounded-lg bg-gray-800/30 text-center">
              <div className="text-gray-500">Position Size</div>
              <div className="text-white font-bold">${suggestions.position_size?.toFixed(0)}</div>
            </div>
          )}
          <div className="flex-1 p-2 rounded-lg bg-gray-800/30 text-center">
            <div className="text-gray-500">Risk/Reward</div>
            <div className="text-white font-bold">
              {suggestions.stop_loss && suggestions.take_profit
                ? `1:${((suggestions.take_profit - Number(explain?.key_levels?.support || 0)) / (Number(explain?.key_levels?.support || 0) - suggestions.stop_loss)).toFixed(1)}`
                : "--"}
            </div>
          </div>
        </div>
      )}

      {/* Reasons */}
      {reasons.length > 0 && (
        <div>
          <h4 className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Why This Decision</h4>
          <ul className="space-y-1">
            {reasons.slice(0, 4).map((r: string, i: number) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-gray-400">
                <span className={cn("w-1.5 h-1.5 rounded-full mt-0.5 flex-shrink-0",
                  isBullish ? "bg-green-500" : isBearish ? "bg-red-500" : "bg-yellow-500")} />
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Warnings / Invalidation */}
      {warnings.length > 0 && (
        <div>
          <h4 className="text-[10px] text-red-400 uppercase tracking-wider mb-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Invalidation
          </h4>
          <ul className="space-y-1">
            {warnings.slice(0, 3).map((w: string, i: number) => (
              <li key={i} className="text-xs text-red-400/70 flex items-start gap-1.5">
                <span className="w-1 h-1 rounded-full bg-red-400 mt-1.5 flex-shrink-0" />
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
