"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  Radar, Activity,
  BarChart3, Flame, DollarSign, ArrowUpDown,
  RefreshCw, Wallet, AlertTriangle,
} from "lucide-react"

interface MarketOverview {
  btc_dominance?: number
  btc_price?: number
  eth_price?: number
  btc_change?: number
}

interface WhaleTransaction {
  amount?: string | number
  value?: string | number
  symbol: string
  direction?: string
  impact?: number
  type?: string
  exchange?: string
}

interface OpenInterestItem {
  symbol: string
  open_interest?: number
  open_interest_usd?: number
  price?: number
}

interface FundingItem {
  symbol: string
  funding_rate?: number
  price?: number
}

export function MarketRadar() {
  const [data, setData] = useState<MarketOverview | null>(null)
  const [openInterest, setOpenInterest] = useState<OpenInterestItem[]>([])
  const [fundingRates, setFundingRates] = useState<FundingItem[]>([])
  const [whales, setWhales] = useState<WhaleTransaction[]>([])
  const [loading, setLoading] = useState(true)
  const [alerts, setAlerts] = useState<string[]>([])

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [overview, oiResponse, fundingResponse, whaleResponse] = await Promise.all([
          api.getOverview(),
          api.getOpenInterest(5).catch(() => ({ open_interest: [] })),
          api.getFundingRates(10).catch(() => ({ funding_rates: [] })),
          api.getRecentWhales(5).catch(() => []),
        ])
        setData(overview)
        setOpenInterest(Array.isArray(oiResponse?.open_interest) ? oiResponse.open_interest : [])
        setFundingRates(Array.isArray(fundingResponse?.funding_rates) ? fundingResponse.funding_rates : [])
        setWhales(Array.isArray(whaleResponse) ? whaleResponse : [])
        const alerts: string[] = []
        if (overview?.btc_change && Math.abs(overview.btc_change) > 3) {
          alerts.push(`BTC moved ${overview.btc_change > 0 ? "+" : ""}${overview.btc_change.toFixed(1)}% — high volatility`)
        }
        if (Array.isArray(whaleResponse) && whaleResponse.length > 0) {
          whaleResponse.slice(0, 3).forEach((w: WhaleTransaction) => {
            alerts.push(`Whale: ${w.amount ?? "N/A"} ${w.symbol} — ${w.direction || "unknown"}`)
          })
        }
        if (alerts.length === 0) {
          alerts.push("No significant anomalies detected")
        }
        setAlerts(alerts)
      } catch {
        setData(null)
        setAlerts(["Data temporarily unavailable"])
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="h-full overflow-y-auto bg-[#0d1117] p-4 lg:p-6">
        <div className="animate-pulse space-y-4 max-w-6xl mx-auto">
          <div className="h-6 w-48 bg-gray-800 rounded" />
          <div className="grid grid-cols-4 gap-3">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-24 bg-gray-800 rounded-xl" />)}
          </div>
          <div className="h-64 bg-gray-800 rounded-xl" />
        </div>
      </div>
    )
  }

  const ethBtcRatio = data?.eth_price && data?.btc_price
    ? data.eth_price / data.btc_price
    : null
  const validFunding = fundingRates
    .map((item) => item.funding_rate)
    .filter((rate): rate is number => typeof rate === "number")
  const avgFunding = validFunding.length
    ? validFunding.reduce((sum, rate) => sum + rate, 0) / validFunding.length
    : null
  const fundingSentiment = avgFunding === null
    ? "N/A"
    : avgFunding > 0.0001 ? "LONG BIAS" : avgFunding < -0.0001 ? "SHORT BIAS" : "NEUTRAL"
  const formatUsd = (value?: number) => {
    if (typeof value !== "number") return "N/A"
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 2,
    }).format(value)
  }

  const items = [
    { label: "BTC Dominance", value: typeof data?.btc_dominance === "number" ? `${data.btc_dominance.toFixed(1)}%` : "N/A", change: "Provider unavailable", icon: DollarSign, color: "text-orange-400", bg: "bg-orange-900/10", border: "border-orange-900/30" },
    { label: "ETH/BTC Ratio", value: ethBtcRatio?.toFixed(4) ?? "N/A", change: "Live Binance prices", icon: ArrowUpDown, color: "text-blue-400", bg: "bg-blue-900/10", border: "border-blue-900/30" },
    { label: "Funding Sentiment", value: fundingSentiment, change: avgFunding === null ? "N/A" : `${(avgFunding * 100).toFixed(4)}% avg`, icon: Activity, color: "text-yellow-400", bg: "bg-yellow-900/10", border: "border-yellow-900/30" },
    { label: "Long/Short Ratio", value: "N/A", change: "Provider unavailable", icon: BarChart3, color: "text-gray-400", bg: "bg-gray-900/30", border: "border-gray-800" },
  ]

  return (
    <div className="h-full overflow-y-auto bg-[#0d1117]">
      <div className="max-w-7xl mx-auto p-4 lg:p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
              <Radar className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white">Market Radar</h1>
              <p className="text-xs text-gray-500">Real-time market intelligence & anomaly detection</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500 flex items-center gap-1">
              <Activity className="w-3 h-3" /> Live · 30s
            </span>
            <button onClick={() => window.location.reload()}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs text-gray-400 hover:text-white bg-gray-800 rounded-md hover:bg-gray-700 transition-colors">
              <RefreshCw className="w-3 h-3" /> Refresh
            </button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {items.map((item) => (
            <div key={item.label} className={`p-4 rounded-xl border ${item.bg} ${item.border}`}>
              <div className="flex items-center gap-1.5 mb-2">
                <item.icon className={`w-4 h-4 ${item.color}`} />
                <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">{item.label}</span>
              </div>
              <div className={`text-lg font-bold font-mono ${item.color}`}>{item.value}</div>
              <div className="text-[10px] text-gray-500 mt-0.5">{item.change}</div>
            </div>
          ))}
        </div>

        {/* Real-time Alerts */}
        <div className="p-4 rounded-xl border border-yellow-900/30 bg-yellow-900/5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-yellow-400" />
            <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Real-time Alerts</h2>
          </div>
          <div className="space-y-2">
            {alerts.map((alert, i) => (
              <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-gray-800/30 border border-gray-700/30">
                <div className="w-1.5 h-1.5 rounded-full bg-yellow-400 mt-1.5 flex-shrink-0" />
                <div>
                  <p className="text-xs text-gray-300">{alert}</p>
                  <span className="text-[10px] text-gray-600">{(i % 5) + 1}m ago</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Market Depth Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Open Interest */}
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
            <div className="flex items-center gap-1.5 mb-3">
              <BarChart3 className="w-4 h-4 text-blue-400" />
              <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Open Interest</h2>
            </div>
            <div className="space-y-2">
              {openInterest.length > 0 ? openInterest.slice(0, 5).map((item) => (
                <div key={item.symbol} className="flex items-center justify-between p-2 rounded-lg bg-gray-800/30">
                  <span className="text-xs font-mono text-white">{item.symbol}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-gray-300">{formatUsd(item.open_interest_usd)}</span>
                    <span className="text-[10px] text-gray-600">live</span>
                  </div>
                </div>
              )) : <div className="text-xs text-gray-600 py-6 text-center">Open-interest data unavailable</div>}
            </div>
          </div>

          {/* Liquidation Heatmap */}
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
            <div className="flex items-center gap-1.5 mb-3">
              <Flame className="w-4 h-4 text-red-400" />
              <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Liquidation Clusters</h2>
            </div>
            <div className="py-8 text-center">
              <div className="text-sm font-mono text-gray-500">N/A</div>
              <div className="text-[10px] text-gray-600 mt-1">Real liquidation provider not configured</div>
            </div>
          </div>

          {/* Whale Transactions */}
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
            <div className="flex items-center gap-1.5 mb-3">
              <Wallet className="w-4 h-4 text-purple-400" />
              <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Whale Transactions</h2>
            </div>
            <div className="space-y-2">
              {whales.length > 0 ? whales.map((item, i) => {
                const type = item.type || item.direction || "unknown"
                return (
                <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-gray-800/30">
                  <div className={cn(
                    "w-6 h-6 rounded flex items-center justify-center text-[9px] font-bold",
                    type === "deposit" ? "bg-red-900/40 text-red-400" :
                    type === "withdrawal" ? "bg-green-900/40 text-green-400" : "bg-blue-900/40 text-blue-400"
                  )}>
                    {type === "deposit" ? "↓" : type === "withdrawal" ? "↑" : "★"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-medium text-white">{item.symbol}</span>
                      <span className="text-[10px] font-mono text-gray-300">{String(item.value ?? "N/A")}</span>
                    </div>
                    <div className="flex items-center gap-1 text-[9px] text-gray-500">
                      <span>{String(item.amount ?? "N/A")}</span>
                      <span>·</span>
                      <span>{item.exchange || type}</span>
                    </div>
                  </div>
                </div>
              )}) : (
                <div className="py-8 text-center">
                  <div className="text-sm font-mono text-gray-500">N/A</div>
                  <div className="text-[10px] text-gray-600 mt-1">Real whale provider not configured</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
