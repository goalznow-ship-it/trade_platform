"use client"

import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api"
import { SignalCard } from "@/components/signals/SignalCard"
import { Button } from "@/components/ui/Button"
import { cn } from "@/lib/utils"
import {
  Filter, ArrowUpDown, Search, RefreshCw, Clock, TrendingUp, TrendingDown,
} from "lucide-react"
import {
  type UnifiedSignal, normalizeSignal, isTradeReady, isWatchlist, displayDate, isStale,
} from "@/lib/unified-signal"

type SortKey = "confidence" | "risk_reward" | "opportunity"
type FilterDir = "all" | "long" | "short"
type FilterType = "all" | "futures" | "top"

export function SignalCenter() {
  const [signals, setSignals] = useState<UnifiedSignal[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<SortKey>("confidence")
  const [filterDir, setFilterDir] = useState<FilterDir>("all")
  const [filterType, setFilterType] = useState<FilterType>("all")
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string>("")

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const minScore = highConfidenceOnly ? 70 : 0
      const data = await api.institutionalScan(minScore, 50) as { signals?: Record<string, unknown>[] }
      const rawSignals = Array.isArray(data?.signals) ? data.signals : []
      const normalized = rawSignals.map(normalizeSignal)
      setSignals(normalized)
      setLastUpdated(new Date().toISOString())
    } catch {
      setSignals([])
    } finally {
      setLoading(false)
    }
  }, [highConfidenceOnly])

  useEffect(() => { load() }, [load])

  let filtered = [...signals]
  if (filterDir === "long") {
    filtered = filtered.filter((s) => s.direction === "long")
  }
  if (filterDir === "short") {
    filtered = filtered.filter((s) => s.direction === "short")
  }
  if (filterType === "futures") {
    filtered = filtered.filter((s) => s.futures !== null)
  }
  if (filterType === "top") {
    filtered = filtered.filter((s) => s.confidence >= 75 && s.risk_reward_1 >= 2)
  }
  if (highConfidenceOnly) {
    filtered = filtered.filter((s) => s.confidence >= 70)
  }

  filtered.sort((a, b) => {
    if (sortBy === "confidence") return b.confidence - a.confidence
    if (sortBy === "risk_reward") return b.risk_reward_1 - a.risk_reward_1
    if (sortBy === "opportunity") return b.opportunity_score - a.opportunity_score
    return b.confidence - a.confidence
  })

  const tradeReadySignals = filtered.filter(isTradeReady)
  const watchlistSignals = filtered.filter(isWatchlist)
  const stale = isStale(lastUpdated, 120)

  return (
    <div className="h-full overflow-y-auto bg-[#0d1117]">
      <div className="max-w-6xl mx-auto p-4 lg:p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white">AI Signals</h1>
            <p className="text-xs text-gray-500 mt-0.5">Professional-grade AI trading signals with multi-factor analysis</p>
          </div>
          <div className="flex items-center gap-2">
            {lastUpdated && (
              <div className="flex items-center gap-1 text-[10px] text-gray-500">
                <Clock className="w-3 h-3" />
                <span>{displayDate(lastUpdated)}</span>
                {stale && <span className="text-amber-400">Stale</span>}
              </div>
            )}
            <Button size="sm" onClick={load} disabled={loading}>
              <RefreshCw className={cn("w-3.5 h-3.5 mr-1", loading && "animate-spin")} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 p-3 rounded-lg border border-gray-800 bg-gray-900/50">
          <Filter className="w-4 h-4 text-gray-500 flex-shrink-0" />
          <div className="flex gap-1">
            {(["all", "long", "short"] as FilterDir[]).map((d) => (
              <button key={d} onClick={() => setFilterDir(d)}
                className={cn(
                  "px-2.5 py-1.5 text-xs rounded-md font-medium transition-colors",
                  filterDir === d
                    ? d === "all" ? "bg-blue-600 text-white" :
                      d === "long" ? "bg-green-600 text-white" : "bg-red-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                )}>
                {d === "all" ? "All" : d === "long" ? "Long" : "Short"}
              </button>
            ))}
          </div>
          <div className="w-px h-5 bg-gray-700" />
          <div className="flex gap-1">
            {(["all", "futures", "top"] as FilterType[]).map((t) => (
              <button key={t} onClick={() => setFilterType(t)}
                className={cn(
                  "px-2.5 py-1.5 text-xs rounded-md transition-colors",
                  filterType === t ? "bg-purple-600/20 text-purple-400" : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"
                )}>
                {t === "all" ? "All Types" : t === "futures" ? "Futures Only" : "Top Opportunities"}
              </button>
            ))}
          </div>
          <div className="w-px h-5 bg-gray-700" />
          <div className="flex gap-1">
            {(["confidence", "risk_reward", "opportunity"] as SortKey[]).map((s) => (
              <button key={s} onClick={() => setSortBy(s)}
                className={cn(
                  "flex items-center gap-1 px-2 py-1.5 text-xs rounded-md transition-colors",
                  sortBy === s ? "bg-blue-600/20 text-blue-400" : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"
                )}>
                <ArrowUpDown className="w-3 h-3" />
                {s === "confidence" ? "Confidence" : s === "risk_reward" ? "Risk/Reward" : "Opportunity Score"}
              </button>
            ))}
          </div>
          <div className="w-px h-5 bg-gray-700" />
          <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer whitespace-nowrap">
            <input type="checkbox" checked={highConfidenceOnly} onChange={(e) => setHighConfidenceOnly(e.target.checked)}
              className="rounded border-gray-600" />
            High confidence only (70%+)
          </label>
        </div>

        {/* Summary */}
        {!loading && signals.length > 0 && (
          <div className="grid grid-cols-3 gap-2">
            <div className="p-2.5 rounded-lg bg-green-900/10 border border-green-900/30 text-center">
              <div className="text-lg font-bold text-green-400">{tradeReadySignals.length}</div>
              <div className="text-[10px] text-gray-500">Trade Ready</div>
            </div>
            <div className="p-2.5 rounded-lg bg-yellow-900/10 border border-yellow-900/30 text-center">
              <div className="text-lg font-bold text-yellow-400">{watchlistSignals.length}</div>
              <div className="text-[10px] text-gray-500">Watchlist</div>
            </div>
            <div className="p-2.5 rounded-lg bg-gray-800/30 border border-gray-700/30 text-center">
              <div className="text-lg font-bold text-white">{filtered.length}</div>
              <div className="text-[10px] text-gray-500">Total Active</div>
            </div>
          </div>
        )}

        {/* Results */}
        {loading ? (
          <div className="grid gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="p-4 rounded-lg border border-gray-800 bg-gray-900/30">
                <div className="animate-pulse space-y-3">
                  <div className="flex justify-between">
                    <div className="h-4 w-32 bg-gray-800 rounded" />
                    <div className="h-4 w-12 bg-gray-800 rounded" />
                  </div>
                  <div className="grid grid-cols-5 gap-1.5">
                    {[1, 2, 3, 4, 5].map((j) => (<div key={j} className="h-10 bg-gray-800 rounded" />))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-gray-600">
            <Search className="w-8 h-8 mx-auto mb-2" />
            <div className="text-sm">No signals match current filters</div>
            <div className="text-xs text-gray-600 mt-1">Try adjusting filters or lowering confidence threshold</div>
          </div>
        ) : (
          <div className="grid gap-2.5">
            {/* Trade Ready section */}
            {tradeReadySignals.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <TrendingUp className="w-3.5 h-3.5 text-green-400" />
                  <span className="text-xs font-semibold text-green-400 uppercase tracking-wider">Trade Ready (70%+)</span>
                </div>
                {tradeReadySignals.map((s, i) => (
                  <SignalCard key={`tr-${s.symbol}-${i}`} signal={s} />
                ))}
              </div>
            )}

            {/* Watchlist section */}
            {watchlistSignals.length > 0 && (
              <div className="mt-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <TrendingDown className="w-3.5 h-3.5 text-yellow-400" />
                  <span className="text-xs font-semibold text-yellow-400 uppercase tracking-wider">Watchlist (50-69%)</span>
                </div>
                {watchlistSignals.map((s, i) => (
                  <SignalCard key={`wl-${s.symbol}-${i}`} signal={s} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
