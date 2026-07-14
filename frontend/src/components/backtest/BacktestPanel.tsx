"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { cn, formatPrice } from "@/lib/utils"
import {
  History, Trash2, Download, BarChart3, TrendingUp, TrendingDown,
} from "lucide-react"

export function BacktestPanel() {
  const [history, setHistory] = useState<any[]>([])

  async function load() {
    try {
      const h = await api.getBacktestHistory()
      setHistory(Array.isArray(h) ? h : [])
    } catch {}
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id: number) {
    await api.deleteBacktest(id)
    load()
  }

  async function handleExport() {
    try {
      const blob = await api.exportTradeHistory()
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "trade_history.csv"
      a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-gray-200">Backtest History</span>
            <Badge variant="info">{history.length}</Badge>
          </div>
          <Button variant="ghost" size="sm" onClick={handleExport}>
            <Download className="w-3 h-3 mr-1" /> CSV
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {history.length === 0 && (
          <div className="p-4 text-center text-gray-600 text-xs">No backtest results saved yet</div>
        )}
        {history.map((b) => (
          <div key={b.id} className="px-3 py-2.5 border-b border-gray-800 hover:bg-gray-800/50 group">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium text-gray-200 font-mono">{b.symbol}</span>
              <Badge variant="info" className="text-[9px]">{b.timeframe || "--"}</Badge>
              <div className="flex-1" />
              <div className={cn("text-xs font-bold font-mono",
                (b.total_return || b.return_pct || 0) >= 0 ? "text-green-400" : "text-red-400"
              )}>
                {(b.total_return || b.return_pct || 0) >= 0 ? "+" : ""}
                {(b.total_return || b.return_pct || 0)?.toFixed(2)}%
              </div>
              <button onClick={() => handleDelete(b.id)}
                className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100">
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
            <div className="flex gap-3 text-[10px] text-gray-500">
              <span>Balance: {formatPrice(b.final_balance || b.balance || 0)}</span>
              <span>Trades: {b.total_trades || 0}</span>
              <span>Win Rate: {(b.win_rate || 0).toFixed(0)}%</span>
              <span>Sharpe: {(b.sharpe_ratio || 0).toFixed(2)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
