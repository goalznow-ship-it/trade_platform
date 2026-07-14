"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice } from "@/lib/utils"
import { TrendingUp, TrendingDown, X } from "lucide-react"
import { Button } from "@/components/ui/Button"

export function ActivePositions() {
  const [positions, setPositions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getPositions().then((data) => {
      setPositions(Array.isArray(data) ? data : [])
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-3">
          <div className="h-3 w-24 bg-gray-800 rounded" />
          {[1, 2].map((i) => (
            <div key={i} className="h-12 bg-gray-800 rounded" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Active Positions {positions.length > 0 && `(${positions.length})`}
      </h3>
      {positions.length === 0 ? (
        <div className="text-center py-6 text-gray-600 text-xs">No open positions</div>
      ) : (
        <div className="space-y-1.5">
          {positions.map((p, i) => (
            <div key={i}
              className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-800/20 hover:bg-gray-800/40 transition-colors">
              <div className={cn("w-1 h-8 rounded-full", p.side === "long" ? "bg-green-500" : "bg-red-500")} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-medium text-white font-mono">{p.symbol}</span>
                  <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded",
                    p.side === "long"
                      ? "bg-green-900/50 text-green-400"
                      : "bg-red-900/50 text-red-400")}>
                    {p.side?.toUpperCase()}
                  </span>
                  <span className="text-[10px] text-gray-600">{p.leverage || 1}x</span>
                </div>
                <div className="text-[11px] text-gray-500">
                  Size: {p.quantity || p.size} · Entry: {formatPrice(p.entry_price)}
                </div>
              </div>
              <div className="text-right">
                <div className={cn("text-sm font-bold font-mono",
                  (p.pnl || p.unrealized_pnl || 0) >= 0 ? "text-green-400" : "text-red-400")}>
                  {(p.pnl || p.unrealized_pnl || 0) >= 0 ? "+" : ""}
                  {((p.pnl || p.unrealized_pnl || 0)).toFixed(2)}
                </div>
                <div className="text-[10px] text-gray-600">PnL</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
