"use client"

import { useEffect, useState, memo } from "react"
import { useMarketStore } from "@/store/market"
import type { TickerData } from "@/store/market"
import { cn, formatPrice, formatPercent, formatVolume } from "@/lib/utils"
import { TrendingUp, TrendingDown, Clock } from "lucide-react"

const TOP_ASSETS = [
  { symbol: "BTC/USDT", color: "bg-orange-500/20 text-orange-400", key: "btc" },
  { symbol: "ETH/USDT", color: "bg-blue-500/20 text-blue-400", key: "eth" },
  { symbol: "SOL/USDT", color: "bg-purple-500/20 text-purple-400", key: "sol" },
  { symbol: "BNB/USDT", color: "bg-yellow-500/20 text-yellow-400", key: "bnb" },
  { symbol: "XRP/USDT", color: "bg-cyan-500/20 text-cyan-400", key: "xrp" },
  { symbol: "SUI/USDT", color: "bg-emerald-500/20 text-emerald-400", key: "sui" },
]

const AssetCard = memo(function AssetCard({ asset, ticker }: { asset: typeof TOP_ASSETS[0]; ticker: TickerData | undefined }) {
  const base = asset.symbol.split("/")[0]
  const price = ticker?.price
  const change = ticker?.change
  const high = ticker?.high_24h
  const low = ticker?.low_24h
  const volume = ticker?.volume_24h

  return (
    <div className="p-2.5 rounded-lg bg-gray-800/20 hover:bg-gray-800/40 transition-all duration-200 border border-transparent hover:border-gray-700/30">
      <div className="flex items-center gap-2 mb-1.5">
        <div className={cn("w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-bold", asset.color)}>
          {base[0]}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-white">{asset.symbol}</div>
        </div>
        {change != null && (
          <div className={cn("text-[10px] font-mono font-medium flex items-center gap-0.5",
            change >= 0 ? "text-green-400" : "text-red-400")}>
            {change >= 0 ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
            {formatPercent(change)}
          </div>
        )}
      </div>
      <div className="flex items-center justify-between">
        <div className="text-sm font-bold text-white font-mono">
          {price ? formatPrice(price, price < 10 ? 4 : 2) : "--"}
        </div>
        {volume != null && <span className="text-[9px] text-gray-600">Vol: {formatVolume(volume)}</span>}
      </div>
      {(high || low) && (
        <div className="flex gap-2 mt-1 text-[9px] text-gray-600">
          {high && <span>H: {formatPrice(high)}</span>}
          {low && <span>L: {formatPrice(low)}</span>}
        </div>
      )}
    </div>
  )
})

export function MarketOverview() {
  const tickers = useMarketStore((s) => s.tickers)
  const lastPerChannel = useMarketStore((s) => s.lastPerChannel)
  const [now, setNow] = useState(Date.now)
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 5000)
    return () => clearInterval(interval)
  }, [])
  const lastUpdate = lastPerChannel["ticker"]
  const ago = lastUpdate ? `${Math.floor((now - lastUpdate) / 1000)}s` : null

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Market Overview</h3>
        <div className="flex items-center gap-2 text-[9px] text-gray-600">
          {ago && (
            <span className="flex items-center gap-1">
              <Clock className="w-2.5 h-2.5" />{ago}
            </span>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
        {TOP_ASSETS.map((asset) => (
          <AssetCard key={asset.symbol} asset={asset} ticker={tickers[asset.symbol]} />
        ))}
      </div>
    </div>
  )
}
