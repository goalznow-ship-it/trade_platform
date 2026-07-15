"use client"

import { useEffect, useState, useMemo, memo, useCallback } from "react"
import { api } from "@/lib/api"
import { useMarketStore } from "@/store/market"
import { cn, formatPrice, getChangeColor, nowISO } from "@/lib/utils"
import {
  DollarSign, TrendingUp, TrendingDown, BarChart3,
  Target, Activity, Wallet, LineChart, Percent,
  ArrowUpRight, ArrowDownRight, Minus, Clock,
} from "lucide-react"

interface Position {
  unrealized_pnl?: number
  size?: number
  mark_price?: number
}

interface Portfolio {
  balance?: number
}

interface BalanceEntry {
  free?: number
  used?: number
}

interface Analytics {
  win_rate?: number
  profit_factor?: number
  avg_risk_reward?: number
  total_trades?: number
}

interface DashboardData {
  portfolio?: Portfolio | null
  analytics?: Analytics | null
  positions: Position[]
  balance?: Record<string, BalanceEntry> | null
}

interface StatCardProps {
  label: string
  value: string
  change?: string
  changeValue?: number
  icon: React.ElementType
  loading?: boolean
  tooltip?: string
  sub?: string
}

const StatCard = memo(function StatCard({
  label, value, change, changeValue, icon: Icon, loading, tooltip, sub,
}: StatCardProps) {
  if (loading) {
    return (
      <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-2">
          <div className="h-3 w-16 bg-gray-800 rounded" />
          <div className="h-6 w-20 bg-gray-800 rounded" />
        </div>
      </div>
    )
  }
  return (
    <div className="group relative p-3 rounded-xl border border-gray-800 bg-gray-900/50 hover:bg-gray-900 hover:border-gray-700 transition-all duration-200 cursor-default"
      title={tooltip}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">{label}</span>
        <Icon className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-400 transition-colors" />
      </div>
      <div className="text-lg font-bold text-white font-mono tracking-tight">{value}</div>
      <div className="flex items-center gap-1.5 mt-1">
        {change !== undefined && changeValue !== undefined && (
          <div className={cn("flex items-center gap-0.5 text-[10px] font-mono font-medium", getChangeColor(changeValue))}>
            {changeValue > 0 ? <ArrowUpRight className="w-3 h-3" />
              : changeValue < 0 ? <ArrowDownRight className="w-3 h-3" />
              : <Minus className="w-3 h-3" />}
            {change}
          </div>
        )}
        {sub && <span className="text-[9px] text-gray-600 ml-auto">{sub}</span>}
      </div>
    </div>
  )
})

function useLiveTimestamp() {
  const [ts, setTs] = useState(nowISO)
  useEffect(() => {
    const interval = setInterval(() => setTs(nowISO), 30000)
    return () => clearInterval(interval)
  }, [])
  return ts
}

