"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  TrendingUp, TrendingDown, Activity, Zap,
  Flame, Clock,
} from "lucide-react"
import {
  type UnifiedSignal, normalizeSignal, displayPrice, displayPercent,
  displayDate, isStale, isTradeReady,
} from "@/lib/unified-signal"

export function FuturesDashboard() {
  const [data, setData] = useState<UnifiedSignal[]>([])
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<string>("")

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [scanResponse, marketIntel] = await Promise.all([
          api.institutionalScan(0, 30) as Promise<{ signals?: Record<string, unknown>[] }>,
          api.getMarketIntelligence(),
        ])
        const rawSignals = Array.isArray(scanResponse?.signals) ? scanResponse.signals : []
        const normalized = rawSignals.map(normalizeSignal)
        const funding = Array.isArray(marketIntel?.futures?.items)
          ? marketIntel.futures.items
          : []
        const futuresBySymbol = new Map<string, any>(
          funding.map((item: any) => [item.symbol.replace("/", ""), item]),
        )
        setData(normalized.map((s) => ({
          ...s,
          // enrich with funding from dedicated endpoint
          futures: {
            funding_rate: futuresBySymbol.get(s.symbol.replace("/", ""))?.funding_rate ?? null,
            funding_rate_8h: futuresBySymbol.get(s.symbol.replace("/", ""))?.funding_rate ?? null,
            funding_pressure: s.futures?.funding_pressure || "neutral",
            open_interest: futuresBySymbol.get(s.symbol.replace("/", ""))?.open_interest ?? null,
            open_interest_usd: futuresBySymbol.get(s.symbol.replace("/", ""))?.open_interest_usd ?? null,
            oi_change: futuresBySymbol.get(s.symbol.replace("/", ""))?.oi_change ?? null,
            volume: futuresBySymbol.get(s.symbol.replace("/", ""))?.volume ?? null,
          },
        })))
        setLastUpdated(new Date().toISOString())
      } catch {
        setData([])
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

  const tradeReady = data.filter(isTradeReady)
  const longSignals = tradeReady.filter((d) => d.direction === "long")
  const shortSignals = tradeReady.filter((d) => d.direction === "short")
  const watchlist = data.filter((d) => d.direction !== "neutral" && d.confidence >= 50 && d.confidence < 70)
  const waiting = data.filter((d) => d.direction === "neutral" || d.confidence < 50)
  const highConf = tradeReady.filter((d) => d.confidence >= 80)
  const stale = isStale(lastUpdated, 120)

  const fundingExtremes = data.filter((item) =>
    item.futures?.funding_rate != null && Math.abs(item.futures.funding_rate) >= 0.0005
  )
  const sortedByFunding = [...fundingExtremes].sort(
    (a, b) => Math.abs(b.futures?.funding_rate || 0) - Math.abs(a.futures?.funding_rate || 0),
  )
  const sortedByConfidence = [...tradeReady].sort(
    (a, b) => (b.confidence || 0) - (a.confidence || 0),
  )

  return (
    <div className="h-full overflow-y-auto bg-[#0d1117]">
      <div className="max-w-7xl mx-auto p-4 lg:p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white">Futures Intelligence</h1>
            <p className="text-xs text-gray-500 mt-0.5">Real-time futures market analysis across all assets</p>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-gray-500">
            <Activity className="w-3 h-3" /> Auto-refresh 60s
            {lastUpdated && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {displayDate(lastUpdated)}
              </span>
            )}
            {stale && <span className="text-amber-400">Stale</span>}
          </div>
        </div>

        {/* Overview Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl border border-green-900/30 bg-green-900/10">
            <div className="flex items-center gap-1 text-xs text-green-400 mb-1">
              <TrendingUp className="w-3.5 h-3.5" /> Bullish Signals
            </div>
            <div className="text-2xl font-bold text-white">{longSignals.length}</div>
            <div className="text-[10px] text-gray-500 mt-0.5">{longSignals.length > 0 ? `${longSignals.length} trade-ready` : "No setups"}</div>
          </div>
          <div className="p-4 rounded-xl border border-red-900/30 bg-red-900/10">
            <div className="flex items-center gap-1 text-xs text-red-400 mb-1">
              <TrendingDown className="w-3.5 h-3.5" /> Bearish Signals
            </div>
            <div className="text-2xl font-bold text-white">{shortSignals.length}</div>
            <div className="text-[10px] text-gray-500 mt-0.5">{shortSignals.length > 0 ? `${shortSignals.length} trade-ready` : "No setups"}</div>
          </div>
          <div className="p-4 rounded-xl border border-yellow-900/30 bg-yellow-900/10">
            <div className="flex items-center gap-1 text-xs text-yellow-400 mb-1">
              <Flame className="w-3.5 h-3.5" /> Funding Extremes
            </div>
            <div className="text-2xl font-bold text-white">{fundingExtremes.length}</div>
            <div className="text-[10px] text-gray-500 mt-0.5">Top 8 below</div>
          </div>
          <div className="p-4 rounded-xl border border-blue-900/30 bg-blue-900/10">
            <div className="flex items-center gap-1 text-xs text-blue-400 mb-1">
              <Zap className="w-3.5 h-3.5" /> High Confidence
            </div>
            <div className="text-2xl font-bold text-white">{highConf.length}</div>
            <div className="text-[10px] text-gray-500 mt-0.5">80%+ · Watchlist {watchlist.length} · WAIT {waiting.length}</div>
          </div>
        </div>

        {/* Funding Extremes */}
        <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Funding Rate Extremes
          </h2>
          <div className="space-y-1.5">
            {sortedByFunding.length === 0 && <div className="text-xs text-gray-600 py-6 text-center">Real ekstremal funding aşkarlanmayıb</div>}
            {sortedByFunding.slice(0, 8).map((item, i) => {
              const fr = item.futures?.funding_rate
              const isExtreme = typeof fr === "number" && Math.abs(fr) >= 0.0005
              return (
                <div key={i}
                  className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-800/20 hover:bg-gray-800/40 transition-colors">
                  <span className="text-sm font-mono text-white w-24">{item.symbol}</span>
                  <span className={cn("text-xs font-bold px-2 py-0.5 rounded",
                    item.direction === "long" ? "bg-green-900/50 text-green-400" :
                    item.direction === "short" ? "bg-red-900/50 text-red-400" :
                    "bg-yellow-900/50 text-yellow-400")}>
                    {item.direction.toUpperCase()}
                  </span>
                  <div className="flex-1" />
                  <span className="text-[10px] text-gray-500">{item.exchange}</span>
                  <span className={cn("text-xs font-mono font-medium",
                    typeof fr === "number" && fr > 0 ? "text-red-400" : typeof fr === "number" && fr < 0 ? "text-green-400" : "text-gray-500")}>
                    {typeof fr === "number" ? `${fr > 0 ? "+" : ""}${(fr * 100).toFixed(4)}%` : "N/A"}
                  </span>
                  {isExtreme && <Flame className="w-3.5 h-3.5 text-orange-400" />}
                  <span className={cn("text-xs font-mono",
                    item.confidence > 75 ? "text-green-400" : "text-gray-500")}>
                    {item.confidence}%
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Top Setups */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl border border-green-900/30 bg-gray-900/50">
            <h2 className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-3">
              Top Bullish Setups
            </h2>
            {sortedByConfidence.filter((d) => d.direction === "long").length === 0 ? (
              <div className="text-center py-4 text-gray-600 text-xs">Hazirda yüksek keyfiyyetli LONG siqnali yoxdur</div>
            ) : (
              <div className="space-y-1.5">
                {sortedByConfidence.filter((d) => d.direction === "long").slice(0, 5).map((item, i) => (
                  <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-800/20">
                    <span className="text-sm font-mono text-white w-24">{item.symbol}</span>
                    <div className="flex-1">
                      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <div className="h-full bg-green-500 rounded-full" style={{ width: `${item.confidence}%` }} />
                      </div>
                    </div>
                    <span className="text-xs font-mono text-green-400 font-bold">{item.confidence}%</span>
                    <span className="text-[10px] text-gray-500">
                      R:R {item.risk_reward_1.toFixed(1)}
                    </span>
                    <span className="text-[10px] text-gray-500">
                      FR: {typeof item.futures?.funding_rate === "number" ? `${(item.futures.funding_rate * 100).toFixed(4)}%` : "N/A"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="p-4 rounded-xl border border-red-900/30 bg-gray-900/50">
            <h2 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-3">
              Top Bearish Setups
            </h2>
            {sortedByConfidence.filter((d) => d.direction === "short").length === 0 ? (
              <div className="text-center py-4 text-gray-600 text-xs">Hazirda yüksek keyfiyyetli SHORT siqnali yoxdur</div>
            ) : (
              <div className="space-y-1.5">
                {sortedByConfidence.filter((d) => d.direction === "short").slice(0, 5).map((item, i) => (
                  <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-800/20">
                    <span className="text-sm font-mono text-white w-24">{item.symbol}</span>
                    <div className="flex-1">
                      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <div className="h-full bg-red-500 rounded-full" style={{ width: `${item.confidence}%` }} />
                      </div>
                    </div>
                    <span className="text-xs font-mono text-red-400 font-bold">{item.confidence}%</span>
                    <span className="text-[10px] text-gray-500">
                      R:R {item.risk_reward_1.toFixed(1)}
                    </span>
                    <span className="text-[10px] text-gray-500">
                      FR: {typeof item.futures?.funding_rate === "number" ? `${(item.futures.funding_rate * 100).toFixed(4)}%` : "N/A"}
                    </span>
                  </div>
                ))}
              </div>
            )}
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
                  <th className="text-right py-2 pr-4">Exchange</th>
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
                        {item.direction.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono">{item.confidence}%</td>
                    <td className={cn("py-2.5 pr-4 text-right font-mono",
                      (item.futures?.funding_rate || 0) > 0.005 ? "text-red-400" :
                      (item.futures?.funding_rate || 0) < -0.005 ? "text-green-400" : "text-gray-500")}>
                      {typeof item.futures?.funding_rate === "number"
                        ? `${item.futures.funding_rate > 0 ? "+" : ""}${(item.futures.funding_rate * 100).toFixed(4)}%`
                        : "N/A"}
                    </td>
                    <td className="py-2.5 pr-4 text-right text-[10px] text-gray-500">
                      {item.exchange}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono text-green-400">
                      {item.institutional_score.long_probability.toFixed(0)}%
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono text-red-400">
                      {item.institutional_score.short_probability.toFixed(0)}%
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
