"use client"

import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, BarChart3, Trophy, XCircle } from "lucide-react"

interface Props {
  history: Record<string, unknown> | null
}

function numVal(v: unknown): number {
  return typeof v === "number" ? v : 0
}

function strVal(v: unknown): string {
  if (v == null) return "—"
  return String(v)
}

export function SKHYHistoryPanel({ history }: Props) {
  if (!history) return (
    <div className="border-b border-gray-800/60 p-3">
      <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-2">Tarixçə</div>
      <div className="text-[10px] text-gray-500 italic">Tarixçə məlumatı gözlənilir...</div>
    </div>
  )

  const signals = Array.isArray(history.signals) ? history.signals : []
  const perf = (history.performance || {}) as Record<string, unknown>

  if (!signals.length && perf.status === "no_trades_yet") {
    return (
      <div className="p-3 border-b border-gray-800/60">
        <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-2">Tarixçə</div>
        <div className="text-[10px] text-gray-500 text-center py-4">Hələ heç bir siqnal yoxdur</div>
      </div>
    )
  }

  return (
    <div className="border-b border-gray-800/60 p-3">
      <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-2">Performans</div>

      {perf.win_rate != null && (
        <div className="grid grid-cols-3 gap-1 mb-2">
          <MetricBox label="Qazanma %" value={strVal(perf.win_rate) + "%"} color="text-green-400" />
          <MetricBox label="Mənfəət Faktoru" value={perf.profit_factor === Infinity ? "∞" : strVal(perf.profit_factor)} color="text-blue-400" />
          <MetricBox label="Ümumi" value={strVal(perf.total_signals)} color="text-gray-300" />
          <MetricBox label="ALIŞ Q%" value={perf.long_win_rate != null ? `${String(perf.long_win_rate)}%` : "—"} color="text-green-400" />
          <MetricBox label="SATIŞ Q%" value={perf.short_win_rate != null ? `${String(perf.short_win_rate)}%` : "—"} color="text-red-400" />
          <MetricBox label="Orta R:R" value={perf.average_rr != null ? strVal(perf.average_rr) : "—"} color="text-yellow-400" />
        </div>
      )}

      {signals.length > 0 && (
        <>
          <div className="text-[10px] text-gray-500 mb-1">Son siqnallar</div>
          <div className="space-y-1 max-h-60 overflow-y-auto">
            {signals.slice(0, 10).map((s: Record<string, unknown>, i: number) => {
              const sig = (s.signal || {}) as Record<string, unknown>
              const res = (s.result || {}) as Record<string, unknown>
              const dir = String(sig.direction || sig.signal || "WAIT").toLowerCase()
              const isWin = res.pnl != null && numVal(res.pnl) > 0
              const hasResult = res.exit_price != null

              return (
                <div key={i} className={cn("px-2 py-1.5 rounded text-[10px]",
                  hasResult ? (isWin ? "bg-green-500/5" : "bg-red-500/5") : "bg-gray-800/20")}>
                  <div className="flex items-center justify-between mb-0.5">
                    <div className="flex items-center gap-1">
                      {dir.includes("long") ? <TrendingUp className="w-2.5 h-2.5 text-green-400" /> :
                       dir.includes("short") ? <TrendingDown className="w-2.5 h-2.5 text-red-400" /> :
                       <BarChart3 className="w-2.5 h-2.5 text-gray-500" />}
                      <span className={cn("font-semibold",
                        dir.includes("long") ? "text-green-400" : dir.includes("short") ? "text-red-400" : "text-gray-500")}>
                        {String(sig.signal || sig.direction || "WAIT").toUpperCase()}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      {sig.confidence != null && (
                        <span className="text-gray-500">{String(sig.confidence)}%</span>
                      )}
                      {hasResult && (isWin
                        ? <Trophy className="w-2.5 h-2.5 text-green-400" />
                        : <XCircle className="w-2.5 h-2.5 text-red-400" />
                      )}
                    </div>
                  </div>
                  {hasResult && (
                    <div className="flex flex-wrap gap-x-2 text-[9px] text-gray-500">
                      {sig.entry_price != null && <span>Giriş: ${numVal(sig.entry_price).toFixed(2)}</span>}
                      {sig.tp != null && <span>TP: ${numVal(sig.tp).toFixed(2)}</span>}
                      {sig.sl != null && <span>SL: ${numVal(sig.sl).toFixed(2)}</span>}
                      {res.exit_price != null && <span>Çıxış: ${numVal(res.exit_price).toFixed(2)}</span>}
                      {res.pnl != null && (
                        <span className={isWin ? "text-green-400" : "text-red-400"}>
                          {isWin ? "+" : ""}{numVal(res.pnl).toFixed(2)}$
                        </span>
                      )}
                      {res.rr != null && <span>R:R {numVal(res.rr).toFixed(1)}</span>}
                    </div>
                  )}
                  {!hasResult && sig.entry_price != null && (
                    <div className="text-[9px] text-gray-600">
                      Giriş: ${numVal(sig.entry_price).toFixed(2)}
                      {sig.tp != null && ` | TP: $${numVal(sig.tp).toFixed(2)}`}
                      {sig.sl != null && ` | SL: $${numVal(sig.sl).toFixed(2)}`}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

function MetricBox({ label, value, color }: { label: string; value: unknown; color?: string }) {
  return (
    <div className="px-1.5 py-1 rounded bg-gray-800/20 text-center">
      <div className="text-[9px] text-gray-500">{label}</div>
      <div className={cn("text-[10px] font-mono font-bold", color || "text-gray-300")}>{String(value)}</div>
    </div>
  )
}
