"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice, formatPercent } from "@/lib/utils"
import { TrendingUp, TrendingDown, BarChart3 } from "lucide-react"

export function MarketOverview() {
  const [overview, setOverview] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getOverview().then(setOverview).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-3">
          <div className="h-3 w-24 bg-gray-800 rounded" />
          <div className="h-8 w-full bg-gray-800 rounded" />
          <div className="h-8 w-full bg-gray-800 rounded" />
        </div>
      </div>
    )
  }

  const markets = [
    {
      symbol: "BTC/USDT",
      price: overview?.btc_price,
      change: overview?.btc_change,
      high: overview?.btc_high,
      low: overview?.btc_low,
      volume: overview?.btc_volume,
      color: "orange",
    },
    {
      symbol: "ETH/USDT",
      price: overview?.eth_price,
      change: overview?.eth_change,
      high: overview?.eth_high,
      low: overview?.eth_low,
      volume: overview?.eth_volume,
      color: "blue",
    },
  ]

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Market Overview</h3>
      <div className="space-y-3">
        {markets.map((m) => (
          <div key={m.symbol} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/30 hover:bg-gray-800/50 transition-colors">
            <div className="flex items-center gap-3">
              <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold",
                m.color === "orange" ? "bg-orange-500/20 text-orange-400" : "bg-blue-500/20 text-blue-400")}>
                {m.symbol.split("/")[0]}
              </div>
              <div>
                <div className="text-sm font-medium text-white">{m.symbol}</div>
                <div className="text-xs text-gray-500">
                  Vol: {m.volume ? `${(m.volume / 1e9).toFixed(2)}B` : "--"}
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm font-bold text-white font-mono">{formatPrice(m.price)}</div>
              <div className={cn("text-xs font-mono flex items-center gap-1 justify-end",
                (m.change || 0) >= 0 ? "text-green-400" : "text-red-400")}>
                {(m.change || 0) >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {formatPercent(m.change)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
