"use client"

import { useEffect, useState, useRef, memo, useCallback } from "react"
import { useWS } from "@/components/WSProvider"
import { api } from "@/lib/api"
import { cn, formatPrice, confidenceColor } from "@/lib/utils"
import { Zap, AlertCircle, Target, Send } from "lucide-react"

interface SignalData {
  symbol?: string
  direction?: string
  score?: number
  confidence?: number
  entry_zone?: { min?: number; max?: number } | number[]
  entry_price?: number
  stop_loss?: number
  take_profit_1?: number
  take_profit_2?: number
  take_profit_3?: number
  take_profit?: number[]
  risk_reward?: number
  timeframe?: string
  reasons?: string[]
  reason?: string
  factors?: string[]
  ai_factors?: string[]
  created_at?: string
}

const SignalCard = memo(function SignalCard({ s }: { s: SignalData }) {
  const entryZone: unknown = s.entry_zone ?? s.entry_price
  const isObj = entryZone != null && typeof entryZone === "object" && !Array.isArray(entryZone)
  const isArr = Array.isArray(entryZone)
  const entryLow: number = isObj
    ? (entryZone as Record<string, number>).min ?? 0
    : isArr
    ? (entryZone as number[])[0] ?? 0
    : (entryZone as number) ?? 0
  const entryHigh: number = isObj
    ? (entryZone as Record<string, number>).max ?? 0
    : isArr
    ? (entryZone as number[])[1] ?? 0
    : (entryZone as number) ?? 0
  const tp1 = Array.isArray(s.take_profit) ? s.take_profit[0] : s.take_profit_1 || 0
  const tp2 = Array.isArray(s.take_profit) ? s.take_profit[1] : s.take_profit_2
  const tp3 = Array.isArray(s.take_profit) ? s.take_profit[2] : s.take_profit_3
  const sl = s.stop_loss || 0
  const confidence = s.confidence || s.score || 0
  const rr = s.risk_reward || (tp1 && sl ? Math.abs((tp1 - entryLow) / (entryLow - sl)) : 0)
  const reasons = Array.isArray(s.reasons) ? s.reasons : s.reason ? [s.reason] : []
  const factors = s.factors || s.ai_factors || []

  return (
    <div className={cn("p-3 rounded-lg border transition-all duration-200 cursor-pointer hover:brightness-110",
      confidence >= 85 ? "bg-green-900/10 border-green-800/20" :
      confidence >= 70 ? "bg-blue-900/10 border-blue-800/20" :
      confidence >= 50 ? "bg-yellow-900/10 border-yellow-800/20" :
      "bg-gray-800/20 border-gray-800")}>
      <div className="flex items-center gap-3 mb-2">
        <div className={cn("w-1 h-12 rounded-full", s.direction === "long" ? "bg-green-500" : "bg-red-500")} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold text-white font-mono">{s.symbol}</span>
            <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded",
              s.direction === "long" ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400")}>
              {s.direction?.toUpperCase()}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-[10px] text-gray-500">{s.timeframe || "1h"}</span>
            {rr > 0 && <span className="text-[10px] text-gray-500">R:R 1:{rr.toFixed(1)}</span>}
          </div>
        </div>
        <div className="text-right">
          <div className={cn("text-lg font-bold font-mono", confidenceColor(confidence))}>
            {Math.round(confidence)}%
          </div>
          <div className="text-[9px] text-gray-600">confidence</div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-1.5 text-[10px] mb-2">
        <div className="p-1.5 rounded bg-gray-800/40">
          <span className="text-gray-600">Entry</span>
          <div className="text-gray-300 font-mono">
            {entryLow === entryHigh
              ? formatPrice(entryLow)
              : `${formatPrice(entryLow)}–${formatPrice(entryHigh)}`}
          </div>
        </div>
        <div className="p-1.5 rounded bg-green-900/15 border border-green-900/20">
          <span className="text-green-400">TP1</span>
          <div className="text-green-300 font-mono">{tp1 ? formatPrice(tp1) : "--"}</div>
        </div>
        <div className="p-1.5 rounded bg-red-900/15 border border-red-900/20">
          <span className="text-red-400">SL</span>
          <div className="text-red-300 font-mono">{sl ? formatPrice(sl) : "--"}</div>
        </div>
        <div className="p-1.5 rounded bg-gray-800/40">
          <span className="text-gray-600">R:R</span>
          <div className="text-gray-300 font-mono">{rr > 0 ? `1:${rr.toFixed(1)}` : "--"}</div>
        </div>
      </div>

      {tp2 || tp3 ? (
        <div className="flex gap-1.5 text-[10px] mb-2">
          {tp2 ? (
            <div className="flex-1 p-1 rounded bg-green-900/10 border border-green-900/15">
              <span className="text-green-400/70">TP2</span>
              <div className="text-green-300/70 font-mono">{formatPrice(tp2)}</div>
            </div>
          ) : null}
          {tp3 ? (
            <div className="flex-1 p-1 rounded bg-green-900/10 border border-green-900/15">
              <span className="text-green-400/50">TP3</span>
              <div className="text-green-300/50 font-mono">{formatPrice(tp3)}</div>
            </div>
          ) : null}
        </div>
      ) : null}

      {reasons.length > 0 && (
        <div className="text-[10px] text-gray-500 leading-relaxed line-clamp-2 mb-1">
          {reasons.join(" · ")}
        </div>
      )}

      {factors.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {factors.slice(0, 3).map((f: string, i: number) => (
            <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-gray-800/50 text-gray-500">{f}</span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 mt-1.5">
        <button className="flex items-center gap-1 text-[9px] text-gray-600 hover:text-gray-400 transition-colors px-1.5 py-0.5 rounded hover:bg-gray-800/30">
          <Target className="w-2.5 h-2.5" /> Copy
        </button>
        <button className="flex items-center gap-1 text-[9px] text-gray-600 hover:text-gray-400 transition-colors px-1.5 py-0.5 rounded hover:bg-gray-800/30">
          <Send className="w-2.5 h-2.5" /> Share
        </button>
      </div>
    </div>
  )
})

export function TopSignals() {
  const { on, isConnected: isLive } = useWS()
  const [signals, setSignals] = useState<SignalData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const wsInitialized = useRef(false)

  useEffect(() => {
    const unsub = on("signal_update", (msg) => {
      const raw = msg?.data as { data?: SignalData[] } | SignalData[] | undefined
      const list = Array.isArray(raw) ? raw : (raw as { data?: SignalData[] })?.data || []
      if (Array.isArray(list) && list.length > 0) {
        setSignals(list.slice(0, 5))
        setError(null)
      }
      setLoading(false)
    })
    return unsub
  }, [on])

  const loadFallback = useCallback(async () => {
    try {
      const data = await api.scanAllV2(70)
      const list = data?.signals || data || []
      setSignals(Array.isArray(list) ? list.slice(0, 5) : [])
      setError(null)
    } catch {
      setError("Signal data unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (signals.length === 0 && !wsInitialized.current) {
      wsInitialized.current = true
      loadFallback()
    }
    const interval = setInterval(() => {
      if (!isLive || signals.length === 0) loadFallback()
    }, isLive ? 120000 : 60000)
    return () => clearInterval(interval)
  }, [isLive, signals.length, loadFallback])

  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-3">
          <div className="h-3 w-24 bg-gray-800 rounded" />
          {[1, 2, 3].map((i) => <div key={i} className="h-28 bg-gray-800 rounded" />)}
        </div>
      </div>
    )
  }

  if (error && signals.length === 0) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Top Signals</h3>
          <Zap className="w-3.5 h-3.5 text-yellow-500" />
        </div>
        <div className="flex items-center gap-2 text-yellow-400 text-xs">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-yellow-500" />
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Top Signals</h3>
        </div>
        <div className="flex items-center gap-2">
          {isLive && <span className="text-[9px] text-green-500">● LIVE</span>}
          {signals.length > 0 && (
            <span className="text-[10px] text-gray-600">
              Best: {Math.round(Math.max(...signals.map((s) => s.confidence || s.score || 0)))}%
            </span>
          )}
        </div>
      </div>
      {signals.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-gray-600">
          <div className="w-10 h-10 rounded-full bg-gray-800/50 flex items-center justify-center mb-2">
            <Zap className="w-5 h-5 text-gray-600" />
          </div>
          <span className="text-xs mb-1">No active signals</span>
          <span className="text-[10px] text-gray-700">Scanning market for opportunities</span>
        </div>
      ) : (
        <div className="space-y-2">
          {signals.map((s, i) => (
            <SignalCard key={i} s={s} />
          ))}
        </div>
      )}
    </div>
  )
}
