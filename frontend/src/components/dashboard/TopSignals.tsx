"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice } from "@/lib/utils"
import { Zap, TrendingUp, TrendingDown } from "lucide-react"

export function TopSignals() {
  const [signals, setSignals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.scanAll("1h", 70).then((data) => {
      setSignals(Array.isArray(data) ? data.slice(0, 5) : [])
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-3">
          <div className="h-3 w-24 bg-gray-800 rounded" />
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-gray-800 rounded" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Top Signals</h3>
        <Zap className="w-3.5 h-3.5 text-yellow-500" />
      </div>
      {signals.length === 0 ? (
        <div className="text-center py-6 text-gray-600 text-xs">No active signals</div>
      ) : (
        <div className="space-y-1.5">
          {signals.map((s, i) => (
            <div key={i}
              className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-800/20 hover:bg-gray-800/40 transition-colors cursor-pointer">
              <div className={cn("w-1 h-8 rounded-full", s.direction === "long" ? "bg-green-500" : "bg-red-500")} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-medium text-white font-mono">{s.symbol}</span>
                  <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded",
                    s.direction === "long"
                      ? "bg-green-900/50 text-green-400"
                      : "bg-red-900/50 text-red-400")}>
                    {s.direction?.toUpperCase()}
                  </span>
                </div>
                <div className="text-[11px] text-gray-500 mt-0.5">
                  {s.reason || s.signal_type || `${s.direction} signal`}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-bold text-white font-mono">{s.confidence || s.score || 0}%</div>
                <div className="text-[10px] text-gray-600">confidence</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
