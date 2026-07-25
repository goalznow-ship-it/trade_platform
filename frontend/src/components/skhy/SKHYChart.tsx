"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import {
  createChart, ColorType, CandlestickSeries, HistogramSeries, LineSeries,
  type IChartApi, type ISeriesApi, type Time, type LogicalRange,
} from "lightweight-charts"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

interface Props {
  symbol: string
  snapshot: Record<string, unknown> | null
  analysis: Record<string, unknown> | null
  triggers: Record<string, unknown>
  sr: Record<string, unknown>
  activeTimeframe: string
  onTimeframeChange: (tf: string) => void
}

interface Candle { time: number; open: number; high: number; low: number; close: number; volume: number }
interface PathPoint { time_offset: number; price: number; label: string; phase: string; probability?: number; reason?: string }
interface Target { level: string; price: number; type: string; probability: number; time_estimate: string }

function num(v: unknown): number { return typeof v === "number" ? v : 0 }
function str(v: unknown): string { return v == null ? "" : String(v) }

type OverlayKey = "structure"|"channel"|"breakout"|"retest"|"fibonacci"|"targets"|"mainScenario"|"altScenario"|"fakeout"|"smc"|"liquidity"|"ema"|"atrStop"|"volumeProfile"|"elliott"|"triggers"|"patterns"|"cone"

