"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice, formatPercent } from "@/lib/utils"
import { PieChart, TrendingUp, TrendingDown, Award } from "lucide-react"

export function PortfolioSummary() {
  const [analytics, setAnalytics] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getPortfolioAnalytics().then(setAnalytics).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-2">
          <div className="h-3 w-24 bg-gray-800 rounded" />
          <div className="h-8 w-full bg-gray-800 rounded" />
          <div className="h-8 w-full bg-gray-800 rounded" />
        </div>
      </div>
    )
  }

  const items = [
    { label: "Best Trade", value: analytics?.best_trade ? formatPrice(analytics.best_trade) : "--", color: "green", icon: TrendingUp },
    { label: "Worst Trade", value: analytics?.worst_trade ? formatPrice(analytics.worst_trade) : "--", color: "red", icon: TrendingDown },
    { label: "Winning Trades", value: String(analytics?.winning_trades ?? 0), color: "green", icon: Award },
    { label: "Losing Trades", value: String(analytics?.losing_trades ?? 0), color: "red", icon: Award },
  ]

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Portfolio Summary</h3>
        <PieChart className="w-3.5 h-3.5 text-blue-400" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        {items.map((item) => (
          <div key={item.label} className="p-2.5 rounded-lg bg-gray-800/20">
            <div className="flex items-center gap-1 mb-1">
              <item.icon className={cn("w-3 h-3", item.color === "green" ? "text-green-400" : "text-red-400")} />
              <span className="text-[10px] text-gray-500">{item.label}</span>
            </div>
            <div className={cn("text-sm font-bold font-mono",
              item.color === "green" ? "text-green-400" : "text-red-400")}>
              {item.value}
            </div>
          </div>
        ))}
      </div>
      {analytics?.avg_holding_time && (
        <div className="mt-2 text-[11px] text-gray-500">
          Avg hold time: {analytics.avg_holding_time}
        </div>
      )}
    </div>
  )
}
