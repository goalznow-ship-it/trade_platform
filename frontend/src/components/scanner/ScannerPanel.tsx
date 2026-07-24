"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { cn } from "@/lib/utils"
import {
  Search, Zap, TrendingUp, TrendingDown, Clock,
} from "lucide-react"
import {
  type UnifiedSignal, normalizeSignal, displayPrice, displayDate, isStale,
  gradeSignal, isTradeReady,
} from "@/lib/unified-signal"

export function ScannerPanel() {
  const [results, setResults] = useState<UnifiedSignal[]>([])
  const [scanning, setScanning] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string>("")

  async function handleScan() {
    setScanning(true)
    try {
      const res = await api.institutionalScan(0, 30) as { signals?: Record<string, unknown>[] }
      const rawSignals = Array.isArray(res?.signals) ? res.signals : []
      const normalized = rawSignals.map(normalizeSignal)
      normalized.sort((a, b) => b.opportunity_score - a.opportunity_score)
      setResults(normalized)
      setLastUpdated(new Date().toISOString())
    } catch {
      setResults([])
    } finally {
      setScanning(false)
    }
  }

  useEffect(() => { handleScan() }, [])

  const tradeReady = results.filter(isTradeReady)
  const longSignals = tradeReady.filter((s) => s.direction === "long")
  const shortSignals = tradeReady.filter((s) => s.direction === "short")
  const stale = isStale(lastUpdated, 120)

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-gray-200">Enterprise Scanner</span>
          </div>
          <Button size="sm" onClick={handleScan} disabled={scanning}>
            <Zap className="w-3 h-3 mr-1" />
            {scanning ? "Scanning..." : "Scan"}
          </Button>
        </div>
        {lastUpdated && (
          <div className="flex items-center gap-1.5 text-[10px] text-gray-500">
            <Clock className="w-3 h-3" />
            <span>Last scan: {displayDate(lastUpdated)}</span>
            {stale && <span className="text-amber-400">Stale data</span>}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-auto">
        {scanning && (
          <div className="p-4 text-center text-gray-500 text-sm">
            <Search className="w-6 h-6 mx-auto mb-2 animate-pulse text-blue-500" />
            Scanning markets...
          </div>
        )}

        {/* Best LONG */}
        <div className="px-3 pt-3 pb-1">
          <div className="flex items-center gap-1.5 mb-2">
            <TrendingUp className="w-3.5 h-3.5 text-green-400" />
            <span className="text-[10px] font-semibold text-green-400 uppercase tracking-wider">Best LONG</span>
          </div>
          {longSignals.length === 0 && !scanning ? (
            <div className="p-3 rounded-lg border border-green-900/20 bg-green-900/5 text-center text-xs text-gray-500">
              Hazirda yüksek keyfiyyetli LONG siqnali yoxdur
            </div>
          ) : (
            longSignals.slice(0, 5).map((s, i) => (
              <SignalRow key={i} signal={s} />
            ))
          )}
        </div>

        {/* Best SHORT */}
        <div className="px-3 pt-2 pb-1">
          <div className="flex items-center gap-1.5 mb-2">
            <TrendingDown className="w-3.5 h-3.5 text-red-400" />
            <span className="text-[10px] font-semibold text-red-400 uppercase tracking-wider">Best SHORT</span>
          </div>
          {shortSignals.length === 0 && !scanning ? (
            <div className="p-3 rounded-lg border border-red-900/20 bg-red-900/5 text-center text-xs text-gray-500">
              Hazirda yüksek keyfiyyetli SHORT siqnali yoxdur
            </div>
          ) : (
            shortSignals.slice(0, 5).map((s, i) => (
              <SignalRow key={i} signal={s} />
            ))
          )}
        </div>

        {/* All Signals */}
        <div className="px-3 pt-2 pb-3">
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
            All Signals ({results.length})
          </div>
          {results.length === 0 && !scanning && (
            <div className="text-center py-4 text-gray-600 text-xs">Click Scan to find trading opportunities</div>
          )}
          {results.map((s, i) => (
            <SignalRow key={i} signal={s} compact />
          ))}
        </div>
      </div>
    </div>
  )
}

function SignalRow({ signal, compact }: { signal: UnifiedSignal; compact?: boolean }) {
  const grade = gradeSignal(signal.confidence)
  const gradeColor = grade === "trade_ready" ? "text-green-400" : grade === "watchlist" ? "text-yellow-400" : "text-gray-500"
  const isLong = signal.direction === "long"
  const isShort = signal.direction === "short"
  const reasons = Object.values(signal.reasons_breakdown).slice(0, 2)

  return (
    <div className="flex items-center gap-3 px-2.5 py-2 rounded-lg hover:bg-gray-800/40 transition-colors mb-0.5">
      <div className={cn(
        "w-1 h-8 rounded-full flex-shrink-0",
        isLong ? "bg-green-500" : isShort ? "bg-red-500" : "bg-gray-600",
      )} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-gray-200 font-mono">{signal.symbol}</span>
          <Badge variant={isLong ? "success" : isShort ? "danger" : "default"} className="text-[9px]">
            {isLong ? "LONG" : isShort ? "SHORT" : "WAIT"}
          </Badge>
          {!compact && grade === "trade_ready" && (
            <Badge variant="success" className="text-[8px]">Trade Ready</Badge>
          )}
        </div>
        <div className="flex items-center gap-2 text-[10px] text-gray-500 mt-0.5">
          <span>Price: {displayPrice(signal.current_price)}</span>
          <span>Score: {signal.opportunity_score}</span>
          {reasons.map((r, i) => (
            <span key={i} className="truncate max-w-[120px]">{r}</span>
          ))}
        </div>
      </div>
      <div className="text-right flex-shrink-0">
        <div className={cn("text-xs font-bold font-mono", gradeColor)}>
          {signal.confidence}%
        </div>
        <div className={cn("text-[10px]", gradeColor)}>
          {grade === "trade_ready" ? "Ready" : grade === "watchlist" ? "Watch" : "Reject"}
        </div>
      </div>
    </div>
  )
}
