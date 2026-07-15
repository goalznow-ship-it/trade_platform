"use client"

import { memo } from "react"
import { useMarketStore } from "@/store/market"
import { cn, formatPrice, formatPercent, formatVolume, getChangeColor } from "@/lib/utils"
import {
  Globe, BarChart3, Activity, Coins,
} from "lucide-react"

const TOP_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "SUI/USDT"]

interface TickerBarProps {
  symbol: string
  price?: number
  change?: number
}

const TickerBar = memo(function TickerBar({ symbol, price, change }: TickerBarProps) {
  const base = symbol.split("/")[0]
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800/20 hover:bg-gray-800/40 transition-colors">
      <span className="text-xs font-semibold text-gray-300 w-8">{base}</span>
      {price != null ? (
        <span className="text-xs font-bold text-white font-mono">{formatPrice(price, price < 10 ? 4 : 2)}</span>
      ) : <span className="text-xs text-gray-600">--</span>}
      {change != null && (
        <span className={cn("text-[10px] font-mono font-medium", getChangeColor(change))}>
          {formatPercent(change)}
        </span>
      )}
    </div>
  )
})

export function MarketSummary() {
  const tickers = useMarketStore((s) => s.tickers)
  const fearGreed = useMarketStore((s) => s.fearGreed)
  const isLive = useMarketStore((s) => s.isLive)
  const breadth = useMarketStore((s) => s.breadth)

  const btc = tickers["BTC/USDT"]
  const totalVolume = btc?.volume_24h ? btc.volume_24h * 50 : null
  const altSeasonPct = breadth
    ? ((breadth.advancing / (breadth.advancing + breadth.declining + breadth.unchanged)) * 100)
    : null

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Market Watch</h2>
        </div>
        <div className="flex items-center gap-3">
          {isLive && <span className="text-[9px] text-green-500">● LIVE</span>}
          {fearGreed && (
            <span className="text-[9px] text-gray-500">
              F&G: {fearGreed.value} ({fearGreed.classification})
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-1.5 mb-3">
        {TOP_SYMBOLS.map((sym) => (
          <TickerBar key={sym} symbol={sym} price={tickers[sym]?.price} change={tickers[sym]?.change} />
        ))}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="p-2.5 rounded-lg bg-gray-800/20">
            <div className="flex items-center gap-1 mb-0.5">
              <BarChart3 className="w-3 h-3 text-gray-500" />
              <span className="text-[10px] text-gray-500">Est. 24h Vol.</span>
            </div>
            <div className="text-sm font-bold text-white font-mono">
              {totalVolume != null ? formatVolume(totalVolume) : "--"}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-gray-800/20">
            <div className="flex items-center gap-1 mb-0.5">
              <Globe className="w-3 h-3 text-gray-500" />
              <span className="text-[10px] text-gray-500">BTC 24h Chg</span>
            </div>
            <div className="text-sm font-bold text-white font-mono">
              {btc?.change != null ? formatPercent(btc.change) : "--"}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-gray-800/20">
            <div className="flex items-center gap-1 mb-0.5">
              <Coins className="w-3 h-3 text-gray-500" />
              <span className="text-[10px] text-gray-500">BTC Volume</span>
            </div>
            <div className="text-sm font-bold text-white font-mono">
              {btc?.volume_24h != null ? formatVolume(btc.volume_24h) : "--"}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-gray-800/20">
            <div className="flex items-center gap-1 mb-0.5">
              <Activity className="w-3 h-3 text-gray-500" />
              <span className="text-[10px] text-gray-500">Breadth</span>
            </div>
            <div className="text-sm font-bold text-white font-mono">
              {altSeasonPct != null ? `${altSeasonPct.toFixed(1)}%` : "--"}
            </div>
          </div>
      </div>
    </div>
  )
}
