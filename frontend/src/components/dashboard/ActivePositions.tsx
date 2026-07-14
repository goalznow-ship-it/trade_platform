"use client"

import { useEffect, useState, useCallback, memo } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice, formatPercent, formatDuration } from "@/lib/utils"
import {
  TrendingUp, AlertCircle, Copy,
} from "lucide-react"

interface Position {
  id?: string
  symbol: string
  side?: string
  size?: number
  entry_price?: number
  mark_price?: number
  liquidation_price?: number
  unrealized_pnl?: number
  pnl_percent?: number
  roi?: number
  margin?: number
  leverage?: number
  risk_percent?: number
  exchange?: string
  opened_at?: string
  take_profit_1?: number
  take_profit?: number[]
  stop_loss?: number
  ai_score?: number
  confidence?: number
  strategy_name?: string
}

const PositionCard = memo(function PositionCard({ p }: { p: Position }) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 60000)
    return () => clearInterval(interval)
  }, [])

  const pnl = p.unrealized_pnl || 0
  const pnlPercent = p.pnl_percent || ((pnl && p.size && p.entry_price) ? (pnl / (p.size * p.entry_price)) * 100 : 0)
  const liqPrice = p.liquidation_price
  const markPrice = p.mark_price || p.entry_price
  const entryPrice = p.entry_price || 0
  const distance = liqPrice && markPrice
    ? Math.abs(markPrice - liqPrice) / (entryPrice || 1) * 100
    : null
  const roi = p.roi || pnlPercent
  const margin = p.margin || ((p.size || 0) * entryPrice) / (p.leverage || 1)
  const riskPercent = p.risk_percent || 0
  const exchange = p.exchange || "binance"
  const positionAge = p.opened_at ? Math.floor((now - new Date(p.opened_at).getTime()) / 60000) : 0
  const tp1 = p.take_profit_1 || p.take_profit?.[0]
  const tp2 = p.take_profit?.[1]
  const tp3 = p.take_profit?.[2]
  const sl = p.stop_loss || 0
  const aiScore = p.ai_score || p.confidence || 0
  const strategy = p.strategy_name || "—"

  return (
    <div className="p-3 rounded-lg bg-gray-800/20 hover:bg-gray-800/40 transition-all duration-200 border border-transparent hover:border-gray-700/30">
      <div className="flex items-start gap-3">
        <div className={cn("w-1 h-14 rounded-full mt-0.5", p.side === "long" ? "bg-green-500" : "bg-red-500")} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-sm font-semibold text-white font-mono">{p.symbol}</span>
            <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded",
              p.side === "long" ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400")}>
              {p.side?.toUpperCase()}
            </span>
            <span className="text-[10px] text-gray-600">{p.leverage || 1}x</span>
            <span className="text-[9px] text-gray-700 uppercase">{exchange}</span>
          </div>

          <div className="grid grid-cols-4 gap-1.5 text-[10px] mb-2">
            <div className="p-1.5 rounded bg-gray-800/40">
              <span className="text-gray-600">Entry</span>
              <div className="text-gray-300 font-mono">{formatPrice(entryPrice)}</div>
            </div>
            <div className="p-1.5 rounded bg-gray-800/40">
              <span className="text-gray-600">Mark</span>
              <div className="text-gray-300 font-mono">{markPrice ? formatPrice(markPrice) : "--"}</div>
            </div>
            <div className="p-1.5 rounded bg-gray-800/40">
              <span className="text-gray-600">Liq.</span>
              <div className={cn("font-mono", distance !== null && distance < 10 ? "text-red-400" : "text-gray-300")}>
                {liqPrice ? formatPrice(liqPrice) : "--"}
              </div>
            </div>
            <div className="p-1.5 rounded bg-gray-800/40">
              <span className="text-gray-600">Margin</span>
              <div className="text-gray-300 font-mono">{formatPrice(margin)}</div>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-1.5 text-[10px] mb-1.5">
            {sl ? (
              <div className="p-1.5 rounded bg-red-900/15 border border-red-900/20">
                <span className="text-red-400">SL</span>
                <div className="text-red-300 font-mono">{formatPrice(sl)}</div>
              </div>
            ) : null}
            {tp1 ? (
              <div className="p-1.5 rounded bg-green-900/15 border border-green-900/20">
                <span className="text-green-400">TP1</span>
                <div className="text-green-300 font-mono">{formatPrice(tp1)}</div>
              </div>
            ) : null}
            {tp2 ? (
              <div className="p-1.5 rounded bg-green-900/10 border border-green-900/15">
                <span className="text-green-400/70">TP2</span>
                <div className="text-green-300/70 font-mono">{formatPrice(tp2)}</div>
              </div>
            ) : null}
            {tp3 ? (
              <div className="p-1.5 rounded bg-green-900/10 border border-green-900/15">
                <span className="text-green-400/50">TP3</span>
                <div className="text-green-300/50 font-mono">{formatPrice(tp3)}</div>
              </div>
            ) : null}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 text-[10px] text-gray-600">
              <span>Size: {p.size || 0}</span>
              <span>Age: {positionAge > 0 ? formatDuration(positionAge) : "<1m"}</span>
              {strategy !== "—" && <span>Strategy: {strategy}</span>}
              {aiScore > 0 && <span>AI: {Math.round(aiScore)}%</span>}
            </div>
            <div className="flex items-center gap-2">
              {riskPercent > 0 && (
                <span className={cn("text-[10px] font-mono", riskPercent > 5 ? "text-red-400" : "text-gray-500")}>
                  Risk: {riskPercent.toFixed(1)}%
                </span>
              )}
              <button className="p-1 rounded hover:bg-gray-700/30 text-gray-600 hover:text-gray-400 transition-colors"
                title="Copy position">
                <Copy className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>

        <div className="text-right flex flex-col items-end gap-1">
          <div className={cn("text-base font-bold font-mono tracking-tight", pnl >= 0 ? "text-green-400" : "text-red-400")}>
            {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}
          </div>
          <div className={cn("text-[10px] font-mono font-medium", pnl >= 0 ? "text-green-500" : "text-red-500")}>
            {formatPercent(roi)}
          </div>
          {distance !== null && (
            <div className={cn("text-[9px] font-mono", distance < 5 ? "text-red-400 animate-pulse" : distance < 10 ? "text-yellow-400" : "text-gray-600")}>
              {distance.toFixed(1)}% to liq
            </div>
          )}
        </div>
      </div>
    </div>
  )
})

