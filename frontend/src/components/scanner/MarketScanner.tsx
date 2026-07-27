"use client"

import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  TrendingUp, TrendingDown, Activity, BarChart3, Flame,
  RefreshCw, Search, Clock,
} from "lucide-react"
import {
  type UnifiedSignal, normalizeSignal, displayPrice, displayDate, isStale,
  isTradeReady, isWatchlist,
} from "@/lib/unified-signal"

interface WhaleItem {
  symbol: string
  direction: string
  price?: number
  reason?: string
}

interface ScannerResults {
  long: UnifiedSignal[]
  short: UnifiedSignal[]
  volatility: UnifiedSignal[]
  volume: UnifiedSignal[]
  whale: WhaleItem[]
}

const emptyResults: ScannerResults = { long: [], short: [], volatility: [], volume: [], whale: [] }

export function MarketScanner() {
  const [results, setResults] = useState<ScannerResults>(emptyResults)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState("long")
  const [lastUpdated, setLastUpdated] = useState("")
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [data, whaleData] = await Promise.all([
        api.institutionalScan(0, 30) as Promise<{ signals?: Record<string, unknown>[] }>,
        api.getRecentWhales(10).catch(() => []),
      ])
      const rawSignals = Array.isArray(data?.signals) ? data.signals : []
      const signals = rawSignals.map(normalizeSignal)
      const directional = signals.filter((signal) => signal.direction !== "neutral")

      const whaleSignals: WhaleItem[] = Array.isArray(whaleData)
        ? whaleData.map((item: Record<string, unknown>) => ({
            symbol: String(item.symbol || "N/A"),
            direction: String(item.direction || "neutral"),
            price: typeof item.price === "number" ? item.price : undefined,
            reason: `Real böyük transfer: ${String(item.amount ?? "N/A")}`,
          }))
        : []

      setResults({
        long: directional.filter((signal) => signal.direction === "long")
          .sort((a, b) => b.confidence - a.confidence).slice(0, 10),
        short: directional.filter((signal) => signal.direction === "short")
          .sort((a, b) => b.confidence - a.confidence).slice(0, 10),
        volatility: signals.filter((signal) => {
          const rsi = signal.institutional_score?.details?.rsi
          return typeof rsi === "number" && (rsi > 70 || rsi < 30)
        }).slice(0, 5),
        volume: signals.filter((signal) => {
          const score = signal.institutional_score?.scores?.volume
          return typeof score === "number" && Math.abs(score) > 8
        }).slice(0, 5),
        whale: whaleSignals.slice(0, 5),
      })
      setLastUpdated(new Date().toISOString())
    } catch (cause) {
      setResults(emptyResults)
      setError(cause instanceof Error ? cause.message : "Scanner məlumatı alınmadı")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [load])

  const stale = isStale(lastUpdated, 120)
  const allDirectional = [...results.long, ...results.short]
  const readyCount = allDirectional.filter(isTradeReady).length
  const watchCount = allDirectional.filter(isWatchlist).length

  return (
    <div className="flex h-full flex-col bg-[#0d1117]">
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-2">
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-blue-400" />
          <div>
            <div className="text-sm font-medium text-gray-200">Market Scanner</div>
            <div className="text-[9px] text-gray-600">Top bazarlar · 1 saatlıq institusional analiz</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="flex items-center gap-1 text-[10px] text-gray-500">
              <Clock className="h-3 w-3" />
              {displayDate(lastUpdated)}
              {stale && <span className="text-amber-400">köhnə məlumat</span>}
            </span>
          )}
          <button onClick={load} disabled={loading} className="flex items-center gap-1.5 rounded-md border border-gray-700 px-2 py-1 text-[10px] text-gray-400 hover:text-white disabled:opacity-50">
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Yenilə
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-px border-b border-gray-800 bg-gray-800">
        <Summary label="İstiqamətli" value={allDirectional.length} />
        <Summary label="Ticarətə hazır" value={readyCount} color="text-green-400" />
        <Summary label="İzləmə" value={watchCount} color="text-yellow-400" />
      </div>

      <div className="flex overflow-x-auto border-b border-gray-800">
        {[
          { id: "long", label: "LONG", icon: TrendingUp, color: "text-green-400" },
          { id: "short", label: "SHORT", icon: TrendingDown, color: "text-red-400" },
          { id: "volatility", label: "Volatillik", icon: Activity, color: "text-yellow-400" },
          { id: "volume", label: "Həcm", icon: BarChart3, color: "text-blue-400" },
          { id: "whale", label: "Böyük transfer", icon: Flame, color: "text-orange-400" },
        ].map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition-colors",
              activeTab === tab.id
                ? "border-blue-500 bg-gray-800/30 text-white"
                : "border-transparent text-gray-500 hover:bg-gray-800/20 hover:text-gray-300",
            )}>
            <tab.icon className={cn("h-3.5 w-3.5", tab.color)} />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-3">
        {error ? (
          <div className="mx-auto max-w-lg rounded-lg border border-red-900/60 bg-red-950/20 p-4 text-center">
            <div className="text-xs text-red-300">Scanner məlumatı alınmadı</div>
            <div className="mt-1 text-[10px] text-gray-500">{error}</div>
            <button onClick={load} className="mt-3 rounded bg-gray-800 px-3 py-1.5 text-xs text-gray-300 hover:text-white">Yenidən yoxla</button>
          </div>
        ) : loading ? (
          <div className="py-8 text-center text-sm text-gray-500">
            <Search className="mx-auto mb-2 h-6 w-6 animate-pulse text-blue-500" />
            Real bazarlar analiz edilir...
          </div>
        ) : activeTab === "long" ? (
          <TabContent items={results.long} empty="Hazırda istiqamətli LONG namizədi yoxdur" />
        ) : activeTab === "short" ? (
          <TabContent items={results.short} empty="Hazırda istiqamətli SHORT namizədi yoxdur" />
        ) : activeTab === "volatility" ? (
          <TabContent items={results.volatility} empty="Yüksək volatillik namizədi yoxdur" />
        ) : activeTab === "volume" ? (
          <TabContent items={results.volume} empty="Yüksək həcm namizədi yoxdur" />
        ) : (
          <div>{results.whale.length === 0
            ? <EmptyState text="Təsdiqlənmiş böyük transfer məlumatı yoxdur" />
            : results.whale.map((item, index) => (
              <div key={`${item.symbol}-${index}`} className="flex items-center gap-3 border-b border-gray-800 p-2.5">
                <span className="w-24 font-mono text-xs text-white">{item.symbol}</span>
                <span className="flex-1 text-[10px] text-gray-400">{item.reason}</span>
                {item.price && <span className="font-mono text-xs text-gray-400">{displayPrice(item.price)}</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Summary({ label, value, color = "text-white" }: { label: string; value: number; color?: string }) {
  return <div className="bg-[#0d1117] px-3 py-2 text-center">
    <div className={cn("font-mono text-sm font-bold", color)}>{value}</div>
    <div className="text-[9px] uppercase text-gray-600">{label}</div>
  </div>
}

function EmptyState({ text }: { text: string }) {
  return <div className="py-8 text-center text-xs text-gray-600">{text}</div>
}

function TabContent({ items, empty }: { items: UnifiedSignal[]; empty: string }) {
  if (items.length === 0) return <EmptyState text={empty} />
  return <div>{items.map((item) => <ScannerRow key={item.symbol} signal={item} />)}</div>
}

function ScannerRow({ signal }: { signal: UnifiedSignal }) {
  const isLong = signal.direction === "long"
  const ready = isTradeReady(signal)
  const watch = isWatchlist(signal)
  const reasons = Object.values(signal.reasons_breakdown).slice(0, 2)

  return (
    <div className="flex items-center gap-3 border-b border-gray-800 p-2.5 transition-colors hover:bg-gray-800/30">
      <div className={cn("h-8 w-1 rounded-full", isLong ? "bg-green-500" : "bg-red-500")} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-mono text-xs font-medium text-white">{signal.symbol}</span>
          <span className={cn("rounded px-1 py-0.5 text-[9px] font-bold", isLong ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400")}>
            {isLong ? "LONG" : "SHORT"}
          </span>
          <span className="font-mono text-[10px] text-gray-400">{signal.confidence}%</span>
          <span className={cn("rounded px-1 py-0.5 text-[8px] font-semibold", ready ? "bg-green-950 text-green-400" : watch ? "bg-yellow-950 text-yellow-400" : "bg-gray-800 text-gray-500")}>
            {ready ? "TİCARƏTƏ HAZIR" : watch ? "İZLƏ" : "ZƏİF"}
          </span>
        </div>
        {reasons.length > 0 && <div className="mt-0.5 truncate text-[10px] text-gray-500">{reasons.join(" · ")}</div>}
      </div>
      <div className="text-right text-[10px] text-gray-500">
        <div>{displayPrice(signal.current_price)}</div>
        <div className="text-[9px]">Bal: {signal.opportunity_score}</div>
      </div>
    </div>
  )
}
