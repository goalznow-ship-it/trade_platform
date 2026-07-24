"use client"

import { useState, useEffect, useCallback } from "react"
import { Navbar } from "@/components/Navbar"
import { api } from "@/lib/api"
import { SKHYChart } from "@/components/skhy/SKHYChart"
import { SKHYAnalysisPanel } from "@/components/skhy/SKHYAnalysisPanel"
import { SKHYScenarioPanel } from "@/components/skhy/SKHYScenarioPanel"
import { SKHYTriggerPanel } from "@/components/skhy/SKHYTriggerPanel"
import { cn } from "@/lib/utils"
import { Activity, AlertTriangle, BarChart3, Brain, Clock, RefreshCw, TrendingDown, TrendingUp } from "lucide-react"

interface AlertType {
  id: string
  type: string
  message: string
  time: string
  severity: "info" | "warning" | "success" | "error"
}

function numOrZero(v: unknown): number {
  return typeof v === "number" ? v : 0
}

function formatVolume(v: unknown): string {
  const n = typeof v === "number" ? v : 0
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`
  return n.toFixed(0)
}

function getStatusColor(status: string): string {
  switch (status) {
    case "STRONG_TRADE_READY": return "text-green-400"
    case "TRADE_READY": return "text-blue-400"
    case "WATCHLIST": return "text-yellow-400"
    default: return "text-gray-500"
  }
}

function PriceItem({ label, value, highlight }: { label: string; value: unknown; highlight?: boolean }) {
  if (value == null) return null
  return (
    <div className="flex items-center gap-1.5 whitespace-nowrap">
      <span className="text-gray-500">{label}:</span>
      <span className={cn("font-mono", highlight ? "text-white font-bold text-sm" : "text-gray-300")}>
        {typeof value === "number" ? value.toFixed(2) : String(value)}
      </span>
    </div>
  )
}

export default function SkhyTerminalPage() {
  const [snapshot, setSnapshot] = useState<Record<string, unknown> | null>(null)
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null)
  const [scenarios, setScenarios] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [alerts, setAlerts] = useState<AlertType[]>([])
  const [wsConnected, setWsConnected] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  const fetchData = useCallback(async () => {
    try {
      const [snap, an, sc] = await Promise.all([
        api.getSkhySnapshot().catch(() => null),
        api.getSkhyAnalysis().catch(() => null),
        api.getSkhyScenarios().catch(() => null),
      ])
      if (snap) setSnapshot(snap)
      if (an) setAnalysis(an)
      if (sc) setScenarios(sc)
      setError(null)
      setLastUpdate(new Date())
    } catch {
      setError("Məlumat əldə edilə bilmir")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [fetchData])

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const wsUrl = `${protocol}//${window.location.hostname}:8000/api/v1/skhy/stream`
    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout>

    function connect() {
      ws = new WebSocket(wsUrl)
      ws.onopen = () => setWsConnected(true)
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.event === "skhy_update") {
            if (msg.data?.snapshot) setSnapshot(msg.data.snapshot)
            if (msg.data?.analysis) setAnalysis(msg.data.analysis)
            if (msg.data?.scenarios) setScenarios(msg.data.scenarios)
            setLastUpdate(new Date())
          }
        } catch { /* ignore */ }
      }
      ws.onclose = () => {
        setWsConnected(false)
        reconnectTimer = setTimeout(connect, 3000)
      }
      ws.onerror = () => ws?.close()
    }

    connect()
    const pingInterval = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping", data: { t: Date.now() } }))
      }
    }, 15000)

    return () => {
      clearInterval(pingInterval)
      clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [])

  const scores = (analysis?.scores || {}) as Record<string, unknown>
  const triggers = (analysis?.triggers || {}) as Record<string, unknown>
  const tfData = (analysis?.timeframes || {}) as Record<string, unknown>
  const alignment = (analysis?.alignment || {}) as Record<string, unknown>
  const sr = (analysis?.support_resistance || {}) as Record<string, unknown>

  const longProb = numOrZero(scores.long_probability)
  const shortProb = numOrZero(scores.short_probability)
  const confidence = numOrZero(scores.signal_confidence)

  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-4 py-1.5 border-b border-gray-800/60 bg-gray-950/90">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-bold text-white">SKHYUSDT</span>
              <span className="text-[10px] text-gray-500 px-1.5 py-0.5 rounded bg-gray-800 border border-gray-700">Binance Futures</span>
            </div>
            {loading && <RefreshCw className="w-3 h-3 text-gray-500 animate-spin" />}
            {error && <span className="text-xs text-red-400">{error}</span>}
          </div>
          <div className="flex items-center gap-3 text-[11px]">
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-gray-500" />
              <span className="text-gray-400">{lastUpdate.toLocaleTimeString()}</span>
            </div>
            <div className={cn("flex items-center gap-1", wsConnected ? "text-green-400" : "text-red-400")}>
              <Activity className="w-3 h-3" />
              <span>{wsConnected ? "Canlı" : "REST"}</span>
            </div>
          </div>
        </div>

        {/* Live Price Bar */}
        {snapshot && (
          <div className="flex items-center gap-4 px-4 py-2 border-b border-gray-800/40 bg-gray-950/50 text-xs overflow-x-auto">
            <PriceItem label="Price" value={snapshot.live_price} highlight />
            <PriceItem label="Mark" value={snapshot.mark_price} />
            <PriceItem label="Index" value={snapshot.index_price} />
            <PriceItem label="24h Change" value={snapshot.change_24h != null ? `${(numOrZero(snapshot.change_24h) >= 0 ? "+" : "")}${numOrZero(snapshot.change_24h).toFixed(2)}%` : "N/A"} />
            <PriceItem label="24h High" value={snapshot.high_24h} />
            <PriceItem label="24h Low" value={snapshot.low_24h} />
            <PriceItem label="Vol 24h" value={snapshot.volume_24h != null ? formatVolume(snapshot.volume_24h) : "N/A"} />
            <PriceItem label="Funding" value={snapshot.funding_rate != null ? `${(numOrZero(snapshot.funding_rate) * 100).toFixed(4)}%` : "N/A"} />
            <PriceItem label="OI" value={snapshot.open_interest != null ? formatVolume(snapshot.open_interest) : "N/A"} />
            <PriceItem label="L/S Ratio" value={snapshot.long_short_ratio != null ? numOrZero(snapshot.long_short_ratio).toFixed(2) : "N/A"} />
            <PriceItem label="Taker B/S" value={snapshot.taker_buy_sell_ratio != null ? numOrZero(snapshot.taker_buy_sell_ratio).toFixed(2) : "N/A"} />
            <PriceItem label="Bid" value={snapshot.bid} />
            <PriceItem label="Ask" value={snapshot.ask} />
            <PriceItem label="Spread" value={snapshot.spread != null ? numOrZero(snapshot.spread).toFixed(2) : "N/A"} />
          </div>
        )}

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 flex flex-col min-w-0">
            <div className="flex-1 min-h-0">
              <SKHYChart symbol="SKHYUSDT" snapshot={snapshot} analysis={analysis} triggers={triggers} sr={sr} />
            </div>
            {scores && (
              <div className="h-16 border-t border-gray-800/40 px-3 flex items-center gap-3 text-xs bg-gray-950/30">
                <div className="flex items-center gap-2">
                  <TrendingUp className={cn("w-4 h-4", longProb > 50 ? "text-green-400" : "text-gray-600")} />
                  <span className="text-gray-400">LONG</span>
                  <span className="font-mono font-bold text-green-400">{longProb}%</span>
                </div>
                <div className="w-px h-6 bg-gray-800" />
                <div className="flex items-center gap-2">
                  <TrendingDown className={cn("w-4 h-4", shortProb > 50 ? "text-red-400" : "text-gray-600")} />
                  <span className="text-gray-400">SHORT</span>
                  <span className="font-mono font-bold text-red-400">{shortProb}%</span>
                </div>
                <div className="w-px h-6 bg-gray-800" />
                <div className="flex items-center gap-2">
                  <Brain className="w-4 h-4 text-blue-400" />
                  <span className="text-gray-400">Confidence</span>
                  <span className={cn("font-mono font-bold", confidence >= 70 ? "text-green-400" : confidence >= 50 ? "text-yellow-400" : "text-gray-500")}>
                    {confidence}%
                  </span>
                </div>
                <div className="w-px h-6 bg-gray-800" />
                <span className={cn("font-semibold", getStatusColor(String(scores.status || "WAIT")))}>{String(scores.status || "WAIT")}</span>
              </div>
            )}
            {alerts.length > 0 && (
              <div className="h-12 border-t border-gray-800/40 px-3 flex items-center gap-2 overflow-x-auto text-[11px]">
                {alerts.slice(-5).map((a) => (
                  <span key={a.id} className={cn("flex items-center gap-1 px-2 py-0.5 rounded whitespace-nowrap",
                    a.severity === "warning" ? "bg-yellow-500/10 text-yellow-400" :
                    a.severity === "error" ? "bg-red-500/10 text-red-400" :
                    a.severity === "success" ? "bg-green-500/10 text-green-400" : "bg-blue-500/10 text-blue-400")}>
                    <AlertTriangle className="w-3 h-3" />{a.message}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Right Panel */}
          <div className="w-96 border-l border-gray-800/60 flex flex-col overflow-hidden bg-gray-950/30">
            <div className="flex-1 overflow-y-auto">
              <SKHYTriggerPanel triggers={triggers} scores={scores} />
              <SKHYAnalysisPanel timeframes={tfData} scores={scores} alignment={alignment} sr={sr} />
              <SKHYScenarioPanel scenarios={scenarios} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
