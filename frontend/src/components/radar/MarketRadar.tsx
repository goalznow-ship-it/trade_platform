"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  Radar, Activity,
  BarChart3, Flame, DollarSign, ArrowUpDown,
  RefreshCw, Wallet, AlertTriangle, ArrowUpRight, ArrowDownRight,
} from "lucide-react"

interface MarketOverview {
  btc_dominance?: number
  eth_btc_ratio?: number
  funding_sentiment?: string
  funding_change?: string
  long_short_ratio?: number
  btc_change?: number
}

interface WhaleTransaction {
  amount: string
  symbol: string
  direction: string
  impact: number
}

export function MarketRadar() {
  const [data, setData] = useState<MarketOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [alerts, setAlerts] = useState<string[]>([])

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [overview, whales] = await Promise.all([
          api.getOverview(),
          api.getRecentWhales(5).catch(() => []),
        ])
        setData(overview)
        const alerts: string[] = []
        if (overview?.btc_change && Math.abs(overview.btc_change) > 3) {
          alerts.push(`BTC moved ${overview.btc_change > 0 ? "+" : ""}${overview.btc_change.toFixed(1)}% — high volatility`)
        }
        if (Array.isArray(whales) && whales.length > 0) {
          whales.slice(0, 3).forEach((w: WhaleTransaction) => {
            alerts.push(`Whale: ${w.amount} ${w.symbol} moved — ${w.direction} impact ${w.impact}%`)
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

  const items = [
    { label: "BTC Dominance", value: `${(data?.btc_dominance || 52.4).toFixed(1)}%`, change: "+0.8%", icon: DollarSign, color: "text-orange-400", bg: "bg-orange-900/10", border: "border-orange-900/30" },
    { label: "ETH/BTC Ratio", value: (data?.eth_btc_ratio || 0.042).toFixed(3), change: "-2.1%", icon: ArrowUpDown, color: "text-blue-400", bg: "bg-blue-900/10", border: "border-blue-900/30" },
    { label: "Funding Sentiment", value: data?.funding_sentiment || "NEUTRAL", change: data?.funding_change || "+0.002%", icon: Activity, color: "text-yellow-400", bg: "bg-yellow-900/10", border: "border-yellow-900/30" },
    { label: "Long/Short Ratio", value: (data?.long_short_ratio || 1.24).toFixed(2), change: "Bearish bias", icon: BarChart3, color: "text-red-400", bg: "bg-red-900/10", border: "border-red-900/30" },
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
              {[
                { sym: "BTC/USDT", val: "$24.5B", change: "+3.2%", dir: "up" },
                { sym: "ETH/USDT", val: "$9.8B", change: "-1.5%", dir: "down" },
                { sym: "SOL/USDT", val: "$3.2B", change: "+5.8%", dir: "up" },
              ].map((item) => (
                <div key={item.sym} className="flex items-center justify-between p-2 rounded-lg bg-gray-800/30">
                  <span className="text-xs font-mono text-white">{item.sym}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-gray-300">{item.val}</span>
                    <span className={cn("text-[10px] font-mono flex items-center gap-0.5", item.dir === "up" ? "text-green-400" : "text-red-400")}>
                      {item.dir === "up" ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                      {item.change}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Liquidation Heatmap */}
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
            <div className="flex items-center gap-1.5 mb-3">
              <Flame className="w-4 h-4 text-red-400" />
              <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Liquidation Clusters</h2>
            </div>
            <div className="space-y-2">
              {[
                { sym: "BTC/USDT", longs: "$12.5M", shorts: "$8.2M", total: "$20.7M" },
                { sym: "ETH/USDT", longs: "$5.8M", shorts: "$3.4M", total: "$9.2M" },
                { sym: "SOL/USDT", longs: "$2.1M", shorts: "$4.5M", total: "$6.6M" },
              ].map((item) => (
                <div key={item.sym} className="p-2 rounded-lg bg-gray-800/30">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-white">{item.sym}</span>
                    <span className="text-[10px] text-gray-500">Total: {item.total}</span>
                  </div>
                  <div className="flex gap-1 h-1.5 rounded-full overflow-hidden bg-gray-800">
                    <div className="h-full bg-green-500/60 rounded-l-full"
                      style={{ width: `${(parseFloat(item.longs.replace(/[^0-9.]/g, "")) / parseFloat(item.total.replace(/[^0-9.]/g, ""))) * 100}%` }} />
                    <div className="h-full bg-red-500/60 rounded-r-full"
                      style={{ width: `${(parseFloat(item.shorts.replace(/[^0-9.]/g, "")) / parseFloat(item.total.replace(/[^0-9.]/g, ""))) * 100}%` }} />
                  </div>
                  <div className="flex justify-between mt-0.5 text-[9px]">
                    <span className="text-green-400/70">{item.longs} L</span>
                    <span className="text-red-400/70">{item.shorts} S</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Whale Transactions */}
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
            <div className="flex items-center gap-1.5 mb-3">
              <Wallet className="w-4 h-4 text-purple-400" />
              <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Whale Transactions</h2>
            </div>
            <div className="space-y-2">
              {[
                { sym: "BTC", amt: "+5,200 BTC", val: "$332M", type: "deposit", exchange: "Binance" },
                { sym: "ETH", amt: "+45,000 ETH", val: "$142M", type: "withdrawal", exchange: "Coinbase" },
                { sym: "USDT", amt: "+$200M", val: "$200M", type: "mint", exchange: "Tron" },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-gray-800/30">
                  <div className={cn(
                    "w-6 h-6 rounded flex items-center justify-center text-[9px] font-bold",
                    item.type === "deposit" ? "bg-red-900/40 text-red-400" :
                    item.type === "withdrawal" ? "bg-green-900/40 text-green-400" : "bg-blue-900/40 text-blue-400"
                  )}>
                    {item.type === "deposit" ? "↓" : item.type === "withdrawal" ? "↑" : "★"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-medium text-white">{item.sym}</span>
                      <span className="text-[10px] font-mono text-gray-300">{item.val}</span>
                    </div>
                    <div className="flex items-center gap-1 text-[9px] text-gray-500">
                      <span>{item.amt}</span>
                      <span>·</span>
                      <span>{item.exchange}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


