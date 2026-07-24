"use client"

import { useState } from "react"
import { cn, formatPrice } from "@/lib/utils"
import {
  Check, X as XIcon,
  ChevronDown, ChevronUp, Activity,
  Shield, AlertTriangle, Zap, Clock,
} from "lucide-react"
import {
  type UnifiedSignal, displayPrice, displayDate, isStale, gradeSignal,
} from "@/lib/unified-signal"

interface SignalCardProps {
  signal: UnifiedSignal
}

function getConfidenceColor(score: number): string {
  if (score >= 90) return "text-green-400"
  if (score >= 80) return "text-green-300"
  if (score >= 70) return "text-yellow-400"
  if (score >= 50) return "text-yellow-300"
  return "text-gray-500"
}

function getConfidenceBg(score: number): string {
  if (score >= 90) return "bg-green-500"
  if (score >= 80) return "bg-green-400"
  if (score >= 70) return "bg-yellow-500"
  if (score >= 50) return "bg-yellow-400"
  return "bg-gray-600"
}

export function SignalCard({ signal }: SignalCardProps) {
  const [expanded, setExpanded] = useState(false)
  const isLong = signal.direction === "long"
  const isShort = signal.direction === "short"
  const grade = gradeSignal(signal.confidence)
  const reasons = signal.reasons || []
  const rb = signal.reasons_breakdown || {}
  const score = signal.institutional_score
  const futures = signal.futures

  return (
    <div className={cn(
      "rounded-lg border transition-all hover:border-gray-600 overflow-hidden",
      isLong ? "border-green-900/40 bg-gradient-to-r from-green-900/5 to-transparent" :
      isShort ? "border-red-900/40 bg-gradient-to-r from-red-900/5 to-transparent" :
      "border-gray-800 bg-gray-900/30",
      grade === "reject" && "opacity-50",
    )}>
      <div className="p-3.5">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold font-mono",
              isLong ? "bg-green-900/30 text-green-400" :
              isShort ? "bg-red-900/30 text-red-400" :
              "bg-yellow-900/30 text-yellow-400"
            )}>
              {isLong ? "L" : isShort ? "S" : "~"}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-white font-mono">{signal.symbol}</span>
                <span className={cn(
                  "text-[10px] font-bold px-1.5 py-0.5 rounded",
                  isLong ? "bg-green-900/60 text-green-300" :
                  isShort ? "bg-red-900/60 text-red-300" :
                  "bg-yellow-900/60 text-yellow-300"
                )}>
                  {isLong ? "LONG" : isShort ? "SHORT" : "WAIT"}
                </span>
                {grade === "trade_ready" && (
                  <span className="text-[9px] font-medium px-1 py-0.5 rounded bg-green-900/40 text-green-300 border border-green-700/30">
                    Trade Ready
                  </span>
                )}
                {grade === "watchlist" && (
                  <span className="text-[9px] font-medium px-1 py-0.5 rounded bg-yellow-900/40 text-yellow-300 border border-yellow-700/30">
                    Watchlist
                  </span>
                )}
              </div>
              {reasons.length > 0 && (
                <div className="text-[11px] text-gray-500 mt-0.5 line-clamp-1">{reasons[0]}</div>
              )}
            </div>
          </div>
          <div className="text-right">
            <div className={cn("text-lg font-bold font-mono", getConfidenceColor(signal.confidence))}>
              {signal.confidence}%
            </div>
            <div className="text-[10px] text-gray-500">
              Opp: {signal.opportunity_score}
            </div>
          </div>
        </div>

        {/* Price Levels */}
        <div className="grid grid-cols-5 gap-1.5 mb-2">
          <PriceBox label="Entry" value={signal.entry_zone.mid} color="text-blue-400" bg="bg-blue-900/15 border-blue-900/20" />
          <PriceBox label="Stop Loss" value={signal.stop_loss} color="text-red-400" bg="bg-red-900/15 border-red-900/20" />
          <PriceBox label="TP1" value={signal.take_profit_1} color="text-green-400" bg="bg-green-900/15 border-green-900/20" />
          <PriceBox label="TP2" value={signal.take_profit_2} color="text-green-400/80" bg="bg-green-900/10 border-green-900/15" />
          <PriceBox label="TP3" value={signal.take_profit_3} color="text-green-400/60" bg="bg-green-900/5 border-green-900/10" />
        </div>

        {/* Meta */}
        <div className="flex items-center gap-2.5 text-[10px] text-gray-500">
          {signal.risk_reward_1 > 0 && (
            <span className="px-1.5 py-0.5 rounded bg-gray-800/50 font-medium">R:R 1:{signal.risk_reward_1.toFixed(1)}</span>
          )}
          <span className="px-1.5 py-0.5 rounded bg-gray-800/50">{signal.timeframe}</span>
          {signal.expected_hold_time && (
            <span className="px-1.5 py-0.5 rounded bg-gray-800/50">{signal.expected_hold_time}</span>
          )}
          {signal.exchange && (
            <span className="px-1.5 py-0.5 rounded bg-gray-800/50">{signal.exchange}</span>
          )}
          {signal.last_updated && (
            <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-gray-800/50">
              <Clock className="w-2.5 h-2.5" />
              {displayDate(signal.last_updated)}
              {isStale(signal.last_updated, 120) && <span className="text-amber-400">Stale</span>}
            </span>
          )}
          <div className="flex-1" />
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-gray-500 hover:text-gray-300 transition-colors"
          >
            <span className="text-[10px]">Details</span>
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>
      </div>

      {/* Expanded */}
      {expanded && (
        <div className="border-t border-gray-800/60 px-3.5 py-3 bg-gray-900/40">
          {/* Score breakdown bar */}
          <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-gray-800/40 border border-gray-700/30">
            <span className="text-[10px] text-gray-400 font-medium whitespace-nowrap">Confidence:</span>
            <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className={cn("h-full rounded-full", getConfidenceBg(signal.confidence))}
                style={{ width: `${signal.confidence}%` }}
              />
            </div>
            <span className="text-xs font-bold font-mono text-white">
              {signal.confidence}/100
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Reasons from reasons_breakdown */}
            <div className="p-2.5 rounded bg-gray-800/30 border border-gray-700/20">
              <div className="flex items-center gap-1.5 mb-2">
                <Activity className="w-3 h-3 text-blue-400" />
                <span className="text-[10px] font-semibold text-gray-300 uppercase tracking-wider">Analysis</span>
              </div>
              <div className="space-y-1">
                {Object.entries(rb).slice(0, 6).map(([k, v]) => (
                  <div key={k} className="flex items-center gap-1.5">
                    <Check className="w-2.5 h-2.5 text-green-400 flex-shrink-0" />
                    <span className="text-[10px] text-gray-400 truncate">{v}</span>
                  </div>
                ))}
                {Object.keys(rb).length === 0 && (
                  <div className="text-[10px] text-gray-600 italic">No detailed analysis</div>
                )}
              </div>
            </div>

            {/* Market Structure */}
            <div className="p-2.5 rounded bg-gray-800/30 border border-gray-700/20">
              <div className="flex items-center gap-1.5 mb-2">
                <Shield className="w-3 h-3 text-purple-400" />
                <span className="text-[10px] font-semibold text-gray-300 uppercase tracking-wider">Market Structure</span>
              </div>
              <div className="space-y-1">
                <MetaCheck label="Trend" value={signal.market_structure.trend} good={["uptrend", "downtrend"].includes(signal.market_structure.trend)} />
                <MetaCheck label="BOS" value={signal.market_structure.bos_count} good={(signal.market_structure.bos_count || 0) > 0} />
                <MetaCheck label="CHoCH" value={signal.market_structure.choch_count} good={(signal.market_structure.choch_count || 0) > 0} />
                <MetaCheck label="Liq Sweep" value={signal.market_structure.liquidity_sweep ? "Yes" : "No"} good={!!signal.market_structure.liquidity_sweep} />
              </div>
            </div>

            {/* Futures */}
            <div className="p-2.5 rounded bg-gray-800/30 border border-gray-700/20">
              <div className="flex items-center gap-1.5 mb-2">
                <Zap className="w-3 h-3 text-orange-400" />
                <span className="text-[10px] font-semibold text-gray-300 uppercase tracking-wider">Futures</span>
              </div>
              {futures ? (
                <div className="space-y-1">
                  <MetaCheck label="Funding" value={futures.funding_rate != null ? `${(futures.funding_rate * 100).toFixed(4)}%` : "N/A"} good={futures.funding_pressure !== "neutral"} />
                  <MetaCheck label="OI" value={futures.open_interest_usd != null ? `$${(futures.open_interest_usd / 1e6).toFixed(0)}M` : "N/A"} good={futures.open_interest_usd != null && futures.open_interest_usd > 0} />
                  <MetaCheck label="Pressure" value={futures.funding_pressure} good={futures.funding_pressure !== "neutral"} />
                  <MetaCheck label="Exchange" value={signal.exchange} good />
                </div>
              ) : (
                <div className="text-[10px] text-gray-600 italic">No futures data</div>
              )}
            </div>

            {/* Score & Risk */}
            <div className="p-2.5 rounded bg-gray-800/30 border border-gray-700/20">
              <div className="flex items-center gap-1.5 mb-2">
                <AlertTriangle className="w-3 h-3 text-yellow-400" />
                <span className="text-[10px] font-semibold text-gray-300 uppercase tracking-wider">Risk & Score</span>
              </div>
              <div className="space-y-1">
                <MetaCheck label="Total Score" value={`${score.abs_score}/100`} good={score.abs_score >= 70} />
                <MetaCheck label="Risk Level" value={score.risk_level} good={score.risk_level === "low"} />
                <MetaCheck label="Opp. Score" value={signal.opportunity_score} good={signal.opportunity_score >= 50} />
                <MetaCheck label="R:R (TP1)" value={`1:${signal.risk_reward_1.toFixed(1)}`} good={signal.risk_reward_1 >= 2} />
              </div>
            </div>
          </div>

          {/* Invalidation */}
          {signal.invalidation && (
            <div className="mt-2 p-2 rounded bg-red-900/10 border border-red-900/20 text-[10px] text-red-300">
              <span className="font-medium">Invalidation: </span>{signal.invalidation}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function PriceBox({ label, value, color, bg }: { label: string; value: number; color: string; bg: string }) {
  return (
    <div className={`p-2 rounded ${bg}`}>
      <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-0.5">{label}</div>
      <div className={`text-[11px] font-bold font-mono leading-tight ${color}`}>
        {value > 0 ? formatPrice(value) : "N/A"}
      </div>
    </div>
  )
}

function MetaCheck({ label, value, good }: { label: string; value: string | number | boolean | null | undefined; good: boolean }) {
  const display = typeof value === "string" ? value : typeof value === "number" ? value.toString() : value ? String(value) : "N/A"
  return (
    <div className="flex items-center gap-1.5">
      {good ? (
        <Check className="w-2.5 h-2.5 text-green-400 flex-shrink-0" />
      ) : (
        <XIcon className="w-2.5 h-2.5 text-gray-600 flex-shrink-0" />
      )}
      <span className="text-[10px] text-gray-400">
        {label}: <span className="text-gray-300">{display}</span>
      </span>
    </div>
  )
}