export function ActivePositions() {
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await api.getPositions()
      setPositions(Array.isArray(data) ? data : [])
      setError(null)
    } catch {
      setError("Positions unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(load, 0)
    const interval = setInterval(load, 15000)
    return () => {
      clearTimeout(timer)
      clearInterval(interval)
    }
  }, [load])

  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-3">
          <div className="h-3 w-28 bg-gray-800 rounded" />
          {[1, 2].map((i) => <div key={i} className="h-24 bg-gray-800 rounded" />)}
        </div>
      </div>
    )
  }

  if (error && positions.length === 0) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Active Positions</h3>
        <div className="flex items-center gap-2 text-yellow-400 text-xs">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          {error}
        </div>
      </div>
    )
  }

  const totalPnl = positions.reduce((s: number, p: Position) => s + (p.unrealized_pnl || 0), 0)

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Active Positions</h3>
          {positions.length > 0 && (
            <span className="text-[10px] text-gray-600">({positions.length})</span>
          )}
        </div>
        <div className={cn("text-xs font-bold font-mono", totalPnl >= 0 ? "text-green-400" : "text-red-400")}>
          Total PnL: {totalPnl >= 0 ? "+" : ""}{formatPrice(totalPnl)}
        </div>
      </div>
      {positions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-gray-600">
          <div className="w-10 h-10 rounded-full bg-gray-800/50 flex items-center justify-center mb-2">
            <TrendingUp className="w-5 h-5 text-gray-600" />
          </div>
          <span className="text-xs mb-1">No open positions</span>
          <span className="text-[10px] text-gray-700">Connect exchange API keys to start trading</span>
        </div>
      ) : (
        <div className="space-y-2">
          {positions.map((p, i) => (
            <PositionCard key={p.id || i} p={p} />
          ))}
        </div>
      )}
    </div>
  )
}
