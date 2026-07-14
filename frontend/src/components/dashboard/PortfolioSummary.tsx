"use client"

import { useEffect, useState, useCallback, memo } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice, formatPercent, getChangeColor, formatDuration } from "@/lib/utils"
import { PieChart, AlertCircle, LineChart } from "lucide-react"

interface Trade {
  pnl: number
  symbol?: string
}

interface Analytics {
  error?: string
  best_trade?: Trade
  worst_trade?: Trade
  avg_win?: number
  avg_loss?: number
  win_rate?: number
  total_trades?: number
  profit_factor?: number
  avg_risk_reward?: number
  avg_holding_time?: number
  total_pnl?: number
  monthly_breakdown?: Array<{ month?: string; trades?: number }>
}

const MetricBox = memo(function MetricBox({ label, value, color, sub }: {
  label: string; value: string; color?: string; sub?: string
}) {
  return (
    <div className="p-2.5 rounded-lg bg-gray-800/20">
      <span className="text-[10px] text-gray-500 block mb-0.5">{label}</span>
      <div className={cn("text-sm font-bold font-mono", color || "text-white")}>{value}</div>
      {sub && <span className="text-[9px] text-gray-600">{sub}</span>}
    </div>
  )
})

export function PortfolioSummary() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await api.getPortfolioAnalytics()
      setAnalytics(data)
      setError(null)
    } catch {
      setError("Failed to load analytics")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(load, 0)
    return () => clearTimeout(timer)
  }, [load])

  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-2">
          <div className="h-3 w-24 bg-gray-800 rounded" />
          <div className="grid grid-cols-2 gap-2">
            <div className="h-14 bg-gray-800 rounded" />
            <div className="h-14 bg-gray-800 rounded" />
            <div className="h-14 bg-gray-800 rounded" />
            <div className="h-14 bg-gray-800 rounded" />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="flex items-center gap-2 text-red-400 text-xs">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          {error}
        </div>
      </div>
    )
  }

  if (analytics?.error) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="flex flex-col items-center justify-center py-6 text-gray-600">
          <PieChart className="w-8 h-8 text-gray-700 mb-2" />
          <span className="text-xs">No trade history yet</span>
          <span className="text-[10px] text-gray-700 mt-1">Complete your first trade to see analytics</span>
        </div>
      </div>
    )
  }

  const { best_trade, worst_trade, avg_win, avg_loss, win_rate, total_trades, profit_factor, avg_risk_reward, avg_holding_time, total_pnl, monthly_breakdown } = analytics || {}

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <LineChart className="w-3.5 h-3.5 text-blue-400" />
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Portfolio Analytics</h3>
        </div>
        {total_pnl != null && (
          <div className={cn("text-xs font-bold font-mono", getChangeColor(total_pnl))}>
            {formatPercent(total_pnl)}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 mb-2">
        {best_trade ? (
          <MetricBox label="Best Trade" value={formatPrice(best_trade.pnl)} color="text-green-400" sub={best_trade.symbol} />
        ) : null}
        {worst_trade ? (
          <MetricBox label="Worst Trade" value={formatPrice(worst_trade.pnl)} color="text-red-400" sub={worst_trade.symbol} />
        ) : null}
        {avg_win != null ? (
          <MetricBox label="Avg Win" value={formatPrice(avg_win)} color="text-green-400" />
        ) : null}
        {avg_loss != null ? (
          <MetricBox label="Avg Loss" value={formatPrice(avg_loss)} color="text-red-400" />
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-2 mb-2">
        <MetricBox label="Win Rate" value={win_rate != null ? `${win_rate.toFixed(1)}%` : "0%"}
          color={win_rate != null && win_rate >= 50 ? "text-green-400" : "text-red-400"} />
        <MetricBox label="Total Trades" value={String(total_trades || 0)} />
      </div>

      <div className="grid grid-cols-2 gap-2 mb-2">
        <MetricBox label="Profit Factor"
          value={profit_factor === Infinity ? "∞" : (profit_factor || 0).toFixed(2)}
          color={profit_factor != null && profit_factor >= 1.5 ? "text-green-400" : profit_factor != null && profit_factor >= 1 ? "text-yellow-400" : "text-red-400"} />
        <MetricBox label="Avg R:R" value={(avg_risk_reward || 0).toFixed(2)}
          color={avg_risk_reward != null && avg_risk_reward >= 2 ? "text-green-400" : "text-white"} />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <MetricBox label="Avg Hold Time" value={avg_holding_time ? formatDuration(Math.round(avg_holding_time)) : "--"} />
        {monthly_breakdown && monthly_breakdown.length > 0 && (
          <MetricBox label="Monthly Trades" value={String(monthly_breakdown.length)} sub={`Last: ${monthly_breakdown[monthly_breakdown.length - 1]?.month || ""} ${monthly_breakdown[monthly_breakdown.length - 1]?.trades || 0}`} />
        )}
      </div>
    </div>
  )
}
