"use client"

import { useState, useEffect, useCallback, useRef, useMemo } from "react"
import { Navbar } from "@/components/Navbar"
import { api } from "@/lib/api"
import { SKHYChart } from "@/components/skhy/SKHYChart"
import { SKHYAnalysisPanel } from "@/components/skhy/SKHYAnalysisPanel"
import { normalizeSkhyAnalysis as clientNormalize, type NormalizedAnalysis } from "@/lib/skhyChartNormalizer"
import { SKHYScenarioPanel } from "@/components/skhy/SKHYScenarioPanel"
import { SKHYTriggerPanel } from "@/components/skhy/SKHYTriggerPanel"
import { SKHYHistoryPanel } from "@/components/skhy/SKHYHistoryPanel"
import { SKHYSignalPlan } from "@/components/skhy/SKHYSignalPlan"
import { cn } from "@/lib/utils"
import { Activity, AlertTriangle, BarChart3, Brain, Clock, RefreshCw, TrendingDown, TrendingUp, Play, Terminal } from "lucide-react"

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

function parseLastUpdated(v: unknown): Date | null {
  if (v == null) return null
  if (typeof v === "number") return new Date(v > 1e12 ? v : v * 1000)
  if (typeof v === "string") {
    const d = new Date(v)
    if (!isNaN(d.getTime())) return d
    const num = Number(v)
    if (!isNaN(num)) return new Date(num > 1e12 ? num : num * 1000)
  }
  if (v instanceof Date) return v
  return null
}

const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

