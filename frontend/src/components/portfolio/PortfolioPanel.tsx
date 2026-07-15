"use client"

import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card"
import { cn, formatPrice } from "@/lib/utils"
import {
  PieChart, TrendingUp, TrendingDown,
  BarChart3, Clock, Award,
} from "lucide-react"

interface PortfolioAnalytics {
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  best_trade: number;
  worst_trade: number;
  winning_trades: number;
  losing_trades: number;
  avg_holding_time: string;
  monthly_breakdown?: {
    month?: string;
    label?: string;
    pnl: number;
  }[];
}

interface DailyPnLEntry {
  date?: string;
  day?: string;
  pnl: number;
}

export function PortfolioPanel() {
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null)
  const [dailyPnl, setDailyPnl] = useState<DailyPnLEntry[]>([])

  const load = useCallback(async () => {
    try {
      const [a, d] = await Promise.all([
        api.getPortfolioAnalytics(),
        api.getDailyPnL(),
      ])
      setAnalytics(a as PortfolioAnalytics)
      setDailyPnl(Array.isArray(d) ? (d as DailyPnLEntry[]) : [])
    } catch {}
  }, [])

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load() }, [load])

  if (!analytics) {
    return <div className="p-4 text-center text-gray-500 text-sm">Loading portfolio...</div>
  }

  const stats = [
    { label: "Win Rate", value: `${(analytics.win_rate || 0).toFixed(1)}%`, color: (analytics.win_rate || 0) >= 50 ? "green" : "red", icon: Award },
    { label: "Profit Factor", value: (analytics.profit_factor || 0).toFixed(2), color: (analytics.profit_factor || 0) >= 1.5 ? "green" : "yellow", icon: TrendingUp },
    { label: "Total Trades", value: analytics.total_trades || 0, color: "blue", icon: BarChart3 },
    { label: "Best Trade", value: formatPrice(analytics.best_trade || 0), color: "green", icon: Award },
    { label: "Worst Trade", value: formatPrice(analytics.worst_trade || 0), color: "red", icon: Award },
    { label: "Win Trades", value: analytics.winning_trades || 0, color: "green", icon: TrendingUp },
    { label: "Loss Trades", value: analytics.losing_trades || 0, color: "red", icon: TrendingDown },
    { label: "Avg Hold Time", value: analytics.avg_holding_time || "--", color: "default", icon: Clock },
  ]

  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      <div className="flex items-center gap-2 mb-2">
        <PieChart className="w-5 h-5 text-blue-400" />
        <h2 className="text-sm font-semibold text-white">Portfolio Analytics</h2>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {stats.map((s) => (
          <Card key={s.label} className="border-gray-700 p-3">
            <div className="flex items-center gap-1 mb-1">
              <s.icon className="w-3 h-3 text-gray-500" />
              <span className="text-[10px] text-gray-500">{s.label}</span>
            </div>
            <div className={cn("text-lg font-bold font-mono", {
              "text-green-400": s.color === "green",
              "text-red-400": s.color === "red",
              "text-yellow-400": s.color === "yellow",
              "text-white": s.color === "blue" || s.color === "default",
            })}>
              {s.value}
            </div>
          </Card>
        ))}
      </div>

      {analytics.monthly_breakdown && (
        <Card>
          <CardHeader>
            <CardTitle>Monthly PnL Heatmap</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-1">
              {analytics.monthly_breakdown.map((m, i) => (
                <div
                  key={i}
                  className={cn(
                    "p-2 rounded text-center",
                    (m.pnl || 0) > 0 ? "bg-green-900/30" : (m.pnl || 0) < 0 ? "bg-red-900/30" : "bg-gray-800/50"
                  )}
                >
                  <div className="text-[9px] text-gray-500">{m.month || m.label || ""}</div>
                  <div className={cn("text-[10px] font-mono font-medium",
                    (m.pnl || 0) > 0 ? "text-green-400" : (m.pnl || 0) < 0 ? "text-red-400" : "text-gray-500"
                  )}>
                    {(m.pnl || 0) > 0 ? "+" : ""}{m.pnl?.toFixed(0)}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {dailyPnl.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Daily PnL</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 max-h-40 overflow-auto">
            {dailyPnl.slice(0, 30).map((d, i) => (
              <div key={i} className="flex items-center justify-between text-[10px]">
                <span className="text-gray-500">{d.date || d.day || ""}</span>
                <span className={cn("font-mono font-medium",
                  (d.pnl || 0) >= 0 ? "text-green-400" : "text-red-400"
                )}>
                  {(d.pnl || 0) >= 0 ? "+" : ""}{d.pnl?.toFixed(2)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
