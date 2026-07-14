"use client"

import { cn, formatPrice } from "@/lib/utils"
import { TrendingUp, TrendingDown, Target } from "lucide-react"

interface SignalCardProps {
  signal: any
}

export function SignalCard({ signal }: SignalCardProps) {
  const dir = signal.direction || signal.signal || "neutral"
  const isLong = dir === "long" || dir === "bullish" || dir === "buy"
  const isShort = dir === "short" || dir === "bearish" || dir === "sell"
  const conf = signal.confidence || signal.score || 0
  const rr = signal.risk_reward || signal.risk_reward_ratio || 0

  return (
    <div className={cn(
      "p-4 rounded-xl border transition-all hover:border-gray-600",
      isLong ? "border-green-900/50 bg-gradient-to-r from-green-900/10 to-transparent" :
      isShort ? "border-red-900/50 bg-gradient-to-r from-red-900/10 to-transparent" :
      "border-gray-800 bg-gray-900/50"
    )}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-base font-bold text-white font-mono">{signal.symbol}</span>
            <span className={cn(
              "text-xs font-bold px-2 py-0.5 rounded",
              isLong ? "bg-green-900/50 text-green-400" :
              isShort ? "bg-red-900/50 text-red-400" :
              "bg-yellow-900/50 text-yellow-400"
            )}>
              {isLong ? "LONG" : isShort ? "SHORT" : "WAIT"}
            </span>
          </div>
          {signal.reason && (
            <div className="text-xs text-gray-500 mt-0.5">{signal.reason}</div>
          )}
        </div>
        <div className="text-right">
          <div className={cn(
            "text-lg font-bold font-mono",
            isLong ? "text-green-400" : isShort ? "text-red-400" : "text-yellow-400"
          )}>
            {conf}%
          </div>
          <div className="text-[10px] text-gray-500">Confidence</div>
        </div>
      </div>

      {/* Price Levels */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="p-2 rounded-lg bg-gray-800/30">
          <div className="text-[10px] text-gray-500">Entry</div>
          <div className="text-xs font-bold text-white font-mono">
            ${(signal.entry_price || signal.price || 0).toFixed(2)}
          </div>
        </div>
        <div className="p-2 rounded-lg bg-red-900/20">
          <div className="text-[10px] text-red-400">Stop Loss</div>
          <div className="text-xs font-bold text-red-400 font-mono">
            ${(signal.stop_loss || 0).toFixed(2)}
          </div>
        </div>
        <div className="p-2 rounded-lg bg-green-900/20">
          <div className="text-[10px] text-green-400">Take Profit</div>
          <div className="text-xs font-bold text-green-400 font-mono">
            ${(signal.take_profit || signal.take_profit_1 || 0).toFixed(2)}
          </div>
        </div>
      </div>

      {/* Meta */}
      <div className="flex items-center gap-3 text-[10px] text-gray-600">
        {rr > 0 && (
          <div className="flex items-center gap-1">
            <Target className="w-3 h-3" />
            <span>R:R 1:{rr.toFixed(1)}</span>
          </div>
        )}
        {signal.timeframe && (
          <span>{signal.timeframe}</span>
        )}
        {signal.signal_type && (
          <span className="px-1.5 py-0.5 rounded bg-gray-800 text-gray-500">{signal.signal_type}</span>
        )}
      </div>
    </div>
  )
}