export function DashboardStats() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const liveTs = useLiveTimestamp()
  const isLive = useMarketStore((s) => s.isLive)

  const load = useCallback(async () => {
    try {
      const [portfolio, analytics, positions, balance] = await Promise.all([
        api.getPortfolio().catch(() => null),
        api.getPortfolioAnalytics().catch(() => null),
        api.getPositions().catch(() => []),
        api.getBalance().catch(() => null),
      ])
      setData({ portfolio, analytics, positions: Array.isArray(positions) ? positions : [], balance })
    } catch {} finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(load, 0)
    const interval = setInterval(load, isLive ? 60000 : 30000)
    return () => {
      clearTimeout(timer)
      clearInterval(interval)
    }
  }, [load, isLive])

  const positions = useMemo(() => data?.positions || [], [data])
  const unrealizedPnl = useMemo(
    () => positions.reduce((sum: number, p: Position) => sum + (p.unrealized_pnl || 0), 0),
    [positions]
  )
  const totalBalance = data?.portfolio?.balance || 0
  const equity = totalBalance + unrealizedPnl

  const exchangeBalances = data?.balance
  let freeMargin = 0
  let usedMargin = 0
  if (exchangeBalances) {
    for (const ex of Object.values(exchangeBalances) as BalanceEntry[]) {
      freeMargin += ex?.free || 0
      usedMargin += ex?.used || 0
    }
  }
  if (freeMargin === 0 && usedMargin === 0) {
    freeMargin = equity
  }

  const marginRatio = usedMargin > 0 ? (usedMargin / (freeMargin + usedMargin)) * 100 : 0
  const analytics = data?.analytics
  const winRate = analytics?.win_rate || 0
  const profitFactor = analytics?.profit_factor || 0
  const avgRR = analytics?.avg_risk_reward || 0
  const totalTrades = analytics?.total_trades || 0

  const stats = useMemo(() => [
    {
      label: "Equity",
      value: formatPrice(equity),
      change: unrealizedPnl !== 0 ? (unrealizedPnl >= 0 ? "+" : "") + formatPrice(Math.abs(unrealizedPnl)) : undefined,
      changeValue: unrealizedPnl,
      icon: LineChart,
      tooltip: "Total account value including unrealized PnL",
    },
    {
      label: "Balance",
      value: formatPrice(totalBalance),
      icon: Wallet,
      tooltip: "Available account balance",
    },
    {
      label: "Free Margin",
      value: formatPrice(freeMargin),
      icon: DollarSign,
      tooltip: "Available margin for new positions",
    },
    {
      label: "Margin Ratio",
      value: `${marginRatio.toFixed(1)}%`,
      changeValue: marginRatio,
      change: marginRatio > 0 ? `${marginRatio.toFixed(1)}%` : undefined,
      icon: Percent,
      tooltip: "Used margin / total equity ratio",
    },
    {
      label: "Unrealized PnL",
      value: unrealizedPnl >= 0 ? "+" + formatPrice(unrealizedPnl) : formatPrice(unrealizedPnl),
      changeValue: unrealizedPnl,
      icon: unrealizedPnl >= 0 ? TrendingUp : TrendingDown,
      tooltip: "Current floating profit/loss on open positions",
    },
    {
      label: "Win Rate",
      value: `${winRate.toFixed(1)}%`,
      changeValue: winRate - 50,
      change: winRate > 0 ? `${winRate.toFixed(1)}%` : undefined,
      icon: Target,
      tooltip: "Percentage of winning trades",
    },
    {
      label: "Profit Factor",
      value: profitFactor === Infinity ? "∞" : profitFactor.toFixed(2),
      changeValue: profitFactor - 1,
      change: profitFactor > 0 ? profitFactor.toFixed(2) : undefined,
      icon: BarChart3,
      tooltip: "Gross profit / gross loss ratio (higher is better)",
    },
    {
      label: "Avg R:R",
      value: avgRR.toFixed(2),
      icon: Activity,
      tooltip: "Average risk-to-reward ratio across all trades",
    },
    {
      label: "Total Trades",
      value: String(totalTrades),
      icon: BarChart3,
      tooltip: "Total number of closed trades",
    },
    {
      label: "Active Pos.",
      value: String(positions.length),
      icon: Activity,
      tooltip: "Currently open positions",
    },
  ], [equity, totalBalance, freeMargin, marginRatio, unrealizedPnl, winRate, profitFactor, avgRR, totalTrades, positions.length])

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] text-gray-600 flex items-center gap-1">
          <Clock className="w-3 h-3" />
          Updated {new Date(liveTs).toLocaleTimeString()}
        </span>
        {!loading && positions.length > 0 && (
          <span className="text-[10px] text-gray-600">
            Exposure: {formatPrice(positions.reduce((s: number, p: Position) => s + (p.size || 0) * (p.mark_price || 0), 0))}
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-5 xl:grid-cols-5 gap-2">
        {stats.map((s) => (
          <StatCard key={s.label} {...s} loading={loading} />
        ))}
      </div>
    </div>
  )
}