export default function SkhyTerminalPage() {
  const [symbol, setSymbol] = useState("SKHYUSDT")
  const [symbols, setSymbols] = useState<string[]>(["SKHYUSDT"])
  const [timeframe, setTimeframe] = useState("1h")
  const [snapshot, setSnapshot] = useState<Record<string, unknown> | null>(null)
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null)
  const [scenarios, setScenarios] = useState<Record<string, unknown> | null>(null)
  const [history, setHistory] = useState<Record<string, unknown> | null>(null)
  const [backtestResult, setBacktestResult] = useState<Record<string, unknown> | null>(null)
  const [backtestRunning, setBacktestRunning] = useState(false)
  const [diagnostics, setDiagnostics] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [tfLoading, setTfLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [scenarioError, setScenarioError] = useState<string | null>(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const wsRef = useRef<WebSocket | null>(null)
  const wsCleanupRef = useRef<(() => void) | null>(null)
  const lastValidAnalysisRef = useRef<Record<string, unknown> | null>(null)
  const lastValidScenariosRef = useRef<Record<string, unknown> | null>(null)
  const requestIdRef = useRef(0)

  function logDebug(tag: string, ...args: unknown[]) {
    if (process.env.NODE_ENV === "production") return
    const ts = new Date().toISOString().slice(11, 23)
    console.log(`[${ts}][SKHY] ${tag}`, ...args)
  }

  function isValidAnalysisPayload(payload: Record<string, unknown> | null | undefined, tf: string): boolean {
    if (!payload) { logDebug("ANALYSIS_REJECTED_EMPTY"); return false }
    const scores = payload.scores as Record<string, unknown> | undefined
    if (!scores) { logDebug("ANALYSIS_REJECTED_NO_SCORES", { tf }); return false }
    const atf = payload.active_timeframe || payload.timeframe
    if (atf && String(atf) !== tf) { logDebug("ANALYSIS_REJECTED_WRONG_TF", { expected: tf, got: atf }); return false }
    const hasCore = !!payload.scenario_paths || !!payload.detected_structure || !!payload.channel_lines
    if (!hasCore) { logDebug("ANALYSIS_REJECTED_NO_CORE", { keys: Object.keys(payload).slice(0, 10) }); return false }
    return true
  }

  function safeSetAnalysis(payload: Record<string, unknown> | null, tf: string) {
    if (isValidAnalysisPayload(payload, tf)) {
      lastValidAnalysisRef.current = payload
      setAnalysis(payload)
      setAnalysisError(null)
      setLastUpdate(new Date())
      logDebug("ANALYSIS_ACCEPTED", { tf })
    } else if (lastValidAnalysisRef.current) {
      logDebug("ANALYSIS_REJECTED_KEEP_CACHED", { tf, hasCache: true })
    }
  }

  function safeSetScenarios(payload: Record<string, unknown> | null, tf: string) {
    const scenarioPayload = payload?.scenarios && typeof payload.scenarios === "object"
      ? payload.scenarios as Record<string, unknown>
      : payload
    if (scenarioPayload?.main_scenario) {
      lastValidScenariosRef.current = scenarioPayload
      setScenarios(scenarioPayload)
      setScenarioError(null)
      logDebug("SCENARIOS_ACCEPTED", { tf })
    } else if (lastValidScenariosRef.current) {
      logDebug("SCENARIOS_REJECTED_KEEP_CACHED", { tf })
    }
  }

  const fetchData = useCallback(async (tf: string) => {
    const reqId = ++requestIdRef.current
    setTfLoading(true)
    try {
      const [snap, an, sc, hist] = await Promise.all([
        api.getSkhySnapshot(tf, symbol).catch(() => null),
        api.getSkhyAnalysis(tf, symbol).catch(() => null),
        api.getSkhyScenarios(tf, symbol).catch(() => null),
        api.getSkhyHistory(tf, 30, symbol).catch(() => null),
      ])
      if (reqId !== requestIdRef.current) { logDebug("FETCH_STALE", { reqId, current: requestIdRef.current, tf }); return }
      if (snap) setSnapshot(snap)
      safeSetAnalysis(an as Record<string, unknown> | null, tf)
      safeSetScenarios(sc as Record<string, unknown> | null, tf)
      if (hist) setHistory(hist)
      if (an || sc) setError(null)
      setLastUpdate(new Date())
      logDebug("FETCH_ACCEPTED", { tf })
    } catch {
      if (reqId === requestIdRef.current) setError("Məlumat əldə edilə bilmir")
    } finally {
      if (reqId === requestIdRef.current) { setLoading(false); setTfLoading(false) }
    }
  }, [symbol])

  useEffect(() => {
    api.getSkhySymbols().then((result) => {
      const available = Array.isArray(result?.symbols) ? result.symbols.filter((item: unknown): item is string => typeof item === "string") : []
      if (available.length) setSymbols(available)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    lastValidAnalysisRef.current = null
    lastValidScenariosRef.current = null
    setSnapshot(null)
    setAnalysis(null)
    setScenarios(null)
    setHistory(null)
    setBacktestResult(null)
  }, [symbol])

  useEffect(() => {
    logDebug("TIMEFRAME_CHANGE", { timeframe })
    fetchData(timeframe)
    api.getSkhyDiagnostics(timeframe, symbol).then(d => {
      if (!d?.timeframe || d.timeframe === timeframe) setDiagnostics(d)
    }).catch(() => {})
  }, [timeframe, symbol, fetchData])

  useEffect(() => {
    const interval = setInterval(() => fetchData(timeframe), 15000)
    return () => clearInterval(interval)
  }, [timeframe, fetchData])

  // WebSocket — fully disconnected on timeframe change, single WS always
  useEffect(() => {
    wsCleanupRef.current?.()
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const wsBase = (process.env.NEXT_PUBLIC_WS_URL || `${protocol}//${window.location.hostname}:8000`).replace(/\/$/, "")
    const wsUrl = `${wsBase}/api/v1/skhy/stream?timeframe=${timeframe}&symbol=${encodeURIComponent(symbol)}`
    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout>
    let pingInterval: ReturnType<typeof setInterval>
    let closed = false

    function connect() {
      if (closed) return
      ws = new WebSocket(wsUrl)
      wsRef.current = ws
      ws.onopen = () => { if (!closed) { setWsConnected(true); logDebug("WS_CONNECTED", { tf: timeframe }) } }
      ws.onmessage = (event) => {
        if (closed) return
        try {
          const msg = JSON.parse(event.data)
          if (msg.event === "pong" || msg.event === "heartbeat" || msg.type === "pong") return
          if (msg.event === "skhy_update") {
            if (msg.data?.snapshot) {
              setSnapshot(msg.data.snapshot)
              logDebug("WS_SNAPSHOT", { tf: timeframe })
            }
            if (msg.data?.analysis !== undefined) {
              logDebug("WS_ANALYSIS_RECEIVED", { tf: timeframe, hasData: !!msg.data.analysis, keys: Object.keys(msg.data.analysis || {}).slice(0, 8) })
              safeSetAnalysis(msg.data.analysis, timeframe)
            }
            if (msg.data?.scenarios !== undefined) {
              safeSetScenarios(msg.data.scenarios, timeframe)
            }
          } else if (msg.type === "analysis" && msg.data) {
            logDebug("WS_ANALYSIS_DIRECT", { tf: timeframe, keys: Object.keys(msg.data).slice(0, 8) })
            safeSetAnalysis(msg.data, timeframe)
          }
        } catch { /* ignore parse errors */ }
      }
      ws.onclose = () => {
        if (!closed) {
          setWsConnected(false)
          logDebug("WS_DISCONNECTED", { tf: timeframe })
          reconnectTimer = setTimeout(connect, 3000)
        }
      }
      ws.onerror = () => ws?.close()
    }

    connect()

    pingInterval = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN && !closed) {
        ws.send(JSON.stringify({ type: "ping", data: { t: Date.now() } }))
      }
    }, 15000)

    const cleanup = () => {
      closed = true
      clearInterval(pingInterval)
      clearTimeout(reconnectTimer)
      if (ws) {
        ws.onclose = null
        ws.onerror = null
        ws.onmessage = null
        ws.close()
      }
      wsRef.current = null
      setWsConnected(false)
    }
    wsCleanupRef.current = cleanup

    return cleanup
  }, [timeframe, symbol])

  const scores = (analysis?.scores || {}) as Record<string, unknown>
  const triggers = (analysis?.triggers || {}) as Record<string, unknown>
  const tfData = (analysis?.timeframes || {}) as Record<string, unknown>
  const alignment = (analysis?.alignment || {}) as Record<string, unknown>
  const sr = (analysis?.support_resistance || {}) as Record<string, unknown>

  const longProb = numOrZero(scores.long_probability)
  const shortProb = numOrZero(scores.short_probability)
  const confidence = numOrZero(scores.signal_confidence)

  const lastUpdated = parseLastUpdated(analysis?.last_updated || analysis?.timestamp)

  const hasValidAnalysis = analysis !== null && analysisError === null && (numOrZero(scores.overall) > 0 || (scores.status && !String(scores.status).startsWith("NO_DATA")))

  const schemaError = analysis !== null && scores.status === undefined && analysis.scores === undefined
    ? "Backend response schema uyğun deyil"
    : null

  const displayError = analysisError || schemaError || (analysis !== null && scores.overall === 0 && String(scores.status || "").startsWith("NO_DATA") ? "Timeframe məlumatı yoxdur" : null)

  const normalizedAnalysis = useMemo(() => clientNormalize(analysis), [analysis])
  const runBacktest = async () => {
    setBacktestRunning(true)
    try {
      const result = await api.runSkhyBacktest(timeframe, "balanced", 500, symbol)
      setBacktestResult(result)
    } catch {
      setBacktestResult({ error: "Backtest uğursuz oldu" })
    } finally {
      setBacktestRunning(false)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-4 py-1.5 border-b border-gray-800/60 bg-gray-950/90">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-purple-400" />
              <select
                value={symbol}
                onChange={(event) => setSymbol(event.target.value)}
                aria-label="SKHY Intelligence bazarı"
                className="h-7 min-w-32 rounded border border-purple-500/40 bg-gray-900 px-2 text-sm font-bold text-white outline-none hover:border-purple-400"
              >
                {symbols.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
              <span className="text-[10px] text-gray-500 px-1.5 py-0.5 rounded bg-gray-800 border border-gray-700">Binance Futures</span>
            </div>
            {(loading || tfLoading) && <RefreshCw className="w-3 h-3 text-gray-500 animate-spin" />}
            {error && <span className="text-xs text-red-400">{error}</span>}
            {displayError && <span className="text-xs text-yellow-400">{displayError}</span>}
            {diagnostics && (diagnostics.diagnostics as Record<string, unknown>)?.candles_loaded != null && (
              <span className={cn("text-[10px] font-mono",
                (diagnostics.diagnostics as Record<string, unknown>).candles_sufficient ? "text-green-500" : "text-red-500")}>
                {String((diagnostics.diagnostics as Record<string, unknown>).candles_loaded)} candles
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-[11px]">
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-gray-500" />
              <span className="text-gray-400">{lastUpdated ? lastUpdated.toLocaleTimeString() : "--:--:--"}</span>
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
              <SKHYChart symbol={symbol} snapshot={snapshot} analysis={analysis} triggers={triggers} sr={sr}
                activeTimeframe={timeframe} onTimeframeChange={setTimeframe}
                normalizedAnalysis={normalizedAnalysis} />
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
                {!hasValidAnalysis && !loading && !tfLoading && (
                  <span className="text-[10px] text-yellow-500/70 ml-2">
                    {displayError || "Analiz məlumatı gözlənilir..."}
                  </span>
                )}
                {/* Backtest button */}
                <div className="flex-1" />
                <button onClick={runBacktest} disabled={backtestRunning}
                  className="flex items-center gap-1 px-2 py-1 rounded text-[10px] bg-gray-800 hover:bg-gray-700 text-gray-300 disabled:opacity-50">
                  <Play className="w-3 h-3" />
                  {backtestRunning ? "İşləyir..." : "Backtest"}
                </button>
              </div>
            )}
          </div>

          {/* Right Panel */}
          <div className="w-96 border-l border-gray-800/60 flex flex-col overflow-hidden bg-gray-950/30">
            <div className="flex-1 overflow-y-auto">
              <SKHYSignalPlan symbol={symbol} analysis={analysis} normalizedAnalysis={normalizedAnalysis} />
              <SKHYTriggerPanel triggers={triggers} scores={scores} />
              <SKHYAnalysisPanel symbol={symbol} timeframes={tfData} scores={scores} alignment={alignment} sr={sr} analysis={analysis}
                normalizedAnalysis={normalizedAnalysis} />
              <SKHYScenarioPanel scenarios={hasValidAnalysis ? scenarios : null} />
              <SKHYHistoryPanel history={history} />
              {backtestResult && (
                <div className="border-b border-gray-800/60 p-3">
                  <div className="flex items-center gap-1.5 text-[11px] text-cyan-400 font-semibold uppercase tracking-wider mb-2">
                    <Terminal className="w-3 h-3" /> Backtest ({timeframe})
                  </div>
                  {(backtestResult as Record<string, unknown>).error ? (
                    <div className="text-[10px] text-red-400">{String((backtestResult as Record<string, unknown>).error)}</div>
                  ) : (
                    <div className="grid grid-cols-2 gap-1 text-[10px]">
                      {(() => {
                        const bt = backtestResult as Record<string, unknown> | null
                        const r = bt?.results as Record<string, unknown> | undefined
                        if (!r) return null
                        return (
                          <>
                            <MetricBox label="Ticarət sayı" value={String(r.total_trades ?? "—")} />
                            <MetricBox label="Qazanma %" value={String(r.win_rate ?? "—") + "%"} color="text-green-400" />
                            <MetricBox label="Balans dəyişimi" value={String(r.return_pct ?? "—") + "%"} color="text-yellow-400" />
                            <MetricBox label="Profit Factor" value={String(r.profit_factor ?? "—")} color="text-blue-400" />
                          </>
                        )
                      })()}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function MetricBox({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="px-1.5 py-1 rounded bg-gray-800/20 text-center">
      <div className="text-[9px] text-gray-500">{label}</div>
      <div className={cn("text-[10px] font-mono font-bold", color || "text-gray-300")}>{value}</div>
    </div>
  )
}
