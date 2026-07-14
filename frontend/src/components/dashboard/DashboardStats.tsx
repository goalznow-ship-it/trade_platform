"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice, formatPercent } from "@/lib/utils"
import {
  DollarSign, TrendingUp, TrendingDown, BarChart3,
  Target, Activity, Wallet,
} from "lucide-react"

interface StatCardProps {
  label: string
  value: string
  change?: string
  changePositive?: boolean
  icon: React.ElementType
  loading?: boolean
}

function StatCard({ label, value, change, changePositive, icon: Icon, loading }: StatCardProps) {
  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-2">
          <div className="h-3 w-20 bg-gray-800 rounded" />
          <div className="h-6 w-24 bg-gray-800 rounded" />
        </div>
      </div>
    )
  }
  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50 hover:bg-gray-900 hover:border-gray-700 transition-all">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-500">{label}</span>
        <Icon className="w-4 h-4 text-gray-600" />
      </div>
      <div className="text-xl font-bold text-white font-mono">{value}</div>
      {change !== undefined && (
        <div className={cn("text-xs font-mono mt-1", changePositive ? "text-green-400" : "text-red-400")}>
          {change}
        </div>
      )}
    </div>
  )
}

export function DashboardStats() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [portfolio, analytics, positions] = await Promise.all([
          api.getPortfolio().catch(() => null),
          api.getPortfolioAnalytics().catch(() => null),
          api.getPositions().catch(() => []),
        ])
        setData({ portfolio, analytics, positions: Array.isArray(positions) ? positions : [] })
      } catch {} finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const stats = [
    {
      label: "Portfolio Value",
      value: data?.portfolio?.total_value ? formatPrice(data.portfolio.total_value) : "$0.00",
      change: data?.portfolio?.daily_change_pct ? formatPercent(data.portfolio.daily_change_pct) : undefined,
      changePositive: (data?.portfolio?.daily_change_pct || 0) >= 0,
      icon: Wallet,
    },
    {
      label: "Daily PnL",
      value: data?.portfolio?.daily_pnl ? formatPrice(data.portfolio.daily_pnl) : "$0.00",
      changePositive: (data?.portfolio?.daily_pnl || 0) >= 0,
      icon: DollarSign,
    },
    {
      label: "Win Rate",
      value: data?.analytics?.win_rate ? `${data.analytics.win_rate.toFixed(1)}%` : "0%",
      changePositive: (data?.analytics?.win_rate || 0) >= 50,
      icon: Target,
    },
    {
      label: "Total Trades",
      value: String(data?.analytics?.total_trades ?? 0),
      icon: BarChart3,
    },
    {
      label: "Active Positions",
      value: String(data?.positions?.length ?? 0),
      icon: Activity,
    },
    {
      label: "Profit Factor",
      value: data?.analytics?.profit_factor ? data.analytics.profit_factor.toFixed(2) : "0.00",
      changePositive: (data?.analytics?.profit_factor || 0) >= 1.5,
      icon: TrendingUp,
    },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {stats.map((s) => (
        <StatCard key={s.label} {...s} loading={loading} />
      ))}
    </div>
  )
}
