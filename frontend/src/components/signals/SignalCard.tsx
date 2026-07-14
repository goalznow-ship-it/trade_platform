"use client"

import { useState } from "react"
import { cn, formatPrice } from "@/lib/utils"
import {
  TrendingUp, TrendingDown, Target, Check, X as XIcon,
  ChevronDown, ChevronUp, BarChart3, Activity,
  Volume2, Shield, AlertTriangle, Zap, Flame,
} from "lucide-react"

interface SignalCardProps {
  signal: any
}

function getScoreLabel(score: number): { label: string; color: string; icon: any } {
  if (score >= 90) return { label: "Strong Signal", color: "text-orange-400 bg-orange-900/30 border-orange-500/30", icon: Flame }
  if (score >= 80) return { label: "High Probability", color: "text-green-400 bg-green-900/30 border-green-500/30", icon: Check }
  if (score >= 70) return { label: "Watch", color: "text-yellow-400 bg-yellow-900/30 border-yellow-500/30", icon: AlertTriangle }
  return { label: "Ignore", color: "text-gray-500 bg-gray-800 border-gray-700", icon: XIcon }
}

function calcWeightedScore(signal: any): { total: number; technical: number; structure: number; futures: number; news: number; sentiment: number } {
  const tech = signal.technical || {}
  const structure = signal.market_structure || signal.structure || {}
  const futures = signal.futures || {}
  const news = signal.news || {}

  const sc = (v: any) => typeof v === "boolean" ? (v ? 1 : -1) : typeof v === "number" ? Math.min(v / 100, 1) : 0

  const technicalScore = (sc(tech.ema_alignment ?? tech.ema) * 0.25 + sc(tech.rsi) * 0.25 + sc(tech.macd) * 0.25 + sc(tech.volume) * 0.25) * 100
  const structureScore = (sc(structure.bos) * 0.25 + sc(structure.choch) * 0.25 + sc(structure.order_block ?? structure.ob) * 0.25 + sc(structure.liquidity) * 0.25) * 100
  const futuresScore = (sc(futures.funding) * 0.34 + sc(futures.open_interest ?? futures.oi) * 0.33 + sc(futures.liquidation ?? futures.liq) * 0.33) * 100
  const newsScore = typeof news.score === "number" ? news.score : (news.impact === "positive" ? 80 : news.impact === "negative" ? 30 : 50)
  const sentimentScore = signal.sentiment_score || 50

  const total = technicalScore * 0.25 + structureScore * 0.25 + futuresScore * 0.20 + newsScore * 0.15 + sentimentScore * 0.15
  return { total: Math.round(total), technical: Math.round(technicalScore), structure: Math.round(structureScore), futures: Math.round(futuresScore), news: Math.round(newsScore), sentiment: Math.round(sentimentScore) }
}

