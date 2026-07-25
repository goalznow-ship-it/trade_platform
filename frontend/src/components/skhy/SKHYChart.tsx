"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import {
  createChart, ColorType, CandlestickSeries, HistogramSeries, LineSeries,
  type IChartApi, type ISeriesApi, type Time,
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

type OverlayKey = "structure"|"channel"|"breakout"|"retest"|"fibonacci"|"targets"|"mainScenario"|"altScenario"|"fakeout"|"smc"|"liquidity"|"ema"|"atrStop"|"volumeProfile"|"elliott"|"triggers"|"patterns"|"cone"

const TV_GREEN = "#089981"
const TV_RED = "#f23645"
const COL_BG = "#0d1117"
const COL_GRID = "#1f2937"
const COL_TEXT = "#6b7280"
const COL_PURPLE = "#a855f7"
const COL_BLUE = "#2962ff"
const COL_ORANGE = "#f59e0b"
const COL_GRAY = "#6b7280"

function n(v: unknown): number { return typeof v === "number" ? v : 0 }
function s(v: unknown): string { return v == null ? "" : String(v) }
function rgbAlpha(base: string, a: number): string {
  const m = base.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  if (m) return `rgba(${m[1]},${m[2]},${m[3]},${a})`
  try { const c = new Option().style; c.color = base; const s = c.color; if (s) return s.replace(/rgb\(/, "rgba(").replace(/\)$/, `,${a})`) } catch {}
  return `rgba(0,255,120,${a})`
}
function calcEMA(data: number[], p: number): number[] {
  if (data.length < p) return data.map(() => 0)
  const k = 2 / (p + 1); const r: number[] = []; let ema = data.slice(0, p).reduce((a, b) => a + b, 0) / p
  r.push(ema); for (let i = p; i < data.length; i++) { ema = (data[i] - ema) * k + ema; r.push(ema) }
  return [...new Array(p - 1).fill(0), ...r]
}
function calcLastEMA(data: number[], p: number): number {
  if (data.length < p) return 0; const f = calcEMA(data, p); return f[f.length - 1] || 0
}
function calcATR(data: Candle[], p: number): number {
  if (data.length < p + 1) return 0
  let sum = 0
  for (let i = data.length - p; i < data.length; i++) {
    const tr = Math.max(data[i].high - data[i].low, Math.abs(data[i].high - data[i - 1].close), Math.abs(data[i].low - data[i - 1].close))
    sum += tr
  }
  return sum / p
}

