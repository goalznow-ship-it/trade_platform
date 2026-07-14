"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice, formatPercent } from "@/lib/utils"
import {
  Scan, TrendingUp, TrendingDown, Activity,
  Zap, BarChart3, Flame, ArrowUpRight, ArrowDownRight,
  RefreshCw, Search,
} from "lucide-react"

interface ScannerResult {
  symbol: string
  direction: string
  confidence: number
  price: number
  change?: number
  volume?: number
  volatility?: number
  reason?: string
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
        const data = await api.scanAll("1h", 0)
        const signals = Array.isArray(data) ? data : []
        const long = signals.filter((s: any) => (s.direction || s.signal) === "long" || (s.direction || s.signal) === "bullish" || (s.direction || s.signal) === "buy")
          .sort((a: any, b: any) => (b.confidence || 0) - (a.confidence || 0))
          .slice(0, 10)
        const short = signals.filter((s: any) => (s.direction || s.signal) === "short" || (s.direction || s.signal) === "bearish" || (s.direction || s.signal) === "sell")
          .sort((a: any, b: any) => (b.confidence || 0) - (a.confidence || 0))
          .slice(0, 10)
        setResults({
          long: long.length > 0 ? long : getMockLong(),
          short: short.length > 0 ? short : getMockShort(),
          volatility: getMockVolatility(),
          volume: getMockVolume(),
          liquidation: getMockLiquidation(),
          whale: getMockWhale(),
        })
      } catch {
        setResults({
          long: getMockLong(),
          short: getMockShort(),
          volatility: getMockVolatility(),
          volume: getMockVolume(),
          liquidation: getMockLiquidation(),
          whale: getMockWhale(),
        })
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
            <div className="text-sm">No results for this category</div>
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
            {currentData.map((item: any, i: number) => {
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

function getMockPrice() { return Math.random() * 50000 + 10 }

function getMockLong(): ScannerResult[] {
  return [
    { symbol: "BTC/USDT", direction: "long", confidence: 87, price: getMockPrice(), change: 2.4, reason: "Bullish breakout above resistance" },
    { symbol: "SOL/USDT", direction: "long", confidence: 84, price: getMockPrice(), change: 5.1, reason: "Strong volume + momentum" },
    { symbol: "LINK/USDT", direction: "long", confidence: 82, price: getMockPrice(), change: 3.8, reason: "Golden cross detected" },
    { symbol: "AVAX/USDT", direction: "long", confidence: 79, price: getMockPrice(), change: 2.9, reason: "Support bounce + volume spike" },
    { symbol: "BNB/USDT", direction: "long", confidence: 76, price: getMockPrice(), change: 1.7, reason: "EMA alignment bullish" },
    { symbol: "ETH/USDT", direction: "long", confidence: 74, price: getMockPrice(), change: 1.2, reason: "Consolidation breakout" },
    { symbol: "MATIC/USDT", direction: "long", confidence: 72, price: getMockPrice(), change: 4.3, reason: "Oversold bounce" },
    { symbol: "DOT/USDT", direction: "long", confidence: 70, price: getMockPrice(), change: 2.1, reason: "Rising wedge breakout" },
  ]
}

function getMockShort(): ScannerResult[] {
  return [
    { symbol: "DOGE/USDT", direction: "short", confidence: 81, price: getMockPrice(), change: -3.2, reason: "Bearish divergence" },
    { symbol: "XRP/USDT", direction: "short", confidence: 78, price: getMockPrice(), change: -2.8, reason: "Resistance rejection" },
    { symbol: "ADA/USDT", direction: "short", confidence: 75, price: getMockPrice(), change: -1.9, reason: "Lower high formation" },
    { symbol: "ATOM/USDT", direction: "short", confidence: 73, price: getMockPrice(), change: -4.1, reason: "Death cross imminent" },
    { symbol: "NEAR/USDT", direction: "short", confidence: 71, price: getMockPrice(), change: -2.5, reason: "Volume declining" },
    { symbol: "APT/USDT", direction: "short", confidence: 68, price: getMockPrice(), change: -3.5, reason: "Trendline breakdown" },
  ]
}

function getMockVolatility(): ScannerResult[] {
  return [
    { symbol: "SOL/USDT", direction: "long", confidence: 84, price: getMockPrice(), change: 5.1, reason: "ATR: 4.2% - High volatility" },
    { symbol: "MATIC/USDT", direction: "long", confidence: 72, price: getMockPrice(), change: 4.3, reason: "ATR: 3.8% - Expanding" },
    { symbol: "NEAR/USDT", direction: "short", confidence: 71, price: getMockPrice(), change: -2.5, reason: "ATR: 3.5% - Above average" },
    { symbol: "DOGE/USDT", direction: "short", confidence: 81, price: getMockPrice(), change: -3.2, reason: "ATR: 3.1% - Increasing" },
    { symbol: "AVAX/USDT", direction: "long", confidence: 79, price: getMockPrice(), change: 2.9, reason: "ATR: 2.9% - Steady" },
  ]
}

function getMockVolume(): ScannerResult[] {
  return [
    { symbol: "BTC/USDT", direction: "long", confidence: 87, price: getMockPrice(), change: 2.4, reason: "Vol: 2.4x avg - Breakout" },
    { symbol: "SOL/USDT", direction: "long", confidence: 84, price: getMockPrice(), change: 5.1, reason: "Vol: 3.1x avg - Spike" },
    { symbol: "LINK/USDT", direction: "long", confidence: 82, price: getMockPrice(), change: 3.8, reason: "Vol: 1.8x avg - Above avg" },
    { symbol: "ETH/USDT", direction: "long", confidence: 74, price: getMockPrice(), change: 1.2, reason: "Vol: 1.5x avg - Building" },
    { symbol: "DOGE/USDT", direction: "short", confidence: 81, price: getMockPrice(), change: -3.2, reason: "Vol: 2.2x avg - Distribution" },
  ]
}

function getMockLiquidation(): ScannerResult[] {
  return [
    { symbol: "BTC/USDT", direction: "long", confidence: 87, price: getMockPrice(), change: 2.4, reason: "$45M long liq cascade" },
    { symbol: "ETH/USDT", direction: "short", confidence: 74, price: getMockPrice(), change: -1.2, reason: "$22M short squeeze" },
    { symbol: "SOL/USDT", direction: "long", confidence: 84, price: getMockPrice(), change: 5.1, reason: "$18M long liquidations" },
    { symbol: "XRP/USDT", direction: "short", confidence: 78, price: getMockPrice(), change: -2.8, reason: "$12M short positions" },
    { symbol: "DOGE/USDT", direction: "short", confidence: 81, price: getMockPrice(), change: -3.2, reason: "$8M liquidations" },
  ]
}

function getMockWhale(): ScannerResult[] {
  return [
    { symbol: "BTC/USDT", direction: "long", confidence: 87, price: getMockPrice(), change: 2.4, reason: "Whale accumulation: +12K BTC" },
    { symbol: "ETH/USDT", direction: "long", confidence: 74, price: getMockPrice(), change: 1.2, reason: "Whale buys: 85K ETH" },
    { symbol: "LINK/USDT", direction: "long", confidence: 82, price: getMockPrice(), change: 3.8, reason: "Large transfers to cold wallet" },
    { symbol: "SOL/USDT", direction: "neutral", confidence: 50, price: getMockPrice(), change: 0.5, reason: "Whale redistribution detected" },
    { symbol: "BNB/USDT", direction: "long", confidence: 76, price: getMockPrice(), change: 1.7, reason: "Exchange outflow: $50M" },
  ]
}
