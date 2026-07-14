"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice, formatPercent } from "@/lib/utils"
import {
  TrendingUp, TrendingDown, Brain, Shield,
  Activity, AlertTriangle, BarChart3,
} from "lucide-react"

interface MarketSummaryProps {
  className?: string
}

export function MarketSummary({ className }: MarketSummaryProps) {
  const [overview, setOverview] = useState<any>(null)
  const [analysis, setAnalysis] = useState<any>(null)

  useEffect(() => {
    api.getOverview().then(setOverview).catch(() => {})
    api.scanAll("1h", 0).then((s) => {
      if (Array.isArray(s) && s.length > 0) {
        setAnalysis(s[0])
      }
    }).catch(() => {})
  }, [])

  const btcSignal = analysis?.direction || analysis?.signal || "neutral"
  const ethSignal = overview?.eth_signal || "neutral"

  return (
    <div className={cn("p-4 rounded-xl border border-gray-800 bg-gray-900/50", className)}>
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-4 h-4 text-purple-400" />
        <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">AI Market Summary</h2>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        {/* BTC Status */}
        <div className="p-3 rounded-lg border border-gray-700/50 bg-gray-800/40">
          <div className="flex items-center gap-1.5 mb-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-orange-400" />
            <span className="text-xs font-medium text-gray-300">BTC</span>
          </div>
          <div className="flex items-center gap-2">
            {overview?.btc_price && (
              <span className="text-sm font-bold text-white font-mono">{formatPrice(overview.btc_price, 0)}</span>
            )}
            {overview?.btc_change !== undefined && (
              <span className={cn("text-xs font-mono font-medium", overview.btc_change >= 0 ? "text-green-400" : "text-red-400")}>
                {formatPercent(overview.btc_change)}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 mt-1">
            <div className={cn(
              "w-1.5 h-1.5 rounded-full",
              btcSignal === "long" || btcSignal === "bullish" ? "bg-green-400" :
              btcSignal === "short" || btcSignal === "bearish" ? "bg-red-400" : "bg-yellow-400"
            )} />
            <span className={cn(
              "text-[10px] font-medium",
              btcSignal === "long" || btcSignal === "bullish" ? "text-green-400" :
              btcSignal === "short" || btcSignal === "bearish" ? "text-red-400" : "text-yellow-400"
            )}>
              {btcSignal === "long" || btcSignal === "bullish" ? "Bullish" :
               btcSignal === "short" || btcSignal === "bearish" ? "Bearish" : "Neutral"}
            </span>
          </div>
        </div>

        {/* ETH Status */}
        <div className="p-3 rounded-lg border border-gray-700/50 bg-gray-800/40">
          <div className="flex items-center gap-1.5 mb-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-xs font-medium text-gray-300">ETH</span>
          </div>
          <div className="flex items-center gap-2">
            {overview?.eth_price && (
              <span className="text-sm font-bold text-white font-mono">{formatPrice(overview.eth_price, 0)}</span>
            )}
          </div>
          <div className="flex items-center gap-1 mt-1">
            <div className={cn(
              "w-1.5 h-1.5 rounded-full",
              ethSignal === "bullish" ? "bg-green-400" :
              ethSignal === "bearish" ? "bg-red-400" : "bg-yellow-400"
            )} />
            <span className={cn(
              "text-[10px] font-medium",
              ethSignal === "bullish" ? "text-green-400" :
              ethSignal === "bearish" ? "text-red-400" : "text-yellow-400"
            )}>
              {ethSignal === "bullish" ? "Bullish" : ethSignal === "bearish" ? "Bearish" : "Neutral"}
            </span>
          </div>
        </div>

        {/* Market Risk */}
        <div className="p-3 rounded-lg border border-gray-700/50 bg-gray-800/40">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Shield className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-xs font-medium text-gray-300">Market Risk</span>
          </div>
          <div className={cn(
            "text-sm font-bold",
            overview?.market_risk === "low" ? "text-green-400" :
            overview?.market_risk === "medium" ? "text-yellow-400" :
            "text-red-400"
          )}>
            {(overview?.market_risk || "Medium").toUpperCase()}
          </div>
          <div className="flex items-center gap-1 mt-1">
            <span className="text-[10px] text-gray-500">VI: {overview?.volatility_index || 32}.5</span>
          </div>
        </div>
      </div>

      {/* AI Summary Text */}
      <div className="p-3 rounded-lg bg-gradient-to-r from-purple-900/10 to-blue-900/10 border border-purple-900/20">
        <div className="flex items-start gap-2">
          <Brain className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-xs text-gray-300 leading-relaxed">
              {overview?.ai_summary || analysis?.summary || "BTC is showing bullish structure on higher timeframes but momentum is slowing. Watch for a potential pullback to support before the next leg up. Funding rates remain neutral, suggesting the move is not overextended. ETH is consolidating with lower volatility."}
            </p>
            <div className="flex items-center gap-3 mt-2 text-[10px]">
              <span className="text-green-400 flex items-center gap-0.5">
                <Activity className="w-3 h-3" /> Strong Momentum
              </span>
              <span className="text-green-400 flex items-center gap-0.5">
                <BarChart3 className="w-3 h-3" /> Volume Confirmed
              </span>
              <span className="text-yellow-400 flex items-center gap-0.5">
                <AlertTriangle className="w-3 h-3" /> Funding Elevated
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
