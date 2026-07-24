"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice } from "@/lib/utils"
import {
  TrendingUp, TrendingDown, Activity,
  Zap, BarChart3, Flame,
  RefreshCw, Search, Clock,
} from "lucide-react"
import {
  type UnifiedSignal, normalizeSignal, displayPrice, displayDate, isStale,
  isTradeReady,
} from "@/lib/unified-signal"

interface WhaleItem {
  symbol: string
  direction: string
  price?: number
  reason?: string
}

export function MarketScanner() {
  const [results, setResults] = useState<{
    long: UnifiedSignal[]
    short: UnifiedSignal[]
    volatility: UnifiedSignal[]
    volume: UnifiedSignal[]
    whale: WhaleItem[]
  }>({ long: [], short: [], volatility: [], volume: [], whale: [] })
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<string>("long")
  const [lastUpdated, setLastUpdated] = useState<string>("")

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [data, whaleData] = await Promise.all([
          api.institutionalScan(0, 30) as Promise<{ signals?: Record<string, unknown>[] }>,
          api.getRecentWhales(10).catch(() => []),
        ])
        const rawSignals = Array.isArray(data?.signals) ? data.signals : []
        const signals = rawSignals.map(normalizeSignal)

        const whaleSignals: WhaleItem[] = Array.isArray(whaleData)
          ? whaleData.map((item: Record<string, unknown>) => ({
              symbol: String(item.symbol || "N/A"),
              direction: String(item.direction || "neutral"),
              price: typeof item.price === "number" ? item.price : undefined,
              reason: `Real whale transfer: ${String(item.amount ?? "N/A")}`,
            }))
          : []

        const tradeReady = signals.filter(isTradeReady)
        const long = tradeReady.filter((s) => s.direction === "long")
          .sort((a, b) => b.confidence - a.confidence)
          .slice(0, 10)
        const short = tradeReady.filter((s) => s.direction === "short")
          .sort((a, b) => b.confidence - a.confidence)
          .slice(0, 10)

        setResults({
          long, short,
          volatility: signals.filter((s) => {
            const rsi = s.institutional_score?.details?.rsi
            return typeof rsi === "number" && (rsi > 70 || rsi < 30)
          }).slice(0, 5),
          volume: signals.filter((s) => s.institutional_score?.scores?.volume && Math.abs(s.institutional_score.scores.volume) > 8).slice(0, 5),
          whale: whaleSignals.slice(0, 5),
        })
        setLastUpdated(new Date().toISOString())
      } catch {
        setResults({ long: [], short: [], volatility: [], volume: [], whale: [] })
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [])

  const stale = isStale(lastUpdated, 120)

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-medium text-gray-200">Market Scanner</span>
        </div>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="flex items-center gap-1 text-[10px] text-gray-500">
              <Clock className="w-3 h-3" />
              {displayDate(lastUpdated)}
              {stale && <span className="text-amber-400">Stale</span>}
            </span>
          )}
          <RefreshCw className={cn("w-3.5 h-3.5 text-gray-500", loading && "animate-spin")} />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800">
        {[
          { id: "long", label: "LONG", icon: TrendingUp, color: "text-green-400" },
          { id: "short", label: "SHORT", icon: TrendingDown, color: "text-red-400" },
          { id: "volatility", label: "Volatility", icon: Activity, color: "text-yellow-400" },
          { id: "volume", label: "Volume", icon: BarChart3, color: "text-blue-400" },
          { id: "whale", label: "Whale", icon: Flame, color: "text-orange-400" },
        ].map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors border-b-2",
              activeTab === tab.id
                ? "border-blue-500 text-white bg-gray-800/30"
                : "border-transparent text-gray-500 hover:text-gray-300 hover:bg-gray-800/20"
            )}>
            <tab.icon className={cn("w-3.5 h-3.5", tab.color)} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3">
        {loading ? (
          <div className="text-center py-6 text-gray-500 text-sm">
            <Search className="w-6 h-6 mx-auto mb-2 animate-pulse text-blue-500" />
            Loading market data...
          </div>
        ) : activeTab === "long" ? (
          <TabContent items={results.long} empty="Hazirda yüksek keyfiyyetli LONG siqnali yoxdur" color="green" />
        ) : activeTab === "short" ? (
          <TabContent items={results.short} empty="Hazirda yüksek keyfiyyetli SHORT siqnali yoxdur" color="red" />
        ) : activeTab === "volatility" ? (
          <div>{results.volatility.length === 0 ? <div className="text-center py-6 text-gray-600 text-xs">No high volatility signals</div> : results.volatility.map((item, i) => <ScannerRow key={i} signal={item} />)}</div>
        ) : activeTab === "volume" ? (
          <div>{results.volume.length === 0 ? <div className="text-center py-6 text-gray-600 text-xs">No high volume signals</div> : results.volume.map((item, i) => <ScannerRow key={i} signal={item} />)}</div>
        ) : (
          <div>{results.whale.length === 0 ? <div className="text-center py-6 text-gray-600 text-xs">No recent whale activity</div> : results.whale.map((item, i) => (
            <div key={i} className="flex items-center gap-3 p-2.5 border-b border-gray-800">
              <span className="text-xs font-mono text-white w-24">{item.symbol}</span>
              <span className="text-[10px] text-gray-400 flex-1">{item.reason}</span>
              {item.price && <span className="text-xs font-mono text-gray-400">{displayPrice(item.price)}</span>}
            </div>
          ))}</div>
        )}
      </div>
    </div>
  )
}

function TabContent({ items, empty, color }: { items: UnifiedSignal[]; empty: string; color: string }) {
  if (items.length === 0) {
    return (
      <div className="text-center py-8 text-gray-600 text-xs">{empty}</div>
    )
  }
  return (
    <div>
      {items.map((item, i) => <ScannerRow key={i} signal={item} />)}
    </div>
  )
}

function ScannerRow({ signal }: { signal: UnifiedSignal }) {
  const isLong = signal.direction === "long"
  const reasons = Object.values(signal.reasons_breakdown).slice(0, 2)

  return (
    <div className="flex items-center gap-3 p-2.5 border-b border-gray-800 hover:bg-gray-800/30 transition-colors">
      <div className={cn("w-1 h-8 rounded-full", isLong ? "bg-green-500" : "bg-red-500")} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-white font-mono">{signal.symbol}</span>
          <span className={cn(
            "text-[9px] font-bold px-1 py-0.5 rounded",
            isLong ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400"
          )}>
            {isLong ? "LONG" : "SHORT"}
          </span>
          <span className="text-[10px] font-mono text-gray-400">{signal.confidence}%</span>
        </div>
        {reasons.length > 0 && (
          <div className="text-[10px] text-gray-500 mt-0.5 truncate">{reasons.join(" · ")}</div>
        )}
      </div>
      <div className="text-right text-[10px] text-gray-500">
        <div>{displayPrice(signal.current_price)}</div>
        <div className="text-[9px]">Score: {signal.opportunity_score}</div>
      </div>
    </div>
  )
}