export function SKHYChart({ symbol, snapshot, analysis, triggers, sr, activeTimeframe, onTimeframeChange }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const volSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null)
  const ema20Ref = useRef<ISeriesApi<"Line"> | null>(null)
  const ema50Ref = useRef<ISeriesApi<"Line"> | null>(null)
  const ema100Ref = useRef<ISeriesApi<"Line"> | null>(null)
  const atrStopRef = useRef<ISeriesApi<"Line"> | null>(null)

  const [ohlcv, setOhlcv] = useState<Candle[]>([])
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null)
  const [emaValues, setEmaValues] = useState<{ ema20: number; ema50: number; ema100: number }>({ ema20: 0, ema50: 0, ema100: 0 })
  const [overlays, setOverlays] = useState<Record<OverlayKey, boolean>>({
    structure: true, channel: true, breakout: true, retest: true,
    fibonacci: true, targets: true, mainScenario: true, altScenario: false,
    fakeout: false, smc: true, liquidity: false, ema: false, atrStop: false,
    volumeProfile: false, elliott: false, triggers: true,
    patterns: true, cone: true,
  })
  const timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

  const scores = (analysis?.scores || {}) as Record<string, unknown>
  const tfs = (analysis?.timeframes || {}) as Record<string, unknown>
  const allStructs = analysis?.all_structures as Record<string, unknown>[] | undefined
  const patterns = analysis?.patterns as Record<string, unknown>[] | undefined
  const ew = analysis?.elliott_wave as Record<string, unknown> | undefined
  const fib = analysis?.fibonacci as Record<string, unknown> | undefined
  const ds = analysis?.detected_structure as Record<string, unknown> | undefined
  const cl = analysis?.channel_lines as Record<string, unknown> | undefined
  const bz = analysis?.breakout_zone as Record<string, unknown> | undefined
  const sp = analysis?.scenario_paths as Record<string, unknown> | undefined
  const th = analysis?.target_hierarchy as Record<string, unknown> | undefined
  const cb = analysis?.confidence_breakdown as Record<string, unknown> | undefined
  const supZone = analysis?.support_zone as Record<string, unknown> | undefined
  const resZone = analysis?.resistance_zone as Record<string, unknown> | undefined
  const invalLevel = num(analysis?.invalidation_level)
  const activePatterns = analysis?.active_patterns as Record<string, unknown>[] | undefined
  const patternCompletion = analysis?.pattern_completion as Record<string, number> | undefined
  const patternInvalidation = analysis?.pattern_invalidation as Record<string, unknown> | undefined
  const tradePlan = analysis?.trade_plan as Record<string, unknown> | undefined

  const confidence = num(scores.signal_confidence)
  const longProb = num(scores.long_probability)
  const shortProb = num(scores.short_probability)
  const status = str(scores.status)
  const ltPrice = num(triggers.long_trigger_price)
  const stPrice = num(triggers.short_trigger_price)
  const price = num(snapshot?.live_price)
  const mainSc = sp?.main_scenario as Record<string, unknown> | undefined
  const mainDir = str(mainSc?.direction_az || mainSc?.direction || "")
  const mainProb = num(mainSc?.probability)

  const toggleOverlay = useCallback((key: OverlayKey) => {
    setOverlays(prev => ({ ...prev, [key]: !prev[key] }))
  }, [])

  const drawOverlay = useCallback(() => {
    const canvas = overlayRef.current; const chart = chartRef.current
    if (!canvas || !chart || !ohlcv.length) return
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * window.devicePixelRatio; canvas.height = rect.height * window.devicePixelRatio
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
    ctx.clearRect(0, 0, rect.width, rect.height)
    const ts = chart.timeScale(); const vr = ts.getVisibleLogicalRange()
    if (!vr) return
    const toX = (t: number) => ts.timeToCoordinate(t as Time) ?? 0
    const toY = (p: number) => candleSeriesRef.current?.priceToCoordinate(p) ?? 0
    const w = rect.width; const h = rect.height
    const candleWidth = ohlcv.length >= 2 ? Math.max(1, (toX(ohlcv[ohlcv.length - 1].time) - toX(ohlcv[ohlcv.length - 2].time))) : 8
    const lastCandleX = toX(ohlcv[ohlcv.length - 1].time)
    const lastPrice = ohlcv[ohlcv.length - 1].close
    const toFutureX = (offset: number) => lastCandleX + candleWidth * offset

    if (overlays.volumeProfile) drawVolumeProfile(ctx, toX, toY, ohlcv, w, h)
    if (overlays.channel) drawChannel(ctx, toX, toY, cl, w, ohlcv, ds, lastCandleX, candleWidth, toFutureX)
    if (overlays.breakout) drawBreakoutZone(ctx, toX, toY, bz, w, h, ohlcv, lastCandleX, candleWidth, toFutureX)
    if (overlays.liquidity) drawLiquidityZones(ctx, toX, toY, sr, ds, w, ohlcv)
    if (overlays.fibonacci) drawFibonacciLevels(ctx, toX, toY, fib, w, ohlcv, lastCandleX, candleWidth)
    if (overlays.retest && ds) drawRetestZone(ctx, toX, toY, ds, w, ohlcv, lastCandleX, candleWidth)
    if (overlays.targets) drawInvalLine(ctx, toX, toY, invalLevel, w, lastCandleX, candleWidth)
    if (overlays.targets) drawTargetLines(ctx, toX, toY, th, fib, w, ohlcv, lastCandleX, lastPrice, candleWidth)
    if (overlays.triggers) drawTradeLevels(ctx, toX, toY, triggers, scores, w, lastCandleX, candleWidth, confidence)
    if (overlays.cone && sp) drawProbabilityCone(ctx, toX, toY, sp, ohlcv, lastCandleX, lastPrice, candleWidth, toFutureX)
    if (overlays.mainScenario && sp) drawScenarioPath(ctx, toX, toY, sp, w, h, cb, confidence, ohlcv, "main", lastCandleX, lastPrice, candleWidth, toFutureX)
    if (overlays.altScenario && sp) drawScenarioPath(ctx, toX, toY, sp, w, h, cb, confidence, ohlcv, "alt", lastCandleX, lastPrice, candleWidth, toFutureX)
    if (overlays.fakeout && sp) drawScenarioPath(ctx, toX, toY, sp, w, h, cb, confidence, ohlcv, "fakeout", lastCandleX, lastPrice, candleWidth, toFutureX)
    if (overlays.smc) drawSMCStructures(ctx, toX, toY, analysis, ohlcv, w)
    if (overlays.elliott) drawElliottWave(ctx, toX, toY, ew, w, ohlcv, confidence)
    if (overlays.structure) {
      drawSR(ctx, toX, toY, sr, price, w)
      drawSupportResistanceZones(ctx, toX, toY, supZone, resZone, w, h, ohlcv)
    }
    if (overlays.patterns) drawPatterns(ctx, toX, toY, activePatterns || patterns, ohlcv, w)
    drawSmartMoney(ctx, toX, toY, analysis, ohlcv)
    drawLegend(ctx, w, h, overlays, activePatterns || (patterns as Record<string, unknown>[] | undefined), mainSc, confidence)
  }, [ohlcv, analysis, triggers, scores, sr, patterns, confidence, price, ew, fib, ds, cl, bz, sp, th, cb, supZone, resZone, invalLevel, overlays, tradePlan, activePatterns, mainSc])

  useEffect(() => {
    api.getSkhyOHLCV(activeTimeframe, 240).then((res) => {
      if (res?.data) {
        setOhlcv(res.data);
        const closes = (res.data as Candle[]).map((d: Candle) => d.close)
        if (closes.length >= 100) {
          setEmaValues({
            ema20: calcLastEMA(closes, 20),
            ema50: calcLastEMA(closes, 50),
            ema100: calcLastEMA(closes, 100),
          })
        }
      }
    }).catch(() => {})
  }, [activeTimeframe])

  useEffect(() => {
    if (!containerRef.current) return
    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: "#0d1117" }, textColor: "#6b7280", fontSize: 11 },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#374151", scaleMargins: { top: 0.05, bottom: 0.25 } },
      timeScale: { borderColor: "#374151", timeVisible: true, secondsVisible: false, fixRightEdge: false, shiftVisibleRangeOnNewBar: false },
      autoSize: true,
      handleScroll: { vertTouchDrag: false },
    })
    chartRef.current = chart
    candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e", downColor: "#ef4444", borderDownColor: "#ef4444", borderUpColor: "#22c55e", wickDownColor: "#ef4444", wickUpColor: "#22c55e",
    })
    volSeriesRef.current = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "volume" })
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.88, bottom: 0 } })
    ema20Ref.current = chart.addSeries(LineSeries, { color: "#f59e0b", lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
    ema50Ref.current = chart.addSeries(LineSeries, { color: "#3b82f6", lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
    ema100Ref.current = chart.addSeries(LineSeries, { color: "#8b5cf6", lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
    atrStopRef.current = chart.addSeries(LineSeries, { color: "#f97316", lineWidth: 1, lineStyle: 3, priceLineVisible: false, lastValueVisible: false })
    return () => { chart.remove() }
  }, [])

  useEffect(() => {
    if (!candleSeriesRef.current || !volSeriesRef.current || !ohlcv.length) return
    const candleData = ohlcv.map((d) => ({ time: d.time as Time, open: d.open, high: d.high, low: d.low, close: d.close }))
    const volData = ohlcv.map((d) => ({ time: d.time as Time, value: d.volume, color: d.close >= d.open ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)" }))
    candleSeriesRef.current.setData(candleData)
    volSeriesRef.current.setData(volData)
    if (overlays.ema) {
      const closes = ohlcv.map((d) => d.close)
      const ema20 = calcEMA(closes, 20); const ema50 = calcEMA(closes, 50); const ema100 = calcEMA(closes, 100)
      ema20Ref.current?.setData(ema20.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter(d => d.value > 0))
      ema50Ref.current?.setData(ema50.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter(d => d.value > 0))
      ema100Ref.current?.setData(ema100.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter(d => d.value > 0))
    } else {
      ema20Ref.current?.setData([]); ema50Ref.current?.setData([]); ema100Ref.current?.setData([])
    }
    if (overlays.atrStop) {
      const atrStopData = calcATRStop(ohlcv, 14, 2.5)
      atrStopRef.current?.setData(atrStopData.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter(d => d.value > 0))
    } else {
      atrStopRef.current?.setData([])
    }
    const chart = chartRef.current
    if (chart) {
      chart.timeScale().fitContent()
      const vr = chart.timeScale().getVisibleLogicalRange()
      if (vr) {
        chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, ohlcv.length - 60), to: ohlcv.length + 50 })
      }
    }
    drawOverlay()
  }, [ohlcv, overlays])

  useEffect(() => { drawOverlay() }, [drawOverlay])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const canvas = overlayRef.current; const chart = chartRef.current
    if (!canvas || !chart) { setTooltip(null); return }
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left; const y = e.clientY - rect.top
    const t = chart.timeScale().coordinateToTime(x) as number | null; const pr = candleSeriesRef.current?.coordinateToPrice(y)
    if (t == null || pr == null) { setTooltip(null); return }
    const txt = findNearestAll(t as number, pr, ohlcv, allStructs, patterns, ds, bz, th, cl, sp, ew, fib)
    if (txt) setTooltip({ x: e.clientX - rect.left + 10, y: e.clientY - rect.top - 10, text: txt })
    else setTooltip(null)
  }, [allStructs, patterns, ds, bz, th, cl, sp, ew, fib, ohlcv])
  const handleMouseLeave = () => setTooltip(null)

  const statusLabel: Record<string, string> = { STRONG_TRADE_READY: "GÜCLÜ HAZIR", TRADE_READY: "HAZIRDIR", WATCHLIST: "İZLƏMƏ", WAIT: "GÖZLƏYİN" }
  const confTier = confidence >= 80 ? 4 : confidence >= 70 ? 3 : confidence >= 50 ? 2 : 1

  const toggleItems: { key: OverlayKey; label: string }[] = [
    { key: "structure", label: "Struktur" },
    { key: "channel", label: "Kanal" },
    { key: "breakout", label: "Breakout" },
    { key: "fibonacci", label: "Fibonacci" },
    { key: "targets", label: "Hədəflər" },
    { key: "triggers", label: "Trigger" },
    { key: "mainScenario", label: "Əsas" },
    { key: "altScenario", label: "Alternativ" },
    { key: "fakeout", label: "Fakeout" },
    { key: "smc", label: "SMC" },
    { key: "liquidity", label: "Likvidlik" },
    { key: "ema", label: "EMA" },
    { key: "atrStop", label: "ATR" },
    { key: "volumeProfile", label: "Həcm" },
    { key: "elliott", label: "Elliott" },
    { key: "patterns" as OverlayKey, label: "Patternlər" },
    { key: "cone" as OverlayKey, label: "Konus" },
  ]

  return (
    <div className="h-full flex flex-col relative">
      <div className="flex items-center px-2 py-0.5 border-b border-gray-800/40 bg-gray-950/60 z-10 shrink-0">
        {timeframes.map((t) => {
          const sig = str((tfs[t] as Record<string, unknown>)?.signal)
          const sigColor = sig.includes("LONG") ? "text-green-400 bg-green-500/10" : sig.includes("SHORT") ? "text-red-400 bg-red-500/10" : "text-gray-500 bg-gray-800/30"
          return (
            <button key={t} onClick={() => onTimeframeChange(t)}
              className={cn("flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] font-mono rounded transition-colors mr-0.5", activeTimeframe === t ? "bg-blue-600/20 border border-blue-500/30" : "hover:bg-gray-800/30")}>
              <span className="text-gray-500">{t}</span>
              {sig && <span className={cn("px-0.5 rounded text-[8px] font-bold", sigColor)}>{sig.includes("LONG") ? "↑" : sig.includes("SHORT") ? "↓" : "−"}</span>}
            </button>
          )
        })}
        <div className="flex-1" />
        <div className="flex items-center gap-0.5 overflow-x-auto max-w-[280px] mr-1">
          {toggleItems.map(({ key, label }) => (
            <button key={key} onClick={() => toggleOverlay(key)}
              className={cn("px-1 py-0.5 text-[7px] font-mono rounded border transition-colors shrink-0",
                overlays[key] ? "bg-blue-600/20 border-blue-500/40 text-blue-400" : "bg-gray-800/30 border-gray-700/30 text-gray-600 hover:text-gray-400")}>
              {label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1.5 px-2">
          <span className="text-[9px] text-gray-500">AI</span>
          <div className="w-16 h-1.5 rounded-full bg-gray-800 overflow-hidden">
            <div className={cn("h-full rounded-full transition-all duration-500", confTier >= 3 ? "bg-green-500" : confTier >= 2 ? "bg-yellow-500" : "bg-red-500")} style={{ width: `${Math.min(confidence, 100)}%` }} />
          </div>
          <span className={cn("text-[10px] font-bold font-mono", confTier >= 3 ? "text-green-400" : confTier >= 2 ? "text-yellow-400" : "text-gray-500")}>{confidence}%</span>
          <span className={cn("text-[8px] px-1 py-0.5 rounded font-semibold",
            confTier >= 4 ? "bg-green-500/20 text-green-400" : confTier >= 3 ? "bg-blue-500/20 text-blue-400" : confTier >= 2 ? "bg-yellow-500/20 text-yellow-400" : "bg-gray-500/20 text-gray-400")}>
            {confTier >= 4 ? "GÜCLÜ HAZIR" : confTier >= 3 ? "HAZIRDIR" : confTier >= 2 ? "İZLƏMƏ" : "GÖZLƏYİN"}</span>
            {tradePlan?.trade_ready ? <span className="text-[8px] px-1 py-0.5 rounded font-semibold bg-green-500/20 text-green-400 border border-green-500/30">TP HAZIR</span> : null}
        </div>
        <span className="text-[9px] text-gray-600 font-mono mr-1">{symbol}</span>
      </div>
      <div className="relative flex-1" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
        <div ref={containerRef} className="absolute inset-0" />
        {price > 0 && (
          <>
            <div className="absolute top-2 left-2 z-[6] flex flex-wrap gap-x-2 gap-y-0.5 text-[9px] pointer-events-none max-w-[65%]">
              {ds && str(ds.label_az) && (
                <span className="px-1.5 py-0.5 rounded bg-gray-900/80 border border-gray-700/50 text-gray-300 font-mono text-[8px]">{str(ds.label_az)} {str(ds.breakout_status) ? `· ${str(ds.breakout_status)}` : ""}</span>
              )}
              <div className={cn("px-1.5 py-0.5 rounded font-bold font-mono", longProb > shortProb ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400")}>
                {longProb > shortProb ? `↑ ALIŞ ${longProb}%` : `↓ SATIŞ ${shortProb}%`}
              </div>
              {ltPrice > 0 && <span className="px-1.5 py-0.5 rounded bg-green-900/30 border border-green-700/30 text-green-400 font-mono">L↑ ${ltPrice.toFixed(2)}</span>}
              {stPrice > 0 && <span className="px-1.5 py-0.5 rounded bg-red-900/30 border border-red-700/30 text-red-400 font-mono">S↓ ${stPrice.toFixed(2)}</span>}
              {invalLevel > 0 && <span className="px-1.5 py-0.5 rounded bg-purple-900/30 border border-purple-700/30 text-purple-400 font-mono">Ləğv ${invalLevel.toFixed(2)}</span>}
              {mainDir && <span className="px-1.5 py-0.5 rounded bg-yellow-900/30 border border-yellow-700/30 text-yellow-400 font-mono">{mainDir} {mainProb}%</span>}
              <span className="px-1.5 py-0.5 rounded bg-gray-900/50 text-gray-500 font-mono">${price.toFixed(2)}</span>
            </div>
            {overlays.ema && emaValues.ema20 > 0 && (
              <div className="absolute top-2 right-2 z-[6] flex flex-col gap-0.5 text-[8px] font-mono pointer-events-none">
                {emaValues.ema20 > 0 && <span className="text-[10px] text-yellow-500/60">EMA20 ${emaValues.ema20.toFixed(2)}</span>}
                {emaValues.ema50 > 0 && <span className="text-[10px] text-blue-400/60">EMA50 ${emaValues.ema50.toFixed(2)}</span>}
                {emaValues.ema100 > 0 && <span className="text-[10px] text-purple-400/60">EMA100 ${emaValues.ema100.toFixed(2)}</span>}
              </div>
            )}
          </>
        )}
        <canvas ref={overlayRef} className="absolute inset-0 pointer-events-none z-[5]" />
        {tooltip && (
          <div className="absolute z-10 pointer-events-none bg-gray-900/95 border border-gray-700 rounded px-2 py-1 text-[9px] text-gray-200 shadow-xl max-w-[260px] whitespace-pre-line" style={{ left: tooltip.x, top: tooltip.y }}>
            {tooltip.text}
          </div>
        )}
        {status === "WAIT" && confidence < 70 && (
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[6] text-center pointer-events-none">
            <div className="text-[11px] font-bold text-yellow-500 mb-0.5">⏳ GÖZLƏYİN</div>
            <div className="text-[8px] text-gray-500">{confidence > 0 ? `İnam ${confidence}% · Siqnal etibarı aşağı` : "Məlumat hazırlanır..."}</div>
            {ltPrice > 0 && <div className="text-[8px] text-green-400/70">LONG üçün bu səviyyəni gözlə: ${ltPrice.toFixed(2)}</div>}
            {stPrice > 0 && <div className="text-[8px] text-red-400/70">SHORT üçün bu səviyyəni gözlə: ${stPrice.toFixed(2)}</div>}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Helpers ───
function calcEMA(data: number[], period: number): number[] {
  if (data.length < period) return data.map(() => 0)
  const k = 2 / (period + 1); const r: number[] = []; let ema = data.slice(0, period).reduce((a, b) => a + b, 0) / period
  r.push(ema); for (let i = period; i < data.length; i++) { ema = (data[i] - ema) * k + ema; r.push(ema) }
  return [...new Array(period - 1).fill(0), ...r]
}
function calcLastEMA(data: number[], period: number): number {
  if (data.length < period) return 0
  const emaFull = calcEMA(data, period)
  return emaFull[emaFull.length - 1] || 0
}
function calcATRStop(data: Candle[], period: number, mult: number): number[] {
  if (data.length < period + 1) return data.map(() => 0)
  const tr: number[] = []
  for (let i = 1; i < data.length; i++) tr.push(Math.max(data[i].high - data[i].low, Math.abs(data[i].high - data[i - 1].close), Math.abs(data[i].low - data[i - 1].close)))
  let atr = tr.slice(0, period).reduce((a, b) => a + b, 0) / period; const atrs: number[] = [atr]
  for (let i = period; i < tr.length; i++) { atr = (atr * (period - 1) + tr[i]) / period; atrs.push(atr) }
  const pad = new Array(period).fill(0); return [...pad, ...atrs.map((a, i) => Math.round((data[i + period].close - a * mult) * 100) / 100)]
}
function p2str(v: unknown): string { return v == null ? "" : String(v) }
function n2(v: unknown): number { return typeof v === "number" ? v : 0 }

function findNearestAll(
  _time: number, price: number,
  ohlcv: Candle[], allStructs: Record<string, unknown>[] | undefined,
  _patterns: Record<string, unknown>[] | undefined,
  ds: Record<string, unknown> | undefined, bz: Record<string, unknown> | undefined,
  th: Record<string, unknown> | undefined, cl: Record<string, unknown> | undefined,
  sp: Record<string, unknown> | undefined,
  ew: Record<string, unknown> | undefined,
  fib: Record<string, unknown> | undefined,
): string | null {
  if (allStructs) {
    for (const s of allStructs.slice(-20)) {
      const sp2 = n2(s.price) || n2(s.gap_high) || 0
      if (sp2 > 0 && Math.abs(sp2 - price) / price < 0.03) {
        const cat = p2str(s.category); const typ = p2str(s.type)
        if (cat === "bos") return `BOS (Struktur dəyişikliyi)\nBazar ${typ.includes("bullish") ? "yuxarı" : "aşağı"} istiqamətə keçir.\nTəsdiq: Yeni HH/HL formalaşması.\nLəğv: Qiymət geri dönərsə.`
        if (cat === "choch") return `CHoCH (Xarakter dəyişikliyi)\nTrend ${typ.includes("bullish") ? "yüksələn" : "enən"} ola bilər. Smart money yeni istiqamət hazırlayır.\nTəsdiq: BOS ilə təsdiqlənməlidir.\nLəğv: Qiymət köhnə trendə qayıtsa.`
        if (cat === "fvg") return `FVG (Qiymət boşluğu)\n${typ.includes("bullish") ? "Yuxarı" : "Aşağı"} likvidite çəkə bilər.\nTəsdiq: Qiymət boşluğa toxunarsa.\nLəğv: Boşluq doldurulmadan keçib gedərsə.`
        if (cat === "order_block") return `OB (Order Block)\nSmart money ${typ.includes("bullish") ? "alış" : "satış"} əmri buraxıb.\nTəsdiq: OB-dən reaksiya (yuxarı/aşağı).\nLəğv: OB dəliklənərsə (gap olarsa).\nMənbə: ${p2str(s.timeframe)}.`
        if (cat === "liquidity") return `Likvidite zonası\n${typ.includes("above") ? "Yuxarıda" : "Aşağıda"} stop-loss toplanıb. Hədəf zona.\nMənbə: ${p2str(s.timeframe)}.`
        if (cat === "swing") return `Swing ${typ === "high" ? "Zirvə" : "Dip"}\nÖnəmli dönüş nöqtəsi.\nTarix: ${new Date(ohlcv[Math.min(n2(s.index)||0, ohlcv.length-1)]?.time * 1000).toLocaleDateString('az')}`
        if (cat === "breaker") return `Breaker Block\n${typ.includes("bullish") ? "Yuxarı" : "Aşağı"} istiqamətdə etibarsız əvvəlki OB.\nTəsdiq: Qiymət bu zonadan reaksiya versə.\nLəğv: Zona dəliklənərsə.`
        if (cat === "equal_high" || cat === "equal_low") return `Bərabər ${cat === "equal_high" ? "Zirvə" : "Dip"} (EQ${cat === "equal_high" ? "H" : "L"})\nLikvidlik ovu üçün hədəf zona.\nQiymət: $${sp2.toFixed(2)}`
        if (cat === "liquidity_sweep") return `Likvidlik ovu\nQiymət ${typ.includes("above") ? "yuxarı" : "aşağı"} likviditeni ovlayıb geri qayıtdı.\nTəsdiq: Sürətli geri dönüş.\nLəğv: Ovlanmış səviyyədən aşağı/qalıq.`
      }
    }
  }
  if (ds && n2(ds.channel_top) > 0 && Math.abs(n2(ds.channel_top) - price) / price < 0.02)
    return `Kanal üst xətti: $${n2(ds.channel_top).toFixed(2)}\n${p2str(ds.label_az)} - ${p2str(ds.breakout_status)}\nBaşlanğıc swing: ${n2(ds.swing_start_price) ? "$"+n2(ds.swing_start_price).toFixed(2) : "N/A"}`
  if (ds && n2(ds.channel_bottom) > 0 && Math.abs(n2(ds.channel_bottom) - price) / price < 0.02)
    return `Kanal alt xətti: $${n2(ds.channel_bottom).toFixed(2)}\n${p2str(ds.label_az)}\nSon swing: ${n2(ds.swing_end_price) ? "$"+n2(ds.swing_end_price).toFixed(2) : "N/A"}`
  if (bz && n2(bz.zone_top) > 0 && Math.abs(n2(bz.zone_top) - price) / price < 0.02)
    return `Breakout zonası üst: $${n2(bz.zone_top).toFixed(2)}\nTest sayı: ${n2(bz.test_count)}\n${n2(bz.bullish_breakout_ready) ? "✓ LONG breakout hazırdır. Qiymət yuxarı getsə təsdiqlənər." : ""} ${n2(bz.bearish_breakout_ready) ? "✓ SHORT breakout hazırdır. Qiymət aşağı getsə təsdiqlənər." : ""}\nLəğv: Qiymət zona içində qalarsa.`
  if (bz && n2(bz.zone_bottom) > 0 && Math.abs(n2(bz.zone_bottom) - price) / price < 0.02)
    return `Breakout zonası alt: $${n2(bz.zone_bottom).toFixed(2)}\nTest sayı: ${n2(bz.test_count)}\nFakeout riski: Qiymət zonadan keçib geri qayıda bilər.`
  if (th) {
    const tgs = th.targets as Target[] | undefined
    if (tgs) for (const t of tgs) {
      if (Math.abs(n2(t.price) - price) / price < 0.02)
        return `${t.level} ${t.type}\nQiymət: $${n2(t.price).toFixed(2)}\nEhtimal: ${n2(t.probability)}%\nMüddət: ${p2str(t.time_estimate)}\nTip: ${t.level.includes("SR") ? "Dəstək/Müqavimət" : t.level.includes("Kanal") ? "Kanal hədəfi" : t.level.includes("TP") ? "Mənfəət hədəfi" : "Fib səviyyəsi"}`
    }
  }
  if (sp) {
    for (const key of ["main_scenario", "alternative_scenario", "fakeout_scenario"]) {
      const sc = sp[key] as Record<string, unknown> | undefined
      const pts = sc?.path_points as PathPoint[] | undefined
      if (pts && sc) for (const p of pts) {
        if (p.time_offset > 0 && Math.abs(n2(p.price) - price) / price < 0.03)
          return `${p.label}\nQiymət: $${n2(p.price).toFixed(2)}\n${p2str(sc.direction_az)} ssenari\nEhtimal: ${n2(sc.probability)}%\nİnam: ${n2(sc.confidence)}%\nMərhələ: ${p2str(p.phase)}`
      }
    }
  }
  if (ew && ew.status === "calculated") {
    const waves = ew.waves as { type: string; start: number; end: number; index: number; label?: string }[] | undefined
    if (waves) for (const w of waves) {
      const idx = w.index; if (idx <= 0 || idx >= ohlcv.length) continue
      const wPrice = w.type === "wave_up" ? w.end : w.start
      if (Math.abs(wPrice - price) / price < 0.02)
        return `Elliott Dalğası ${w.label || ""}\nTip: ${w.type === "wave_up" ? "Yüksələn" : "Enən"}\nCari dalğa: ${w.label || "N/A"}\nNövbəti: ${w.label === "5" ? "A-B-C korreksiyası" : w.label === "C" ? "Yeni tsikl" : ""}`
    }
  }
  if (fib && fib.status === "calculated") {
    const levels = fib.retracement_levels as Record<string, number> | undefined
    if (levels) for (const [k, v] of Object.entries(levels)) {
      if (Math.abs(v - price) / price < 0.02)
        return `Fib ${(Number(k)*100).toFixed(1)}%\nQiymət: $${v.toFixed(2)}\nSwing yüksək: ${n2(fib.swing_high) ? "$"+n2(fib.swing_high).toFixed(2) : "N/A"}\nSwing aşağı: ${n2(fib.swing_low) ? "$"+n2(fib.swing_low).toFixed(2) : "N/A"}\nQızıl zona: 61.8-70.5% arası`
    }
  }
  return null
}

// ─── DRAWING FUNCTIONS ───

function drawChannel(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, cl: Record<string, unknown> | undefined, w: number, ohlcv: Candle[], ds: Record<string, unknown> | undefined, lastCandleX: number, candleWidth: number, toFutureX: (offset: number) => number) {
  if (!cl || cl.status !== "calculated" || !ohlcv.length) return
  const upper = cl.upper as { time: number; value: number }[] | undefined
  const lower = cl.lower as { time: number; value: number }[] | undefined
  const mid = cl.mid as { time: number; value: number }[] | undefined
  if (!upper || !lower || upper.length < 2) return

  const drawLine = (pts: { time: number; value: number }[], color: string, dash: number[] = []) => {
    if (pts.length < 2) return
    ctx.strokeStyle = color; ctx.lineWidth = 1; ctx.setLineDash(dash)
    ctx.beginPath()
    let started = false
    for (const p of pts) { const x = toX(p.time); const y = toY(p.value); if (x <= 0 || y <= 0) continue; if (!started) { ctx.moveTo(x, y); started = true } else ctx.lineTo(x, y) }
    ctx.stroke(); ctx.setLineDash([])
  }

  drawLine(upper, "rgba(168,85,247,0.65)", [4, 4])
  drawLine(lower, "rgba(168,85,247,0.65)", [4, 4])
  if (mid) drawLine(mid, "rgba(168,85,247,0.25)", [2, 6])

  const lu = upper[upper.length - 1]; const xu = toX(lu.time); const yu = toY(lu.value)
  if (xu > 0 && yu > 0) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.8)"; ctx.fillText(`Üst: $${lu.value.toFixed(2)}`, Math.max(xu, lastCandleX) + 3, yu - 2) }
  const ll = lower[lower.length - 1]; const xll = toX(ll.time); const yll = toY(ll.value)
  if (xll > 0 && yll > 0) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.8)"; ctx.fillText(`Alt: $${ll.value.toFixed(2)}`, Math.max(xll, lastCandleX) + 3, yll + 10) }

  if (ds) {
    const label = p2str(ds.label_az)
    const bs = p2str(ds.breakout_status)
    const sx = toFutureX(1)
    ctx.font = "bold 8px monospace"; ctx.fillStyle = "rgba(168,85,247,0.9)"
    ctx.fillText(`📊 ${label}`, sx, 20)
    if (bs) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.6)"; ctx.fillText(`Status: ${bs}`, sx, 32) }
    const accum = !!ds.accumulation_zone; const distrib = !!ds.distribution_zone
    if (accum || distrib) {
      ctx.fillText(accum && distrib ? "Yığım + Paylanma zonası" : accum ? "Yığım zonası" : "Paylanma zonası", sx, 44)
    }
  }
}

function drawBreakoutZone(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, bz: Record<string, unknown> | undefined, w: number, h: number, ohlcv: Candle[], lastCandleX: number, candleWidth: number, toFutureX: (offset: number) => number) {
  if (!bz || bz.status !== "calculated" || !ohlcv.length) return
  const zoneTop = n2(bz.zone_top); const zoneBottom = n2(bz.zone_bottom)
  if (zoneTop <= 0 || zoneBottom <= 0) return
  const yTop = toY(zoneTop); const yBottom = toY(zoneBottom)
  if (yTop <= 0 || yBottom <= 0) return
  const midY = (yTop + yBottom) / 2

  ctx.fillStyle = "rgba(168,85,247,0.1)"
  ctx.fillRect(0, Math.min(yTop, yBottom), w, Math.abs(yTop - yBottom))
  ctx.strokeStyle = "rgba(168,85,247,0.35)"; ctx.lineWidth = 0.5; ctx.setLineDash([3, 3])
  ctx.strokeRect(0, Math.min(yTop, yBottom), w, Math.abs(yTop - yBottom)); ctx.setLineDash([])

  const isBullishReady = !!bz.bullish_breakout_ready
  const isBearishReady = !!bz.bearish_breakout_ready
  const testCount = n2(bz.test_count)
  const sx = lastCandleX + candleWidth * 2

  ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.8)"
  ctx.fillText(`BO Üst $${zoneTop.toFixed(2)}`, sx, yTop - 2)
  ctx.fillText(`BO Alt $${zoneBottom.toFixed(2)}`, sx, yBottom + 10)
  if (testCount > 0) { ctx.font = "6px monospace"; ctx.fillStyle = "rgba(168,85,247,0.5)"; ctx.fillText(`${testCount}x test`, sx, midY + 10) }
  if (isBullishReady) { ctx.font = "6px monospace"; ctx.fillStyle = "rgba(34,197,94,0.6)"; ctx.fillText("✓ Breakout LONG hazır", sx, midY - 6) }
  if (isBearishReady) { ctx.font = "6px monospace"; ctx.fillStyle = "rgba(239,68,68,0.6)"; ctx.fillText("✓ Breakout SHORT hazır", sx, midY - 6) }
  ctx.font = "6px monospace"; ctx.fillStyle = "rgba(245,158,11,0.4)"; ctx.fillText("⚠ Fakeout riski: zonadan keçib geri qayıda bilər", sx, midY + 24)
}

function drawRetestZone(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, ds: Record<string, unknown> | undefined, w: number, ohlcv: Candle[], lastCandleX: number, candleWidth: number) {
  if (!ds) return
  const top = n2(ds.channel_top); const bot = n2(ds.channel_bottom)
  if (top <= 0 || bot <= 0) return
  const yT = toY(top); const yB = toY(bot)
  if (yT <= 0 || yB <= 0) return
  const sx = lastCandleX + candleWidth
  ctx.fillStyle = "rgba(59,130,246,0.06)"; ctx.fillRect(sx - 15, yT, 30, yB - yT)
  ctx.strokeStyle = "rgba(59,130,246,0.25)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 4])
  ctx.strokeRect(sx - 15, yT, 30, yB - yT); ctx.setLineDash([])
  ctx.font = "6px monospace"; ctx.fillStyle = "rgba(59,130,246,0.5)"; ctx.fillText("Retest", sx - 12, yT - 2)
  ctx.fillText("gözlənilir", sx - 12, yB + 10)
}

function drawLiquidityZones(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, sr: Record<string, unknown>, ds: Record<string, unknown> | undefined, w: number, ohlcv: Candle[]) {
  const liqAbove = sr.liquidity_above as { price: number; strength: number }[] | undefined
  const liqBelow = sr.liquidity_below as { price: number; strength: number }[] | undefined
  const take = 3
  const allAbove = (liqAbove || []).slice(-take)
  const allBelow = (liqBelow || []).slice(-take)
  for (const l of allAbove) { const y = toY(l.price); if (y <= 0) continue; ctx.strokeStyle = "rgba(239,68,68,0.2)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 6]); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([]); ctx.font = "6px monospace"; ctx.fillStyle = "rgba(239,68,68,0.35)"; ctx.fillText(`Likvidite $${l.price.toFixed(2)}`, 2, y - 2) }
  for (const l of allBelow) { const y = toY(l.price); if (y <= 0) continue; ctx.strokeStyle = "rgba(34,197,94,0.2)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 6]); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([]); ctx.font = "6px monospace"; ctx.fillStyle = "rgba(34,197,94,0.35)"; ctx.fillText(`Likvidite $${l.price.toFixed(2)}`, 2, y - 2) }
}

function drawInvalLine(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, invalLevel: number, w: number, lastCandleX: number, candleWidth: number) {
  if (invalLevel <= 0) return
  const y = toY(invalLevel); if (y <= 0) return
  ctx.strokeStyle = "rgba(239,68,68,0.5)"; ctx.lineWidth = 1; ctx.setLineDash([4, 4])
  ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
  ctx.font = "7px monospace"; ctx.fillStyle = "rgba(239,68,68,0.7)"; ctx.fillText(`Ləğv $${invalLevel.toFixed(2)}`, lastCandleX + candleWidth * 2, y - 2)
}

function drawFibonacciLevels(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, fib: Record<string, unknown> | undefined, w: number, ohlcv: Candle[], lastCandleX: number, candleWidth: number) {
  if (!fib || fib.status !== "calculated" || !ohlcv.length) return
  const levels = fib.retracement_levels as Record<string, number> | undefined
  if (!levels) return
  const keyLevels = ["0", "0.236", "0.382", "0.5", "0.618", "0.705", "0.786", "1"]
  const colors: Record<string, string> = {
    "0": "rgba(255,255,255,0.1)", "0.236": "rgba(34,197,94,0.2)", "0.382": "rgba(34,197,94,0.25)",
    "0.5": "rgba(245,158,11,0.25)", "0.618": "rgba(34,197,94,0.3)", "0.705": "rgba(245,158,11,0.2)", "0.786": "rgba(239,68,68,0.25)", "1": "rgba(255,255,255,0.1)"
  }
  const labels: Record<string, string> = { "0": "0%", "0.236": "23.6%", "0.382": "38.2%", "0.5": "50%", "0.618": "61.8%", "0.705": "70.5%", "0.786": "78.6%", "1": "100%" }

  const goldenTop = n2(levels["0.618"]); const goldenBot = n2(levels["0.786"])
  if (goldenTop > 0 && goldenBot > 0) {
    const yGt = toY(goldenTop); const yGb = toY(goldenBot)
    if (yGt > 0 && yGb > 0) {
      ctx.fillStyle = "rgba(245,158,11,0.05)"; ctx.fillRect(0, Math.min(yGt, yGb), w, Math.abs(yGt - yGb))
      ctx.strokeStyle = "rgba(245,158,11,0.15)"; ctx.lineWidth = 0.5; ctx.strokeRect(0, Math.min(yGt, yGb), w, Math.abs(yGt - yGb))
      ctx.font = "6px monospace"; ctx.fillStyle = "rgba(245,158,11,0.35)"; ctx.fillText("Qızıl zona", lastCandleX + candleWidth * 2, (yGt + yGb) / 2)
    }
  }

  for (const k of keyLevels) {
    const p = levels[k]; if (!p) continue
    const y = toY(p); if (y <= 0) continue
    ctx.strokeStyle = colors[k] || "rgba(255,255,255,0.1)"; ctx.lineWidth = 0.5
    ctx.setLineDash(k === "0.5" ? [4, 4] : [2, 4])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = colors[k] || "rgba(255,255,255,0.2)"
    ctx.fillText(`Fib ${labels[k]} $${p.toFixed(2)}`, w - 105, y - 2)
  }

  const extUp = fib.extension_up as Record<string, number> | undefined
  if (extUp) { for (const [k, v] of Object.entries(extUp)) { const y = toY(v); if (y <= 0) continue; ctx.strokeStyle = "rgba(34,197,94,0.15)"; ctx.lineWidth = 0.5; ctx.setLineDash([1, 6]); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([]); ctx.font = "6px monospace"; ctx.fillStyle = "rgba(34,197,94,0.35)"; ctx.fillText(`Ext ${k} $${v.toFixed(2)}`, w - 105, y - 2) } }
  const extDn = fib.extension_down as Record<string, number> | undefined
  if (extDn) { for (const [k, v] of Object.entries(extDn)) { const y = toY(v); if (y <= 0) continue; ctx.strokeStyle = "rgba(239,68,68,0.15)"; ctx.lineWidth = 0.5; ctx.setLineDash([1, 6]); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([]); ctx.font = "6px monospace"; ctx.fillStyle = "rgba(239,68,68,0.35)"; ctx.fillText(`Ext ${k} $${v.toFixed(2)}`, w - 105, y - 2) } }

  const swingHigh = n2(fib.swing_high); const swingLow = n2(fib.swing_low)
  if (swingHigh > 0) { const y = toY(swingHigh); if (y > 0) { ctx.beginPath(); ctx.arc(0, y, 3, 0, Math.PI * 2); ctx.fillStyle = "rgba(255,255,255,0.2)"; ctx.fill(); ctx.font = "6px monospace"; ctx.fillStyle = "rgba(255,255,255,0.15)"; ctx.fillText(`SH $${swingHigh.toFixed(2)}`, 2, y - 4) } }
  if (swingLow > 0) { const y = toY(swingLow); if (y > 0) { ctx.beginPath(); ctx.arc(0, y, 3, 0, Math.PI * 2); ctx.fillStyle = "rgba(255,255,255,0.2)"; ctx.fill(); ctx.font = "6px monospace"; ctx.fillStyle = "rgba(255,255,255,0.15)"; ctx.fillText(`SL $${swingLow.toFixed(2)}`, 2, y - 4) } }
}

function getTPLevels(th: Record<string, unknown> | undefined, fib: Record<string, unknown> | undefined, lastPrice: number, isLong: boolean): { level: string; price: number; prob: number; distPct: number }[] {
  const result: { level: string; price: number; prob: number; distPct: number }[] = []
  const usedPrices = new Set<number>()

  // Collect from target_hierarchy
  if (th) {
    const targets = (th.targets as Target[] | undefined) || []
    for (const t of targets) {
      if (t.price <= 0 || usedPrices.has(t.price)) continue
      const isTargetLong = t.price >= lastPrice
      if (isTargetLong !== isLong) continue
      const match = t.level.match(/^TP(\d)$/)
      if (match || t.level.includes("TP")) {
        usedPrices.add(t.price)
        result.push({ level: t.level, price: t.price, prob: t.probability || 50, distPct: Math.abs(t.price - lastPrice) / lastPrice * 100 })
      }
    }
  }

  // Collect from fib extensions
  if (fib) {
    const extKey = isLong ? "extension_up" : "extension_down"
    const extData = fib[extKey] as Record<string, number> | undefined
    if (extData) {
      const extLevels = isLong
        ? [["1.272", "TP1"], ["1.618", "TP2"], ["2.618", "TP3"], ["3.618", "TP4"]]
        : [["1.272", "TP1"], ["1.618", "TP2"], ["2.618", "TP3"], ["3.618", "TP4"]]
      for (const [key, label] of extLevels) {
        const price = extData[key]
        if (price && price > 0 && !usedPrices.has(price)) {
          const isTargetLong = price >= lastPrice
          if (isTargetLong === isLong) {
            usedPrices.add(price)
            const prob = key === "1.272" ? 75 : key === "1.618" ? 60 : key === "2.618" ? 40 : 25
            result.push({ level: label, price, prob, distPct: Math.abs(price - lastPrice) / lastPrice * 100 })
          }
        }
      }
    }
  }

  // Deduplicate + sort by distance
  const seen = new Set<string>()
  const deduped = result.filter(r => {
    const k = r.level
    if (seen.has(k)) return false
    seen.add(k); return true
  })
  deduped.sort((a, b) => a.distPct - b.distPct)

  // Renumber TP1-TP5
  const final: { level: string; price: number; prob: number; distPct: number }[] = []
  let counter = 1
  for (const r of deduped) {
    if (counter > 5) break
    final.push({ ...r, level: `TP${counter}` })
    counter++
  }

  // If less than 5, extrapolate from slope of last 2
  while (final.length < 5 && final.length >= 2) {
    const last = final[final.length - 1]
    const prev = final[final.length - 2]
    const ratio = last.price / prev.price
    const nextPrice = isLong ? last.price * ratio : last.price / ratio
    if (nextPrice > 0 && !usedPrices.has(Math.round(nextPrice * 100))) {
      final.push({ level: `TP${final.length + 1}`, price: Math.round(nextPrice * 100) / 100, prob: Math.max(5, last.prob - 10), distPct: Math.abs(nextPrice - lastPrice) / lastPrice * 100 })
      usedPrices.add(Math.round(nextPrice * 100))
    } else break
  }

  return final
}

function drawTargetLines(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, th: Record<string, unknown> | undefined, fib: Record<string, unknown> | undefined, w: number, ohlcv: Candle[], lastCandleX: number, lastPrice: number, candleWidth: number) {
  if (!th || !ohlcv.length) return

  const longTPs = getTPLevels(th, fib, lastPrice, true)
  const shortTPs = getTPLevels(th, fib, lastPrice, false)

  const drawSingleTarget = (tgt: { level: string; price: number; prob: number; distPct: number }, color: string, idx: number) => {
    const y = toY(tgt.price); if (y <= 0) return
    const isFirst = idx === 0
    ctx.strokeStyle = color; ctx.lineWidth = isFirst ? 0.75 : 0.5; ctx.setLineDash(isFirst ? [] : [3, 6])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])

    const labelX = lastCandleX + candleWidth * (2 + idx * 1.5)
    const bgW = 110; const bgH = 14
    ctx.fillStyle = "rgba(11,17,23,0.8)"; ctx.fillRect(labelX - 2, y - 8, bgW, bgH)
    ctx.strokeStyle = color; ctx.lineWidth = 0.5; ctx.strokeRect(labelX - 2, y - 8, bgW, bgH)

    ctx.font = "bold 8px monospace"; ctx.fillStyle = color
    ctx.fillText(`${tgt.level} $${tgt.price.toFixed(2)}`, labelX, y + 3)
    ctx.font = "7px monospace"; ctx.fillStyle = color.replace(")", ",0.5)").replace("0.55", "0.35").replace("0.65", "0.45")
    ctx.fillText(`${tgt.prob}% ${tgt.distPct.toFixed(1)}%`, labelX, y - 12)
  }

  for (let i = 0; i < longTPs.length; i++) drawSingleTarget(longTPs[i], "rgba(34,197,94,0.65)", i)
  for (let i = 0; i < shortTPs.length; i++) drawSingleTarget(shortTPs[i], "rgba(239,68,68,0.65)", i)
}

function drawSupportResistanceZones(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, supZone: Record<string, unknown> | undefined, resZone: Record<string, unknown> | undefined, w: number, h: number, ohlcv: Candle[]) {
  if (!supZone || !resZone || !ohlcv.length) return
  const sTop = n2(supZone.top); const sBot = n2(supZone.bottom)
  const rTop = n2(resZone.top); const rBot = n2(resZone.bottom)
  if (sBot > 0 && sTop > 0) { const ys = toY(sBot); const ys2 = toY(sTop); if (ys > 0 && ys2 > 0) { ctx.fillStyle = "rgba(34,197,94,0.06)"; ctx.fillRect(0, ys, w, ys2 - ys); ctx.strokeStyle = "rgba(34,197,94,0.2)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(0, ys); ctx.lineTo(w, ys); ctx.stroke(); ctx.setLineDash([]); ctx.font = "7px monospace"; ctx.fillStyle = "rgba(34,197,94,0.5)"; ctx.fillText(`Dəstək $${sBot.toFixed(2)}-$${sTop.toFixed(2)}`, 2, ys - 2) } }
  if (rBot > 0 && rTop > 0) { const yr = toY(rBot); const yr2 = toY(rTop); if (yr > 0 && yr2 > 0) { ctx.fillStyle = "rgba(239,68,68,0.06)"; ctx.fillRect(0, yr, w, yr2 - yr); ctx.strokeStyle = "rgba(239,68,68,0.2)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(0, yr); ctx.lineTo(w, yr); ctx.stroke(); ctx.setLineDash([]); ctx.font = "7px monospace"; ctx.fillStyle = "rgba(239,68,68,0.5)"; ctx.fillText(`Müqavimət $${rBot.toFixed(2)}-$${rTop.toFixed(2)}`, 2, yr - 2) } }
}

function getConfidenceStyle(confidence: number, which: "main" | "alt" | "fakeout") {
  const isLow = confidence < 50; const isMid = confidence >= 50 && confidence < 70; const isHigh = confidence >= 70 && confidence < 80; const isVeryHigh = confidence >= 80
  let base: { lineWidth: number; dash: number[]; alpha: number; label: string; status: string }
  if (which === "main") {
    if (isVeryHigh) base = { lineWidth: 3, dash: [], alpha: 0.9, label: "ƏSAS SSENARİ", status: "GÜCLÜ HAZIR" }
    else if (isHigh) base = { lineWidth: 2.5, dash: [], alpha: 0.7, label: "ƏSAS SSENARİ", status: "HAZIRDIR" }
    else if (isMid) base = { lineWidth: 2, dash: [4, 4], alpha: 0.45, label: "ƏSAS SSENARİ", status: "İZLƏMƏ" }
    else base = { lineWidth: 1, dash: [6, 6], alpha: 0.15, label: "ƏSAS SSENARİ", status: "Təsdiq gözlənilir" }
  } else if (which === "alt") {
    if (isVeryHigh) base = { lineWidth: 1.5, dash: [3, 5], alpha: 0.5, label: "ALTERNATİV", status: "GÜCLÜ" }
    else if (isHigh) base = { lineWidth: 1, dash: [4, 6], alpha: 0.35, label: "ALTERNATİV", status: "HAZIR" }
    else if (isMid) base = { lineWidth: 1, dash: [5, 7], alpha: 0.2, label: "ALTERNATİV", status: "İZLƏMƏ" }
    else base = { lineWidth: 0.5, dash: [6, 8], alpha: 0.1, label: "ALTERNATİV", status: "Təsdiq gözlənilir" }
  } else {
    if (isVeryHigh) base = { lineWidth: 1.5, dash: [2, 4, 2, 6], alpha: 0.5, label: "FAKEOUT / LIKVIDLIK OVU", status: "GÜCLÜ" }
    else if (isHigh) base = { lineWidth: 1, dash: [2, 5, 2, 7], alpha: 0.35, label: "FAKEOUT / LIKVIDLIK OVU", status: "HAZIR" }
    else base = { lineWidth: 0.5, dash: [3, 6, 3, 8], alpha: 0.1, label: "FAKEOUT / LIKVIDLIK OVU", status: "Risk mümkün" }
  }
  return base
}

function drawScenarioPath(
  ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number,
  sp: Record<string, unknown> | undefined, w: number, h: number,
  cb: Record<string, unknown> | undefined, confidence: number,
  ohlcv: Candle[], which: "main" | "alt" | "fakeout",
  lastCandleX: number, lastPrice: number, candleWidth: number,
  toFutureX: (offset: number) => number,
) {
  if (!sp || !ohlcv.length) return
  const key = which === "main" ? "main_scenario" : which === "alt" ? "alternative_scenario" : "fakeout_scenario"
  const sc = sp[key] as Record<string, unknown> | undefined
  if (!sc) return
  const pts = sc.path_points as PathPoint[] | undefined
  if (!pts || pts.length < 2) return
  if (lastCandleX <= 0) return

  const signalConf = cb ? n2(cb.signal_confidence) : confidence
  const startX = toFutureX(0.5)
  const startY = toY(lastPrice)
  if (startX <= 0 || startY <= 0) return

  const style = getConfidenceStyle(signalConf, which)
  const dir = str(sc.direction)
  const isLong = dir === "LONG" || dir === "BULLISH"
  const color = which === "fakeout" ? "#f59e0b" : which === "alt" ? "#6b7280" : isLong ? "#22c55e" : "#ef4444"

  ctx.save()
  ctx.strokeStyle = color; ctx.lineWidth = style.lineWidth; ctx.setLineDash(style.dash)
  ctx.globalAlpha = style.alpha; ctx.beginPath()
  ctx.moveTo(startX, startY)
  let drawn = false
  for (const p of pts) {
    if (p.time_offset === 0) continue
    const x = toFutureX(p.time_offset); const y = toY(p.price)
    if (y <= 0) continue
    ctx.lineTo(x, y); drawn = true
  }
  if (drawn) ctx.stroke()
  ctx.setLineDash([])

  // Draw zig-zag arrows between path segments (main scenario only)
  if (which === "main" && signalConf >= 50) {
    ctx.save(); ctx.globalAlpha = Math.min(style.alpha * 1.8, 0.9)
    const pathPts = [{ x: startX, y: startY }, ...pts.filter(p => p.time_offset > 0).map(p => ({ x: toFutureX(p.time_offset), y: toY(p.price), p: p.price }))]
    for (let i = 1; i < pathPts.length; i++) {
      const p0 = pathPts[i - 1]; const p1 = pathPts[i] as { x: number; y: number; p?: number }
      if (p0.y <= 0 || p1.y <= 0 || p0.x <= 0 || p1.x <= 0) continue
      const midX = (p0.x + p1.x) / 2; const midY = (p0.y + p1.y) / 2
      const angle = Math.atan2(p1.y - p0.y, p1.x - p0.x)
      const arrowLen = 6; const arrowAngle = 0.4
      ctx.fillStyle = color; ctx.beginPath()
      ctx.moveTo(midX + arrowLen * Math.cos(angle), midY + arrowLen * Math.sin(angle))
      ctx.lineTo(midX - arrowLen * Math.cos(angle - arrowAngle), midY - arrowLen * Math.sin(angle - arrowAngle))
      ctx.lineTo(midX - arrowLen * Math.cos(angle + arrowAngle), midY - arrowLen * Math.sin(angle + arrowAngle))
      ctx.closePath(); ctx.fill()
    }
    ctx.restore()
  }

  if (signalConf >= 50) {
    ctx.globalAlpha = Math.min(style.alpha * 1.5, 1)
    for (const p of pts) {
      if (p.time_offset === 0) continue
      const x = toFutureX(p.time_offset); const y = toY(p.price)
      if (y <= 0) continue
      ctx.font = which === "fakeout" ? "6px monospace" : "bold 6px monospace"
      ctx.fillStyle = color; ctx.textAlign = "center"
      ctx.fillText(p.label, x, Math.max(10, y - 6))
      ctx.beginPath(); ctx.arc(x, y, which === "main" ? 3 : 2, 0, Math.PI * 2); ctx.fill()
      ctx.textAlign = "left"
    }
    ctx.globalAlpha = 1
  }

  ctx.globalAlpha = Math.min(style.alpha * 2, 1)
  const prob = n2(sc.probability)
  const lastP = pts[pts.length - 1]
  const lx = toFutureX(lastP.time_offset)
  const ly = toY(lastP.price)
  if (ly > 0) {
    ctx.font = "bold 7px monospace"; ctx.fillStyle = color; ctx.textAlign = "center"
    ctx.fillText(`📊 ${style.label} ${prob}% · ${style.status}`, lx, Math.max(10, ly - 16))
    ctx.font = "6px monospace"; ctx.fillStyle = color
    ctx.fillText(`🎯 $${lastP.price.toFixed(2)} · ${p2str(sc.direction_az || sc.direction)}`, lx, Math.max(10, ly - 4))
    if (signalConf < 50) {
      ctx.font = "6px monospace"; ctx.fillStyle = "rgba(255,255,255,0.25)"; ctx.textAlign = "center"
      ctx.fillText("Ehtimal olunan ssenari — təsdiqlənməyib", lx, Math.max(20, h - 10))
      ctx.textAlign = "left"
    }
  }

  const triggerPrice = which === "main" ? (n2(sc.activation_price) || 0) : 0
  if (triggerPrice > 0) {
    const ty = toY(triggerPrice)
    if (ty > 0) {
      ctx.strokeStyle = isLong ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"; ctx.lineWidth = 0.5; ctx.setLineDash([3, 5])
      ctx.beginPath(); ctx.moveTo(startX, ty); ctx.lineTo(toFutureX(pts[pts.length - 1].time_offset), ty); ctx.stroke(); ctx.setLineDash([])
      ctx.font = "6px monospace"; ctx.fillStyle = color; ctx.textAlign = "center"; ctx.fillText(`Trigger $${triggerPrice.toFixed(2)}`, startX, ty - 4); ctx.textAlign = "left"
    }
  }

  ctx.restore()
}

function drawSMCStructures(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, analysis: Record<string, unknown> | null, ohlcv: Candle[], w: number) {
  if (!analysis || !ohlcv.length) return
  const allStructs = (analysis as Record<string, unknown>).all_structures as Record<string, unknown>[] | undefined
  if (!allStructs) return

  const lastPrice = ohlcv[ohlcv.length - 1].close
  const sorted = allStructs.filter(s => n2(s.price) > 0 || n2(s.gap_high) > 0).map(s => ({ s, _dist: Math.abs((n2(s.price) || n2(s.gap_high) || 0) - lastPrice) })).sort((a, b) => a._dist - b._dist).map(x => x.s)

  const fvgs = sorted.filter(s => p2str(s.category) === "fvg").slice(0, 2)
  for (const fvg of fvgs) {
    const idx = n2(fvg.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const top = toY(n2(fvg.gap_high)); const bot = toY(n2(fvg.gap_low))
    if (x <= 0 || top <= 0 || bot <= 0) continue
    const isBullish = p2str(fvg.type).includes("bullish")
    ctx.fillStyle = isBullish ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)"
    ctx.fillRect(x - 4, Math.min(top, bot), 8, Math.abs(top - bot))
    ctx.strokeStyle = isBullish ? "rgba(34,197,94,0.5)" : "rgba(239,68,68,0.5)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 2])
    ctx.strokeRect(x - 4, Math.min(top, bot), 8, Math.abs(top - bot)); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = isBullish ? "rgba(34,197,94,0.7)" : "rgba(239,68,68,0.7)"; ctx.fillText(p2str(fvg.fvg_type || "FVG"), x - 4, Math.max(top, bot) + 10)
  }

  const obs = sorted.filter(s => p2str(s.category) === "order_block").slice(0, 2)
  for (const ob of obs) {
    const idx = n2(ob.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const top = toY(n2(ob.high)); const bot = toY(n2(ob.low))
    if (x <= 0 || top <= 0 || bot <= 0) continue
    const isBullish = p2str(ob.type).includes("bullish")
    ctx.fillStyle = isBullish ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)"
    ctx.fillRect(x - 6, Math.min(top, bot), 12, Math.abs(top - bot))
    ctx.strokeStyle = isBullish ? "#22c55e" : "#ef4444"; ctx.lineWidth = 1
    ctx.strokeRect(x - 6, Math.min(top, bot), 12, Math.abs(top - bot))
    ctx.font = "7px monospace"; ctx.fillStyle = isBullish ? "#22c55e" : "#ef4444"; ctx.fillText("OB", x - 6, Math.min(top, bot) - 3)
  }

  const bosList = sorted.filter(s => p2str(s.category) === "bos").slice(0, 2)
  for (const bos of bosList) {
    const idx = n2(bos.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const y = toY(n2(bos.price))
    if (x <= 0 || y <= 0) continue
    const isBullish = p2str(bos.type).includes("bullish"); const sz = 5
    ctx.strokeStyle = isBullish ? "#22c55e" : "#ef4444"; ctx.lineWidth = 1.5; ctx.beginPath()
    if (isBullish) { ctx.moveTo(x - sz, y + sz); ctx.lineTo(x, y); ctx.lineTo(x + sz, y + sz) }
    else { ctx.moveTo(x - sz, y - sz); ctx.lineTo(x, y); ctx.lineTo(x + sz, y - sz) }
    ctx.stroke(); ctx.font = "6px monospace"; ctx.fillStyle = isBullish ? "#22c55e" : "#ef4444"; ctx.fillText("BOS", x + sz + 1, y + (isBullish ? sz : -sz) + 2)
  }

  const chochList = sorted.filter(s => p2str(s.category) === "choch").slice(0, 2)
  for (const choch of chochList) {
    const idx = n2(choch.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const y = toY(ohlcv[idx].high); if (x <= 0 || y <= 0) continue
    ctx.font = "6px monospace"; ctx.fillStyle = "#a855f7"; ctx.fillText("CHoCH", x + 2, y - 3)
  }

  const liqSweeps = sorted.filter(s => p2str(s.category) === "liquidity_sweep").slice(0, 2)
  for (const ls of liqSweeps) {
    const pt = n2(ls.price); if (pt <= 0) continue; const y = toY(pt); if (y <= 0) continue
    ctx.strokeStyle = "rgba(168,85,247,0.3)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 4])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = "rgba(168,85,247,0.5)"; ctx.fillText(`Likvidlik ovu $${pt.toFixed(2)}`, 2, y - 2)
  }

  const eqs = sorted.filter(s => p2str(s.category) === "equal_high" || p2str(s.category) === "equal_low").slice(0, 2)
  for (const eq of eqs) {
    const pt = n2(eq.price); if (pt <= 0) continue; const y = toY(pt); if (y <= 0) continue
    const isEH = p2str(eq.category) === "equal_high"
    ctx.strokeStyle = isEH ? "rgba(239,68,68,0.2)" : "rgba(34,197,94,0.2)"; ctx.lineWidth = 0.5; ctx.setLineDash([3, 3])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = isEH ? "rgba(239,68,68,0.4)" : "rgba(34,197,94,0.4)"; ctx.fillText(isEH ? `EQH $${pt.toFixed(2)}` : `EQL $${pt.toFixed(2)}`, 2, y - 2)
  }
}

function drawSR(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, sr: Record<string, unknown>, price: number, w: number) {
  const levels = [
    { key: "nearest_support", label: "D", color: "rgba(34,197,94,0.65)" },
    { key: "nearest_resistance", label: "Q", color: "rgba(239,68,68,0.65)" },
    { key: "strongest_support", label: "GD", color: "rgba(34,197,94,0.35)" },
    { key: "strongest_resistance", label: "GQ", color: "rgba(239,68,68,0.35)" },
  ]
  for (const l of levels) { const p = n2(sr[l.key]); if (p <= 0) continue; const y = toY(p); if (y <= 0) continue; ctx.strokeStyle = l.color; ctx.lineWidth = 0.5; ctx.setLineDash(l.key.startsWith("strongest") ? [4, 4] : [2, 2]); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([]); ctx.font = "7px monospace"; ctx.fillStyle = l.color; ctx.fillText(`${l.label} $${p.toFixed(2)}`, w - 80, y - 2) }
}

function drawPatterns(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, patterns: Record<string, unknown>[] | undefined, ohlcv: Candle[], w: number) {
  if (!patterns || !ohlcv.length) return
  let yOff = 20; const st: Record<string,string> = { CONFIRMED:"TƏSDİQLƏNDİ", DETECTED:"AŞKAR EDİLDİ", FORMING:"FORMALAŞIR" }

  const drawMeasuredMove = (bLevel: number, mTarget: number, color: string) => {
    if (bLevel <= 0 || mTarget <= 0) return
    const y1 = toY(bLevel); const y2 = toY(mTarget)
    if (y1 <= 0 || y2 <= 0) return
    ctx.strokeStyle = color; ctx.lineWidth = 0.5; ctx.setLineDash([3, 3])
    ctx.beginPath(); ctx.moveTo(w - 40, y1); ctx.lineTo(w - 40, y2); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = color
    ctx.fillText(`→$${mTarget.toFixed(1)}`, w - 38, (y1 + y2) / 2)
  }

  for (const pat of patterns.slice(0, 4)) {
    const name = p2str(pat.name); const prob = n2(pat.probability)
    const bLevel = n2(pat.breakout_level) || n2(pat.breakdown_level)
    const mTarget = n2(pat.measured_target)
    const color = p2str(pat.status) === "CONFIRMED" ? "rgba(34,197,94,0.7)" : p2str(pat.status) === "DETECTED" ? "rgba(245,158,11,0.7)" : "rgba(107,114,128,0.5)"
    const labelColor = p2str(pat.status) === "CONFIRMED" ? "#22c55e" : p2str(pat.status) === "DETECTED" ? "#f59e0b" : "#6b7280"
    const tf = p2str(pat.timeframe)

    // Draw pattern-specific shapes
    if (name.includes("Head and Shoulders") || name.includes("Inverse Head")) {
      // Draw H&S shape: 3 circles at swing points
      const isInv = name.includes("Inverse")
      if (ohlcv.length >= 20) {
        const step = Math.max(1, Math.floor(ohlcv.length / 5))
        const idxs = [Math.floor(ohlcv.length * 0.15), Math.floor(ohlcv.length * 0.35), Math.floor(ohlcv.length * 0.55)]
        const prices = idxs.map(i => ohlcv[Math.min(i, ohlcv.length-1)]?.close || 0)
        if (prices.every(p => p > 0)) {
          const xs = idxs.map(i => toX(ohlcv[Math.min(i, ohlcv.length-1)].time))
          const ys = prices.map(p => toY(p))
          if (xs.every(x => x > 0) && ys.every(y => y > 0)) {
            ctx.strokeStyle = color; ctx.lineWidth = 0.5; ctx.setLineDash([])
            // Left shoulder
            ctx.beginPath(); ctx.arc(xs[0], ys[0], 5, 0, Math.PI * 2); ctx.stroke()
            ctx.font = "6px monospace"; ctx.fillStyle = labelColor
            ctx.fillText("LS", xs[0] + 6, ys[0] + 2)
            // Head
            ctx.beginPath(); ctx.arc(xs[1], ys[1], 7, 0, Math.PI * 2); ctx.stroke()
            ctx.fillText("HD", xs[1] + 8, ys[1] + 2)
            // Right shoulder
            ctx.beginPath(); ctx.arc(xs[2], ys[2], 5, 0, Math.PI * 2); ctx.stroke()
            ctx.fillText("RS", xs[2] + 6, ys[2] + 2)
            // Neckline
            const neckMin = isInv ? Math.max(...ys) : Math.min(...ys)
            ctx.strokeStyle = "rgba(239,68,68,0.3)"; ctx.lineWidth = 0.5; ctx.setLineDash([3, 3])
            ctx.beginPath(); ctx.moveTo(xs[0], neckMin); ctx.lineTo(xs[2], neckMin); ctx.stroke(); ctx.setLineDash([])
            ctx.font = "5px monospace"; ctx.fillStyle = "rgba(239,68,68,0.4)"
            ctx.fillText("Boyun xətti", xs[1] + 2, neckMin - 2)
          }
        }
      }
      drawMeasuredMove(bLevel, mTarget, color)
    } else if (name.includes("Cup and Handle")) {
      // Draw cup shape: curve from rim to bottom back to rim, then handle dip
      if (ohlcv.length >= 15) {
        const cupRim = n2(pat.cup_rim); const cupBot = n2(pat.cup_bottom)
        const handleLow = n2(pat.handle_low)
        const startIdx = Math.max(0, ohlcv.length - 30)
        const midIdx = Math.floor((ohlcv.length + startIdx) / 2)
        const lastIdx = ohlcv.length - 1
        const x0 = toX(ohlcv[startIdx].time); const xm = toX(ohlcv[midIdx].time); const x1 = toX(ohlcv[lastIdx].time)
        const yRim = toY(cupRim); const yBot = toY(cupBot); const yH = toY(handleLow || cupBot)
        if (x0 > 0 && xm > 0 && x1 > 0 && yRim > 0 && yBot > 0) {
          ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.setLineDash([])
          ctx.beginPath()
          ctx.moveTo(x0, yRim)
          const cp1x = (x0 + xm) / 2; const cp1y = yRim
          const cp2x = xm; const cp2y = yBot
          ctx.quadraticCurveTo((x0 + xm) / 2, yBot, xm, yBot)
          ctx.quadraticCurveTo((xm + x1) / 2, yBot, x1, yRim)
          ctx.stroke()
          // Handle dip
          if (handleLow > 0 && cupRim > handleLow) {
            ctx.strokeStyle = "rgba(245,158,11,0.4)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 3])
            const handleX = x1 - (x1 - xm) * 0.4
            ctx.beginPath(); ctx.moveTo(handleX, yRim); ctx.lineTo(handleX, yH); ctx.stroke(); ctx.setLineDash([])
            ctx.font = "6px monospace"; ctx.fillStyle = "rgba(245,158,11,0.5)"
            ctx.fillText("Handle", handleX + 2, (yRim + yH) / 2)
          }
          ctx.font = "7px monospace"; ctx.fillStyle = labelColor
          ctx.fillText("C&H", xm - 10, yBot + 14)
        }
      }
      drawMeasuredMove(bLevel, mTarget, color)
    } else if (name.includes("Double Top") || name.includes("Double Bottom")) {
      // Draw 2 circles at swing points + neckline
      if (ohlcv.length >= 15) {
        const isTop = name.includes("Top")
        const step = Math.max(1, Math.floor(ohlcv.length / 4))
        const idx1 = Math.floor(ohlcv.length * 0.25); const idx2 = Math.floor(ohlcv.length * 0.55)
        const x1 = toX(ohlcv[Math.min(idx1, ohlcv.length-1)].time)
        const x2 = toX(ohlcv[Math.min(idx2, ohlcv.length-1)].time)
        const p1 = ohlcv[Math.min(idx1, ohlcv.length-1)]?.close || 0
        const p2 = ohlcv[Math.min(idx2, ohlcv.length-1)]?.close || 0
        const y1 = toY(p1); const y2 = toY(p2)
        if (x1 > 0 && x2 > 0 && y1 > 0 && y2 > 0) {
          ctx.strokeStyle = color; ctx.lineWidth = 1
          ctx.beginPath(); ctx.arc(x1, y1, 5, 0, Math.PI * 2); ctx.stroke()
          ctx.beginPath(); ctx.arc(x2, y2, 5, 0, Math.PI * 2); ctx.stroke()
          ctx.font = "7px monospace"; ctx.fillStyle = labelColor
          ctx.fillText(isTop ? "1st Top" : "1st Bot", x1 + 6, y1 + 2)
          ctx.fillText(isTop ? "2nd Top" : "2nd Bot", x2 + 6, y2 + 2)
          // Neckline
          const neckY = isTop ? Math.max(y1, y2) : Math.min(y1, y2)
          ctx.strokeStyle = "rgba(239,68,68,0.2)"; ctx.lineWidth = 0.5; ctx.setLineDash([3, 3])
          ctx.beginPath(); ctx.moveTo(x1, neckY); ctx.lineTo(x2, neckY); ctx.stroke(); ctx.setLineDash([])
        }
      }
      drawMeasuredMove(bLevel, mTarget, color)
    } else if (name.includes("Flag") || name.includes("Pennant")) {
      // Draw flag pole + rectangle
      if (ohlcv.length >= 10) {
        const idxStart = Math.max(0, ohlcv.length - 15)
        const xStart = toX(ohlcv[idxStart].time)
        const xEnd = toX(ohlcv[ohlcv.length-1].time)
        const yHigh = toY(Math.max(...ohlcv.slice(idxStart).map(d => d.high)))
        const yLow = toY(Math.min(...ohlcv.slice(idxStart).map(d => d.low)))
        if (xStart > 0 && xEnd > 0 && yHigh > 0 && yLow > 0) {
          ctx.strokeStyle = color; ctx.lineWidth = 0.5; ctx.setLineDash([2, 3])
          ctx.strokeRect(xStart, yHigh, xEnd - xStart, yLow - yHigh)
          ctx.setLineDash([])
        }
      }
      drawMeasuredMove(bLevel, mTarget, color)
    } else if (name.includes("Triangle") || name.includes("Wedge")) {
      // Draw converging lines
      if (ohlcv.length >= 10) {
        const idxs = [Math.max(0, ohlcv.length - 15), ohlcv.length - 1]
        const highs = idxs.map(i => ohlcv[i].high)
        const lows = idxs.map(i => ohlcv[i].low)
        const xs = idxs.map(i => toX(ohlcv[i].time))
        if (xs.every(x => x > 0)) {
          const yh1 = toY(highs[0]); const yh2 = toY(highs[1])
          const yl1 = toY(lows[0]); const yl2 = toY(lows[1])
          if (yh1 > 0 && yh2 > 0 && yl1 > 0 && yl2 > 0) {
            ctx.strokeStyle = color; ctx.lineWidth = 0.5; ctx.setLineDash([2, 3])
            ctx.beginPath(); ctx.moveTo(xs[0], yh1); ctx.lineTo(xs[1], yh2); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(xs[0], yl1); ctx.lineTo(xs[1], yl2); ctx.stroke()
            ctx.setLineDash([])
          }
        }
      }
      drawMeasuredMove(bLevel, mTarget, color)
    } else if (name.includes("Rectangle") || name.includes("Range")) {
      // Draw rectangular range
      if (ohlcv.length >= 10) {
        const idxStart = Math.max(0, ohlcv.length - 20)
        const xStart = toX(ohlcv[idxStart].time)
        const xEnd = toX(ohlcv[ohlcv.length-1].time)
        const topVal = n2(pat.breakout_level) || Math.max(...ohlcv.slice(idxStart).map(d => d.high))
        const botVal = n2(pat.breakdown_level) || Math.min(...ohlcv.slice(idxStart).map(d => d.low))
        const yT = toY(topVal); const yB = toY(botVal)
        if (xStart > 0 && xEnd > 0 && yT > 0 && yB > 0) {
          ctx.strokeStyle = "rgba(99,102,241,0.3)"; ctx.lineWidth = 1; ctx.setLineDash([4, 4])
          ctx.strokeRect(xStart, yT, xEnd - xStart, yB - yT)
          ctx.setLineDash([])
          ctx.fillStyle = "rgba(99,102,241,0.03)"; ctx.fillRect(xStart, yT, xEnd - xStart, yB - yT)
        }
      }
      drawMeasuredMove(bLevel, mTarget, color)
    } else {
      // Generic: draw measured move only
      drawMeasuredMove(bLevel, mTarget, color)
    }

    // Draw pattern label on top-left side
    ctx.font = "7px monospace"; ctx.fillStyle = labelColor
    ctx.fillText(`${name} ${st[p2str(pat.status)]||p2str(pat.status)} ${prob}% · ${tf}`, 10, yOff + 10)
    yOff += 14
  }
}

function drawTradeLevels(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, triggers: Record<string, unknown>, scores: Record<string, unknown>, w: number, lastCandleX: number, candleWidth: number, confidence: number) {
  const ltP = n2(triggers.long_trigger_price); const stP = n2(triggers.short_trigger_price)
  const inv = n2(triggers.bullish_invalidation) || n2(triggers.bearish_invalidation)
  const confThick = confidence >= 70 ? 2 : 1; const confDash = confidence >= 70 ? [] : [6, 4]; const confAlpha = confidence >= 70 ? 0.75 : 0.35
  const drawLine = (price: number, color: string, label: string, dash: number[], width: number) => {
    const y = toY(price); if (y <= 0) return
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash)
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "bold 7px monospace"; ctx.fillStyle = color
    ctx.fillText(label, lastCandleX + candleWidth * 2, y - 3)
  }
  const longConds = triggers.long_trigger_conditions as string[] | undefined
  const shortConds = triggers.short_trigger_conditions as string[] | undefined
  if (ltP > 0) {
    drawLine(ltP, `rgba(34,197,94,${confAlpha})`, `↑ ALIŞ $${ltP.toFixed(2)}`, confDash, confThick)
    if (longConds && longConds.length > 0 && confidence >= 50) {
      const yBase = toY(ltP); if (yBase > 0) { ctx.font = "5px monospace"; ctx.fillStyle = "rgba(34,197,94,0.3)"; ctx.textAlign = "left"; ctx.fillText(`Şərtlər: ${longConds.length}`, lastCandleX + candleWidth * 2, yBase + 10); ctx.textAlign = "left" }
    }
  }
  if (stP > 0) {
    drawLine(stP, `rgba(239,68,68,${confAlpha})`, `↓ SATIŞ $${stP.toFixed(2)}`, confDash, confThick)
    if (shortConds && shortConds.length > 0 && confidence >= 50) {
      const yBase = toY(stP); if (yBase > 0) { ctx.font = "5px monospace"; ctx.fillStyle = "rgba(239,68,68,0.3)"; ctx.textAlign = "left"; ctx.fillText(`Şərtlər: ${shortConds.length}`, lastCandleX + candleWidth * 2, yBase + 10); ctx.textAlign = "left" }
    }
  }
  if (inv > 0) drawLine(inv, "rgba(168,85,247,0.45)", `Ləğv $${inv.toFixed(2)}`, [4, 4], 0.5)
}

function drawVolumeProfile(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, ohlcv: Candle[], w: number, h: number) {
  if (ohlcv.length < 50) return
  const maxH = Math.max(...ohlcv.map(d => d.high)); const minL = Math.min(...ohlcv.map(d => d.low))
  const priceRange = maxH - minL; if (priceRange <= 0) return
  const buckets = 30; const bs = priceRange / buckets
  const volB = new Array(buckets).fill(0)
  for (const d of ohlcv) {
    const idx = Math.min(buckets - 1, Math.max(0, Math.floor((d.close - minL) / bs)))
    volB[idx] += d.volume
  }
  const maxV = Math.max(...volB); if (maxV <= 0) return
  const totalVol = volB.reduce((a, b) => a + b, 0)
  const barMaxWidth = 70; const barGap = 1.5

  // Sort by volume to find Value Area (70% of total)
  const volSorted = [...volB].map((v, i) => ({ v, i })).sort((a, b) => b.v - a.v)
  let cumVol = 0; const vaIndices = new Set<number>()
  for (const item of volSorted) {
    if (cumVol / totalVol >= 0.7) break
    vaIndices.add(item.i); cumVol += item.v
  }
  let vaHigh = -Infinity; let vaLow = Infinity
  for (const i of vaIndices) {
    const p = minL + bs * (i + 0.5)
    vaHigh = Math.max(vaHigh, p); vaLow = Math.min(vaLow, p)
  }

  // Draw bars from right edge going left
  const rightEdge = w - 2
  for (let i = 0; i < buckets; i++) {
    const price = minL + bs * (i + 0.5)
    const y = toY(price)
    if (y <= 0 || y > h) continue
    const volRatio = volB[i] / maxV
    const bw = Math.max(1, volRatio * barMaxWidth)
    const inVA = vaIndices.has(i)
    const isPOC = volB[i] === maxV
    const alpha = isPOC ? 0.45 : inVA ? 0.2 : 0.08
    ctx.fillStyle = `rgba(245,158,11,${alpha})`
    ctx.fillRect(rightEdge - bw, y - barGap, bw, Math.max(1.5, bs * 0.08))
    if (isPOC) {
      ctx.fillStyle = "rgba(245,158,11,0.15)"
      ctx.fillRect(0, y - 1, w, 2)
    }
  }

  // POC label
  const pocIdx = volB.indexOf(maxV); const pocP = minL + bs * (pocIdx + 0.5); const pocY = toY(pocP)
  if (pocY > 0) {
    ctx.save()
    ctx.fillStyle = "rgba(11,17,23,0.8)"; ctx.fillRect(rightEdge - 48, pocY - 7, 50, 14)
    ctx.strokeStyle = "rgba(245,158,11,0.4)"; ctx.lineWidth = 0.5; ctx.strokeRect(rightEdge - 48, pocY - 7, 50, 14)
    ctx.font = "bold 7px monospace"; ctx.fillStyle = "rgba(245,158,11,0.8)"; ctx.textAlign = "right"
    ctx.fillText(`POC $${pocP.toFixed(2)}`, w - 4, pocY + 3); ctx.textAlign = "left"
    ctx.restore()
  }

  // Value Area labels
  if (vaHigh > 0 && vaLow > 0 && vaHigh !== vaLow) {
    const vaHighY = toY(vaHigh); const vaLowY = toY(vaLow)
    if (vaHighY > 0 && vaLowY > 0) {
      ctx.fillStyle = "rgba(245,158,11,0.06)"; ctx.fillRect(0, vaHighY, w, vaLowY - vaHighY)
      ctx.strokeStyle = "rgba(245,158,11,0.15)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 4])
      ctx.beginPath(); ctx.moveTo(0, vaHighY); ctx.lineTo(rightEdge - barMaxWidth - 4, vaHighY); ctx.stroke()
      ctx.beginPath(); ctx.moveTo(0, vaLowY); ctx.lineTo(rightEdge - barMaxWidth - 4, vaLowY); ctx.stroke()
      ctx.setLineDash([])
      ctx.font = "6px monospace"; ctx.fillStyle = "rgba(245,158,11,0.4)"; ctx.textAlign = "right"
      ctx.fillText(`VAH $${vaHigh.toFixed(2)}`, rightEdge - barMaxWidth - 6, vaHighY - 2)
      ctx.fillText(`VAL $${vaLow.toFixed(2)}`, rightEdge - barMaxWidth - 6, vaLowY + 10)
      ctx.textAlign = "left"
    }
  }
}

function drawProbabilityCone(
  ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number,
  sp: Record<string, unknown> | undefined, ohlcv: Candle[],
  lastCandleX: number, lastPrice: number, candleWidth: number,
  toFutureX: (offset: number) => number,
) {
  if (!sp || !ohlcv.length) return
  const sc = sp.main_scenario as Record<string, unknown> | undefined
  if (!sc) return
  const pts = sc.path_points as PathPoint[] | undefined
  if (!pts || pts.length < 2) return

  // Estimate base volatility from recent candles
  const lookback = Math.min(20, ohlcv.length)
  let sumRange = 0
  for (let i = ohlcv.length - lookback; i < ohlcv.length; i++) {
    sumRange += (ohlcv[i].high - ohlcv[i].low) / ohlcv[i].close
  }
  const avgRange = sumRange / lookback

  const startX = toFutureX(0.5)
  const startY = toY(lastPrice)
  if (startX <= 0 || startY <= 0) return

  const points: { x: number; y: number; prob: number; offset: number; price: number }[] = [{ x: startX, y: startY, prob: 100, offset: 0, price: lastPrice }]
  for (const p of pts) {
    if (p.time_offset === 0) continue
    const x = toFutureX(p.time_offset); const y = toY(p.price)
    if (y <= 0) continue
    points.push({ x, y, prob: p.probability || 50, offset: p.time_offset, price: p.price })
  }

  // Build upper/lower bands
  const upper: { x: number; y: number }[] = []
  const lower: { x: number; y: number }[] = []

  for (const pt of points) {
    const uncertainty = avgRange * (1 - pt.prob / 100) * Math.sqrt(pt.offset + 1) * 2.5
    const priceOffset = pt.price * uncertainty
    const upperY = toY(pt.price + priceOffset)
    const lowerY = toY(pt.price - priceOffset)
    if (upperY > 0 && lowerY > 0) {
      upper.push({ x: pt.x, y: upperY })
      lower.push({ x: pt.x, y: lowerY })
    }
  }

  if (upper.length < 2 || lower.length < 2) return

  // Draw cone fill (gradient from center outward)
  ctx.save()
  ctx.beginPath(); ctx.moveTo(upper[0].x, upper[0].y)
  for (let i = 1; i < upper.length; i++) ctx.lineTo(upper[i].x, upper[i].y)
  for (let i = lower.length - 1; i >= 0; i--) ctx.lineTo(lower[i].x, lower[i].y)
  ctx.closePath()
  const grad = ctx.createLinearGradient(startX, upper[0].y, startX, lower[0].y)
  grad.addColorStop(0, "rgba(34,197,94,0.08)")
  grad.addColorStop(0.5, "rgba(34,197,94,0.04)")
  grad.addColorStop(1, "rgba(34,197,94,0.08)")
  ctx.fillStyle = grad; ctx.fill()

  // Cone outline (subtle)
  ctx.strokeStyle = "rgba(34,197,94,0.12)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 6])
  ctx.beginPath(); ctx.moveTo(upper[0].x, upper[0].y)
  for (let i = 1; i < upper.length; i++) ctx.lineTo(upper[i].x, upper[i].y); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(lower[0].x, lower[0].y)
  for (let i = 1; i < lower.length; i++) ctx.lineTo(lower[i].x, lower[i].y); ctx.stroke()
  ctx.setLineDash([])
  ctx.restore()

  // Label the cone
  const lastPt = points[points.length - 1]
  if (lastPt.y > 0) {
    ctx.font = "7px monospace"; ctx.fillStyle = "rgba(34,197,94,0.3)"
    ctx.textAlign = "center"; ctx.fillText("Ehtimal konusu", lastPt.x, Math.min(upper[upper.length - 1].y, lower[lower.length - 1].y) - 6)
    ctx.textAlign = "left"
  }
}

function drawLegend(
  ctx: CanvasRenderingContext2D, w: number, h: number,
  overlays: Record<string, boolean>, activePatterns: Record<string, unknown>[] | undefined,
  mainSc: Record<string, unknown> | undefined, confidence: number,
) {
  const items: { label: string; color: string; active: boolean }[] = [
    { label: "Şam (OHLCV)", color: "#22c55e", active: true },
    { label: "Əsas ssenari", color: "#22c55e", active: overlays.mainScenario },
    { label: "Alternativ", color: "#6b7280", active: overlays.altScenario },
    { label: "Fakeout", color: "#f59e0b", active: overlays.fakeout },
    { label: "Hədəflər (TP1-TP5)", color: "#22c55e", active: overlays.targets },
    { label: "Ehtimal konusu", color: "rgba(34,197,94,0.4)", active: overlays.cone },
    { label: "Breakout zonası", color: "#a855f7", active: overlays.breakout },
    { label: "Retest zonası", color: "#3b82f6", active: overlays.retest },
    { label: "Kanal", color: "#a855f7", active: overlays.channel },
    { label: "Fibonacci", color: "#f59e0b", active: overlays.fibonacci },
    { label: "Patternlər", color: "#f59e0b", active: overlays.patterns },
    { label: "Elliott dalğaları", color: "#a855f7", active: overlays.elliott },
    { label: "SMC (FVG/OB/BOS)", color: "#a855f7", active: overlays.smc },
    { label: "Likvidlik", color: "#ef4444", active: overlays.liquidity },
    { label: "Trigger səviyyələri", color: "#22c55e", active: overlays.triggers },
    { label: "Həcm profili", color: "#f59e0b", active: overlays.volumeProfile },
    { label: "Struktur", color: "#6b7280", active: overlays.structure },
  ]
  const activeItems = items.filter(i => i.active)
  if (!activeItems.length) return

  // Detect patterns
  const patternNames = (activePatterns || []).slice(0, 3).map(p => String(p.name || ""))
  const extraLines: string[] = []
  if (patternNames.length > 0) {
    extraLines.push(`Pattern: ${patternNames.join(", ")}`)
  }
  if (mainSc) {
    const dir = String(mainSc.direction_az || mainSc.direction || "")
    const prob = typeof (mainSc as Record<string, unknown>).probability === "number" ? (mainSc as Record<string, unknown>).probability as number : 0
    if (dir) extraLines.push(`${dir} ${prob}%`)
  }

  const lineH = 11; const pad = 4; const colW = 130
  const totalLines = Math.ceil(activeItems.length / 2)
  const boxH = totalLines * lineH + pad * 2 + extraLines.length * lineH + pad
  const boxW = colW * 2 + pad * 2
  const bx = w - boxW - 8; const by = h - boxH - 8

  ctx.save()
  ctx.fillStyle = "rgba(11,17,23,0.85)"
  ctx.strokeStyle = "rgba(55,65,81,0.5)"; ctx.lineWidth = 0.5
  ctx.beginPath(); ctx.roundRect(bx, by, boxW, boxH, 3); ctx.fill(); ctx.stroke()

  ctx.font = "7px monospace"
  let yy = by + pad + 8
  for (let i = 0; i < activeItems.length; i++) {
    const col = Math.floor(i / totalLines)
    const row = i % totalLines
    const ix = bx + pad + col * colW
    const iy = by + pad + row * lineH + 8
    ctx.fillStyle = activeItems[i].color; ctx.fillRect(ix, iy - 5, 6, 6)
    ctx.fillStyle = "rgba(156,163,175,0.8)"; ctx.fillText(activeItems[i].label, ix + 9, iy + 1)
    yy = iy + lineH
  }

  for (const line of extraLines) {
    ctx.fillStyle = "rgba(156,163,175,0.5)"; ctx.fillText(line, bx + pad, yy + lineH)
    yy += lineH
  }

  ctx.fillStyle = "rgba(156,163,175,0.3)"; ctx.font = "6px monospace"
  ctx.fillText(`AI inam: ${confidence}%`, bx + pad, yy + lineH)
  ctx.restore()
}

function drawSmartMoney(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, analysis: Record<string, unknown> | null, ohlcv: Candle[]) {
  if (!analysis || ohlcv.length < 30) return
  const allStructs = (analysis as Record<string, unknown>).all_structures as Record<string, unknown>[] | undefined
  if (!allStructs) return
  let bc = 0, sc = 0
  for (const s of allStructs) { if (p2str(s.category) === "order_block" && p2str(s.type).includes("bullish")) bc++; if (p2str(s.category) === "order_block" && p2str(s.type).includes("bearish")) sc++ }
  if (bc > sc * 1.5) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(34,197,94,0.3)"; ctx.fillText("Yığım Zonası", 10, 50) }
  else if (sc > bc * 1.5) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(239,68,68,0.3)"; ctx.fillText("Paylanma Zonası", 10, 50) }
}

function drawElliottWave(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, ew: Record<string, unknown> | undefined, w: number, ohlcv: Candle[], confidence: number) {
  if (!ew || ew.status === "insufficient_data" || !ohlcv.length) return
  const waves = ew.waves as { type: string; start: number; end: number; index: number; label?: string }[] | undefined
  if (!waves || waves.length < 3) { return }

  const ewConf = n2(ew.confidence) || confidence
  const isUncertain = ewConf < 50

  const numLabels = ["1", "2", "3", "4", "5", "A", "B", "C"]
  for (let i = 0; i < Math.min(waves.length, 8); i++) {
    const wave = waves[i]; const idx = wave.index; if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); if (x <= 0) continue
    const isUp = wave.type === "wave_up"; const y = toY(isUp ? wave.end : wave.start); if (y <= 0) continue
    if (isUncertain) {
      ctx.fillStyle = "rgba(168,85,247,0.15)"; const sz = 3; ctx.beginPath(); ctx.arc(x, y, sz, 0, Math.PI * 2); ctx.fill()
      ctx.font = "6px monospace"; ctx.fillStyle = "rgba(168,85,247,0.3)"; ctx.fillText(numLabels[i] || "", x + 4, y + 3)
    } else {
      ctx.fillStyle = isUp ? "#22c55e" : "#ef4444"; const sz = 4; ctx.beginPath()
      if (isUp) { ctx.moveTo(x, y - sz); ctx.lineTo(x - sz, y); ctx.lineTo(x + sz, y) }
      else { ctx.moveTo(x, y + sz); ctx.lineTo(x - sz, y); ctx.lineTo(x + sz, y) }
      ctx.fill(); ctx.fillStyle = isUp ? "rgba(34,197,94,0.8)" : "rgba(239,68,68,0.8)"
      ctx.fillText(numLabels[i] || String(i+1), x + sz + 2, y + 3)
    }
  }

  if (isUncertain) {
    ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.4)"; ctx.fillText("Elliott sayımı qeyri-müəyyəndir", 10, 70)
  } else {
    const currentLabel = waves[waves.length - 1]?.label || ""
    const nextProb = str(ew.next_probable_wave || "")
    ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.6)"; ctx.fillText(`Cari: Dalğa ${currentLabel} · ${nextProb || ""}`, 10, 70)
  }
}
