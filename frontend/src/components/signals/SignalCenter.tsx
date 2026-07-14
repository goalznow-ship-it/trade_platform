"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { SignalCard } from "@/components/signals/SignalCard"
import { Button } from "@/components/ui/Button"
import { cn } from "@/lib/utils"
import {
  Zap, Filter, ArrowUpDown, Search, RefreshCw,
} from "lucide-react"

type SortKey = "confidence" | "risk_reward" | "opportunity"
type FilterDir = "all" | "long" | "short"

export function SignalCenter() {
  const [signals, setSignals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<SortKey>("confidence")
  const [filterDir, setFilterDir] = useState<FilterDir>("all")
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const data = await api.scanAll("1h", highConfidenceOnly ? 80 : 0)
      setSignals(Array.isArray(data) ? data : [])
    } catch {
      setSignals(getMockSignals())
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

  filtered.sort((a, b) => {
    const aConf = a.confidence || a.score || 0
    const bConf = b.confidence || b.score || 0
    if (sortBy === "confidence") return bConf - aConf
    if (sortBy === "risk_reward") {
      const aRR = a.risk_reward || a.risk_reward_ratio || 0
      const bRR = b.risk_reward || b.risk_reward_ratio || 0
      return bRR - aRR
    }
    return bConf - aConf
  })

  return (
    <div className="h-full overflow-y-auto bg-[#0d1117]">
      <div className="max-w-6xl mx-auto p-4 lg:p-6 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white">Signal Center</h1>
            <p className="text-xs text-gray-500 mt-0.5">AI-generated trading signals across all markets</p>
          </div>
          <Button size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={cn("w-3.5 h-3.5 mr-1", loading && "animate-spin")} />
            Refresh
          </Button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <Filter className="w-4 h-4 text-gray-500" />
          <div className="flex gap-1">
            {(["all", "long", "short"] as FilterDir[]).map((d) => (
              <button
                key={d}
                onClick={() => setFilterDir(d)}
                className={cn(
                  "px-3 py-1.5 text-xs rounded-lg font-medium transition-colors",
                  filterDir === d
                    ? d === "all" ? "bg-blue-600 text-white" :
                      d === "long" ? "bg-green-600 text-white" : "bg-red-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                )}
              >
                {d === "all" ? "All" : d === "long" ? "Long" : "Short"}
              </button>
            ))}
          </div>
          <div className="w-px h-6 bg-gray-700 mx-1" />
          <div className="flex gap-1">
            {(["confidence", "risk_reward", "opportunity"] as SortKey[]).map((s) => (
              <button
                key={s}
                onClick={() => setSortBy(s)}
                className={cn(
                  "flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg transition-colors",
                  sortBy === s ? "bg-blue-600/20 text-blue-400" : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"
                )}
              >
                <ArrowUpDown className="w-3 h-3" />
                {s === "confidence" ? "Confidence" : s === "risk_reward" ? "Risk/Reward" : "Opportunity"}
              </button>
            ))}
          </div>
          <div className="w-px h-6 bg-gray-700 mx-1" />
          <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={highConfidenceOnly}
              onChange={(e) => setHighConfidenceOnly(e.target.checked)}
              className="rounded border-gray-600"
            />
            High confidence only
          </label>
        </div>

        {/* Signals Grid */}
        {loading ? (
          <div className="grid gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
                <div className="animate-pulse space-y-3">
                  <div className="flex justify-between">
                    <div className="h-4 w-24 bg-gray-800 rounded" />
                    <div className="h-4 w-12 bg-gray-800 rounded" />
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {[1, 2, 3].map((j) => (
                      <div key={j} className="h-10 bg-gray-800 rounded" />
                    ))}
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
          <div className="grid gap-3">
            {filtered.map((s, i) => (
              <SignalCard key={i} signal={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function getMockSignals() {
  const symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT", "DOGE/USDT"]
  return symbols.map((s) => {
    const dirs = ["long", "short", "neutral"]
    const dir = dirs[Math.floor(Math.random() * 3)]
    const price = Math.random() * 50000 + 10
    return {
      symbol: s,
      direction: dir,
      confidence: Math.floor(Math.random() * 40) + 50,
      entry_price: price,
      stop_loss: dir === "long" ? price * 0.97 : price * 1.03,
      take_profit: dir === "long" ? price * 1.04 : price * 0.96,
      risk_reward: (Math.random() * 3 + 1).toFixed(1),
      reason: dir === "long" ? "Bullish momentum + volume spike" : dir === "short" ? "Bearish divergence" : "Market consolidating",
      timeframe: "1h",
      signal_type: dir === "long" ? "Breakout" : dir === "short" ? "Breakdown" : "Neutral",
    }
  })
}