export function SignalCard({ signal }: SignalCardProps) {
  const [expanded, setExpanded] = useState(false)
  const dir = signal.direction || signal.signal || "neutral"
  const isLong = dir === "long" || dir === "bullish" || dir === "buy"
  const isShort = dir === "short" || dir === "bearish" || dir === "sell"
  const rr = signal.risk_reward || signal.risk_reward_ratio || 0
  const entry = signal.entry_price || signal.price || 0
  const entryZoneHigh = signal.entry_zone_high || entry * 1.002
  const sl = signal.stop_loss || 0
  const tp1 = signal.take_profit || signal.take_profit_1 || 0
  const tp2 = signal.take_profit_2 || tp1 * 1.025 || 0
  const tp3 = signal.take_profit_3 || tp1 * 1.05 || 0

  const scores = calcWeightedScore(signal)
  const scoreInfo = getScoreLabel(scores.total)

  const tech = signal.technical || {}
  const structure = signal.market_structure || signal.structure || {}
  const futures = signal.futures || {}
  const news = signal.news || {}

  const hasDetailedAnalysis = Object.keys(tech).length > 0 || Object.keys(structure).length > 0 || Object.keys(futures).length > 0

  function renderCheck(val: boolean | string | number | undefined | null, label: string) {
    const isGood = val === true || val === "yes" || val === "bullish" || val === "positive" || (typeof val === "number" && val > 0)
    const isBad = val === false || val === "no" || val === "bearish" || val === "negative" || (typeof val === "number" && val < 0)
    if (val === undefined || val === null) return null
    return (
      <div className="flex items-center gap-1.5">
        {isGood ? (
          <Check className="w-3 h-3 text-green-400 flex-shrink-0" />
        ) : isBad ? (
          <XIcon className="w-3 h-3 text-red-400 flex-shrink-0" />
        ) : (
          <div className="w-3 h-3 rounded-full border border-gray-600 flex-shrink-0" />
        )}
        <span className="text-[11px] text-gray-400">{label}</span>
      </div>
    )
  }

  return (
    <div className={cn(
      "rounded-lg border transition-all hover:border-gray-600 overflow-hidden",
      isLong ? "border-green-900/40 bg-gradient-to-r from-green-900/5 to-transparent" :
      isShort ? "border-red-900/40 bg-gradient-to-r from-red-900/5 to-transparent" :
      "border-gray-800 bg-gray-900/30"
    )}>
      {/* Main Row */}
      <div className="p-3.5">
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
              </div>
              {signal.reason && (
                <div className="text-[11px] text-gray-500 mt-0.5 line-clamp-1">{signal.reason}</div>
              )}
            </div>
          </div>
          <div className="text-right">
            <div className={cn(
              "text-lg font-bold font-mono",
              scores.total >= 80 ? "text-green-400" : scores.total >= 70 ? "text-yellow-400" : "text-gray-400"
            )}>
              {scores.total}%
            </div>
            <div className={cn(
              "inline-flex items-center gap-0.5 text-[9px] font-medium px-1 py-0.5 rounded border mt-0.5",
              scoreInfo.color
            )}>
              {scoreInfo.label}
            </div>
          </div>
        </div>

        {/* Price Levels Grid */}
        <div className="grid grid-cols-5 gap-1.5 mb-3">
          <div className="col-span-1 p-2 rounded bg-gray-800/40 border border-gray-700/30">
            <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-0.5">Entry Zone</div>
            <div className="text-[11px] font-bold text-white font-mono leading-tight">
              {formatPrice(entry)}
              {entryZoneHigh > entry && <span className="text-gray-500"> - {formatPrice(entryZoneHigh)}</span>}
            </div>
          </div>
          <div className="col-span-1 p-2 rounded bg-red-900/15 border border-red-900/20">
            <div className="text-[9px] text-red-400 uppercase tracking-wider mb-0.5">Stop Loss</div>
            <div className="text-[11px] font-bold text-red-400 font-mono">{formatPrice(sl)}</div>
          </div>
          <div className="col-span-1 p-2 rounded bg-green-900/15 border border-green-900/20">
            <div className="text-[9px] text-green-400 uppercase tracking-wider mb-0.5">TP1</div>
            <div className="text-[11px] font-bold text-green-400 font-mono">{formatPrice(tp1)}</div>
          </div>
          <div className="col-span-1 p-2 rounded bg-green-900/10 border border-green-900/15">
            <div className="text-[9px] text-green-400/70 uppercase tracking-wider mb-0.5">TP2</div>
            <div className="text-[11px] font-bold text-green-400/80 font-mono">{formatPrice(tp2)}</div>
          </div>
          <div className="col-span-1 p-2 rounded bg-green-900/5 border border-green-900/10">
            <div className="text-[9px] text-green-400/50 uppercase tracking-wider mb-0.5">TP3</div>
            <div className="text-[11px] font-bold text-green-400/60 font-mono">{formatPrice(tp3)}</div>
          </div>
        </div>

        {/* Meta Row */}
        <div className="flex items-center gap-2.5 text-[10px] text-gray-500">
          {rr > 0 && (
            <div className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-gray-800/50">
              <Target className="w-3 h-3" />
              <span className="font-medium text-gray-400">R:R 1:{rr.toFixed(1)}</span>
            </div>
          )}
          {signal.timeframe && (
            <span className="px-1.5 py-0.5 rounded bg-gray-800/50">{signal.timeframe}</span>
          )}
          {signal.signal_type && (
            <span className="px-1.5 py-0.5 rounded bg-gray-800/50">{signal.signal_type}</span>
          )}
          <div className="flex-1" />
          {hasDetailedAnalysis && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-gray-500 hover:text-gray-300 transition-colors"
            >
              <span className="text-[10px]">Analysis</span>
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}
        </div>
      </div>

      {/* Expanded Analysis */}
      {expanded && (
        <div className="border-t border-gray-800/60 px-3.5 py-3 bg-gray-900/40">
          {/* Weighted Score Bar */}
          <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-gray-800/40 border border-gray-700/30">
            <span className="text-[10px] text-gray-400 font-medium whitespace-nowrap">Score:</span>
            <div className="flex-1 flex gap-0.5 h-4 rounded overflow-hidden">
              <div className="bg-blue-500/70 h-full" style={{ width: `${scores.technical * 0.25}%` }} title="Technical" />
              <div className="bg-purple-500/70 h-full" style={{ width: `${scores.structure * 0.25}%` }} title="Market Structure" />
              <div className="bg-orange-500/70 h-full" style={{ width: `${scores.futures * 0.20}%` }} title="Futures" />
              <div className="bg-yellow-500/70 h-full" style={{ width: `${scores.news * 0.15}%` }} title="News" />
              <div className="bg-green-500/70 h-full" style={{ width: `${scores.sentiment * 0.15}%` }} title="Sentiment" />
            </div>
            <div className="flex items-center gap-1.5 text-[9px] text-gray-500">
              <span className="w-2 h-2 rounded-sm bg-blue-500/70" />T <span className="w-2 h-2 rounded-sm bg-purple-500/70" />S <span className="w-2 h-2 rounded-sm bg-orange-500/70" />F <span className="w-2 h-2 rounded-sm bg-yellow-500/70" />N <span className="w-2 h-2 rounded-sm bg-green-500/70" />S
            </div>
            <span className={cn("text-xs font-bold font-mono", scores.total >= 80 ? "text-green-400" : scores.total >= 70 ? "text-yellow-400" : "text-gray-400")}>
              {scores.total}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Technical */}
            <div className="p-2.5 rounded bg-gray-800/30 border border-gray-700/20">
              <div className="flex items-center gap-1.5 mb-2">
                <Activity className="w-3 h-3 text-blue-400" />
                <span className="text-[10px] font-semibold text-gray-300 uppercase tracking-wider">Technical</span>
              </div>
              <div className="space-y-1">
                {renderCheck(tech.ema_alignment ?? tech.ema, "EMA Alignment")}
                {renderCheck(tech.rsi, "RSI")}
                {renderCheck(tech.macd, "MACD")}
                {renderCheck(tech.volume, "Volume")}
                {renderCheck(tech.atr ?? tech.support, "ATR")}
                {Object.keys(tech).length === 0 && <div className="text-[10px] text-gray-600 italic">No data</div>}
              </div>
            </div>

            {/* Market Structure */}
            <div className="p-2.5 rounded bg-gray-800/30 border border-gray-700/20">
              <div className="flex items-center gap-1.5 mb-2">
                <BarChart3 className="w-3 h-3 text-purple-400" />
                <span className="text-[10px] font-semibold text-gray-300 uppercase tracking-wider">Market Structure</span>
              </div>
              <div className="space-y-1">
                {renderCheck(structure.bos, "BOS")}
                {renderCheck(structure.choch, "CHoCH")}
                {renderCheck(structure.order_block ?? structure.ob, "Order Block")}
                {renderCheck(structure.liquidity, "Liquidity")}
                {renderCheck(structure.fvg, "FVG")}
                {Object.keys(structure).length === 0 && <div className="text-[10px] text-gray-600 italic">No data</div>}
              </div>
            </div>

            {/* Futures */}
            <div className="p-2.5 rounded bg-gray-800/30 border border-gray-700/20">
              <div className="flex items-center gap-1.5 mb-2">
                <Zap className="w-3 h-3 text-orange-400" />
                <span className="text-[10px] font-semibold text-gray-300 uppercase tracking-wider">Futures</span>
              </div>
              <div className="space-y-1">
                {renderCheck(futures.funding, "Funding")}
                {renderCheck(futures.open_interest ?? futures.oi, "Open Interest")}
                {renderCheck(futures.liquidation ?? futures.liq, "Liquidation Zones")}
                {renderCheck(futures.long_short_ratio ?? futures.ls_ratio, "Long/Short Ratio")}
                {Object.keys(futures).length === 0 && <div className="text-[10px] text-gray-600 italic">No data</div>}
              </div>
            </div>

            {/* News */}
            <div className="p-2.5 rounded bg-gray-800/30 border border-gray-700/20">
              <div className="flex items-center gap-1.5 mb-2">
                <Shield className="w-3 h-3 text-yellow-400" />
                <span className="text-[10px] font-semibold text-gray-300 uppercase tracking-wider">News Impact</span>
              </div>
              <div className="space-y-1">
                {renderCheck(news.impact === "positive" || news.sentiment === "bullish", "Positive Impact")}
                {renderCheck(news.impact === "negative" || news.sentiment === "bearish", "Negative Impact")}
                {news.score !== undefined && (
                  <div className="flex items-center gap-1.5 mt-1">
                    <span className="text-[10px] text-gray-500">Score:</span>
                    <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className={cn(
                        "h-full rounded-full",
                        (news.score || 0) > 70 ? "bg-green-500" :
                        (news.score || 0) > 40 ? "bg-yellow-500" : "bg-red-500"
                      )} style={{ width: `${news.score || 0}%` }} />
                    </div>
                    <span className="text-[10px] font-mono text-gray-400">{news.score || 0}</span>
                  </div>
                )}
                {!news.impact && news.score === undefined && <div className="text-[10px] text-gray-600 italic">No data</div>}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
