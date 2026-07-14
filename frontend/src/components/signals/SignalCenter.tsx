"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { SignalCard } from "@/components/signals/SignalCard"
import { Button } from "@/components/ui/Button"
import { cn } from "@/lib/utils"
import {
  Zap, Filter, ArrowUpDown, Search, RefreshCw, SlidersHorizontal,
} from "lucide-react"

type SortKey = "confidence" | "risk_reward" | "opportunity"
type FilterDir = "all" | "long" | "short"
type FilterType = "all" | "futures" | "top"

export function SignalCenter() {
  const [signals, setSignals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<SortKey>("confidence")
  const [filterDir, setFilterDir] = useState<FilterDir>("all")
  const [filterType, setFilterType] = useState<FilterType>("all")
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const data = await api.scanAllV2(highConfidenceOnly ? 80 : 0)
      setSignals(Array.isArray(data) ? data : [])
    } catch {
      setSignals([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [highConfidenceOnly])

  let filtered = [...signals]
  if (filterDir === "long") {
    filtered = filtered.filter((s) => (s.direction || s.signal) === "long" || (s.direction || s.signal) === "bullish" || (s.direction || s.signal) === "buy")
  }
  if (filterDir === "short") {
    filtered = filtered.filter((s) => (s.direction || s.signal) === "short" || (s.direction || s.signal) === "bearish" || (s.direction || s.signal) === "sell")
  }
  if (filterType === "futures") {
    filtered = filtered.filter((s) => s.futures || s.funding_rate !== undefined)
  }
  if (filterType === "top") {
    filtered = filtered.filter((s) => (s.confidence || 0) >= 75 && (s.risk_reward || 0) >= 2)
  }

  filtered.sort((a, b) => {
    const aConf = a.confidence || a.score || 0
    const bConf = b.confidence || b.score || 0
    if (sortBy === "confidence") return bConf - aConf
    if (sortBy === "risk_reward") {
      const aRR = a.risk_reward || a.risk_reward_ratio || 0
      const bRR = b.risk_reward || b.risk_reward_ratio || 0
      return bRR - aRR
    }
    if (sortBy === "opportunity") {
      const aScore = (a.confidence || 0) * (a.risk_reward || 1)
      const bScore = (b.confidence || 0) * (b.risk_reward || 1)
      return bScore - aScore
    }
    return bConf - aConf
  })

  return (
    <div className="h-full overflow-y-auto bg-[#0d1117]">
      <div className="max-w-6xl mx-auto p-4 lg:p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white">AI Signals</h1>
            <p className="text-xs text-gray-500 mt-0.5">Professional-grade AI trading signals with multi-factor analysis</p>
          </div>
          <Button size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={cn("w-3.5 h-3.5 mr-1", loading && "animate-spin")} />
            Refresh
          </Button>
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
            High confidence only
          </label>
        </div>

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
          </div>
        ) : (
          <div className="grid gap-2.5">
            {filtered.map((s, i) => (
              <SignalCard key={`${s.symbol}-${i}`} signal={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}


