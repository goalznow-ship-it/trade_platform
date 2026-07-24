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
  side?: string
  entry_price?: number
  leverage?: number
}

interface Portfolio {
  balance?: number
  total_pnl?: number
  win_rate?: number
  total_trades?: number
  open_positions?: number
}

interface PaperAccount {
  balance?: number
  equity?: number
  free_margin?: number
  used_margin?: number
  total_pnl?: number
  total_trades?: number
  win_count?: number
  loss_count?: number
  win_rate?: number
  profit_factor?: number
  initial_balance?: number
  is_paper?: boolean
}

interface Analytics {
  win_rate?: number
  profit_factor?: number
  avg_risk_reward?: number
  total_trades?: number
}

interface BalanceEntry {
  free?: number
  used?: number
}

interface DashboardData {
  portfolio?: Portfolio | null
  paper?: PaperAccount | null
  analytics?: Analytics | null
  positions: Position[]
  balance?: Record<string, BalanceEntry> | null
  isPaper?: boolean
  dataSource?: string
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
  dataSource?: string
}

const StatCard = memo(function StatCard({
  label, value, change, changeValue, icon: Icon, loading, tooltip, sub, dataSource,
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
        <div className="flex items-center gap-1">
          {dataSource && <span className="text-[8px] text-gray-700">{dataSource}</span>}
          <Icon className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-400 transition-colors" />
        </div>
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
  const [error, setError] = useState<string | null>(null)
  const liveTs = useLiveTimestamp()
  const isLive = useMarketStore((s) => s.isLive)

  const load = useCallback(async () => {
    try {
      let portfolio: Portfolio | null = null
      let paper: PaperAccount | null = null
      let analytics: Analytics | null = null
      let positions: Position[] = []
      let balance: Record<string, BalanceEntry> | null = null
      let isPaper = false
      let dataSource = "provider unavailable"

      try { portfolio = await api.getPortfolio() } catch { portfolio = null }
      try {
        paper = await api.getPaperAccount()
        if (paper && paper.balance !== undefined) paper.is_paper = true
      } catch { paper = null }

      try {
        analytics = await api.getPortfolioAnalytics()
      } catch {
        analytics = null
      }

      try {
        const pos = await api.getPositions()
        positions = Array.isArray(pos) ? pos : []
      } catch {
        positions = []
      }

      try {
        balance = await api.getBalance()
        if (balance && Object.keys(balance).length > 0) {
          dataSource = "real exchange"
        } else {
          balance = null
        }
      } catch {
        balance = null
      }

      // A database user balance is not proof of an exchange connection.
      // Prefer the explicitly separated paper account unless a real exchange
      // balance response exists.
      if (!balance && paper) {
        isPaper = true
        dataSource = "paper account · Exchange qoşulmayıb"
      } else if (!balance) {
        portfolio = null
        dataSource = "Exchange qoşulmayıb"
      }

      if (!portfolio && !paper && !analytics && positions.length === 0) {
        setError("No verified data - account not initialized")
      } else {
        setError(null)
      }

      setData({ portfolio, paper, analytics, positions, balance, isPaper, dataSource })
    } catch {
      setError("provider unavailable")
    } finally {
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

  const totalBalance = data?.isPaper ? data?.paper?.balance : data?.portfolio?.balance
  const equity = data?.portfolio && data.portfolio.balance !== undefined
    && !data?.isPaper && totalBalance != null
    ? totalBalance + unrealizedPnl
    : (data?.paper?.equity ?? (totalBalance != null ? totalBalance + unrealizedPnl : undefined))
  const isPaper = data?.isPaper ?? false

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
    freeMargin = data?.paper?.free_margin ?? equity ?? 0
    usedMargin = data?.paper?.used_margin ?? 0
  }

  const marginRatio = usedMargin > 0 ? (usedMargin / (freeMargin + usedMargin)) * 100 : 0

  const winRate = data?.analytics?.win_rate ?? data?.paper?.win_rate ?? 0
  const profitFactor = data?.analytics?.profit_factor ?? data?.paper?.profit_factor ?? 0
  const avgRR = data?.analytics?.avg_risk_reward ?? 0
  const totalTrades = data?.analytics?.total_trades ?? data?.paper?.total_trades ?? 0

  const dataSource = data?.dataSource ?? (error || "N/A")

  const stats = useMemo(() => [
    {
      label: "Equity",
      value: equity == null ? "Exchange qoşulmayıb" : formatPrice(equity),
      change: unrealizedPnl !== 0 ? (unrealizedPnl >= 0 ? "+" : "") + formatPrice(Math.abs(unrealizedPnl)) : undefined,
      changeValue: unrealizedPnl,
      icon: LineChart,
      tooltip: `Total account value including unrealized PnL (${dataSource})`,
      sub: isPaper ? "Paper Balance" : undefined,
    },
    {
      label: "Balance",
      value: totalBalance == null ? "Exchange qoşulmayıb" : formatPrice(totalBalance),
      icon: Wallet,
      tooltip: `Available account balance (${dataSource})`,
      sub: isPaper ? "Paper" : undefined,
    },
    {
      label: "Free Margin",
      value: formatPrice(freeMargin),
      icon: DollarSign,
      tooltip: `Available margin for new positions (${dataSource})`,
    },
    {
      label: "Margin Ratio",
      value: marginRatio > 0 ? `${marginRatio.toFixed(1)}%` : error ? "N/A" : "0%",
      changeValue: marginRatio,
      change: marginRatio > 0 ? `${marginRatio.toFixed(1)}%` : undefined,
      icon: Percent,
      tooltip: "Used margin / total equity ratio",
      sub: marginRatio === 0 && !error ? "no positions" : undefined,
    },
    {
      label: "Unrealized PnL",
      value: unrealizedPnl !== 0
        ? (unrealizedPnl >= 0 ? "+" : "") + formatPrice(Math.abs(unrealizedPnl))
        : error ? "N/A" : "$0.00",
      changeValue: unrealizedPnl,
      icon: unrealizedPnl >= 0 ? TrendingUp : TrendingDown,
      tooltip: "Current floating profit/loss on open positions",
      sub: unrealizedPnl === 0 && !error ? "no positions" : undefined,
    },
    {
      label: "Win Rate",
      value: winRate > 0 ? `${winRate.toFixed(1)}%` : (error ? "N/A" : "0%"),
      changeValue: winRate - 50,
      change: winRate > 0 ? `${winRate.toFixed(1)}%` : undefined,
      icon: Target,
      tooltip: `Percentage of winning trades (${dataSource})`,
      sub: winRate === 0 && !error ? "no trades" : undefined,
    },
    {
      label: "Profit Factor",
      value: profitFactor === Infinity ? "∞" : profitFactor > 0 ? profitFactor.toFixed(2) : (error ? "N/A" : "0.00"),
      changeValue: typeof profitFactor === "number" ? profitFactor - 1 : 0,
      change: profitFactor > 0 ? profitFactor.toFixed(2) : undefined,
      icon: BarChart3,
      tooltip: `Gross profit / gross loss ratio (${dataSource})`,
      sub: profitFactor === 0 && !error ? "no trades" : undefined,
    },
    {
      label: "Avg R:R",
      value: avgRR > 0 ? avgRR.toFixed(2) : (error ? "N/A" : "0.00"),
      icon: Activity,
      tooltip: `Average risk-to-reward ratio (${dataSource})`,
      sub: avgRR === 0 && !error ? "no trades" : undefined,
    },
    {
      label: "Total Trades",
      value: totalTrades > 0 ? String(totalTrades) : (error ? "N/A" : "0"),
      icon: BarChart3,
      tooltip: `Total number of closed trades (${dataSource})`,
    },
    {
      label: "Active Pos.",
      value: String(positions.length),
      icon: Activity,
      tooltip: "Currently open positions",
      sub: positions.length === 0 && !error ? "no positions" : undefined,
    },
  ], [equity, totalBalance, freeMargin, marginRatio, unrealizedPnl, winRate, profitFactor, avgRR, totalTrades, positions.length, dataSource, isPaper, error])

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-600 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Updated {new Date(liveTs).toLocaleTimeString()}
          </span>
          {dataSource !== "N/A" && (
            <span className={cn(
              "text-[9px] px-1.5 py-0.5 rounded",
              dataSource === "live portfolio" ? "bg-green-900/20 text-green-400" :
              dataSource === "paper balance" ? "bg-blue-900/20 text-blue-400" :
              "bg-yellow-900/20 text-yellow-400"
            )}>
              {dataSource}
            </span>
          )}
          {error && (
            <span className="text-[9px] text-red-400 bg-red-900/20 px-1.5 py-0.5 rounded">
              {error}
            </span>
          )}
        </div>
        {!loading && positions.length > 0 && (
          <span className="text-[10px] text-gray-600">
            Exposure: {formatPrice(positions.reduce((s: number, p: Position) => s + (p.size || 0) * (p.mark_price || 0), 0))}
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-5 xl:grid-cols-5 gap-2">
        {stats.map((s) => (
          <StatCard key={s.label} {...s} loading={loading} dataSource={undefined} />
        ))}
      </div>
    </div>
  )
}
