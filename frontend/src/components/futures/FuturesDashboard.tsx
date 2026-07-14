"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice, formatPercent } from "@/lib/utils"
import {
  TrendingUp, TrendingDown, Activity, Zap,
  DollarSign, BarChart3, Flame, AlertTriangle,
} from "lucide-react"

export function FuturesDashboard() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const res = await request("/api/v1/enterprise/futures-dashboard")
        setData(Array.isArray(res) ? res : [])
      } catch {
        setData(getMockData())
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="p-4 lg:p-6 space-y-4">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-gray-800 rounded" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-800 rounded-xl" />
            ))}
          </div>
          <div className="h-64 bg-gray-800 rounded-xl" />
        </div>
      </div>
    )
  }

  const sortedByFunding = [...data].sort((a, b) => Math.abs(b.funding_rate || 0) - Math.abs(a.funding_rate || 0))
  const sortedByConfidence = [...data].sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
  const topGainers = data.filter((d) => d.direction === "long").slice(0, 3)
  const topLosers = data.filter((d) => d.direction === "short").slice(0, 3)

  return (
    <div className="h-full overflow-y-auto bg-[#0d1117]">
      <div className="max-w-7xl mx-auto p-4 lg:p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white">Futures Intelligence</h1>
            <p className="text-xs text-gray-500 mt-0.5">Real-time futures market analysis across all assets</p>
          </div>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <Activity className="w-3 h-3" /> Auto-refresh 60s
          </div>
        </div>

        {/* Market Overview Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl border border-green-900/30 bg-green-900/10">
            <div className="flex items-center gap-1 text-xs text-green-400 mb-1">
              <TrendingUp className="w-3.5 h-3.5" /> Bullish Signals
            </div>
            <div className="text-2xl font-bold text-white">{topGainers.length}</div>
          </div>
          <div className="p-4 rounded-xl border border-red-900/30 bg-red-900/10">
            <div className="flex items-center gap-1 text-xs text-red-400 mb-1">
              <TrendingDown className="w-3.5 h-3.5" /> Bearish Signals
            </div>
            <div className="text-2xl font-bold text-white">{topLosers.length}</div>
          </div>
          <div className="p-4 rounded-xl border border-yellow-900/30 bg-yellow-900/10">
            <div className="flex items-center gap-1 text-xs text-yellow-400 mb-1">
              <Flame className="w-3.5 h-3.5" /> Funding Extremes
            </div>
            <div className="text-2xl font-bold text-white">{sortedByFunding.filter((d) => Math.abs(d.funding_rate || 0) > 0.005).length}</div>
          </div>
          <div className="p-4 rounded-xl border border-blue-900/30 bg-blue-900/10">
            <div className="flex items-center gap-1 text-xs text-blue-400 mb-1">
              <Zap className="w-3.5 h-3.5" /> High Confidence
            </div>
            <div className="text-2xl font-bold text-white">{sortedByConfidence.filter((d) => (d.confidence || 0) > 75).length}</div>
          </div>
        </div>

        {/* Funding Extremes */}
        <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Funding Rate Extremes
          </h2>
          <div className="space-y-1.5">
            {sortedByFunding.slice(0, 8).map((item, i) => {
              const fr = item.funding_rate || 0
              const isExtreme = Math.abs(fr) > 0.01
              return (
                <div key={i}
                  className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-800/20 hover:bg-gray-800/40 transition-colors">
                  <span className="text-sm font-mono text-white w-24">{item.symbol}</span>
                  <span className={cn("text-xs font-bold px-2 py-0.5 rounded",
                    item.direction === "long" ? "bg-green-900/50 text-green-400" :
                    item.direction === "short" ? "bg-red-900/50 text-red-400" :
                    "bg-yellow-900/50 text-yellow-400")}>
                    {item.direction?.toUpperCase() || "--"}
                  </span>
                  <div className="flex-1" />
                  <span className={cn("text-xs font-mono font-medium",
                    fr > 0 ? "text-red-400" : fr < 0 ? "text-green-400" : "text-gray-500")}>
                    {fr > 0 ? "+" : ""}{(fr * 100).toFixed(4)}%
                  </span>
                  {isExtreme && <Flame className="w-3.5 h-3.5 text-orange-400" />}
                  <span className={cn("text-xs font-mono",
                    (item.confidence || 0) > 75 ? "text-green-400" : "text-gray-500")}>
                    {item.confidence || 0}%
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Top Opportunities */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl border border-green-900/30 bg-gray-900/50">
            <h2 className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-3">
              Top Bullish Setups
            </h2>
            <div className="space-y-1.5">
              {sortedByConfidence.filter((d) => d.direction === "long").slice(0, 5).map((item, i) => (
                <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-800/20">
                  <span className="text-sm font-mono text-white w-24">{item.symbol}</span>
                  <div className="flex-1">
                    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full bg-green-500 rounded-full" style={{ width: `${item.confidence || 0}%` }} />
                    </div>
                  </div>
                  <span className="text-xs font-mono text-green-400 font-bold">{item.confidence || 0}%</span>
                  <span className="text-[10px] text-gray-500">
                    FR: {(item.funding_rate || 0) > 0 ? "+" : ""}{(item.funding_rate || 0) * 100}%
                  </span>
                </div>
              ))}
              {sortedByConfidence.filter((d) => d.direction === "long").length === 0 && (
                <div className="text-center py-4 text-gray-600 text-xs">No bullish setups</div>
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl border border-red-900/30 bg-gray-900/50">
            <h2 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-3">
              Top Bearish Setups
            </h2>
            <div className="space-y-1.5">
              {sortedByConfidence.filter((d) => d.direction === "short").slice(0, 5).map((item, i) => (
                <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-800/20">
                  <span className="text-sm font-mono text-white w-24">{item.symbol}</span>
                  <div className="flex-1">
                    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full bg-red-500 rounded-full" style={{ width: `${item.confidence || 0}%` }} />
                    </div>
                  </div>
                  <span className="text-xs font-mono text-red-400 font-bold">{item.confidence || 0}%</span>
                  <span className="text-[10px] text-gray-500">
                    FR: {(item.funding_rate || 0) > 0 ? "+" : ""}{(item.funding_rate || 0) * 100}%
                  </span>
                </div>
              ))}
              {sortedByConfidence.filter((d) => d.direction === "short").length === 0 && (
                <div className="text-center py-4 text-gray-600 text-xs">No bearish setups</div>
              )}
            </div>
          </div>
        </div>

        {/* Full Market Table */}
        <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            All Markets
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-800">
                  <th className="text-left py-2 pr-4">Symbol</th>
                  <th className="text-left py-2 pr-4">Signal</th>
                  <th className="text-right py-2 pr-4">Confidence</th>
                  <th className="text-right py-2 pr-4">Funding Rate</th>
                  <th className="text-right py-2 pr-4">Long %</th>
                  <th className="text-right py-2 pr-4">Short %</th>
                </tr>
              </thead>
              <tbody>
                {data.map((item, i) => (
                  <tr key={i} className="border-b border-gray-800/50 text-gray-300 hover:bg-gray-800/30">
                    <td className="py-2.5 pr-4 font-mono font-medium">{item.symbol}</td>
                    <td className="py-2.5 pr-4">
                      <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded",
                        item.direction === "long" ? "bg-green-900/50 text-green-400" :
                        item.direction === "short" ? "bg-red-900/50 text-red-400" :
                        "bg-yellow-900/50 text-yellow-400")}>
                        {(item.direction || "neutral").toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono">{item.confidence || 0}%</td>
                    <td className={cn("py-2.5 pr-4 text-right font-mono",
                      (item.funding_rate || 0) > 0.005 ? "text-red-400" :
                      (item.funding_rate || 0) < -0.005 ? "text-green-400" : "text-gray-500")}>
                      {(item.funding_rate || 0) > 0 ? "+" : ""}{(item.funding_rate || 0).toFixed(4)}%
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono text-green-400">
                      {item.long_probability?.toFixed(0) || 50}%
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono text-red-400">
                      {item.short_probability?.toFixed(0) || 50}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

async function request(url: string) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null
  const headers: Record<string, string> = {}
  if (token) headers["Authorization"] = `Bearer ${token}`
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  const res = await fetch(`${base}${url}`, { headers })
  if (!res.ok) throw new Error("Request failed")
  return res.json()
}

function getMockData() {
  const symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "AVAX/USDT", "DOGE/USDT"]
  return symbols.map((s) => ({
    symbol: s,
    price: Math.random() * 50000 + 10,
    direction: ["long", "short", "neutral"][Math.floor(Math.random() * 3)],
    confidence: Math.floor(Math.random() * 40) + 50,
    funding_rate: (Math.random() - 0.5) * 0.02,
    funding_pressure: Math.random() > 0.5 ? "bullish" : "bearish",
    long_probability: Math.floor(Math.random() * 60) + 20,
    short_probability: Math.floor(Math.random() * 60) + 20,
  }))
}