export function SKHYChart({ symbol, snapshot, analysis, triggers, sr, activeTimeframe, onTimeframeChange }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const offscreenRef = useRef<HTMLCanvasElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const volSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null)
  const ema20Ref = useRef<ISeriesApi<"Line"> | null>(null)
  const ema50Ref = useRef<ISeriesApi<"Line"> | null>(null)
  const ema100Ref = useRef<ISeriesApi<"Line"> | null>(null)
  const atrStopRef = useRef<ISeriesApi<"Line"> | null>(null)
  const rafRef = useRef<number>(0)
  const dirtyRef = useRef(true)
  const lastDrawnData = useRef<string>("")
  const lastValidOhlcvRef = useRef<Candle[]>([])
  const lastValidAnalysisRef = useRef<Record<string, unknown> | null>(null)

  const [ohlcv, setOhlcv] = useState<Candle[]>([])
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string[] } | null>(null)
  const [emaValues, setEmaValues] = useState({ ema20: 0, ema50: 0, ema100: 0 })
  const [dbg, setDbg] = useState<string>("")
  const [overlays, setOverlays] = useState<Record<OverlayKey, boolean>>({
    structure: true, channel: true, breakout: true, retest: true,
    fibonacci: true, targets: true, mainScenario: true, altScenario: false,
    fakeout: false, smc: true, liquidity: false, ema: false, atrStop: false,
    volumeProfile: false, elliott: false, triggers: true,
    patterns: true, cone: true,
  })
  const timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

  // ── cache last valid analysis + OHLCV to survive stale/null props ──
  useEffect(() => {
    if (analysis && analysis.scores) lastValidAnalysisRef.current = analysis
  }, [analysis])
  const activeAnalysis = analysis ?? lastValidAnalysisRef.current
  const hasAnalysis = !!(activeAnalysis?.scores)

  const scores = (activeAnalysis?.scores || {}) as Record<string, unknown>
  const tfs = (activeAnalysis?.timeframes || {}) as Record<string, unknown>
  const allStructs = activeAnalysis?.all_structures as Record<string, unknown>[] | undefined
  const patterns = activeAnalysis?.patterns as Record<string, unknown>[] | undefined
  const ew = activeAnalysis?.elliott_wave as Record<string, unknown> | undefined
  const fib = activeAnalysis?.fibonacci as Record<string, unknown> | undefined
  const ds = activeAnalysis?.detected_structure as Record<string, unknown> | undefined
  const cl = activeAnalysis?.channel_lines as Record<string, unknown> | undefined
  const bz = activeAnalysis?.breakout_zone as Record<string, unknown> | undefined
  const sp = activeAnalysis?.scenario_paths as Record<string, unknown> | undefined
  const th = activeAnalysis?.target_hierarchy as Record<string, unknown> | undefined
  const cb = activeAnalysis?.confidence_breakdown as Record<string, unknown> | undefined
  const supZone = activeAnalysis?.support_zone as Record<string, unknown> | undefined
  const resZone = activeAnalysis?.resistance_zone as Record<string, unknown> | undefined
  const invalLevel = n(activeAnalysis?.invalidation_level)
  const activePatterns = activeAnalysis?.active_patterns as Record<string, unknown>[] | undefined
  const tradePlan = activeAnalysis?.trade_plan as Record<string, unknown> | undefined

  const confidence = n(scores.signal_confidence)
  const longProb = n(scores.long_probability)
  const shortProb = n(scores.short_probability)
  const status = s(scores.status)
  const ltPrice = n(triggers.long_trigger_price)
  const stPrice = n(triggers.short_trigger_price)
  const price = n(snapshot?.live_price)
  const mainSc = sp?.main_scenario as Record<string, unknown> | undefined
  const mainDir = s(mainSc?.direction_az || mainSc?.direction || "")
  const mainProb = n(mainSc?.probability)

  // ── track canvas size to avoid unnecessary resize resets ──
  const canvasSizeRef = useRef({ w: 0, h: 0 })

  // ── drawOnCanvas: renders ALL overlays to offscreen ctx ──
  //     returns true if drawing completed, false if skipped
  const drawOnCanvas = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number): boolean => {
    const chart = chartRef.current; const cs = candleSeriesRef.current
    const data = ohlcv.length > 0 ? ohlcv : lastValidOhlcvRef.current
    // Skip render when no chart, no data, or no valid analysis
    if (!chart || !cs || data.length === 0 || !hasAnalysis) {
      const reason = !chart ? "NO_CHART" : !cs ? "NO_SERIES" : data.length === 0 ? "NO_DATA" : "NO_ANALYSIS"
      const tag = hasAnalysis ? "SKIP_NO_DATA" : "FRAME_REUSED_LAST_VALID"
      console.log(`[SKHY] ${tag} reason=${reason} chart=${!!chart} series=${!!cs} data=${data.length} analysis=${!!activeAnalysis?.scores}`)
      return false
    }
    const ts = chart.timeScale()
    const safeC = (v: number) => Number.isFinite(v) ? v : 0
    const toX = (t: number) => safeC(ts.timeToCoordinate(t as Time) ?? 0)
    const toY = (p: number) => safeC(cs.priceToCoordinate(p) ?? 0)
    const cw = data.length >= 2 ? Math.max(1, toX(data[data.length - 1].time) - toX(data[data.length - 2].time)) : 8
    const lx = toX(data[data.length - 1].time)
    const lp = data[data.length - 1].close
    const fX = (off: number) => { const v = lx + cw * off; return Number.isFinite(v) ? v : 0 }

    if (w <= 0 || h <= 0 || lx <= 0 || lp <= 0) {
      console.log("[SKHY] SKIP_NO_DIMS", { w, h, lx, lp })
      return false
    }

    console.log("[SKHY] FRAME_START")
    ctx.clearRect(0, 0, w, h)
    console.log("[SKHY] CLEAR")

    const called: string[] = []
    const wrap = (name: string, fn: () => void) => { try { fn(); called.push(name) } catch (e) { console.error(`[SKHY] ${name} error:`, e) } }

    // Priority z-order: background → foreground
    if (overlays.volumeProfile) wrap("volprof", () => drawVolProf(ctx, toX, toY, data, w, h, overlays))
    if (overlays.structure) { wrap("sr", () => drawSR(ctx, toX, toY, sr, price, w)); wrap("srz", () => drawSRZ(ctx, toX, toY, supZone, resZone, w, data)) }
    if (overlays.channel) wrap("channel", () => drawCh(ctx, toX, toY, cl, ds, w, data, lx, cw, lp))
    if (overlays.fibonacci) wrap("fib", () => drawFib(ctx, toX, toY, fib, w, data, lp))
    if (overlays.smc) wrap("smc", () => drawSMC(ctx, toX, toY, activeAnalysis, data, w))
    if (overlays.liquidity) wrap("liq", () => drawLiq(ctx, toX, toY, sr, w))
    if (overlays.breakout) wrap("breakout", () => drawBO(ctx, toX, toY, bz, w, h, data, lx, cw))
    if (overlays.patterns) wrap("patterns", () => drawPats(ctx, toX, toY, activePatterns || patterns, data, w))
    if (overlays.retest && ds) wrap("retest", () => drawRet(ctx, toX, toY, ds, w, lx, cw))
    if (overlays.cone || overlays.mainScenario || overlays.altScenario || overlays.fakeout) wrap("future", () => drawFP(ctx, toX, toY, sp, cb, confidence, data, w, h, lx, lp, cw, fX, overlays))
    if (overlays.targets) wrap("targets", () => drawTgt(ctx, toX, toY, th, fib, w, data, lx, lp, cw, confidence, status))
    if (overlays.targets) wrap("inval", () => drawInv(ctx, toX, toY, invalLevel, w, lx, cw))
    if (overlays.triggers) wrap("triggers", () => drawTrig(ctx, toX, toY, triggers, scores, w, lx, cw, confidence))
    if (overlays.elliott) wrap("elliott", () => drawEW(ctx, toX, toY, ew, w, data, confidence))
    wrap("legend", () => drawLegend(ctx, w, h, overlays, activePatterns || patterns, mainSc, confidence, activeAnalysis))

    console.log(`[SKHY] DRAW_COMPLETE layers=${called.join(",")}`)
    setDbg(`[${new Date().toISOString().slice(11,19)}] ${called.join(",")}`)
    return true
  }, [ohlcv, overlays, activeAnalysis, triggers, scores, sr, patterns, ew, fib, ds, cl, bz, sp, th, cb, confidence, price, supZone, resZone, invalLevel, activePatterns, tradePlan, mainSc, ltPrice, stPrice, longProb, shortProb, hasAnalysis])

  // ── rAF render loop: only commits frame if drawOnCanvas completed ──
  useEffect(() => {
    const loop = () => {
      const canvas = overlayRef.current; const off = offscreenRef.current
      if (!canvas || !off) { rafRef.current = requestAnimationFrame(loop); return }
      if (!dirtyRef.current) {
        rafRef.current = requestAnimationFrame(loop)
        return // SKIP_NO_DIRTY — never touch canvas when clean
      }
      const rect = canvas.getBoundingClientRect()
      const w = rect.width; const h = rect.height
      if (w <= 0 || h <= 0) { rafRef.current = requestAnimationFrame(loop); return }
      const dpr = window.devicePixelRatio
      const cw = w * dpr; const ch = h * dpr
      // Only resize when dimensions actually change (avoids canvas auto-clear)
      const sz = canvasSizeRef.current
      if (sz.w !== cw || sz.h !== ch) {
        off.width = cw; off.height = ch
        canvas.width = cw; canvas.height = ch
        sz.w = cw; sz.h = ch
        console.log("[SKHY] RESIZED", { cw, ch })
      }
      const octx = off.getContext("2d")
      if (!octx) { rafRef.current = requestAnimationFrame(loop); return }
      octx.scale(dpr, dpr)
      const completed = drawOnCanvas(octx, w, h)
      if (completed) {
        const vctx = canvas.getContext("2d")
        if (vctx) {
          vctx.clearRect(0, 0, cw, ch)
          vctx.drawImage(off, 0, 0)
          console.log("[SKHY] COMMIT")
        }
        dirtyRef.current = false
      } else {
        console.log("[SKHY] SKIP — keeping previous frame")
      }
      rafRef.current = requestAnimationFrame(loop)
    }
    rafRef.current = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(rafRef.current)
  }, [drawOnCanvas])

  // ── init offscreen canvas ──
  useEffect(() => {
    offscreenRef.current = document.createElement("canvas")
    dirtyRef.current = true
  }, [])

  const markDirty = useCallback(() => { dirtyRef.current = true }, [])

  // ── OHLCV fetch ──
  useEffect(() => {
    let cancelled = false
    const reqId = Date.now()
    api.getSkhyOHLCV(activeTimeframe, 240).then((res) => {
      if (cancelled) { console.log(`[SKHY] OHLCV_REJECTED_STALE reqId=${reqId}`); return }
      if (res?.data && Array.isArray(res.data) && (res.data as Candle[]).length > 0) {
        setOhlcv(res.data)
        lastValidOhlcvRef.current = res.data as Candle[]
        const closes = (res.data as Candle[]).map((d: Candle) => d.close)
        if (closes.length >= 100) setEmaValues({ ema20: calcLastEMA(closes, 20), ema50: calcLastEMA(closes, 50), ema100: calcLastEMA(closes, 100) })
        console.log(`[SKHY] OHLCV_ACCEPTED reqId=${reqId} candles=${(res.data as Candle[]).length}`)
      } else {
        console.log(`[SKHY] OHLCV_REJECTED_EMPTY reqId=${reqId}`)
      }
    }).catch(() => { console.log(`[SKHY] OHLCV_ERROR reqId=${reqId}`) })
    return () => { cancelled = true }
  }, [activeTimeframe])

  // ── Chart creation ──
  useEffect(() => {
    if (!containerRef.current) return
    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: COL_BG }, textColor: COL_TEXT, fontSize: 11 },
      grid: { vertLines: { color: COL_GRID }, horzLines: { color: COL_GRID } },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#374151", scaleMargins: { top: 0.05, bottom: 0.25 } },
      timeScale: { borderColor: "#374151", timeVisible: true, secondsVisible: false, fixRightEdge: false, shiftVisibleRangeOnNewBar: false },
      autoSize: true, handleScroll: { vertTouchDrag: false },
    })
    chartRef.current = chart
    candleSeriesRef.current = chart.addSeries(CandlestickSeries, { upColor: TV_GREEN, downColor: TV_RED, borderDownColor: TV_RED, borderUpColor: TV_GREEN, wickDownColor: TV_RED, wickUpColor: TV_GREEN })
    volSeriesRef.current = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "volume" })
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.88, bottom: 0 } })
    ema20Ref.current = chart.addSeries(LineSeries, { color: COL_ORANGE, lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
    ema50Ref.current = chart.addSeries(LineSeries, { color: COL_BLUE, lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
    ema100Ref.current = chart.addSeries(LineSeries, { color: COL_PURPLE, lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
    atrStopRef.current = chart.addSeries(LineSeries, { color: "#f97316", lineWidth: 1, lineStyle: 3, priceLineVisible: false, lastValueVisible: false })
    return () => chart.remove()
  }, [])

  // ── Data sync ──
  useEffect(() => {
    if (!candleSeriesRef.current || !volSeriesRef.current || !ohlcv.length) return
    const candleData = ohlcv.map((d: Candle) => ({ time: d.time as Time, open: d.open, high: d.high, low: d.low, close: d.close }))
    const volData = ohlcv.map((d: Candle) => ({ time: d.time as Time, value: d.volume, color: d.close >= d.open ? "rgba(8,153,129,0.3)" : "rgba(242,54,69,0.3)" }))
    candleSeriesRef.current.setData(candleData)
    volSeriesRef.current.setData(volData)
    if (overlays.ema) {
      const closes = ohlcv.map((d: Candle) => d.close)
      const e20 = calcEMA(closes, 20); const e50 = calcEMA(closes, 50); const e100 = calcEMA(closes, 100)
      ema20Ref.current?.setData(e20.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter(d => d.value > 0))
      ema50Ref.current?.setData(e50.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter(d => d.value > 0))
      ema100Ref.current?.setData(e100.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter(d => d.value > 0))
    } else { ema20Ref.current?.setData([]); ema50Ref.current?.setData([]); ema100Ref.current?.setData([]) }
    if (overlays.atrStop) {
      const atr = calcATR(ohlcv, 14); const stopMult = 2.5
      const stopData = ohlcv.map((d, i) => ({ time: d.time as Time, value: i >= 14 ? Math.round((d.close - (d.close >= ohlcv[i - 1]?.close ? atr : -atr) * stopMult) * 100) / 100 : 0 })).filter(d => d.value > 0)
      atrStopRef.current?.setData(stopData)
    } else atrStopRef.current?.setData([])
    const chart = chartRef.current
    if (chart) {
      chart.timeScale().fitContent()
      const vr = chart.timeScale().getVisibleLogicalRange()
      if (vr) chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, ohlcv.length - 60), to: ohlcv.length + 55 })
    }
    markDirty()
  }, [ohlcv, overlays, markDirty])

  useEffect(() => { markDirty() }, [markDirty, analysis, triggers, sr, confidence, price])

  // ── Hover handler ──
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const canvas = overlayRef.current; const chart = chartRef.current
    if (!canvas || !chart) { setTooltip(null); return }
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left; const my = e.clientY - rect.top
    const t = chart.timeScale().coordinateToTime(mx) as number | null; const pr = candleSeriesRef.current?.coordinateToPrice(my)
    if (t == null || pr == null) { setTooltip(null); return }
    const lines = buildHover(pr, ohlcv, allStructs, patterns, ds, bz, th, cl, sp, ew, fib)
    if (lines.length > 0) setTooltip({ x: e.clientX - rect.left + 12, y: e.clientY - rect.top - 12, text: lines })
    else setTooltip(null)
  }, [allStructs, patterns, ds, bz, th, cl, sp, ew, fib, ohlcv])
  const handleMouseLeave = () => setTooltip(null)

  const toggleOverlay = useCallback((key: OverlayKey) => {
    setOverlays(prev => ({ ...prev, [key]: !prev[key] })); dirtyRef.current = true
  }, [])

  const confTier = confidence >= 80 ? 4 : confidence >= 70 ? 3 : confidence >= 50 ? 2 : 1
  const toggleItems: { key: OverlayKey; label: string }[] = [
    { key: "structure", label: "Struktur" }, { key: "channel", label: "Kanal" },
    { key: "breakout", label: "Breakout" }, { key: "fibonacci", label: "Fib" },
    { key: "targets", label: "Hədəflər" }, { key: "triggers", label: "Trigger" },
    { key: "mainScenario", label: "Əsas" }, { key: "altScenario", label: "Alt" },
    { key: "fakeout", label: "Fakeout" }, { key: "smc", label: "SMC" },
    { key: "liquidity", label: "Likvid" }, { key: "ema", label: "EMA" },
    { key: "atrStop", label: "ATR" }, { key: "volumeProfile", label: "Həcm" },
    { key: "elliott", label: "Elliott" }, { key: "patterns" as OverlayKey, label: "Pattern" },
    { key: "cone" as OverlayKey, label: "Konus" },
  ]

  return (
    <div className="h-full flex flex-col relative">
      <div className="flex items-center px-2 py-0.5 border-b border-gray-800/40 bg-gray-950/60 z-10 shrink-0">
        {timeframes.map((t) => {
          const sig = s((tfs[t] as Record<string, unknown>)?.signal)
          const sigC = sig.includes("LONG") ? "text-green-400 bg-green-500/10" : sig.includes("SHORT") ? "text-red-400 bg-red-500/10" : "text-gray-500 bg-gray-800/30"
          return (
            <button key={t} onClick={() => onTimeframeChange(t)}
              className={cn("flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] font-mono rounded transition-colors mr-0.5", activeTimeframe === t ? "bg-blue-600/20 border border-blue-500/30" : "hover:bg-gray-800/30")}>
              <span className="text-gray-500">{t}</span>
              {sig && <span className={cn("px-0.5 rounded text-[8px] font-bold", sigC)}>{sig.includes("LONG") ? "↑" : sig.includes("SHORT") ? "↓" : "−"}</span>}
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
          <span className={cn("text-[8px] px-1 py-0.5 rounded font-semibold", confTier >= 4 ? "bg-green-500/20 text-green-400" : confTier >= 3 ? "bg-blue-500/20 text-blue-400" : confTier >= 2 ? "bg-yellow-500/20 text-yellow-400" : "bg-gray-500/20 text-gray-400")}>
            {confTier >= 4 ? "GÜCLÜ HAZIR" : confTier >= 3 ? "HAZIRDIR" : confTier >= 2 ? "İZLƏMƏ" : "GÖZLƏYİN"}</span>
          {tradePlan?.trade_ready ? <span className="text-[8px] px-1 py-0.5 rounded font-semibold bg-green-500/20 text-green-400 border border-green-500/30">TP HAZIR</span> : null}
        </div>
        <span className="text-[8px] text-gray-700 font-mono mr-1">{dbg || symbol}</span>
      </div>
      <div className="relative flex-1" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
        <div ref={containerRef} className="absolute inset-0" />
        {price > 0 && (
          <>
            <div className="absolute top-2 left-2 z-[6] flex flex-wrap gap-x-2 gap-y-0.5 text-[9px] pointer-events-none max-w-[65%]">
              {ds && s(ds.label_az) && <span className="px-1.5 py-0.5 rounded bg-gray-900/80 border border-gray-700/50 text-gray-300 font-mono text-[8px]">{s(ds.label_az)}{s(ds.breakout_status) ? ` · ${s(ds.breakout_status)}` : ""}</span>}
              <div className={cn("px-1.5 py-0.5 rounded font-bold font-mono", longProb > shortProb ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400")}>
                {longProb > shortProb ? `↑ ALIŞ ${longProb}%` : `↓ SATIŞ ${shortProb}%`}</div>
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
        <canvas ref={overlayRef} className="absolute inset-0 pointer-events-none z-[999]" />
        {tooltip && (
          <div className="absolute z-10 pointer-events-none bg-gray-900/95 border border-gray-700 rounded px-2 py-1 text-[9px] text-gray-200 shadow-xl max-w-[280px] whitespace-pre-line" style={{ left: tooltip.x, top: tooltip.y }}>
            {tooltip.text.map((line, i) => <div key={i}>{line}</div>)}
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

// ══════════════════════════════════════════════════
//  1. drawFP — Future Projection (cone + 3 paths)
// ══════════════════════════════════════════════════

function drawFP(
  ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number,
  sp: Record<string, unknown> | undefined, cb: Record<string, unknown> | undefined,
  confidence: number, ohlcv: Candle[], w: number, h: number,
  lx: number, lp: number, cw: number, fX: (off: number) => number,
  ov: Record<string, boolean>,
) {
  if (!sp || ohlcv.length === 0) return
  const avr = ohlcv.length >= 14 ? calcATR(ohlcv, 14) / lp : 0.01

  const drawPath = (key: string, which: "main" | "alt" | "fakeout") => {
    const sc = sp[key] as Record<string, unknown> | undefined
    if (!sc) return
    const pts = sc.path_points as PathPoint[] | undefined
    if (!pts || pts.length < 2) return
    const dir = s(sc.direction); const isLong = dir === "LONG" || dir === "BULLISH"
    const sigConf = cb ? n(cb.signal_confidence) : confidence
    const isMain = which === "main"

    let color: string; let lw: number; let dash: number[]; let alpha: number
    if (which === "main") {
      color = isLong ? TV_GREEN : TV_RED; lw = 2; dash = []; alpha = Math.min(1, 0.5 + sigConf / 200)
    } else if (which === "alt") {
      color = COL_GRAY; lw = 1; dash = [4, 4]; alpha = 0.5
    } else {
      color = COL_ORANGE; lw = 1.5; dash = [2, 4, 2, 6]; alpha = 0.6
    }

    const startX = fX(0.5); const startY = toY(lp)
    if (startX <= 0 || startY <= 0) return

    ctx.save(); ctx.globalAlpha = alpha
    ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.setLineDash(dash)
    ctx.beginPath(); ctx.moveTo(startX, startY)
    let drawn = false
    for (const p of pts) {
      if (p.time_offset === 0) continue
      const x = fX(p.time_offset); const y = toY(p.price)
      if (y <= 0) continue; ctx.lineTo(x, y); drawn = true
    }
    if (drawn) ctx.stroke()
    ctx.setLineDash([])

    // Zig-zag arrows on main
    if (isMain && sigConf >= 40) {
      ctx.globalAlpha = Math.min(1, alpha * 1.5)
      const allPts = [{ x: startX, y: startY, p: lp }, ...pts.filter(p => p.time_offset > 0).map(p => ({ x: fX(p.time_offset), y: toY(p.price), p: p.price }))]
      for (let i = 1; i < allPts.length; i++) {
        const p0 = allPts[i - 1]; const p1 = allPts[i]
        if (p0.y <= 0 || p1.y <= 0 || p0.x <= 0 || p1.x <= 0) continue
        const mx = (p0.x + p1.x) / 2; const my = (p0.y + p1.y) / 2
        const ang = Math.atan2(p1.y - p0.y, p1.x - p0.x); const al = 5; const aa = 0.35
        ctx.fillStyle = color; ctx.beginPath()
        ctx.moveTo(mx + al * Math.cos(ang), my + al * Math.sin(ang))
        ctx.lineTo(mx - al * Math.cos(ang - aa), my - al * Math.sin(ang - aa))
        ctx.lineTo(mx - al * Math.cos(ang + aa), my - al * Math.sin(ang + aa))
        ctx.closePath(); ctx.fill()
      }
    }

    // Labels on main scenario
    if (isMain && sigConf >= 40) {
      ctx.globalAlpha = Math.min(1, alpha * 1.8)
      for (const p of pts) {
        if (p.time_offset === 0) continue
        const x = fX(p.time_offset); const y = toY(p.price)
        if (y <= 0) continue
        ctx.font = "bold 7px monospace"; ctx.fillStyle = color; ctx.textAlign = "center"
        ctx.fillText(p.label, x, Math.max(10, y - 8))
        ctx.beginPath(); ctx.arc(x, y, 3.5, 0, Math.PI * 2); ctx.fill()
        ctx.textAlign = "left"
      }
    }

    // Final label
    const lastP = pts[pts.length - 1]; const lx2 = fX(lastP.time_offset); const ly2 = toY(lastP.price)
    if (ly2 > 0) {
      ctx.globalAlpha = Math.min(1, alpha * 2)
      const prob = n(sc.probability); const lbl = isMain ? `ƏSAS ${prob}%` : which === "alt" ? `ALT ${prob}%` : `FAKEOUT ${prob}%`
      ctx.font = "bold 7px monospace"; ctx.fillStyle = color; ctx.textAlign = "center"
      ctx.fillText(lbl, lx2, Math.max(10, ly2 - 18))
      ctx.font = "7px monospace"; ctx.fillText(`$${lastP.price.toFixed(2)}`, lx2, Math.max(10, ly2 - 4))
      ctx.textAlign = "left"
    }
    ctx.restore()
  }

  // ── Probability cone (behind main path) ──
  if (ov.cone) {
    const mainSc = sp.main_scenario as Record<string, unknown> | undefined
    if (mainSc) {
      const pts = mainSc.path_points as PathPoint[] | undefined
      if (pts && pts.length >= 2) {
        const conePts: { x: number; y: number; prob: number; off: number; price: number }[] = [{ x: fX(0.5), y: toY(lp), prob: 100, off: 0, price: lp }]
        for (const p of pts) {
          if (p.time_offset === 0) continue
          const cx = fX(p.time_offset); const cy = toY(p.price)
          if (cy > 0) conePts.push({ x: cx, y: cy, prob: p.probability || 50, off: p.time_offset, price: p.price })
        }
        const up: { x: number; y: number }[] = []; const dn: { x: number; y: number }[] = []
        for (const pt of conePts) {
          const unc = avr * (1 - pt.prob / 100) * Math.sqrt(pt.off + 1) * 3
          const off = pt.price * unc
          const uy = toY(pt.price + off); const dy = toY(pt.price - off)
          if (uy > 0 && dy > 0) { up.push({ x: pt.x, y: uy }); dn.push({ x: pt.x, y: dy }) }
        }
        if (up.length >= 2 && dn.length >= 2) {
          ctx.save()
          ctx.beginPath(); ctx.moveTo(up[0].x, up[0].y)
          for (let i = 1; i < up.length; i++) ctx.lineTo(up[i].x, up[i].y)
          for (let i = dn.length - 1; i >= 0; i--) ctx.lineTo(dn[i].x, dn[i].y)
          ctx.closePath()
          const g = ctx.createLinearGradient(fX(0.5), up[0].y, fX(0.5), dn[0].y)
          g.addColorStop(0, "rgba(8,153,129,0.12)")
          g.addColorStop(0.5, "rgba(8,153,129,0.06)")
          g.addColorStop(1, "rgba(8,153,129,0.12)")
          ctx.fillStyle = g; ctx.fill()
          ctx.strokeStyle = "rgba(8,153,129,0.1)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 6])
          ctx.beginPath(); ctx.moveTo(up[0].x, up[0].y)
          for (let i = 1; i < up.length; i++) { ctx.lineTo(up[i].x, up[i].y) }
          ctx.stroke()
          ctx.beginPath(); ctx.moveTo(dn[0].x, dn[0].y)
          for (let i = 1; i < dn.length; i++) { ctx.lineTo(dn[i].x, dn[i].y) }
          ctx.stroke()
          ctx.setLineDash([])
          const last = conePts[conePts.length - 1]
          if (last.y > 0) {
            ctx.font = "7px monospace"; ctx.fillStyle = "rgba(8,153,129,0.3)"; ctx.textAlign = "center"
            ctx.fillText("Ehtimal konusu", last.x, Math.min(up[up.length - 1].y, dn[dn.length - 1].y) - 6); ctx.textAlign = "left"
          }
          ctx.restore()
        }
      }
    }
  }

  // Draw paths
  if (ov.mainScenario) drawPath("main_scenario", "main")
  if (ov.altScenario) drawPath("alternative_scenario", "alt")
  if (ov.fakeout) drawPath("fakeout_scenario", "fakeout")
}

// ══════════════════════════════════════════════════
//  2. drawPats — Pattern Renderer (Bezier / SVG)
// ══════════════════════════════════════════════════

function drawPats(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, pats: Record<string, unknown>[] | undefined, ohlcv: Candle[], w: number) {
  if (!pats || ohlcv.length === 0) return
  const sorted = [...pats].sort((a, b) => n(b.probability) - n(a.probability))
  const best = sorted[0]
  if (!best || n(best.probability) < 50) return
  const pat = best; const name = s(pat.name); const prob = n(pat.probability)
  const bLv = n(pat.breakout_level) || n(pat.breakdown_level); const mTgt = n(pat.measured_target)
  const confirmed = s(pat.status) === "CONFIRMED"
  const clr = confirmed ? "rgba(8,153,129,0.7)" : s(pat.status) === "DETECTED" ? "rgba(245,158,11,0.6)" : "rgba(107,114,128,0.4)"
  const lclr = confirmed ? TV_GREEN : s(pat.status) === "DETECTED" ? COL_ORANGE : COL_GRAY
  const stLbl: Record<string, string> = { CONFIRMED: "TƏSDİQLƏNDİ", DETECTED: "ASKAR", FORMING: "FORMALAŞIR" }

  const dm = (bl: number, mt: number, c: string) => {
    if (bl <= 0 || mt <= 0) return; const y1 = toY(bl); const y2 = toY(mt)
    if (y1 <= 0 || y2 <= 0) return; ctx.strokeStyle = c; ctx.lineWidth = 0.5; ctx.setLineDash([3, 4])
    ctx.beginPath(); ctx.moveTo(w - 42, y1); ctx.lineTo(w - 42, y2); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = c; ctx.fillText(`→$${mt.toFixed(1)}`, w - 40, (y1 + y2) / 2)
  }

  if (name.includes("Cup and Handle")) {
    const rim = n(pat.cup_rim); const bot = n(pat.cup_bottom); const hLow = n(pat.handle_low)
    const si = Math.max(0, ohlcv.length - 35); const mi = Math.floor((ohlcv.length + si) / 2); const ei = ohlcv.length - 1
    const x0 = toX(ohlcv[si].time); const xm = toX(ohlcv[mi].time); const x1 = toX(ohlcv[ei].time)
    const yr = toY(rim); const yb = toY(bot); const yh = toY(hLow || bot)
    if (x0 > 0 && xm > 0 && x1 > 0 && yr > 0 && yb > 0) {
      ctx.save(); ctx.strokeStyle = clr; ctx.lineWidth = 1.8; ctx.setLineDash([])
      ctx.beginPath(); ctx.moveTo(x0, yr)
      ctx.bezierCurveTo((x0 + xm) / 2, yr, xm * 0.8, yb, xm, yb)
      ctx.bezierCurveTo(xm * 1.2, yb, (xm + x1) / 2, yr, x1, yr)
      ctx.stroke()
      if (hLow > 0 && rim > hLow) {
        ctx.strokeStyle = "rgba(245,158,11,0.5)"; ctx.lineWidth = 0.8; ctx.setLineDash([3, 4])
        const hx = x1 - (x1 - xm) * 0.35; ctx.beginPath(); ctx.moveTo(hx, yr); ctx.lineTo(hx, yh); ctx.stroke(); ctx.setLineDash([])
        ctx.font = "7px monospace"; ctx.fillStyle = "rgba(245,158,11,0.6)"; ctx.fillText("Handle", hx + 3, (yr + yh) / 2)
      }
      ctx.font = "bold 8px monospace"; ctx.fillStyle = lclr; ctx.fillText("C&H", xm - 14, yb + 18)
      ctx.restore()
    }
    dm(bLv, mTgt, clr)
  } else if (name.includes("Head and Shoulders") || name.includes("Inverse Head")) {
    const isInv = name.includes("Inverse")
    const iL = Math.floor(ohlcv.length * 0.12); const iH = Math.floor(ohlcv.length * 0.35); const iR = Math.floor(ohlcv.length * 0.55)
    const pL = ohlcv[Math.min(iL, ohlcv.length - 1)]?.close || 0; const pH = ohlcv[Math.min(iH, ohlcv.length - 1)]?.close || 0; const pR = ohlcv[Math.min(iR, ohlcv.length - 1)]?.close || 0
    const xL = toX(ohlcv[Math.min(iL, ohlcv.length - 1)].time); const xH = toX(ohlcv[Math.min(iH, ohlcv.length - 1)].time); const xR = toX(ohlcv[Math.min(iR, ohlcv.length - 1)].time)
    const yL = toY(pL); const yH = toY(pH); const yR = toY(pR)
    if (xL > 0 && xH > 0 && xR > 0 && yL > 0 && yH > 0 && yR > 0) {
      ctx.save(); ctx.strokeStyle = clr; ctx.lineWidth = 0.8; const rSz = isInv ? 7 : 5; const rH = isInv ? 5 : 7
      ctx.beginPath(); ctx.arc(xL, yL, rSz, 0, Math.PI * 2); ctx.stroke()
      ctx.beginPath(); ctx.arc(xH, yH, rH, 0, Math.PI * 2); ctx.stroke()
      ctx.beginPath(); ctx.arc(xR, yR, rSz, 0, Math.PI * 2); ctx.stroke()
      ctx.font = "7px monospace"; ctx.fillStyle = lclr; ctx.fillText("LS", xL + rSz + 3, yL + 3); ctx.fillText("HD", xH + rH + 4, yH + 3); ctx.fillText("RS", xR + rSz + 3, yR + 3)
      const neckY = isInv ? Math.max(yL, yR) : Math.min(yL, yR)
      ctx.strokeStyle = "rgba(242,54,69,0.4)"; ctx.lineWidth = 0.8; ctx.setLineDash([3, 4])
      ctx.beginPath(); ctx.moveTo(xL, neckY); ctx.lineTo(xR, neckY); ctx.stroke(); ctx.setLineDash([])
      ctx.font = "6px monospace"; ctx.fillStyle = "rgba(242,54,69,0.5)"; ctx.fillText("Boyun xətti", (xL + xR) / 2 - 20, neckY - 3)
      ctx.restore()
    }
    dm(bLv, mTgt, clr)
  } else if (name.includes("Double Top") || name.includes("Double Bottom")) {
    const isTop = name.includes("Top")
    const i1 = Math.floor(ohlcv.length * 0.2); const i2 = Math.floor(ohlcv.length * 0.5)
    const x1 = toX(ohlcv[Math.min(i1, ohlcv.length - 1)].time); const x2 = toX(ohlcv[Math.min(i2, ohlcv.length - 1)].time)
    const p1 = ohlcv[Math.min(i1, ohlcv.length - 1)]?.close || 0; const p2 = ohlcv[Math.min(i2, ohlcv.length - 1)]?.close || 0
    const y1 = toY(p1); const y2 = toY(p2)
    if (x1 > 0 && x2 > 0 && y1 > 0 && y2 > 0) {
      ctx.save(); ctx.strokeStyle = clr; ctx.lineWidth = 1.2
      ctx.beginPath(); ctx.arc(x1, y1, 6, 0, Math.PI * 2); ctx.stroke()
      ctx.beginPath(); ctx.arc(x2, y2, 6, 0, Math.PI * 2); ctx.stroke()
      ctx.font = "bold 7px monospace"; ctx.fillStyle = lclr
      ctx.fillText(isTop ? "①" : "①", x1 + 7, y1 + 3); ctx.fillText(isTop ? "②" : "②", x2 + 7, y2 + 3)
      const neckY = isTop ? Math.max(y1, y2) : Math.min(y1, y2)
      ctx.strokeStyle = "rgba(242,54,69,0.3)"; ctx.lineWidth = 0.5; ctx.setLineDash([3, 4])
      ctx.beginPath(); ctx.moveTo(x1, neckY); ctx.lineTo(x2, neckY); ctx.stroke(); ctx.setLineDash([])
      ctx.restore()
    }
    dm(bLv, mTgt, clr)
  } else if (name.includes("Wedge")) {
    const isRising = name.includes("Rising"); const si = Math.max(0, ohlcv.length - 18); const ei = ohlcv.length - 1
    const xs = toX(ohlcv[si].time); const xe = toX(ohlcv[ei].time)
    if (xs > 0 && xe > 0) {
      const lb = ohlcv.slice(si); const top1 = lb[0].high; const top2 = lb[lb.length - 1].high; const bot1 = lb[0].low; const bot2 = lb[lb.length - 1].low
      const yt1 = toY(top1); const yt2 = toY(top2); const yb1 = toY(bot1); const yb2 = toY(bot2)
      if (yt1 > 0 && yt2 > 0 && yb1 > 0 && yb2 > 0) {
        ctx.save(); ctx.strokeStyle = clr; ctx.lineWidth = 1; ctx.setLineDash([2, 3])
        ctx.beginPath(); ctx.moveTo(xs, yt1); ctx.lineTo(xe, yt2); ctx.stroke()
        ctx.beginPath(); ctx.moveTo(xs, yb1); ctx.lineTo(xe, yb2); ctx.stroke(); ctx.setLineDash([])
        ctx.fillStyle = clr.replace("0.7)", "0.05)").replace("0.8)", "0.06)").replace("0.5)", "0.03)")
        ctx.beginPath(); ctx.moveTo(xs, yt1); ctx.lineTo(xe, yt2); ctx.lineTo(xe, yb2); ctx.lineTo(xs, yb1); ctx.closePath(); ctx.fill()
        ctx.font = "7px monospace"; ctx.fillStyle = lclr; ctx.fillText(isRising ? "Rising Wedge" : "Falling Wedge", (xs + xe) / 2 - 30, (yt1 + yb2) / 2)
        ctx.restore()
      }
    }
    dm(bLv, mTgt, clr)
  } else if (name.includes("Triangle")) {
    const isAsc = name.includes("Ascending"); const isDesc = name.includes("Descending")
    const si = Math.max(0, ohlcv.length - 18); const ei = ohlcv.length - 1
    const xs = toX(ohlcv[si].time); const xe = toX(ohlcv[ei].time)
    if (xs > 0 && xe > 0) {
      const lb = ohlcv.slice(si); const top1 = lb[0].high; const top2 = lb[lb.length - 1].high; const bot1 = lb[0].low; const bot2 = lb[lb.length - 1].low
      const yt1 = toY(top1); const yt2 = toY(top2); const yb1 = toY(bot1); const yb2 = toY(bot2)
      if (yt1 > 0 && yt2 > 0 && yb1 > 0 && yb2 > 0) {
        ctx.save(); ctx.strokeStyle = clr; ctx.lineWidth = 1; ctx.setLineDash(isAsc || isDesc ? [] : [2, 3])
        if (isAsc) { ctx.beginPath(); ctx.moveTo(xs, yt1); ctx.lineTo(xe, yt2); ctx.stroke(); ctx.strokeStyle = clr.replace("0.7)", "0.5)").replace("0.8)", "0.6)").replace("0.5)", "0.3)"); ctx.beginPath(); ctx.moveTo(xs, yb1); ctx.lineTo(xe, yb2); ctx.stroke(); ctx.fillStyle = clr.replace("0.7)", "0.05)").replace("0.8)", "0.06)").replace("0.5)", "0.03)") }
        else if (isDesc) { ctx.strokeStyle = clr.replace("0.7)", "0.5)").replace("0.8)", "0.6)").replace("0.5)", "0.3)"); ctx.beginPath(); ctx.moveTo(xs, yt1); ctx.lineTo(xe, yt2); ctx.stroke(); ctx.strokeStyle = clr; ctx.beginPath(); ctx.moveTo(xs, yb1); ctx.lineTo(xe, yb2); ctx.stroke(); ctx.fillStyle = clr.replace("0.7)", "0.05)").replace("0.8)", "0.06)").replace("0.5)", "0.03)") }
        else { ctx.beginPath(); ctx.moveTo(xs, yt1); ctx.lineTo(xe, yt2); ctx.stroke(); ctx.beginPath(); ctx.moveTo(xs, yb1); ctx.lineTo(xe, yb2); ctx.stroke(); ctx.fillStyle = clr.replace("0.7)", "0.04)").replace("0.8)", "0.05)").replace("0.5)", "0.02)") }
        ctx.setLineDash([])
        ctx.beginPath(); ctx.moveTo(xs, yt1); ctx.lineTo(xe, yt2); ctx.lineTo(xe, yb2); ctx.lineTo(xs, yb1); ctx.closePath(); ctx.fill()
        ctx.font = "7px monospace"; ctx.fillStyle = lclr; ctx.fillText(name, (xs + xe) / 2 - 30, (yt1 + yb2) / 2)
        ctx.restore()
      }
    }
    dm(bLv, mTgt, clr)
  } else if (name.includes("Rectangle") || name.includes("Range")) {
    const si = Math.max(0, ohlcv.length - 22); const ei = ohlcv.length - 1
    const xs = toX(ohlcv[si].time); const xe = toX(ohlcv[ei].time)
    const tV = n(pat.breakout_level) || Math.max(...ohlcv.slice(si).map(d => d.high))
    const bV = n(pat.breakdown_level) || Math.min(...ohlcv.slice(si).map(d => d.low))
    const yT = toY(tV); const yB = toY(bV)
    if (xs > 0 && xe > 0 && yT > 0 && yB > 0) {
      ctx.save(); ctx.strokeStyle = "rgba(99,102,241,0.35)"; ctx.lineWidth = 1; ctx.setLineDash([4, 4])
      ctx.strokeRect(xs, yT, xe - xs, yB - yT); ctx.fillStyle = "rgba(99,102,241,0.04)"; ctx.fillRect(xs, yT, xe - xs, yB - yT); ctx.setLineDash([])
      ctx.restore()
    }
    dm(bLv, mTgt, clr)
  } else if (name.includes("Flag") || name.includes("Pennant")) {
    const si = Math.max(0, ohlcv.length - 16); const xs = toX(ohlcv[si].time); const xe = toX(ohlcv[ohlcv.length - 1].time)
    const yH = toY(Math.max(...ohlcv.slice(si).map(d => d.high))); const yL = toY(Math.min(...ohlcv.slice(si).map(d => d.low)))
    if (xs > 0 && xe > 0 && yH > 0 && yL > 0) {
      ctx.save(); ctx.strokeStyle = clr; ctx.lineWidth = 0.6; ctx.setLineDash([2, 3])
      ctx.strokeRect(xs, yH, xe - xs, yL - yH); ctx.setLineDash([])
      ctx.font = "7px monospace"; ctx.fillStyle = lclr; ctx.fillText(name.includes("Bull") ? "Bull Flag" : name.includes("Bear") ? "Bear Flag" : "Pennant", xs + 2, yH - 3)
      ctx.restore()
    }
    dm(bLv, mTgt, clr)
  }

  ctx.save(); ctx.font = "7px monospace"; ctx.fillStyle = lclr
  ctx.fillText(`${name} ${stLbl[s(pat.status)] || s(pat.status)} ${prob}% · ${s(pat.timeframe)}`, 10, 28)
  ctx.restore()
}

// ══════════════════════════════════════════════════
//  3. drawVolProf — Volume Profile (TradingView style)
// ══════════════════════════════════════════════════

function drawVolProf(ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number, ohlcv: Candle[], w: number, h: number, ov: Record<string, boolean>) {
  if (ohlcv.length < 50) return
  const mn = Math.min(...ohlcv.map(d => d.low)); const mx = Math.max(...ohlcv.map(d => d.high))
  const rng = mx - mn; if (rng <= 0) return
  const B = 30; const bs = rng / B
  const bins = new Array(B).fill(0)
  for (const d of ohlcv) bins[Math.min(B - 1, Math.max(0, Math.floor((d.close - mn) / bs)))] += d.volume
  const maxV = Math.max(...bins); if (maxV <= 0) return
  const totalV = bins.reduce((a, b) => a + b, 0)
  const barMaxW = 72

  const sorted = bins.map((v, i) => ({ v, i })).sort((a, b) => b.v - a.v)
  let cum = 0; const vaSet = new Set<number>()
  for (const item of sorted) { if (cum / totalV >= 0.7) break; vaSet.add(item.i); cum += item.v }
  let vaH = -Infinity; let vaL = Infinity
  for (const i of vaSet) { const p = mn + bs * (i + 0.5); vaH = Math.max(vaH, p); vaL = Math.min(vaL, p) }

  const re = w - 2

  // Histogram bars (only when volumeProfile overlay is enabled, which it already is to call this)
  if (ov.volumeProfile) {
    for (let i = 0; i < B; i++) {
      const p = mn + bs * (i + 0.5); const y = toY(p)
      if (y <= 0 || y > h) continue
      const ratio = bins[i] / maxV; const bw = Math.max(1, ratio * barMaxW)
      const inVA = vaSet.has(i); const isPOC = bins[i] === maxV
      const alpha = isPOC ? 0.5 : inVA ? 0.22 : 0.08
      ctx.fillStyle = `rgba(245,158,11,${alpha})`
      ctx.fillRect(re - bw, y - 1, bw, Math.max(1.5, 3))
      if (isPOC) { ctx.fillStyle = "rgba(245,158,11,0.12)"; ctx.fillRect(0, y - 1, w, 2) }
    }
  }

  // POC label (always visible)
  const pocI = bins.indexOf(maxV); const pocP = mn + bs * (pocI + 0.5); const pocY = toY(pocP)
  if (pocY > 0) {
    ctx.save()
    ctx.fillStyle = "rgba(11,17,23,0.85)"; ctx.fillRect(re - 50, pocY - 7, 52, 14)
    ctx.strokeStyle = "rgba(245,158,11,0.4)"; ctx.lineWidth = 0.5; ctx.strokeRect(re - 50, pocY - 7, 52, 14)
    ctx.font = "bold 7px monospace"; ctx.fillStyle = "rgba(245,158,11,0.85)"; ctx.textAlign = "right"
    ctx.fillText(`POC $${pocP.toFixed(2)}`, w - 4, pocY + 3); ctx.textAlign = "left"
    ctx.restore()
  }

  // VA labels (always visible)
  if (vaH > 0 && vaL > 0 && vaH !== vaL) {
    const vyH = toY(vaH); const vyL = toY(vaL)
    if (vyH > 0 && vyL > 0) {
      ctx.fillStyle = "rgba(245,158,11,0.05)"; ctx.fillRect(0, vyH, w, vyL - vyH)
      ctx.strokeStyle = "rgba(245,158,11,0.15)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 5])
      ctx.beginPath(); ctx.moveTo(0, vyH); ctx.lineTo(re - barMaxW - 6, vyH); ctx.stroke()
      ctx.beginPath(); ctx.moveTo(0, vyL); ctx.lineTo(re - barMaxW - 6, vyL); ctx.stroke()
      ctx.setLineDash([])
      ctx.font = "6px monospace"; ctx.fillStyle = "rgba(245,158,11,0.45)"; ctx.textAlign = "right"
      ctx.fillText(`VAH $${vaH.toFixed(2)}`, re - barMaxW - 8, vyH - 2)
      ctx.fillText(`VAL $${vaL.toFixed(2)}`, re - barMaxW - 8, vyL + 10)
      ctx.textAlign = "left"
    }
  }
}

// ══════════════════════════════════════════════════
//  4. drawFib — Fibonacci (retrace + extension + golden zone)
// ══════════════════════════════════════════════════

function drawFib(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, fib: Record<string, unknown> | undefined, w: number, ohlcv: Candle[], lp: number) {
  if (!fib || fib.status !== "calculated" || ohlcv.length === 0) return
  const levels = fib.retracement_levels as Record<string, number> | undefined
  if (!levels) return

  const keys = ["0", "0.236", "0.382", "0.5", "0.618", "0.705", "0.786", "1"]
  const cls: Record<string, string> = {
    "0": "rgba(255,255,255,0.08)", "0.236": "rgba(8,153,129,0.2)", "0.382": "rgba(8,153,129,0.25)",
    "0.5": "rgba(245,158,11,0.25)", "0.618": "rgba(8,153,129,0.3)", "0.705": "rgba(245,158,11,0.2)",
    "0.786": "rgba(242,54,69,0.25)", "1": "rgba(255,255,255,0.08)",
  }
  const lbls: Record<string, string> = { "0": "0%", "0.236": "23.6%", "0.382": "38.2%", "0.5": "50%", "0.618": "61.8%", "0.705": "70.5%", "0.786": "78.6%", "1": "100%" }
  let lineCount = 0; let extCount = 0

  // Golden zone highlight
  const gTop = n(levels["0.618"]); const gBot = n(levels["0.786"])
  if (gTop > 0 && gBot > 0) {
    const yGt = toY(gTop); const yGb = toY(gBot)
    if (yGt > 0 && yGb > 0) {
      ctx.fillStyle = "rgba(245,158,11,0.05)"; ctx.fillRect(0, Math.min(yGt, yGb), w, Math.abs(yGt - yGb))
      ctx.strokeStyle = "rgba(245,158,11,0.15)"; ctx.lineWidth = 0.5; ctx.strokeRect(0, Math.min(yGt, yGb), w, Math.abs(yGt - yGb))
      ctx.font = "7px monospace"; ctx.fillStyle = "rgba(245,158,11,0.4)"
      ctx.fillText("Qızıl zona 61.8-78.6%", w - 150, (yGt + yGb) / 2)
    }
  }

  for (const k of keys) {
    const p = levels[k]; if (!p) continue; const y = toY(p)
    if (y <= 0) continue
    ctx.strokeStyle = cls[k] || "rgba(255,255,255,0.08)"; ctx.lineWidth = 0.6
    ctx.setLineDash(k === "0.5" ? [4, 4] : k === "0.618" || k === "0.786" ? [3, 5] : [2, 4])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.save()
    ctx.fillStyle = cls[k] || "rgba(255,255,255,0.2)"; ctx.font = "7px monospace"
    ctx.fillText(`Fib ${lbls[k]} $${p.toFixed(2)}`, w - 110, y - 3)
    ctx.restore()
    lineCount++
  }

  // Extensions
  const extUp = fib.extension_up as Record<string, number> | undefined
  const extDn = fib.extension_down as Record<string, number> | undefined
  const extKeys = ["0.382", "0.618", "1.0", "1.272", "1.618", "2.0", "2.618", "3.618"]
  if (extUp) for (const k of extKeys) {
    const v = extUp[k]; if (!v) continue; const y = toY(v)
    if (y <= 0) continue
    ctx.strokeStyle = "rgba(8,153,129,0.15)"; ctx.lineWidth = 0.4; ctx.setLineDash([1, 6])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = "rgba(8,153,129,0.4)"; ctx.fillText(`Ext ${k} $${(v).toFixed(2)}`, w - 110, y - 2)
    extCount++
  }
  if (extDn) for (const k of extKeys) {
    const v = extDn[k]; if (!v) continue; const y = toY(v)
    if (y <= 0) continue
    ctx.strokeStyle = "rgba(242,54,69,0.15)"; ctx.lineWidth = 0.4; ctx.setLineDash([1, 6])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = "rgba(242,54,69,0.4)"; ctx.fillText(`Ext ${k} $${(v).toFixed(2)}`, w - 110, y - 2)
    extCount++
  }

  // Swing markers
  const sh = n(fib.swing_high); const sl = n(fib.swing_low)
  if (sh > 0) { const y = toY(sh); if (y > 0) { ctx.beginPath(); ctx.arc(0, y, 3, 0, Math.PI * 2); ctx.fillStyle = "rgba(255,255,255,0.2)"; ctx.fill(); ctx.font = "7px monospace"; ctx.fillStyle = "rgba(255,255,255,0.15)"; ctx.fillText(`SH $${sh.toFixed(2)}`, 3, y - 4) } }
  if (sl > 0) { const y = toY(sl); if (y > 0) { ctx.beginPath(); ctx.arc(0, y, 3, 0, Math.PI * 2); ctx.fillStyle = "rgba(255,255,255,0.2)"; ctx.fill(); ctx.font = "7px monospace"; ctx.fillStyle = "rgba(255,255,255,0.15)"; ctx.fillText(`SL $${sl.toFixed(2)}`, 3, y - 4) } }
}

// ══════════════════════════════════════════════════
//  5. drawTgt — Targets TP1–TP5 (gradient box)
// ══════════════════════════════════════════════════

function getTPs(th: Record<string, unknown> | undefined, fib: Record<string, unknown> | undefined, lp: number, isLong: boolean): { level: string; price: number; prob: number; dist: number; time?: string }[] {
  const r: { level: string; price: number; prob: number; dist: number; time?: string }[] = []; const used = new Set<number>()

  if (th) {
    const tgts = (th.targets as Target[] | undefined) || []
    for (const t of tgts) {
      if (t.price <= 0 || used.has(Math.round(t.price * 100))) continue
      if ((isLong && t.price < lp) || (!isLong && t.price > lp)) continue
      if (t.level.includes("TP") || t.level.includes("tp")) {
        used.add(Math.round(t.price * 100))
        r.push({ level: t.level, price: t.price, prob: t.probability || 50, dist: Math.abs(t.price - lp) / lp * 100, time: t.time_estimate })
      }
    }
  }

  if (fib) {
    const ek = isLong ? "extension_up" : "extension_down"
    const ed = fib[ek] as Record<string, number> | undefined
    if (ed) {
      const map2: [string, number][] = [["1.272", 75], ["1.618", 60], ["2.618", 40], ["3.618", 25]]
      for (const [key, probVal] of map2) {
        const v = ed[key]
        if (v && v > 0 && !used.has(Math.round(v * 100))) {
          const ok = isLong ? v >= lp : v <= lp
          if (ok) { used.add(Math.round(v * 100)); r.push({ level: `TP${r.length + 1}`, price: v, prob: probVal, dist: Math.abs(v - lp) / lp * 100 }) }
        }
      }
    }
  }

  r.sort((a, b) => a.dist - b.dist)
  const seen = new Set<string>(); const deduped = r.filter(x => { const k = x.level; if (seen.has(k)) return false; seen.add(k); return true })
  const final: typeof r = []
  let c = 1
  for (const x of deduped) { if (c > 5) break; final.push({ ...x, level: `TP${c}` }); c++ }
  while (final.length < 5 && final.length >= 2) {
    const last = final[final.length - 1]; const prev = final[final.length - 2]
    const ratio = last.price / prev.price
    const np = isLong ? last.price * ratio : last.price / ratio
    if (np > 0 && !used.has(Math.round(np * 100))) { used.add(Math.round(np * 100)); final.push({ level: `TP${final.length + 1}`, price: Math.round(np * 100) / 100, prob: Math.max(5, last.prob - 10), dist: Math.abs(np - lp) / lp * 100 }) }
    else break
  }
  return final
}

function drawTgt(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, th: Record<string, unknown> | undefined, fib: Record<string, unknown> | undefined, w: number, ohlcv: Candle[], lx: number, lp: number, cw: number, confidence: number, status: string) {
  if (!th || ohlcv.length === 0) return
  // Only show TP labels when confidence >= 70% or trade is ready
  const showLabels = confidence >= 70 || status === "ACTIVE"
  const longTPs = getTPs(th, fib, lp, true); const shortTPs = getTPs(th, fib, lp, false)

  const drawOne = (tgt: { level: string; price: number; prob: number; dist: number; time?: string }, color: string, idx: number) => {
    const y = toY(tgt.price); if (y <= 0) return
    if (!showLabels) {
      // WAIT mode - only draw thin trigger line, no label box
      ctx.strokeStyle = color; ctx.lineWidth = 0.4; ctx.setLineDash([4, 6])
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
      return
    }
    ctx.strokeStyle = color; ctx.lineWidth = idx === 0 ? 0.8 : 0.5; ctx.setLineDash(idx === 0 ? [] : [3, 6])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])

    const bx = lx + cw * (2 + idx * 1.8); const by = y - 10; const bw = 108; const bh = 20
    ctx.save()
    ctx.fillStyle = "rgba(11,17,23,0.85)"; ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, 3); ctx.fill()
    ctx.strokeStyle = color; ctx.lineWidth = 0.5; ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, 3); ctx.stroke()

    const gC0 = rgbAlpha(color, 0.65); const gC1 = rgbAlpha(color, 0.2)
    const grad = ctx.createLinearGradient(bx, by, bx + 3, by + bh)
    grad.addColorStop(0, gC0); grad.addColorStop(1, gC1)
    ctx.fillStyle = grad; ctx.fillRect(bx + 1, by + 1, 2, bh - 2)

    ctx.font = "bold 8px monospace"; ctx.fillStyle = color
    ctx.fillText(`${tgt.level} $${tgt.price.toFixed(2)}`, bx + 6, by + 8)
    ctx.font = "7px monospace"; ctx.fillStyle = rgbAlpha(color, 0.6)
    ctx.fillText(`${tgt.prob}% · +${tgt.dist.toFixed(1)}%${tgt.time ? ` · ${tgt.time}` : ""}`, bx + 6, by + 17)
    ctx.restore()
  }

  for (let i = 0; i < longTPs.length; i++) drawOne(longTPs[i], "rgba(8,153,129,0.65)", i)
  for (let i = 0; i < shortTPs.length; i++) drawOne(shortTPs[i], "rgba(242,54,69,0.65)", i)
}

// ══════════════════════════════════════════════════
//  6. drawCh — Channel (median + breakout/retest arrows)
// ══════════════════════════════════════════════════

function drawCh(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, cl: Record<string, unknown> | undefined, ds: Record<string, unknown> | undefined, w: number, ohlcv: Candle[], lx: number, cw: number, lp: number) {
  if (!cl || cl.status !== "calculated" || ohlcv.length === 0) return
  const upper = cl.upper as { time: number; value: number }[] | undefined
  const lower = cl.lower as { time: number; value: number }[] | undefined
  const mid = cl.mid as { time: number; value: number }[] | undefined
  if (!upper || !lower || upper.length < 2) return

  const drawLine = (pts: { time: number; value: number }[], color: string, lw: number, dash: number[] = []) => {
    if (pts.length < 2) return
    ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.setLineDash(dash)
    ctx.beginPath(); let started = false
    for (const p of pts) { const x = toX(p.time); const y = toY(p.value); if (x <= 0 || y <= 0) continue; if (!started) { ctx.moveTo(x, y); started = true } else ctx.lineTo(x, y) }
    ctx.stroke(); ctx.setLineDash([]); ctx.restore()
  }

  drawLine(upper, "rgba(168,85,247,0.7)", 1, [4, 4])
  drawLine(lower, "rgba(168,85,247,0.7)", 1, [4, 4])
  if (mid) drawLine(mid, "rgba(168,85,247,0.25)", 0.5, [2, 6])

  // Labels
  const lu = upper[upper.length - 1]; const xu = toX(lu.time); const yu = toY(lu.value)
  if (xu > 0 && yu > 0) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.8)"; ctx.fillText(`Üst $${lu.value.toFixed(2)}`, Math.max(xu, lx) + 3, yu - 3) }
  const ll = lower[lower.length - 1]; const xll = toX(ll.time); const yll = toY(ll.value)
  if (xll > 0 && yll > 0) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.8)"; ctx.fillText(`Alt $${ll.value.toFixed(2)}`, Math.max(xll, lx) + 3, yll + 11) }

  // Breakout / Retest arrows
  if (ds) {
    const bs = s(ds.breakout_status); const ax = lx + cw * 2; const am = Math.min(yu, yll) + Math.abs(yu - yll) / 2
    if (bs.includes("yuxarı") || bs.includes("up") || bs.includes("YUXARI")) {
      ctx.save(); ctx.fillStyle = "rgba(8,153,129,0.6)"
      ctx.beginPath(); ctx.moveTo(ax, am - 6); ctx.lineTo(ax - 4, am); ctx.lineTo(ax + 4, am); ctx.closePath(); ctx.fill()
      ctx.font = "7px monospace"; ctx.fillStyle = "rgba(8,153,129,0.6)"; ctx.fillText("Breakout", ax + 6, am + 3)
      ctx.restore()
    } else if (bs.includes("aşağı") || bs.includes("down") || bs.includes("ASAGI")) {
      ctx.save(); ctx.fillStyle = "rgba(242,54,69,0.6)"
      ctx.beginPath(); ctx.moveTo(ax, am + 6); ctx.lineTo(ax - 4, am); ctx.lineTo(ax + 4, am); ctx.closePath(); ctx.fill()
      ctx.font = "7px monospace"; ctx.fillStyle = "rgba(242,54,69,0.6)"; ctx.fillText("Breakdown", ax + 6, am + 3)
      ctx.restore()
    }
    // Retest arrow
    const hasRetest = s(ds.label_az).includes("Retest") || s(ds.label_az).includes("retest")
    if (hasRetest) {
      const rx = lx + cw * 4; const ry = am
      ctx.save(); ctx.fillStyle = "rgba(41,98,255,0.5)"
      ctx.beginPath(); ctx.moveTo(rx, ry - 4); ctx.lineTo(rx - 3, ry + 2); ctx.lineTo(rx + 3, ry + 2); ctx.closePath(); ctx.fill()
      ctx.font = "7px monospace"; ctx.fillStyle = "rgba(41,98,255,0.5)"; ctx.fillText("Retest", rx + 5, ry + 3)
      ctx.restore()
    }
    // Label
    if (s(ds.label_az)) {
      ctx.font = "bold 8px monospace"; ctx.fillStyle = "rgba(168,85,247,0.85)"
      ctx.fillText(s(ds.label_az), lx + cw * 2, 18)
    }
  }
}

// ══════════════════════════════════════════════════
//  7. drawSMC — Order Blocks, FVG, IFVG, Liquidity, BOS, CHoCH, EQ
// ══════════════════════════════════════════════════

function drawSMC(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, analysis: Record<string, unknown> | null, ohlcv: Candle[], w: number) {
  if (!analysis || ohlcv.length === 0) return
  const all = (analysis as Record<string, unknown>).all_structures as Record<string, unknown>[] | undefined
  if (!all) return

  const lastP = ohlcv[ohlcv.length - 1].close
  const sorted = all.filter(s => n(s.price) > 0 || n(s.gap_high) > 0)
    .map(s => ({ s, d: Math.abs((n(s.price) || n(s.gap_high) || 0) - lastP) }))
    .sort((a, b) => a.d - b.d).map(x => x.s)

  // ── OB (Order Block) ──
  for (const ob of sorted.filter(x => s(x.category) === "order_block").slice(0, 2)) {
    const idx = n(ob.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const top = toY(n(ob.high)); const bot = toY(n(ob.low))
    if (x <= 0 || top <= 0 || bot <= 0) continue
    const bull = s(ob.type).includes("bullish")
    ctx.save()
    ctx.fillStyle = bull ? "rgba(8,153,129,0.12)" : "rgba(242,54,69,0.12)"
    const obw = Math.max(4, Math.min(14, cw(ohlcv, toX, idx) * 1.5))
    ctx.fillRect(x - obw / 2, Math.min(top, bot), obw, Math.abs(top - bot))
    ctx.strokeStyle = bull ? TV_GREEN : TV_RED; ctx.lineWidth = 1.2
    ctx.strokeRect(x - obw / 2, Math.min(top, bot), obw, Math.abs(top - bot))
    ctx.font = "bold 7px monospace"; ctx.fillStyle = bull ? TV_GREEN : TV_RED
    ctx.fillText("OB", x - obw / 2, Math.min(top, bot) - 3)
    ctx.restore()
  }

  // ── FVG ──
  for (const fvg of sorted.filter(x => s(x.category) === "fvg").slice(0, 2)) {
    const idx = n(fvg.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const top = toY(n(fvg.gap_high)); const bot = toY(n(fvg.gap_low))
    if (x <= 0 || top <= 0 || bot <= 0) continue
    const bull = s(fvg.type).includes("bullish")
    ctx.save()
    ctx.fillStyle = bull ? "rgba(8,153,129,0.15)" : "rgba(242,54,69,0.15)"
    const fw = Math.max(4, Math.min(10, cw(ohlcv, toX, idx)))
    ctx.fillRect(x - fw / 2, Math.min(top, bot), fw, Math.abs(top - bot))
    ctx.strokeStyle = bull ? "rgba(8,153,129,0.5)" : "rgba(242,54,69,0.5)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 2])
    ctx.strokeRect(x - fw / 2, Math.min(top, bot), fw, Math.abs(top - bot)); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = bull ? "rgba(8,153,129,0.7)" : "rgba(242,54,69,0.7)"
    ctx.fillText(s(fvg.fvg_type || "FVG"), x - fw / 2, Math.max(top, bot) + 10)
    ctx.restore()
  }

  // ── BOS ──
  for (const bos of sorted.filter(x2 => s(x2.category) === "bos").slice(0, 2)) {
    const idx = n(bos.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const y = toY(n(bos.price))
    if (x <= 0 || y <= 0) continue
    const bull = s(bos.type).includes("bullish"); const sz = 6
    ctx.save(); ctx.strokeStyle = bull ? TV_GREEN : TV_RED; ctx.lineWidth = 1.2
    ctx.beginPath()
    if (bull) { ctx.moveTo(x - sz, y + sz); ctx.lineTo(x, y); ctx.lineTo(x + sz, y + sz) }
    else { ctx.moveTo(x - sz, y - sz); ctx.lineTo(x, y); ctx.lineTo(x + sz, y - sz) }
    ctx.stroke(); ctx.font = "bold 7px monospace"; ctx.fillStyle = bull ? TV_GREEN : TV_RED
    ctx.fillText("BOS", x + sz + 2, y + (bull ? sz : -sz) + 3)
    ctx.restore()
  }

  // ── CHoCH ──
  for (const choch of sorted.filter(x2 => s(x2.category) === "choch").slice(0, 2)) {
    const idx = n(choch.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const y = toY(ohlcv[idx].high); if (x <= 0 || y <= 0) continue
    ctx.save(); ctx.font = "bold 7px monospace"; ctx.fillStyle = COL_PURPLE
    ctx.fillText("CHoCH", x + 3, y - 3)
    ctx.restore()
  }

  // ── Liquidity Sweeps ──
  for (const ls of sorted.filter(x2 => s(x2.category) === "liquidity_sweep").slice(0, 2)) {
    const pt = n(ls.price); if (pt <= 0) continue; const y = toY(pt); if (y <= 0) continue
    ctx.save(); ctx.strokeStyle = "rgba(168,85,247,0.4)"; ctx.lineWidth = 0.6; ctx.setLineDash([2, 4])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.6)";     ctx.fillText(`Liq Sweep $${pt.toFixed(2)}`, 3, y - 2)
    ctx.restore()
  }

  // ── EQH / EQL ──
  for (const eq of sorted.filter(x2 => s(x2.category) === "equal_high" || s(x2.category) === "equal_low").slice(0, 2)) {
    const pt = n(eq.price); if (pt <= 0) continue; const y = toY(pt); if (y <= 0) continue
    const isEH = s(eq.category) === "equal_high"
    ctx.save(); ctx.strokeStyle = isEH ? "rgba(242,54,69,0.5)" : "rgba(8,153,129,0.5)"; ctx.lineWidth = 0.6; ctx.setLineDash([3, 3])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "7px monospace"; ctx.fillStyle = isEH ? "rgba(242,54,69,0.7)" : "rgba(8,153,129,0.7)"
    ctx.fillText(isEH ? `EQH $${pt.toFixed(2)}` : `EQL $${pt.toFixed(2)}`, 3, y - 2)
    ctx.restore()
  }

  // ── Breaker Block ──
  for (const brk of sorted.filter(x2 => s(x2.category) === "breaker").slice(0, 1)) {
    const idx = n(brk.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const top = toY(n(brk.high)); const bot = toY(n(brk.low))
    if (x <= 0 || top <= 0 || bot <= 0) continue
    const bull = s(brk.type).includes("bullish")
    ctx.save()
    ctx.fillStyle = bull ? "rgba(8,153,129,0.15)" : "rgba(242,54,69,0.15)"
    const bw2 = Math.max(4, Math.min(12, cw(ohlcv, toX, idx)))
    ctx.fillRect(x - bw2 / 2, Math.min(top, bot), bw2, Math.abs(top - bot))
    ctx.strokeStyle = bull ? TV_GREEN : TV_RED; ctx.lineWidth = 0.8; ctx.setLineDash([3, 3])
    ctx.strokeRect(x - bw2 / 2, Math.min(top, bot), bw2, Math.abs(top - bot)); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = bull ? TV_GREEN : TV_RED;     ctx.fillText("BB", x - bw2 / 2, Math.min(top, bot) - 2)
    ctx.restore()
  }

  let bc = 0; let sc2 = 0
  for (const s2 of all) { if (s(s2.category) === "order_block" && s(s2.type).includes("bullish")) bc++; if (s(s2.category) === "order_block" && s(s2.type).includes("bearish")) sc2++ }
  if (bc > sc2 * 1.5) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(8,153,129,0.7)"; ctx.fillText("Yığım Zonası", 10, 50) }
  else if (sc2 > bc * 1.5) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(242,54,69,0.7)"; ctx.fillText("Paylanma Zonası", 10, 50) }
}

function cw(ohlcv: Candle[], toX: (t: number) => number, idx: number): number {
  if (idx <= 0 || idx >= ohlcv.length) return 6
  return Math.abs(toX(ohlcv[idx].time) - toX(ohlcv[idx - 1].time)) || 6
}

// ══════════════════════════════════════════════════
//  8. drawLegend — Bottom-right info panel
// ══════════════════════════════════════════════════

function drawLegend(
  ctx: CanvasRenderingContext2D, w: number, h: number,
  ov: Record<string, boolean>, pats: Record<string, unknown>[] | undefined,
  mainSc: Record<string, unknown> | undefined, confidence: number,
  analysis: Record<string, unknown> | null,
) {
  const items: { label: string; color: string; active: boolean }[] = [
    { label: "Şam", color: TV_GREEN, active: true },
    { label: "Əsas", color: TV_GREEN, active: ov.mainScenario },
    { label: "Alt", color: COL_GRAY, active: ov.altScenario },
    { label: "Fakeout", color: COL_ORANGE, active: ov.fakeout },
    { label: "TP1–TP5", color: TV_GREEN, active: ov.targets },
    { label: "Konus", color: "rgba(8,153,129,0.4)", active: ov.cone },
    { label: "Breakout", color: COL_PURPLE, active: ov.breakout },
    { label: "Kanal", color: COL_PURPLE, active: ov.channel },
    { label: "Fib", color: COL_ORANGE, active: ov.fibonacci },
    { label: "Pattern", color: COL_ORANGE, active: ov.patterns },
    { label: "Elliott", color: COL_PURPLE, active: ov.elliott },
    { label: "SMC", color: COL_PURPLE, active: ov.smc },
  ]
  const active = items.filter(i => i.active)
  if (active.length === 0) return

  const pn = (pats || []).slice(0, 1).map(p => s(p.name)).filter(Boolean)
  const extra: string[] = []
  if (pn.length > 0) extra.push(`${pn[0]}`)
  if (mainSc) {
    const dir = s(mainSc.direction_az || mainSc.direction || "")
    const prob = n(mainSc.probability)
    if (dir) extra.push(`${dir} ${prob}%`)
  }

  const scores = analysis?.scores as Record<string, unknown> | undefined
  if (scores) {
    const oa = n(scores.overall)
    extra.push(`Skor: ${oa}/100 · İnam: ${confidence}%`)
  }

  const lh = 10; const pd = 4; const cols = 2
  const rows = Math.ceil(active.length / cols)
  const boxH = rows * lh + pd * 2 + extra.length * lh + pd + lh
  const boxW = 140
  const bx = Math.max(2, w - boxW - 6); const by = Math.max(2, h - boxH - 6)

  ctx.save()
  ctx.fillStyle = "rgba(11,17,23,0.88)"
  ctx.strokeStyle = "rgba(55,65,81,0.5)"; ctx.lineWidth = 0.5
  ctx.beginPath(); ctx.roundRect(bx, by, boxW, boxH, 3); ctx.fill(); ctx.stroke()

  let yy = by + pd + 7
  for (let i = 0; i < active.length; i++) {
    const col = Math.floor(i / rows); const row = i % rows
    const ix = bx + pd + col * (boxW / 2); const iy = by + pd + row * lh + 7
    ctx.fillStyle = active[i].color; ctx.fillRect(ix, iy - 4, 5, 5)
    ctx.fillStyle = "rgba(156,163,175,0.8)"; ctx.font = "7px monospace"
    ctx.fillText(active[i].label, ix + 7, iy + 1)
    yy = iy + lh
  }

  for (const line of extra) {
    ctx.fillStyle = "rgba(156,163,175,0.6)"; ctx.font = "7px monospace"
    ctx.fillText(line, bx + pd, yy + lh); yy += lh
  }
  ctx.restore()
}

// ══════════════════════════════════════════════════
//  9. buildHover — Full analysis text on hover
// ══════════════════════════════════════════════════

function buildHover(
  price: number, ohlcv: Candle[],
  allStructs: Record<string, unknown>[] | undefined,
  patterns: Record<string, unknown>[] | undefined,
  ds: Record<string, unknown> | undefined, bz: Record<string, unknown> | undefined,
  th: Record<string, unknown> | undefined, cl: Record<string, unknown> | undefined,
  sp: Record<string, unknown> | undefined,
  ew: Record<string, unknown> | undefined,
  fib: Record<string, unknown> | undefined,
): string[] {
  const lines: string[] = []
  const DP = (p: number) => "$" + p.toFixed(2)

  lines.push("Price: " + DP(price))
  const idx = ohlcv.findIndex(d => Math.abs(d.close - price) / price < 0.01)
  if (idx >= 0) {
    const c = ohlcv[idx]
    lines.push("Candle #" + idx + " O:" + c.open.toFixed(2) + " H:" + c.high.toFixed(2) + " L:" + c.low.toFixed(2) + " C:" + c.close.toFixed(2) + " V:" + (c.volume / 1000).toFixed(0) + "K")
  }

  if (allStructs) {
    for (const s2 of allStructs.slice(-25)) {
      const sp2 = n(s2.price) || n(s2.gap_high) || 0
      if (sp2 > 0 && Math.abs(sp2 - price) / price < 0.025) {
        const cat = s(s2.category); const typ = s(s2.type)
        if (cat === "bos") lines.push("BOS " + (typ.includes("bullish") ? "Up" : "Down") + " structure change")
        else if (cat === "choch") lines.push("CHoCH " + (typ.includes("bullish") ? "Up" : "Down") + " character change")
        else if (cat === "fvg") lines.push("FVG " + (typ.includes("bullish") ? "Up" : "Down") + " gap")
        else if (cat === "order_block") lines.push("OB " + (typ.includes("bullish") ? "Buy" : "Sell") + " block " + s(s2.timeframe))
        else if (cat === "liquidity") lines.push("Liquidity " + (typ.includes("above") ? "Above" : "Below") + " zone")
        else if (cat === "breaker") lines.push("Breaker " + (typ.includes("bullish") ? "Up" : "Down"))
        else if (cat === "equal_high" || cat === "equal_low")
          lines.push("EQ" + (cat === "equal_high" ? "H" : "L") + " $" + sp2.toFixed(2))
        else if (cat === "liquidity_sweep")
          lines.push("Liq Sweep " + (typ.includes("above") ? "Above" : "Below") + " $" + sp2.toFixed(2))
        else if (cat === "swing")
          lines.push("Swing " + (typ === "high" ? "High" : "Low") + " " + new Date(ohlcv[Math.min(n(s2.index) || 0, ohlcv.length - 1)]?.time * 1000).toLocaleDateString())
      }
    }
  }

  if (ds && n(ds.channel_top) > 0 && Math.abs(n(ds.channel_top) - price) / price < 0.02)
    lines.push("Channel top: " + DP(n(ds.channel_top)) + " " + s(ds.label_az))
  if (ds && n(ds.channel_bottom) > 0 && Math.abs(n(ds.channel_bottom) - price) / price < 0.02)
    lines.push("Channel bot: " + DP(n(ds.channel_bottom)) + " " + s(ds.label_az))

  if (bz && n(bz.zone_top) > 0 && Math.abs(n(bz.zone_top) - price) / price < 0.02)
    lines.push("BO top: " + DP(n(bz.zone_top)) + " Tests: " + n(bz.test_count) + "x")
  if (bz && n(bz.zone_bottom) > 0 && Math.abs(n(bz.zone_bottom) - price) / price < 0.02)
    lines.push("BO bot: " + DP(n(bz.zone_bottom)) + " Tests: " + n(bz.test_count) + "x")

  if (th) {
    const tgts = th.targets as Target[] | undefined
    if (tgts) for (const t of tgts) {
      if (Math.abs(n(t.price) - price) / price < 0.02)
        lines.push(t.level + " " + DP(n(t.price)) + " " + n(t.probability) + "% " + s(t.time_estimate) + " " + t.type)
    }
  }

  if (sp) {
    for (const key of ["main_scenario", "alternative_scenario", "fakeout_scenario"]) {
      const sc = sp[key] as Record<string, unknown> | undefined
      const pts = sc?.path_points as PathPoint[] | undefined
      if (pts && sc) for (const p of pts) {
        if (p.time_offset > 0 && Math.abs(n(p.price) - price) / price < 0.03)
          lines.push(p.label + " " + DP(n(p.price)) + " " + s(sc.direction_az) + " " + n(sc.probability) + "% " + s(p.phase))
      }
    }
  }

  if (ew && ew.status === "calculated") {
    const waves = ew.waves as { type: string; start: number; end: number; index: number; label?: string }[] | undefined
    if (waves) for (const w of waves) {
      const wP = w.type === "wave_up" ? w.end : w.start
      if (Math.abs(wP - price) / price < 0.02)
        lines.push("Elliott Wave " + (w.label || "") + " " + (w.type === "wave_up" ? "Up" : "Down"))
    }
  }

  if (fib && fib.status === "calculated") {
    const levels = fib.retracement_levels as Record<string, number> | undefined
    if (levels) for (const [k, v] of Object.entries(levels)) {
      if (Math.abs(v - price) / price < 0.02)
        lines.push("Fib " + (Number(k) * 100).toFixed(1) + "% " + DP(v))
    }
  }

  if (patterns) for (const pat of patterns.slice(0, 3)) {
    if (Math.abs(n(pat.breakout_level) - price) / price < 0.03 || Math.abs(n(pat.breakdown_level) - price) / price < 0.03)
      lines.push(s(pat.name) + " " + s(pat.status) + " Target: " + DP(n(pat.measured_target)))
  }

  return lines
}

// ══════════════════════════════════════════════════
//  Legacy helpers (kept as-is for existing callers)
// ══════════════════════════════════════════════════

function drawBO(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, bz: Record<string, unknown> | undefined, w: number, h: number, ohlcv: Candle[], lx: number, cw: number) {
  if (!bz || bz.status !== "calculated" || ohlcv.length === 0) return
  const zt = n(bz.zone_top); const zb = n(bz.zone_bottom)
  if (zt <= 0 || zb <= 0) return
  const yt = toY(zt); const yb = toY(zb)
  if (yt <= 0 || yb <= 0) return
  ctx.save(); ctx.fillStyle = "rgba(168,85,247,0.12)"; ctx.fillRect(0, Math.min(yt, yb), w, Math.abs(yt - yb))
  ctx.strokeStyle = "rgba(168,85,247,0.5)"; ctx.lineWidth = 0.6; ctx.setLineDash([3, 3])
  ctx.strokeRect(0, Math.min(yt, yb), w, Math.abs(yt - yb)); ctx.setLineDash([])
  const midY = (yt + yb) / 2; const sx = lx + cw * 2
  ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.7)"
  ctx.fillText(`BO Üst $${zt.toFixed(2)}`, sx, yt - 2)
  ctx.fillText(`BO Alt $${zb.toFixed(2)}`, sx, yb + 10)
  if (n(bz.test_count) > 0) { ctx.font = "6px monospace"; ctx.fillStyle = "rgba(168,85,247,0.6)"; ctx.fillText(`${n(bz.test_count)}x test`, sx, midY + 10) }
  if (bz.bullish_breakout_ready) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(8,153,129,0.7)"; ctx.fillText("✓ UZUN breakout", sx, midY - 6) }
  if (bz.bearish_breakout_ready) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(242,54,69,0.7)"; ctx.fillText("✓ QISA breakdown", sx, midY - 6) }
  ctx.restore()
}

function drawRet(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, ds: Record<string, unknown> | undefined, w: number, lx: number, cw: number) {
  if (!ds) return
  const top = n(ds.channel_top); const bot = n(ds.channel_bottom)
  if (top <= 0 || bot <= 0) return
  const yT = toY(top); const yB = toY(bot)
  if (yT <= 0 || yB <= 0) return
  const sx = lx + cw
  ctx.save(); ctx.fillStyle = "rgba(41,98,255,0.12)"; ctx.fillRect(sx - 12, yT, 24, yB - yT)
  ctx.strokeStyle = "rgba(41,98,255,0.5)"; ctx.lineWidth = 0.6; ctx.setLineDash([2, 4])
  ctx.strokeRect(sx - 12, yT, 24, yB - yT); ctx.setLineDash([])
  ctx.font = "7px monospace"; ctx.fillStyle = "rgba(41,98,255,0.7)"; ctx.fillText("Retest", sx - 10, yT - 3)
  ctx.fillText("gözlənilir", sx - 10, yB + 10)
  ctx.restore()
}

function drawLiq(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, sr: Record<string, unknown>, w: number) {
  const la = sr.liquidity_above as { price: number; strength: number }[] | undefined
  const lb = sr.liquidity_below as { price: number; strength: number }[] | undefined
  for (const l of (la || []).slice(-3)) { const y = toY(l.price); if (y <= 0) continue; ctx.save(); ctx.strokeStyle = "rgba(242,54,69,0.35)"; ctx.lineWidth = 0.6; ctx.setLineDash([2, 6]); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([]); ctx.font = "7px monospace"; ctx.fillStyle = "rgba(242,54,69,0.6)"; ctx.fillText(`Likvidite $${l.price.toFixed(2)}`, 3, y - 2); ctx.restore() }
  for (const l of (lb || []).slice(-3)) { const y = toY(l.price); if (y <= 0) continue; ctx.save(); ctx.strokeStyle = "rgba(8,153,129,0.35)"; ctx.lineWidth = 0.6; ctx.setLineDash([2, 6]); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([]); ctx.font = "7px monospace"; ctx.fillStyle = "rgba(8,153,129,0.6)"; ctx.fillText(`Likvidite $${l.price.toFixed(2)}`, 3, y - 2); ctx.restore() }
}

function drawInv(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, invalLevel: number, w: number, lx: number, cw: number) {
  if (invalLevel <= 0) return; const y = toY(invalLevel); if (y <= 0) return
  ctx.save(); ctx.strokeStyle = "rgba(242,54,69,0.5)"; ctx.lineWidth = 0.8; ctx.setLineDash([4, 4])
  ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
  ctx.font = "7px monospace"; ctx.fillStyle = "rgba(242,54,69,0.7)"; ctx.fillText(`Ləğv $${invalLevel.toFixed(2)}`, lx + cw * 2, y - 3)
  ctx.restore()
}

function drawSR(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, sr: Record<string, unknown>, price: number, w: number) {
  const lvs = [
    { key: "nearest_support", label: "D", color: "rgba(8,153,129,0.7)" },
    { key: "nearest_resistance", label: "Q", color: "rgba(242,54,69,0.7)" },
    { key: "strongest_support", label: "GD", color: "rgba(8,153,129,0.85)" },
    { key: "strongest_resistance", label: "GQ", color: "rgba(242,54,69,0.85)" },
  ]
  for (const l of lvs) { const p = n(sr[l.key]); if (p <= 0) continue; const y = toY(p); if (y <= 0) continue; ctx.save(); ctx.strokeStyle = l.color; ctx.lineWidth = l.key.startsWith("strongest") ? 1 : 0.6; ctx.setLineDash(l.key.startsWith("strongest") ? [4, 4] : [2, 2]); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([]); ctx.font = "7px monospace"; ctx.fillStyle = l.color; ctx.fillText(`${l.label} $${p.toFixed(2)}`, w - 80, y - 2); ctx.restore() }
}

function drawSRZ(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, supZone: Record<string, unknown> | undefined, resZone: Record<string, unknown> | undefined, w: number, ohlcv: Candle[]) {
  if (!supZone || !resZone || ohlcv.length === 0) return
  const sBot = n(supZone.bottom); const sTop = n(supZone.top)
  const rBot = n(resZone.bottom); const rTop = n(resZone.top)
  if (sBot > 0 && sTop > 0) { const ys = toY(sBot); const ys2 = toY(sTop); if (ys > 0 && ys2 > 0) { ctx.save(); ctx.fillStyle = "rgba(8,153,129,0.12)"; ctx.fillRect(0, ys, w, ys2 - ys); ctx.strokeStyle = "rgba(8,153,129,0.4)"; ctx.lineWidth = 0.6; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(0, ys); ctx.lineTo(w, ys); ctx.stroke(); ctx.setLineDash([]); ctx.font = "7px monospace"; ctx.fillStyle = "rgba(8,153,129,0.6)"; ctx.fillText(`D $${sBot.toFixed(2)}-$${sTop.toFixed(2)}`, 3, ys - 2); ctx.restore() } }
  if (rBot > 0 && rTop > 0) { const yr = toY(rBot); const yr2 = toY(rTop); if (yr > 0 && yr2 > 0) { ctx.save(); ctx.fillStyle = "rgba(242,54,69,0.12)"; ctx.fillRect(0, yr, w, yr2 - yr); ctx.strokeStyle = "rgba(242,54,69,0.4)"; ctx.lineWidth = 0.6; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(0, yr); ctx.lineTo(w, yr); ctx.stroke(); ctx.setLineDash([]); ctx.font = "7px monospace"; ctx.fillStyle = "rgba(242,54,69,0.6)"; ctx.fillText(`Q $${rBot.toFixed(2)}-$${rTop.toFixed(2)}`, 3, yr - 2); ctx.restore() } }
}

function drawTrig(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, triggers: Record<string, unknown>, scores: Record<string, unknown>, w: number, lx: number, cw: number, confidence: number) {
  const ltP = n(triggers.long_trigger_price); const stP = n(triggers.short_trigger_price)
  const inv = n(triggers.bullish_invalidation) || n(triggers.bearish_invalidation)
  const alpha = 0.65
  const draw = (price: number, color: string, label: string, d: number[], lw: number) => {
    const y = toY(price); if (y <= 0) return
    ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.setLineDash(d)
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "bold 7px monospace"; ctx.fillStyle = color; ctx.fillText(label, lx + cw * 2, y - 3)
    ctx.restore()
  }
  if (ltP > 0) draw(ltP, `rgba(8,153,129,${alpha})`, `↑ ALIŞ $${ltP.toFixed(2)}`, [], 1)
  if (stP > 0) draw(stP, `rgba(242,54,69,${alpha})`, `↓ SATIŞ $${stP.toFixed(2)}`, [], 1)
  if (inv > 0) draw(inv, "rgba(168,85,247,0.6)", `Ləğv $${inv.toFixed(2)}`, [4, 4], 0.8)
}

function drawEW(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, ew: Record<string, unknown> | undefined, w: number, ohlcv: Candle[], confidence: number) {
  if (!ew || ew.status === "insufficient_data" || ohlcv.length === 0) return
  if (confidence < 60) return
  const waves = ew.waves as { type: string; start: number; end: number; index: number; label?: string }[] | undefined
  if (!waves || waves.length < 3) return
  const ewConf = n(ew.confidence) || confidence; const uncertain = ewConf < 50
  const labels = ["1", "2", "3", "4", "5", "A", "B", "C"]
  let wCount = 0

  for (let i = 0; i < Math.min(waves.length, 8); i++) {
    const wave = waves[i]; const idx = wave.index
    if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); if (x <= 0) continue
    const isUp = wave.type === "wave_up"; const y = toY(isUp ? wave.end : wave.start); if (y <= 0) continue
    ctx.save()
    if (uncertain) {
      ctx.fillStyle = "rgba(168,85,247,0.5)"; ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill()
      ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.5)"; ctx.fillText(labels[i] || "", x + 5, y + 3)
    } else {
      ctx.fillStyle = isUp ? TV_GREEN : TV_RED; const sz = 3
      ctx.beginPath()
      if (isUp) { ctx.moveTo(x, y - sz); ctx.lineTo(x - sz, y); ctx.lineTo(x + sz, y) }
      else { ctx.moveTo(x, y + sz); ctx.lineTo(x - sz, y); ctx.lineTo(x + sz, y) }
      ctx.fill()
      ctx.fillStyle = isUp ? "rgba(8,153,129,0.7)" : "rgba(242,54,69,0.7)"
      ctx.fillText(labels[i] || String(i + 1), x + sz + 3, y + 3)
    }
    ctx.restore()
    wCount++
  }

  if (uncertain) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.6)"; ctx.fillText("Elliott sayımı qeyri-müəyyəndir", 10, 72) }
  else { const cl = waves[waves.length - 1]?.label || ""; ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.6)"; ctx.fillText(`Cari: Dalğa ${cl}`, 10, 72) }
}
