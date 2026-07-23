"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice, formatPercent } from "@/lib/utils"
import {
  TrendingUp, TrendingDown, Activity,
  Zap, BarChart3, Flame,
  RefreshCw, Search,
} from "lucide-react"

interface ScannerResult {
  symbol: string
  direction?: string
  signal?: string
  confidence?: number
  score?: number
  price?: number
  change?: number
  volume?: number
  volatility?: number
  reason?: string
  signal_type?: string
  details?: {
    atr?: number
  }
  scores?: {
    volume?: number
  }
  futures?: {
    liquidation?: unknown
  }
  providerUnavailable?: boolean
}

export function MarketScanner() {
  const [results, setResults] = useState<{
    long: ScannerResult[]
    short: ScannerResult[]
    volatility: ScannerResult[]
    volume: ScannerResult[]
    liquidation: ScannerResult[]
    whale: ScannerResult[]
  }>({ long: [], short: [], volatility: [], volume: [], liquidation: [], whale: [] })
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<string>("long")

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [data, whaleData] = await Promise.all([
          api.scanAllV2(0),
          api.getRecentWhales(10).catch(() => []),
        ])
        const signals: ScannerResult[] = Array.isArray(data) ? data : []
        const whaleSignals: ScannerResult[] = Array.isArray(whaleData)
          ? whaleData.map((item: Record<string, unknown>) => ({
              symbol: String(item.symbol || "N/A"),
              direction: String(item.direction || "neutral"),
              price: typeof item.price === "number" ? item.price : undefined,
              reason: `Real whale transfer: ${String(item.amount ?? "N/A")}`,
            }))
          : []
        const long = signals.filter((s: ScannerResult) => (s.direction || s.signal) === "long" || (s.direction || s.signal) === "bullish" || (s.direction || s.signal) === "buy")
          .sort((a: ScannerResult, b: ScannerResult) => (b.confidence || 0) - (a.confidence || 0))
          .slice(0, 10)
        const short = signals.filter((s: ScannerResult) => (s.direction || s.signal) === "short" || (s.direction || s.signal) === "bearish" || (s.direction || s.signal) === "sell")
          .sort((a: ScannerResult, b: ScannerResult) => (b.confidence || 0) - (a.confidence || 0))
          .slice(0, 10)
        setResults({
          long, short,
          volatility: signals.filter((s: ScannerResult) => s.details?.atr && s.details.atr > 2).slice(0, 5),
          volume: signals.filter((s: ScannerResult) => (s.scores?.volume || 0) > 0.3).slice(0, 5),
          liquidation: signals.filter((s: ScannerResult) => s.futures?.liquidation).slice(0, 5),
          whale: whaleSignals.slice(0, 5),
        })
      } catch {
        setResults({ long: [], short: [], volatility: [], volume: [], liquidation: [], whale: [] })
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [])

  const tabs = [
    { id: "long", label: "Best LONG", icon: TrendingUp, color: "text-green-400" },
    { id: "short", label: "Best SHORT", icon: TrendingDown, color: "text-red-400" },
    { id: "volatility", label: "High Volatility", icon: Activity, color: "text-orange-400" },
    { id: "volume", label: "Volume Breakout", icon: BarChart3, color: "text-blue-400" },
    { id: "liquidation", label: "Liquidation Events", icon: Flame, color: "text-purple-400" },
    { id: "whale", label: "Whale Activity", icon: Zap, color: "text-yellow-400" },
  ]

  const currentData = results[activeTab as keyof typeof results] || []
  const providerUnavailable = activeTab === "liquidation" || activeTab === "whale"

  return (
    <div className="h-full overflow-y-auto bg-[#0d1117]">
      <div className="max-w-6xl mx-auto p-4 lg:p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white">Market Scanner</h1>
            <p className="text-xs text-gray-500 mt-0.5">Real-time market scanning across all categories</p>
          </div>
          <button onClick={() => window.location.reload()}
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs text-gray-400 hover:text-white bg-gray-800 rounded-md hover:bg-gray-700 transition-colors">
            <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} /> Scan
          </button>
        </div>

        {/* Scanner Tabs */}
        <div className="flex flex-wrap gap-1 p-1 rounded-lg border border-gray-800 bg-gray-900/50">
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-2 text-xs rounded-md transition-all flex-1 min-w-[100px] justify-center",
                activeTab === tab.id
                  ? "bg-gray-800 text-white shadow-sm"
                  : "text-gray-500 hover:text-gray-300 hover:bg-gray-800/50"
              )}>
              <tab.icon className={cn("w-3.5 h-3.5", activeTab === tab.id ? tab.color : "")} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Results */}
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="p-3 rounded-lg border border-gray-800 bg-gray-900/30">
                <div className="animate-pulse flex items-center gap-3">
                  <div className="h-4 w-24 bg-gray-800 rounded" />
                  <div className="flex-1" />
                  <div className="h-4 w-16 bg-gray-800 rounded" />
                  <div className="h-4 w-12 bg-gray-800 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : currentData.length === 0 ? (
          <div className="text-center py-12 text-gray-600">
            <Search className="w-8 h-8 mx-auto mb-2" />
            <div className="text-sm">
              {providerUnavailable ? "Real provider unavailable or no verified events" : "No real results for this category"}
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            {/* Header */}
            <div className="flex items-center px-3 py-1.5 text-[10px] text-gray-500 uppercase tracking-wider">
              <span className="w-8">#</span>
              <span className="w-28">Symbol</span>
              <span className="w-16">Signal</span>
              <span className="w-20 text-right">Confidence</span>
              <span className="w-24 text-right">Price</span>
              <span className="w-20 text-right">Change</span>
              <span className="flex-1 text-right">Reason</span>
            </div>
            {currentData.map((item: ScannerResult, i: number) => {
              const isLong = (item.direction || item.signal) === "long" || (item.direction || item.signal) === "bullish"
              const isShort = (item.direction || item.signal) === "short" || (item.direction || item.signal) === "bearish"
              return (
                <div key={i}
                  className="flex items-center px-3 py-2.5 rounded-lg border border-gray-800/50 bg-gray-900/20 hover:bg-gray-800/40 transition-colors">
                  <span className="w-8 text-[10px] text-gray-600 font-mono">{i + 1}</span>
                  <span className="w-28 text-xs font-mono font-medium text-white">{item.symbol}</span>
                  <span className="w-16">
                    <span className={cn(
                      "text-[10px] font-bold px-1.5 py-0.5 rounded",
                      isLong ? "bg-green-900/50 text-green-400" :
                      isShort ? "bg-red-900/50 text-red-400" :
                      "bg-yellow-900/50 text-yellow-400"
                    )}>
                      {isLong ? "LONG" : isShort ? "SHORT" : "NEUTRAL"}
                    </span>
                  </span>
                  <span className="w-20 text-right">
                    <span className={cn(
                      "text-xs font-bold font-mono",
                      isLong ? "text-green-400" : isShort ? "text-red-400" : "text-yellow-400"
                    )}>
                      {item.confidence || item.score || 0}%
                    </span>
                  </span>
                  <span className="w-24 text-right text-xs font-mono text-gray-300">
                    {formatPrice(item.price || 0, 2)}
                  </span>
                  <span className="w-20 text-right">
                    {item.change !== undefined && (
                      <span className={cn("text-xs font-mono", item.change >= 0 ? "text-green-400" : "text-red-400")}>
                        {formatPercent(item.change)}
                      </span>
                    )}
                  </span>
                  <span className="flex-1 text-right text-[11px] text-gray-500 truncate pl-2">
                    {item.reason || item.signal_type || "--"}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

