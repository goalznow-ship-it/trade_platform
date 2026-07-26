"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import {
  createChart, ColorType, CandlestickSeries, HistogramSeries, LineSeries,
  type IChartApi, type ISeriesApi, type Time,
} from "lightweight-charts"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import { normalizeSkhyAnalysis, type NormalizedAnalysis } from "@/lib/skhyChartNormalizer"

interface Props {
  symbol: string
  snapshot: Record<string, unknown> | null
  analysis: Record<string, unknown> | null
  triggers: Record<string, unknown>
  sr: Record<string, unknown>
  activeTimeframe: string
  onTimeframeChange: (tf: string) => void
  normalizedAnalysis: NormalizedAnalysis | null
}

interface Candle { time: number; open: number; high: number; low: number; close: number; volume: number }
interface PathPoint { time_offset: number; price: number; label: string; phase: string; probability?: number; reason?: string }
interface Target { level: string; price: number; type: string; probability: number; time_estimate: string }

type OverlayKey = "aiOverlay"|"structure"|"channel"|"breakout"|"retest"|"fibonacci"|"targets"|"mainScenario"|"altScenario"|"fakeout"|"smc"|"liquidity"|"ema"|"atrStop"|"volumeProfile"|"elliott"|"triggers"|"patterns"|"cone"

const TV_GREEN = "#089981"
const TV_RED = "#f23645"
const COL_BG = "#0d1117"
const COL_GRID = "#1f2937"
const COL_TEXT = "#6b7280"
const COL_PURPLE = "#a855f7"
const COL_BLUE = "#2962ff"
const COL_ORANGE = "#f59e0b"
const COL_GRAY = "#6b7280"
const COL_CYAN = "#22d3ee"

function n(v: unknown): number { return typeof v === "number" ? v : 0 }
function s(v: unknown): string { return v == null ? "" : String(v) }
function rgbAlpha(base: string, a: number): string {
  const m = base.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  if (m) return `rgba(${m[1]},${m[2]},${m[3]},${a})`
  try { const c = new Option().style; c.color = base; const sc = c.color; if (sc) return sc.replace(/rgb\(/, "rgba(").replace(/\)$/, `,${a})`) } catch {}
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
function fv(obj: Record<string, unknown> | undefined, ...keys: string[]): unknown {
  if (!obj) return undefined
  for (const k of keys) { const v = obj[k]; if (v !== undefined && v !== null) return v }
  return undefined
}
function nf(obj: Record<string, unknown> | undefined, ...keys: string[]): number { return n(fv(obj, ...keys)) }
function af<T>(obj: Record<string, unknown> | undefined, ...keys: string[]): T[] | undefined {
  const v = fv(obj, ...keys); return Array.isArray(v) ? v as T[] : undefined
}

export function SKHYChart({ symbol, snapshot, analysis, triggers: triggersProp, sr: srProp, activeTimeframe, onTimeframeChange, normalizedAnalysis }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const parentRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const volSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null)
  const ema20Ref = useRef<ISeriesApi<"Line"> | null>(null)
  const ema50Ref = useRef<ISeriesApi<"Line"> | null>(null)
  const ema100Ref = useRef<ISeriesApi<"Line"> | null>(null)
  const atrStopRef = useRef<ISeriesApi<"Line"> | null>(null)
  const rafRef = useRef<number>(0)
  const dirtyRef = useRef(true)
  const lastValidOhlcvRef = useRef<Candle[]>([])
  const lastValidAnalysisRef = useRef<Record<string, unknown> | null>(null)
  const fitDoneRef = useRef(false)

  const [ohlcv, setOhlcv] = useState<Candle[]>([])
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string[] } | null>(null)
  const [emaValues, setEmaValues] = useState({ ema20: 0, ema50: 0, ema100: 0 })
  const [dbg, setDbg] = useState<string>("")
  const [overlays, setOverlays] = useState<Record<OverlayKey, boolean>>({
    aiOverlay: true, structure: true, channel: true, breakout: true, retest: true,
    fibonacci: true, targets: true, mainScenario: true, altScenario: false,
    fakeout: false, smc: true, liquidity: false, ema: false, atrStop: false,
    volumeProfile: false, elliott: false, triggers: true,
    patterns: true, cone: true,
  })
  const timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

  useEffect(() => {
    if (analysis && analysis.scores) lastValidAnalysisRef.current = analysis
  }, [analysis])
  const activeAnalysis = analysis ?? lastValidAnalysisRef.current

  // ── Normalized analysis (from parent prop — single source of truth) ──
  const norm = normalizedAnalysis || normalizeSkhyAnalysis(activeAnalysis)
  useEffect(() => {
    console.log("[SKHY] NORMALIZED_RUNTIME", {
      longTrigger: norm.longTrigger,
      shortTrigger: norm.shortTrigger,
      breakout: norm.breakout,
      channel: norm.channel,
      supports: norm.supports,
      resistances: norm.resistances,
      fibonacci: norm.fibonacci,
      scenarios: norm.scenarios,
      strongestPattern: norm.strongestPattern,
      confidence: norm.confidence,
      status: norm.status,
    })
    console.log("[SKHY] NORMALIZED_CHANNEL", norm.channel)
  }, [norm])
  const hasAnalysis = !!(activeAnalysis?.scores)
  const scores = (activeAnalysis?.scores || {}) as Record<string, unknown>
  const tfs = (activeAnalysis?.timeframes || {}) as Record<string, unknown>
  const price = n(snapshot?.live_price)
  const confidence = norm.confidence
  const status = norm.status
  const longProb = norm.longProb
  const shortProb = norm.shortProb
  const ltPrice = norm.longTrigger
  const stPrice = norm.shortTrigger
  const confTier = confidence >= 80 ? 4 : confidence >= 70 ? 3 : confidence >= 50 ? 2 : 1
  const showEntrySLTP = confidence >= 70 && norm.tradePlan?.trade_ready

  // Raw fields for draw functions that need them
  const ds = activeAnalysis?.detected_structure as Record<string, unknown> | undefined
  const cl = activeAnalysis?.channel_lines as Record<string, unknown> | undefined
  const bz = activeAnalysis?.breakout_zone as Record<string, unknown> | undefined
  const allStructs = activeAnalysis?.all_structures as Record<string, unknown>[] | undefined
  const patterns = activeAnalysis?.patterns as Record<string, unknown>[] | undefined
  const activePatterns = activeAnalysis?.active_patterns as Record<string, unknown>[] | undefined
  const sp = activeAnalysis?.scenario_paths as Record<string, unknown> | undefined
  const fpv2 = activeAnalysis?.future_path_v2 as Record<string, unknown> | undefined
  const th = activeAnalysis?.target_hierarchy as Record<string, unknown> | undefined
  const cb = activeAnalysis?.confidence_breakdown as Record<string, unknown> | undefined
  const fib = activeAnalysis?.fibonacci as Record<string, unknown> | undefined
  const ew = activeAnalysis?.elliott_wave as Record<string, unknown> | undefined
  const mainSc = sp?.main_scenario as Record<string, unknown> | undefined
  const mainDir = s(mainSc?.direction_az || mainSc?.direction || "")
  const mainProb = n(mainSc?.probability)
  const invalLevel = n(activeAnalysis?.invalidation_level)
  const tradePlan = activeAnalysis?.trade_plan as Record<string, unknown> | undefined
  const analysisTriggers = (activeAnalysis?.triggers || {}) as Record<string, unknown>
  const sr = srProp

  const canvasSizeRef = useRef({ w: 0, h: 0 })
  const markDirty = useCallback(() => { dirtyRef.current = true }, [])

  const fitToAnalysis = useCallback(() => {
    const chart = chartRef.current; const cs = candleSeriesRef.current; const d = ohlcv.length > 0 ? ohlcv : lastValidOhlcvRef.current
    if (!chart || !cs || d.length === 0) return
    const prices: number[] = [d[d.length - 1].close]
    if (norm.longTrigger > 0) prices.push(norm.longTrigger)
    if (norm.shortTrigger > 0) prices.push(norm.shortTrigger)
    if (norm.breakout.top > 0) prices.push(norm.breakout.top, norm.breakout.bottom)
    for (const s of norm.supports) { if (s.price > 0) prices.push(s.price) }
    for (const r of norm.resistances) { if (r.price > 0) prices.push(r.price) }
    const pad = (Math.max(...prices) - Math.min(...prices)) * 0.1 || 2
    const minP = Math.min(...prices) - pad; const maxP = Math.max(...prices) + pad
    // Force price scale by adding invisible markers via scatter / extending visible range
    if (d.length >= 2) {
      chart.timeScale().setVisibleLogicalRange({
        from: Math.max(0, d.length - 80),
        to: d.length + 30,
      })
      markDirty()
    }
    console.log("[SKHY] FIT_TO_ANALYSIS", { minPrice: minP, maxPrice: maxP, levels: prices.length })
  }, [ohlcv, norm, markDirty])

  // Auto-fit on first load
  useEffect(() => {
    if (hasAnalysis && ohlcv.length > 0 && !fitDoneRef.current) {
      setTimeout(() => { fitToAnalysis(); fitDoneRef.current = true }, 300)
    }
  }, [hasAnalysis, ohlcv, fitToAnalysis])

  const drawOnCanvas = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number): boolean => {
    const chart = chartRef.current; const cs = candleSeriesRef.current
    const data = ohlcv.length > 0 ? ohlcv : lastValidOhlcvRef.current
    if (!chart || !cs || data.length === 0 || !hasAnalysis) {
      return false
    }
    // ── AI Overlay master toggle ──
    if (!overlays.aiOverlay) { return false }

    const ts = chart.timeScale()
    const safeC = (v: number) => Number.isFinite(v) ? v : 0
    const toX = (t: number) => safeC(ts.timeToCoordinate(t as Time) ?? 0)
    const toY = (p: number) => safeC(cs.priceToCoordinate(p) ?? 0)
    const candleW = data.length >= 2 ? Math.max(1, toX(data[data.length - 1].time) - toX(data[data.length - 2].time)) : 8
    const lx = toX(data[data.length - 1].time)
    const lp = data[data.length - 1].close
    const fX = (off: number) => { const v = lx + candleW * off; return Number.isFinite(v) ? v : 0 }
    if (w <= 0 || h <= 0 || lx <= 0 || lp <= 0) return false

    // ── PLOT RECT LOG ──
    const plotRect = chart.timeScale().getVisibleLogicalRange()
    const containerRect = containerRef.current?.getBoundingClientRect()
    console.log("[SKHY] PLOT_RECT", {
      w, h, lx, lp,
      logicalRange: plotRect ? { from: plotRect.from, to: plotRect.to } : null,
      containerRect: containerRect ? { left: containerRect.left, top: containerRect.top, width: containerRect.width, height: containerRect.height } : null,
    })

    // ── DIAGNOSTIC RED RECT (if visible, canvas overlay works) ──
    ctx.save()
    ctx.fillStyle = "rgba(255,0,0,0.3)"
    ctx.fillRect(10, 10, 50, 50)
    ctx.fillStyle = "#fff"
    ctx.font = "8px monospace"
    ctx.fillText("DIAG", 12, 50)
    ctx.restore()

    // ── LAYER TRACKING ──
    // Each draw function returns { dataCount, drawnCount }
    const counter: Record<string, { dataCount: number; drawnCount: number }> = {}
    const track = (name: string, fn: () => { dataCount: number; drawnCount: number }) => {
      try {
        const res = fn()
        counter[name] = { dataCount: (counter[name]?.dataCount || 0) + res.dataCount, drawnCount: (counter[name]?.drawnCount || 0) + res.drawnCount }
      } catch (e) {
        console.error(`[SKHY] ${name}:`, e)
        counter[name] = { dataCount: 0, drawnCount: 0 }
      }
    }

    // ── VISIBLE PRICE RANGE ──
    const vMin = n(cs.coordinateToPrice(h))
    const vMax = n(cs.coordinateToPrice(0))
    console.log("[SKHY] VISIBLE_PRICE_RANGE", { min: vMin, max: vMax, longTrigger: norm.longTrigger, shortTrigger: norm.shortTrigger })

    // ── Z-ORDER: draw layers back to front, triggers LAST ──
    const pw = w // plot width = full canvas width

    // 1. Breakout fill (rearmost)
    if (overlays.breakout) track("breakout", () => drawBreakoutPrimitive(ctx, pw, h, norm, cs, confidence))
    // 2. S/R zones
    if (overlays.structure) track("sr_zones", () => drawSRPrimitive(ctx, pw, h, norm, cs, confidence))
    // 3. Channel
    if (overlays.channel) track("channel", () => drawChannelPrimitive(ctx, pw, h, toX, toY, norm, confidence, data, lx))
    // 4. Fibonacci
    if (overlays.fibonacci) track("fib", () => drawFibPrimitive(ctx, pw, h, norm, cs, confidence))
    // 5. SMC
    if (overlays.smc) track("smc", () => drawSMCPrimitive(ctx, pw, norm, cs, confidence))
    // 6. Pattern
    if (overlays.patterns) track("pattern", () => drawPatternPrimitive(ctx, toX, toY, norm, data, w, confidence, lx, candleW))
    // 7. Future projection
    if (overlays.mainScenario || overlays.altScenario || overlays.fakeout || overlays.cone)
      track("future", () => drawFPPrimitive(ctx, pw, h, toX, toY, sp || fpv2, cb, confidence, data, lx, lp, candleW, fX, overlays))

    // 8. TRIGGERS (drawn on top of everything)
    const trigRes = drawTriggersPrimitive(ctx, pw, h, norm, cs)
    counter["triggers"] = trigRes

    // 9. Legend / status (always on top)
    drawLegend(ctx, w, h, overlays, norm, confidence)

    // ── STATUS BUILD ──
    const maxConfig: Record<string, number> = { triggers: 2, breakout: 1, channel: 3, pattern: 1, fib: 4, sr_zones: 4, future: 1, smc: 8 }
    const dataParts: string[] = []; const visParts: string[] = []
    for (const [key, denom] of Object.entries(maxConfig)) {
      const c = counter[key]
      if (!c) continue
      const dc = c.dataCount || denom
      dataParts.push(`${key.toUpperCase().slice(0, 3)} D${dc}`)
      if (c.drawnCount > 0) visParts.push(`${key.toUpperCase().slice(0, 3)} V${c.drawnCount}`)
    }
    setDbg(dataParts.join(" ") + (visParts.length > 0 ? "  │  " + visParts.join(" ") : ""))
    return true

    // ── Confidence-based visibility ──
    
    return true
  }, [ohlcv, overlays, activeAnalysis, triggersProp, sr, confidence, norm, ew, fib, ds, cl, bz, sp, th, cb, price, activePatterns, tradePlan, mainSc, ltPrice, stPrice, longProb, shortProb, hasAnalysis, analysisTriggers, fpv2, invalLevel, markDirty])

  // ── DIRECT VISIBLE CANVAS RENDER ──
  useEffect(() => {
    const loop = () => {
      const canvas = overlayRef.current; const parent = parentRef.current
      if (!canvas || !parent) { rafRef.current = requestAnimationFrame(loop); return }

      if (parent.lastChild !== canvas) {
        parent.appendChild(canvas)
      }

      if (!dirtyRef.current) { rafRef.current = requestAnimationFrame(loop); return }

      const rect = canvas.getBoundingClientRect()
      const w = rect.width; const h = rect.height
      if (w <= 0 || h <= 0) { rafRef.current = requestAnimationFrame(loop); return }

      const dpr = window.devicePixelRatio
      const cw = Math.round(w * dpr); const ch = Math.round(h * dpr)
      const sz = canvasSizeRef.current

      if (sz.w !== cw || sz.h !== ch) {
        canvas.width = cw; canvas.height = ch
        canvas.style.width = `${w}px`; canvas.style.height = `${h}px`
        sz.w = cw; sz.h = ch
      }

      const ctx = canvas.getContext("2d")
      if (!ctx) { rafRef.current = requestAnimationFrame(loop); return }

      ctx.save()
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.clearRect(0, 0, cw, ch)
      ctx.restore()

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      drawOnCanvas(ctx, w, h)

      dirtyRef.current = false
      rafRef.current = requestAnimationFrame(loop)
    }
    rafRef.current = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(rafRef.current)
  }, [drawOnCanvas])

  useEffect(() => {
    let cancelled = false
    api.getSkhyOHLCV(activeTimeframe, 240).then((res) => {
      if (cancelled) return
      if (res?.data && Array.isArray(res.data) && (res.data as Candle[]).length > 0) {
        setOhlcv(res.data)
        lastValidOhlcvRef.current = res.data as Candle[]
        const closes = (res.data as Candle[]).map((d: Candle) => d.close)
        if (closes.length >= 100) setEmaValues({ ema20: calcLastEMA(closes, 20), ema50: calcLastEMA(closes, 50), ema100: calcLastEMA(closes, 100) })
      }
    }).catch(() => {})
    return () => { cancelled = true }
  }, [activeTimeframe])

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

  useEffect(() => { markDirty() }, [markDirty, analysis, triggersProp, sr, confidence, price])

  const data = ohlcv.length > 0 ? ohlcv : lastValidOhlcvRef.current

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const canvas = overlayRef.current; const chart = chartRef.current
    if (!canvas || !chart) { setTooltip(null); return }
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left; const my = e.clientY - rect.top
    const t = chart.timeScale().coordinateToTime(mx) as number | null; const pr = candleSeriesRef.current?.coordinateToPrice(my)
    if (t == null || pr == null) { setTooltip(null); return }
    const lines = buildHover(pr, data, norm, ew as Record<string, unknown> | undefined, fib as Record<string, unknown> | undefined)
    if (lines.length > 0) setTooltip({ x: e.clientX - rect.left + 12, y: e.clientY - rect.top - 12, text: lines })
    else setTooltip(null)
  }, [data, norm, ew, fib])
  const handleMouseLeave = () => setTooltip(null)

  const toggleOverlay = useCallback((key: OverlayKey) => {
    setOverlays(prev => ({ ...prev, [key]: !prev[key] })); dirtyRef.current = true
  }, [])

  const toggleItems: { key: OverlayKey; label: string }[] = [
    { key: "aiOverlay", label: "AI Overlay" },
    { key: "structure", label: "Struktur" }, { key: "channel", label: "Kanal" },
    { key: "breakout", label: "Breakout" }, { key: "fibonacci", label: "Fib" },
    { key: "targets", label: "Hədəflər" }, { key: "triggers", label: "Trigger" },
    { key: "mainScenario", label: "Ssenari" }, { key: "smc", label: "SMC" },
    { key: "patterns", label: "Pattern" }, { key: "elliott", label: "Elliott" },
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
        <div className="flex items-center gap-0.5 overflow-x-auto max-w-[340px] mr-1">
          {toggleItems.map(({ key, label }) => (
            <button key={key} onClick={() => toggleOverlay(key)}
              className={cn("px-1 py-0.5 text-[7px] font-mono rounded border transition-colors shrink-0",
                overlays[key] ? "bg-blue-600/20 border-blue-500/40 text-blue-400" : "bg-gray-800/30 border-gray-700/30 text-gray-600 hover:text-gray-400")}>
              {label}
            </button>
          ))}
          <button onClick={fitToAnalysis}
            className="px-1 py-0.5 text-[7px] font-mono rounded border border-cyan-700/40 bg-cyan-900/20 text-cyan-400 hover:bg-cyan-900/40 shrink-0">
            Analizə uyğunlaşdır
          </button>
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
      <div ref={parentRef} className="relative flex-1 overflow-hidden" style={{ isolation: "isolate" }} onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
        <div ref={containerRef} className="absolute inset-0" />
            {price > 0 && (
              <>
                <div className="absolute top-0.5 left-1 z-[6] flex flex-col gap-px text-[7px] pointer-events-none max-w-[55%]">
                  <div className="flex flex-wrap gap-x-1.5 gap-y-px items-center">
                    {ds && s(ds.label_az) && <span className="px-1 py-0.5 rounded bg-gray-900/70 border border-gray-700/30 text-gray-300 font-mono">{s(ds.label_az)}</span>}
                    <div className={cn("px-1 py-0.5 rounded font-semibold font-mono", longProb > shortProb ? "bg-green-500/15 text-green-400" : "bg-red-500/15 text-red-400")}>
                      {longProb > shortProb ? `↑${longProb}%` : `↓${shortProb}%`}</div>
                    <span className={cn("px-1 py-0.5 rounded font-mono font-semibold", confidence >= 70 ? "text-green-400" : confidence >= 50 ? "text-yellow-400" : "text-gray-500")}>
                      {status} {confidence}%</span>
                  </div>
                  <div className="flex flex-wrap gap-x-1.5 gap-y-px items-center">
                    {ltPrice > 0 && <span className="px-1 py-0.5 rounded bg-green-900/20 border border-green-700/20 text-green-400 font-mono">L↑${ltPrice.toFixed(2)}</span>}
                    {stPrice > 0 && <span className="px-1 py-0.5 rounded bg-red-900/20 border border-red-700/20 text-red-400 font-mono">S↓${stPrice.toFixed(2)}</span>}
                    {invalLevel > 0 && <span className="px-1 py-0.5 rounded bg-purple-900/20 border border-purple-700/20 text-purple-400 font-mono">✕${invalLevel.toFixed(2)}</span>}
                    {mainDir && <span className="px-1 py-0.5 rounded bg-yellow-900/20 border border-yellow-700/20 text-yellow-400 font-mono">{mainDir}{mainProb}%</span>}
                    <span className="px-1 py-0.5 rounded bg-gray-900/40 text-gray-500 font-mono">${price.toFixed(2)}</span>
                  </div>
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
          <div className="absolute z-10 pointer-events-none bg-gray-900/95 border border-gray-700 rounded px-2 py-1 text-[9px] text-gray-200 shadow-xl max-w-[320px] whitespace-pre-line" style={{ left: tooltip.x, top: tooltip.y }}>
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
//  AI OVERLAY DRAW FUNCTIONS (enhanced)
// ══════════════════════════════════════════════════

function drawSRZones(
  ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, confidence: number, w: number, data: Candle[],
) {
  const alpha = Math.max(0.08, 0.08 + confidence / 300)
  const zoneH = Math.max(8, (data[data.length - 1]?.high || 160) * 0.005)
  const srLog: { label: string; price: number; y: number; inView: boolean }[] = []
  for (const res of norm.resistances.slice(0, 2)) {
    const y = toY(res.price); const inView = y > 0 && y < 1e6 && y < 10000
    srLog.push({ label: "MÜQ", price: res.price, y, inView })
    if (!inView) continue
    ctx.save()
    ctx.fillStyle = `rgba(242,54,69,${alpha * 0.5})`; ctx.fillRect(0, y - zoneH / 2, w, zoneH)
    ctx.strokeStyle = `rgba(242,54,69,${Math.max(0.4, 0.5 * (confidence / 50))})`; ctx.lineWidth = 0.8; ctx.setLineDash([3, 4])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "7px monospace"; ctx.fillStyle = "rgba(242,54,69,0.8)"
    ctx.fillText(`MÜQAVİMƏT $${res.price.toFixed(2)}`, w - 110, Math.max(10, y - 3))
    ctx.restore()
  }
  for (const sup of norm.supports.slice(0, 2)) {
    const y = toY(sup.price); const inView = y > 0 && y < 1e6 && y < 10000
    srLog.push({ label: "DƏS", price: sup.price, y, inView })
    if (!inView) continue
    ctx.save()
    ctx.fillStyle = `rgba(8,153,129,${alpha * 0.5})`; ctx.fillRect(0, y - zoneH / 2, w, zoneH)
    ctx.strokeStyle = `rgba(8,153,129,${Math.max(0.4, 0.5 * (confidence / 50))})`; ctx.lineWidth = 0.8; ctx.setLineDash([3, 4])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "7px monospace"; ctx.fillStyle = "rgba(8,153,129,0.8)"
    ctx.fillText(`DƏSTƏK $${sup.price.toFixed(2)}`, w - 100, Math.max(10, y - 3))
    ctx.restore()
  }
  console.log("[SKHY] SR_ZONES", srLog)
}

function drawChannelEnhanced(
  ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, confidence: number, w: number, data: Candle[], lx: number,
) {
  const ch = norm.channel
  const hasPoints = ch.upper.length >= 2 || ch.lower.length >= 2 || (ch.channel_top > 0 && ch.channel_bottom > 0)
  if (!hasPoints) return
  const alpha = Math.min(0.75, 0.35 + confidence / 120)
  // Extend lines to cover full visible x range
  const extendPts = (pts: { time: number; value: number }[]): { time: number; value: number }[] => {
    if (pts.length < 2) return pts
    const firstX = toX(pts[0].time); const lastX = toX(pts[pts.length - 1].time)
    if (firstX <= 0 || lastX <= 0 || lastX <= firstX) return pts
    const slope = (pts[pts.length - 1].value - pts[0].value) / (lastX - firstX)
    const extended = [...pts]
    // Extend to right (current candle + future)
    const targetX = lx + 100
    if (lastX < targetX) {
      const extVal = pts[pts.length - 1].value + slope * (targetX - lastX)
      if (extVal > 0) extended.push({ time: pts[pts.length - 1].time + 1000, value: extVal })
    }
    return extended
  }
  const drawLine = (pts: { time: number; value: number }[], color: string, lw: number, dash: number[]) => {
    if (pts.length < 2) return
    const extPts = extendPts(pts)
    ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.setLineDash(dash)
    ctx.beginPath(); let started = false; const coordLog: { t: number; v: number; x: number; y: number }[] = []
    for (const p of extPts) {
      const x = toX(p.time); const y = toY(p.value)
      coordLog.push({ t: p.time, v: p.value, x, y })
      if (x <= 0 || y <= 0 || !Number.isFinite(x) || !Number.isFinite(y)) continue
      if (!started) { ctx.moveTo(x, y); started = true } else ctx.lineTo(x, y)
    }
    if (started) ctx.stroke(); ctx.setLineDash([]); ctx.restore()
  }
  if (ch.upper.length >= 2) drawLine(ch.upper, `rgba(34,211,238,${alpha})`, 1.5, [])
  if (ch.lower.length >= 2) drawLine(ch.lower, `rgba(34,211,238,${alpha})`, 1.5, [])
  if (ch.mid.length >= 2) drawLine(ch.mid, `rgba(34,211,238,${alpha * 0.65})`, 0.8, [6, 4])
  // Fallback: channel_top/channel_bottom
  if ((ch.upper.length < 2 || ch.lower.length < 2) && ch.channel_top > 0 && ch.channel_bottom > 0 && data.length >= 2) {
    const yt = toY(ch.channel_top); const yb = toY(ch.channel_bottom)
    if (yt > 0 && yb > 0) {
      ctx.save(); ctx.strokeStyle = `rgba(34,211,238,${alpha})`; ctx.lineWidth = 1.5
      ctx.beginPath(); ctx.moveTo(0, yt); ctx.lineTo(w, yt); ctx.stroke()
      ctx.beginPath(); ctx.moveTo(0, yb); ctx.lineTo(w, yb); ctx.stroke()
      ctx.setLineDash([6, 4]); ctx.strokeStyle = `rgba(34,211,238,${alpha * 0.65})`; ctx.lineWidth = 0.8
      const ym = toY((ch.channel_top + ch.channel_bottom) / 2)
      ctx.beginPath(); ctx.moveTo(0, ym); ctx.lineTo(w, ym); ctx.stroke(); ctx.setLineDash([]); ctx.restore()
    }
  }
  // Log channel points
  console.log("[SKHY] CHANNEL_POINTS", {
    upper: ch.upper.map(p => ({ t: p.time, v: p.value, x: toX(p.time), y: toY(p.value) })),
    lower: ch.lower.map(p => ({ t: p.time, v: p.value, x: toX(p.time), y: toY(p.value) })),
    mid: ch.mid.map(p => ({ t: p.time, v: p.value, x: toX(p.time), y: toY(p.value) })),
  })
}

function drawFibEnhanced(
  ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, confidence: number, w: number, h: number, data: Candle[], lp: number,
) {
  if (Object.keys(norm.fibonacci.levels).length === 0) return
  const sorted = Object.entries(norm.fibonacci.levels).sort((a, b) => Number(a[0]) - Number(b[0]))
  const alpha = Math.max(0.25, 0.35 * (confidence / 50))

  // Golden zone: 0.618 - 0.786
  const golden618 = norm.fibonacci.levels["0.618"]; const golden786 = norm.fibonacci.levels["0.786"]
  if (golden618 > 0 && golden786 > 0) {
    const y618 = toY(golden618); const y786 = toY(golden786)
    if (y618 > 0 && y786 > 0 && y618 < 10000 && y786 < 10000) {
      ctx.save()
      ctx.fillStyle = `rgba(245,158,11,${Math.max(0.04, 0.06 * (confidence / 50))})`
      ctx.fillRect(0, Math.min(y618, y786), w, Math.abs(y618 - y786))
      ctx.font = "6px monospace"; ctx.fillStyle = `rgba(245,158,11,${Math.max(0.2, 0.3 * (confidence / 50))})`
      ctx.fillText("QIZIL ZONA", 4, (y618 + y786) / 2 + 2)
      ctx.restore()
    }
  }

  const fibLog: { ratio: string; price: number; y: number; validPrice: boolean; inViewport: boolean }[] = []
  for (const [key, price] of sorted) {
    if (price <= 0) continue; const y = toY(price)
    const inView = y > 0 && y < 1e6 && y < 10000
    fibLog.push({ ratio: key, price, y, validPrice: price > 0, inViewport: inView })
    if (!inView) continue
    const pct = (Number(key) * 100).toFixed(1)
    ctx.save()
    ctx.strokeStyle = `rgba(245,158,11,${Math.max(0.25, 0.35 * (confidence / 50))})`; ctx.lineWidth = 0.8; ctx.setLineDash([2, 4])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "7px monospace"; ctx.fillStyle = "rgba(245,158,11,0.8)"
    ctx.fillText(`Fib ${pct}% $${price.toFixed(2)}`, w - 110, Math.max(10, y - 3))
    ctx.restore()
  }

  // Edge badges for out-of-viewport Fib levels
  for (const f of fibLog) {
    if (f.inViewport || !f.validPrice) continue
    const dir = f.price > (data.length > 0 ? data[data.length - 1].close : f.price) ? "up" : "down"
    ctx.save(); ctx.font = "6px monospace"; ctx.fillStyle = "rgba(245,158,11,0.6)"; ctx.textAlign = "right"
    ctx.fillText(`${dir === "up" ? "↑" : "↓"} Fib ${(Number(f.ratio) * 100).toFixed(0)}%`, w - 4, dir === "up" ? 14 : h - 6)
    ctx.textAlign = "left"; ctx.restore()
  }

  console.log("[SKHY] FIB_LEVELS", fibLog)

  // Extensions at any confidence
  const allExt = { ...norm.fibonacci.extensions_up, ...norm.fibonacci.extensions_down }
  for (const [key, price] of Object.entries(allExt)) {
    if (price <= 0) continue; const y = toY(price)
    if (y <= 0 || y >= 1e6 || y >= 10000) continue
    ctx.save()
    ctx.strokeStyle = `rgba(99,102,241,${Math.max(0.2, 0.3 * (confidence / 50))})`; ctx.lineWidth = 0.5; ctx.setLineDash([1, 5])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = `rgba(99,102,241,${Math.max(0.3, 0.5 * (confidence / 50))})`
    ctx.fillText(`Ext ${key} $${price.toFixed(2)}`, w - 95, Math.max(10, y - 2))
    ctx.restore()
  }
}

function drawSMCEnhanced(
  ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, data: Candle[], w: number, confidence: number,
) {
  const alpha = 0.3 + confidence / 200
  // OB: max 2
  for (const ob of norm.smc.near_ob.slice(0, 2)) {
    const p = n(ob.price); if (p <= 0) continue; const y = toY(p)
    if (y <= 0 || y >= 1e6) continue
    ctx.save(); ctx.strokeStyle = `rgba(168,85,247,${alpha})`; ctx.lineWidth = 0.6; ctx.setLineDash([3, 3])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "7px monospace"; ctx.fillStyle = `rgba(168,85,247,${alpha})`
    ctx.fillText(`OB $${p.toFixed(2)}`, 4, y - 2); ctx.restore()
  }
  // FVG: max 2
  for (const f of norm.smc.near_fvg.slice(0, 2)) {
    const top = n(f.gap_high) || n(f.price); const bot = n(f.gap_low) || (top * 0.998)
    if (top <= 0 || bot <= 0) continue; const yt = toY(top); const yb = toY(bot)
    if (yt <= 0 || yb <= 0 || Math.abs(yt - yb) < 2) continue
    ctx.save(); ctx.fillStyle = `rgba(34,211,238,${alpha * 0.3})`
    ctx.fillRect(0, Math.min(yt, yb), w, Math.abs(yt - yb))
    ctx.strokeStyle = `rgba(34,211,238,${alpha * 0.6})`; ctx.lineWidth = 0.4; ctx.setLineDash([2, 4])
    ctx.strokeRect(0, Math.min(yt, yb), w, Math.abs(yt - yb)); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = `rgba(34,211,238,${alpha * 0.7})`
    ctx.fillText("FVG", 4, (yt + yb) / 2 + 2); ctx.restore()
  }
  // BOS: max 2
  for (const bos of norm.smc.near_bos.slice(0, 2)) {
    const p = n(bos.price); if (p <= 0) continue; const y = toY(p)
    if (y <= 0 || y >= 1e6) continue
    ctx.save(); ctx.strokeStyle = `rgba(245,158,11,${alpha})`; ctx.lineWidth = 0.8; ctx.setLineDash([5, 3])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "7px monospace"; ctx.fillStyle = `rgba(245,158,11,${alpha})`
    ctx.fillText("BOS", 4, y - 2); ctx.restore()
  }
  // CHoCH: max 2
  for (const ch of norm.smc.near_choch.slice(0, 2)) {
    const p = n(ch.price); if (p <= 0) continue; const y = toY(p)
    if (y <= 0 || y >= 1e6) continue
    ctx.save(); ctx.strokeStyle = `rgba(242,54,69,${alpha})`; ctx.lineWidth = 0.8; ctx.setLineDash([5, 3])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "7px monospace"; ctx.fillStyle = `rgba(242,54,69,${alpha})`
    ctx.fillText("CHoCH", 4, y - 2); ctx.restore()
  }
  // Liquidity sweep: max 2
  for (const liq of norm.smc.near_liq.slice(0, 2)) {
    const p = n(liq.price); if (p <= 0) continue; const y = toY(p)
    if (y <= 0 || y >= 1e6) continue
    ctx.save(); ctx.strokeStyle = `rgba(34,211,238,${alpha * 0.5})`; ctx.lineWidth = 0.5; ctx.setLineDash([2, 6])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = `rgba(34,211,238,${alpha * 0.6})`
    ctx.fillText("Likvidlik", 4, y - 2); ctx.restore()
  }
  // EQH/EQL: max 2
  for (const eq of norm.smc.near_eq.slice(0, 2)) {
    const p = n(eq.price); if (p <= 0) continue; const y = toY(p)
    if (y <= 0 || y >= 1e6) continue
    const isH = s(eq.category).includes("equal_high")
    ctx.save(); ctx.strokeStyle = `rgba(168,85,247,${alpha * 0.4})`; ctx.lineWidth = 0.4; ctx.setLineDash([1, 4])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = `rgba(168,85,247,${alpha * 0.5})`
    ctx.fillText(isH ? "EQH" : "EQL", 4, y - 2); ctx.restore()
  }
}

function drawLiquidityPools(
  ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, data: Candle[], w: number,
) {
  // if explicit liquidity data exists, use it; otherwise skip
}

function drawBreakoutEnhanced(
  ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, confidence: number, w: number, h: number, data: Candle[], lx: number, candleW: number,
) {
  const bo = norm.breakout
  if (bo.top <= 0 || bo.bottom <= 0) return
  const yt = toY(bo.top); const yb = toY(bo.bottom)
  if (yt <= 0 || yb <= 0) return
  const alpha = 0.3 + confidence / 200
  ctx.save()
  ctx.fillStyle = `rgba(168,85,247,${alpha * 0.35})`
  ctx.fillRect(0, Math.min(yt, yb), w, Math.abs(yt - yb))
  ctx.strokeStyle = `rgba(168,85,247,${alpha})`; ctx.lineWidth = 0.6
  ctx.setLineDash(bo.bullishReady && bo.bearishReady ? [4, 4] : [3, 3])
  ctx.strokeRect(0, Math.min(yt, yb), w, Math.abs(yt - yb)); ctx.setLineDash([])
  const sx = lx + candleW * 2
  const readyLabel = bo.bullishReady ? "YUXARI QIRILMA" : bo.bearishReady ? "AŞAĞI QIRILMA" : "BREAKOUT GÖZLƏNİR"
  ctx.font = "bold 7px monospace"
  ctx.fillStyle = bo.bullishReady ? "rgba(8,153,129,0.8)" : bo.bearishReady ? "rgba(242,54,69,0.8)" : `rgba(168,85,247,${alpha})`
  ctx.fillText(readyLabel, sx, Math.min(yt, yb) - 4)
  ctx.font = "7px monospace"; ctx.fillStyle = `rgba(168,85,247,${alpha * 0.7})`
  ctx.fillText(`${bo.testCount > 0 ? `${bo.testCount}x test` : "Təsdiq gözlənilir"}`, sx, Math.max(yt, yb) + 12)
  ctx.restore()
}

function drawPatternEnhanced(
  ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, data: Candle[], w: number, confidence: number, lx: number, candleW: number,
) {
  const pat = norm.strongestPattern
  if (!pat) return
  const prob = n(pat.probability)
  if (prob < 50) return
  const name = s(pat.name)
  const bLv = n(pat.breakout_level) || n(pat.breakdown_level)
  const mTgt = n(pat.measured_target)
  const confirmed = s(pat.status) === "CONFIRMED"
  const clr = confirmed ? "rgba(8,153,129,0.7)" : "rgba(245,158,11,0.6)"
  const lclr = confirmed ? TV_GREEN : COL_ORANGE

  if (name.includes("Double Top") || name.includes("Double Bottom")) {
    const isTop = name.includes("Top")
    const p1Price = n(pat.peak1_price) || n(pat.left_peak_price)
    const p2Price = n(pat.peak2_price) || n(pat.right_peak_price)
    const p1Idx = n(pat.peak1_index) > 0 ? Math.min(n(pat.peak1_index), data.length - 1) : -1
    const p2Idx = n(pat.peak2_index) > 0 ? Math.min(n(pat.peak2_index), data.length - 1) : -1
    const i1 = p1Idx > 0 ? p1Idx : Math.floor(data.length * 0.2)
    const i2 = p2Idx > 0 ? p2Idx : Math.floor(data.length * 0.5)
    const pp1 = p1Price > 0 ? p1Price : data[Math.min(i1, data.length - 1)]?.close || 0
    const pp2 = p2Price > 0 ? p2Price : data[Math.min(i2, data.length - 1)]?.close || 0
    const x1 = toX(data[Math.min(i1, data.length - 1)]?.time); const x2 = toX(data[Math.min(i2, data.length - 1)]?.time)
    const y1 = toY(pp1); const y2 = toY(pp2)
    if (x1 > 0 && x2 > 0 && y1 > 0 && y2 > 0) {
      ctx.save(); ctx.strokeStyle = clr; ctx.lineWidth = 1.2
      ctx.beginPath(); ctx.arc(x1, y1, 6, 0, Math.PI * 2); ctx.stroke()
      ctx.beginPath(); ctx.arc(x2, y2, 6, 0, Math.PI * 2); ctx.stroke()
      ctx.font = "bold 7px monospace"; ctx.fillStyle = lclr
      ctx.fillText(isTop ? "Ⅰ" : "Ⅰ", x1 + 7, y1 + 3); ctx.fillText(isTop ? "Ⅱ" : "Ⅱ", x2 + 7, y2 + 3)
      const neckY = isTop ? Math.max(y1, y2) : Math.min(y1, y2)
      ctx.strokeStyle = "rgba(242,54,69,0.3)"; ctx.lineWidth = 0.5; ctx.setLineDash([3, 4])
      ctx.beginPath(); ctx.moveTo(x1, neckY); ctx.lineTo(x2, neckY); ctx.stroke(); ctx.setLineDash([])
      ctx.restore()
    }
  } else if (name.includes("Head and Shoulders") || name.includes("Inverse Head")) {
    const isInv = name.includes("Inverse")
    const iL = Math.floor(data.length * 0.12); const iH = Math.floor(data.length * 0.35); const iR = Math.floor(data.length * 0.55)
    const pL = data[Math.min(iL, data.length - 1)]?.close || 0; const pH = data[Math.min(iH, data.length - 1)]?.close || 0; const pR = data[Math.min(iR, data.length - 1)]?.close || 0
    const xL = toX(data[Math.min(iL, data.length - 1)]?.time); const xH = toX(data[Math.min(iH, data.length - 1)]?.time); const xR = toX(data[Math.min(iR, data.length - 1)]?.time)
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
  } else if (name.includes("Wedge")) {
    const isRising = name.includes("Rising"); const si = Math.max(0, data.length - 18); const ei = data.length - 1
    const xs = toX(data[si]?.time); const xe = toX(data[ei]?.time)
    if (xs > 0 && xe > 0) {
      const lb = data.slice(si); const top1 = lb[0]?.high || 0; const top2 = lb[lb.length - 1]?.high || 0; const bot1 = lb[0]?.low || 0; const bot2 = lb[lb.length - 1]?.low || 0
      const yt1 = toY(top1); const yt2 = toY(top2); const yb1 = toY(bot1); const yb2 = toY(bot2)
      if (yt1 > 0 && yt2 > 0 && yb1 > 0 && yb2 > 0) {
        ctx.save(); ctx.strokeStyle = clr; ctx.lineWidth = 1; ctx.setLineDash([2, 3])
        ctx.beginPath(); ctx.moveTo(xs, yt1); ctx.lineTo(xe, yt2); ctx.stroke()
        ctx.beginPath(); ctx.moveTo(xs, yb1); ctx.lineTo(xe, yb2); ctx.stroke(); ctx.setLineDash([])
        ctx.font = "7px monospace"; ctx.fillStyle = lclr; ctx.fillText(isRising ? "Rising Wedge" : "Falling Wedge", (xs + xe) / 2 - 30, (yt1 + yb2) / 2)
        ctx.restore()
      }
    }
  } else if (name.includes("Triangle")) {
    const si = Math.max(0, data.length - 18); const ei = data.length - 1
    const xs = toX(data[si]?.time); const xe = toX(data[ei]?.time)
    if (xs > 0 && xe > 0) {
      const lb = data.slice(si); const top1 = lb[0]?.high || 0; const top2 = lb[lb.length - 1]?.high || 0; const bot1 = lb[0]?.low || 0; const bot2 = lb[lb.length - 1]?.low || 0
      const yt1 = toY(top1); const yt2 = toY(top2); const yb1 = toY(bot1); const yb2 = toY(bot2)
      if (yt1 > 0 && yt2 > 0 && yb1 > 0 && yb2 > 0) {
        ctx.save(); ctx.strokeStyle = clr; ctx.lineWidth = 1; ctx.setLineDash([2, 3])
        ctx.beginPath(); ctx.moveTo(xs, yt1); ctx.lineTo(xe, yt2); ctx.stroke()
        ctx.beginPath(); ctx.moveTo(xs, yb1); ctx.lineTo(xe, yb2); ctx.stroke(); ctx.setLineDash([])
        ctx.font = "7px monospace"; ctx.fillStyle = lclr; ctx.fillText(name, (xs + xe) / 2 - 30, (yt1 + yb2) / 2)
        ctx.restore()
      }
    }
  }

  // Compact single-line label at top-right (avoids candle overlap)
  const stLbl: Record<string, string> = { CONFIRMED: "✓", DETECTED: "?", FORMING: "~" }
  ctx.save(); ctx.font = "bold 7px monospace"; ctx.fillStyle = lclr; ctx.textAlign = "right"
  ctx.fillText(`${stLbl[s(pat.status)] || "?"} ${name} ${prob}% ${s(pat.timeframe)}`, w - 4, 12)
  ctx.textAlign = "left"; ctx.restore()
}

function drawRetestEnhanced(
  ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, w: number, lx: number, candleW: number,
) {
  if (!norm.retest.active || norm.retest.level <= 0) return
  const y = toY(norm.retest.level); if (y <= 0) return
  ctx.save()
  ctx.strokeStyle = "rgba(41,98,255,0.5)"; ctx.lineWidth = 0.6; ctx.setLineDash([2, 4])
  ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
  ctx.font = "7px monospace"; ctx.fillStyle = "rgba(41,98,255,0.7)"
  ctx.fillText("RETEST GÖZLƏNİR", lx + candleW * 2, y - 3)
  ctx.restore()
}

function drawTargetsEnhanced(
  ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, confidence: number, w: number, data: Candle[], lx: number, candleW: number, status: string,
) {
  const tgts = norm.targets
  if (!tgts || tgts.length === 0) return
  const isWait = confidence < 50
  const maxShow = confidence >= 80 ? 5 : confidence >= 70 ? 3 : 2
  const alpha = 0.2 + confidence / 200
  for (let i = 0; i < Math.min(tgts.length, maxShow); i++) {
    const t = tgts[i]; const p = n(t.price)
    if (p <= 0) continue
    const y = toY(p); if (y <= 0 || y > 1e6) continue
    const faded = 1 - (i / (maxShow + 1))
    ctx.save()
    ctx.strokeStyle = `rgba(8,153,129,${alpha * faded * 0.6})`; ctx.lineWidth = Math.max(0.3, 1 - i * 0.2)
    ctx.setLineDash(isWait ? [2, 5] : [])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "7px monospace"; ctx.fillStyle = `rgba(8,153,129,${alpha * faded})`
    ctx.fillText(`${t.level} $${p.toFixed(2)}${t.probability ? ` ${t.probability}%` : ""}`, w - 100, y - 2)
    ctx.restore()
  }
}

function drawEntrySL(
  ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, w: number, lx: number, candleW: number,
) {
  const tp = norm.tradePlan
  if (!tp) return

  // Entry zone
  const entryMin = n((tp.entry_zone as Record<string, unknown>)?.min)
  const entryMax = n((tp.entry_zone as Record<string, unknown>)?.max)
  if (entryMin > 0 && entryMax > 0) {
    const yMin = toY(entryMin); const yMax = toY(entryMax)
    if (yMin > 0 && yMax > 0) {
      ctx.save()
      ctx.fillStyle = "rgba(8,153,129,0.10)"; ctx.fillRect(0, Math.min(yMin, yMax), w, Math.abs(yMin - yMax))
      ctx.strokeStyle = "rgba(8,153,129,0.6)"; ctx.lineWidth = 1; ctx.setLineDash([])
      ctx.beginPath(); ctx.moveTo(0, yMin); ctx.lineTo(w, yMin); ctx.stroke()
      ctx.beginPath(); ctx.moveTo(0, yMax); ctx.lineTo(w, yMax); ctx.stroke()
      ctx.font = "bold 7px monospace"; ctx.fillStyle = "rgba(8,153,129,0.8)"
      ctx.fillText(`GİRİŞ $${entryMin.toFixed(2)}-$${entryMax.toFixed(2)}`, lx + candleW * 2, Math.min(yMin, yMax) - 3)
      ctx.restore()
    }
  }

  // Stop Loss
  const sl = n(tp.stop_loss)
  if (sl > 0) {
    const y = toY(sl); if (y > 0 && y < 1e6) {
      ctx.save()
      ctx.strokeStyle = "rgba(242,54,69,0.7)"; ctx.lineWidth = 1.2
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
      ctx.font = "bold 7px monospace"; ctx.fillStyle = "rgba(242,54,69,0.8)"
      ctx.fillText(`SL $${sl.toFixed(2)}`, lx + candleW * 2, y - 3)
      ctx.restore()
    }
  }
}

function drawTPLevels(
  ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, w: number, data: Candle[], candleW: number,
) {
  const tp = norm.tradePlan
  if (!tp) return
  const tps = (tp.take_profits as { level: string; price: number; risk_reward: number; probability: number }[] || []).slice(0, 5)
  for (let i = 0; i < tps.length; i++) {
    const tpItem = tps[i]; const p = n(tpItem.price)
    if (p <= 0) continue; const y = toY(p)
    if (y <= 0 || y > 1e6) continue
    const fade = 1 - i * 0.15
    ctx.save()
    ctx.strokeStyle = `rgba(8,153,129,${0.3 * fade})`; ctx.lineWidth = Math.max(0.4, 1.2 - i * 0.2)
    ctx.setLineDash([]); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
    ctx.font = "7px monospace"; ctx.fillStyle = `rgba(8,153,129,${0.7 * fade})`
    ctx.fillText(`${tpItem.level} $${p.toFixed(2)} R:${n(tpItem.risk_reward).toFixed(1)}`, w - 120, y - 2)
    ctx.restore()
  }
}

function drawTriggersEnhanced(
  ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, confidence: number, w: number, lx: number, candleW: number, status: string,
) {
  const alpha = 0.5 + confidence / 150
  // LONG trigger
  if (norm.longTrigger > 0) {
    const y = toY(norm.longTrigger)
    if (y > 0 && y < 1e6) {
      ctx.save()
      ctx.strokeStyle = `rgba(8,153,129,${alpha})`; ctx.lineWidth = 1.5; ctx.setLineDash([6, 4])
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
      ctx.font = "bold 7px monospace"; ctx.fillStyle = `rgba(8,153,129,${Math.min(1, alpha + 0.2)})`
      ctx.fillText(`LONG TƏSDİQİ $${norm.longTrigger.toFixed(2)}`, lx + candleW * 2, y - 3)
      ctx.restore()
    }
  }
  // SHORT trigger
  if (norm.shortTrigger > 0) {
    const y = toY(norm.shortTrigger)
    if (y > 0 && y < 1e6) {
      ctx.save()
      ctx.strokeStyle = `rgba(242,54,69,${alpha})`; ctx.lineWidth = 1.5; ctx.setLineDash([6, 4])
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
      ctx.font = "bold 7px monospace"; ctx.fillStyle = `rgba(242,54,69,${Math.min(1, alpha + 0.2)})`
      ctx.fillText(`SHORT TƏSDİQİ $${norm.shortTrigger.toFixed(2)}`, lx + candleW * 2, y - 3)
      ctx.restore()
    }
  }
}

function drawEWEnhanced(
  ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number,
  ew: Record<string, unknown> | undefined, data: Candle[], w: number, confidence: number,
) {
  if (!ew || confidence < 60 || data.length === 0) return
  const waves = ew.waves as { type: string; start: number; end: number; index: number; label?: string }[] | undefined
  if (!waves || waves.length < 3) return
  const ewConf = n(ew.confidence) || confidence; const uncertain = ewConf < 50
  const labels = ["1", "2", "3", "4", "5", "A", "B", "C"]
  for (let i = 0; i < Math.min(waves.length, 8); i++) {
    const wave: { type: string; start: number; end: number; index: number; label?: string } = waves[i]; const idx = wave.index
    if (idx <= 0 || idx >= data.length) continue
    const x = toX(data[idx]?.time); if (x <= 0) continue
    const isUp = wave.type === "wave_up"; const y = toY(isUp ? wave.end : wave.start)
    if (y <= 0) continue
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
      ctx.font = "7px monospace"; ctx.fillStyle = isUp ? "rgba(8,153,129,0.7)" : "rgba(242,54,69,0.7)"
      ctx.fillText(labels[i] || String(i + 1), x + sz + 3, y + 3)
    }
    ctx.restore()
  }
  const lastLabel = waves[waves.length - 1]?.label || ""
  ctx.save(); ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.6)"
  ctx.fillText(uncertain ? "Elliott sayımı qeyri-müəyyəndir" : `Cari: Dalğa ${lastLabel}`, 10, 72)
  ctx.restore()
}

function drawScenarioBlocks(
  ctx: CanvasRenderingContext2D, _toX: (t: number) => number, _toY: (p: number) => number,
  norm: NormalizedAnalysis, w: number, h: number, lx: number, lp: number, candleW: number,
) {
  const main = norm.scenarios.main; const alt = norm.scenarios.alt
  const bh = 52; const bw = w > 600 ? 180 : 140; const gap = 6; const pad = 4
  const by = h - bh - 2
  const mainDir = main ? s(main.direction_az || main.direction || "") : ""
  const mainProb = main ? n(main.probability) : 0
  const mainTrigger = main ? s(main.activation_trigger || m(main)) : ""
  const mainInv = main ? s(main.invalidation_condition || "") : ""
  const altDir = alt ? s(alt.direction_az || alt.direction || "") : ""
  const altProb = alt ? n(alt.probability) : 0
  const altTrigger = alt ? s(alt.activation_trigger || m(alt)) : ""

  function m(sc: Record<string, unknown>): string {
    const tp = sc.path_points as PathPoint[] | undefined
    if (tp && tp.length > 0) return tp[0]?.label || ""
    return ""
  }

  // Main scenario block (left)
  if (main) {
    const bx = pad
    const isLong = mainDir.includes("ALIŞ") || mainDir.includes("LONG") || mainDir.includes("UP")
    ctx.save()
    ctx.fillStyle = "rgba(11,17,23,0.85)"; ctx.strokeStyle = isLong ? "rgba(8,153,129,0.4)" : "rgba(242,54,69,0.4)"; ctx.lineWidth = 0.5
    ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, 3); ctx.fill(); ctx.stroke()
    ctx.font = "bold 7px monospace"; ctx.fillStyle = isLong ? "rgba(8,153,129,0.9)" : "rgba(242,54,69,0.9)"
    ctx.fillText(`ƏSAS ${mainDir}`, bx + 4, by + 10)
    ctx.font = "7px monospace"; ctx.fillStyle = "rgba(245,158,11,0.8)"; ctx.fillText(`${mainProb}%`, bx + bw - 35, by + 10)
    ctx.font = "6px monospace"; ctx.fillStyle = "rgba(156,163,175,0.6)"
    if (mainTrigger) ctx.fillText(`Trigger: ${mainTrigger.slice(0, 18)}`, bx + 4, by + 24)
    if (mainInv) ctx.fillText(`Ləğv: ${mainInv.slice(0, 20)}`, bx + 4, by + 36)
    ctx.restore()
  }

  // Alternative scenario block (right)
  if (alt) {
    const bx = pad + bw + gap
    const isLong = altDir.includes("ALIŞ") || altDir.includes("LONG") || altDir.includes("UP")
    ctx.save()
    ctx.fillStyle = "rgba(11,17,23,0.85)"; ctx.strokeStyle = "rgba(107,114,128,0.4)"; ctx.lineWidth = 0.5
    ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, 3); ctx.fill(); ctx.stroke()
    ctx.font = "bold 7px monospace"; ctx.fillStyle = "rgba(156,163,175,0.9)"
    ctx.fillText(`ALT ${altDir}`, bx + 4, by + 10)
    ctx.font = "7px monospace"; ctx.fillStyle = "rgba(245,158,11,0.8)"; ctx.fillText(`${altProb}%`, bx + bw - 35, by + 10)
    ctx.font = "6px monospace"; ctx.fillStyle = "rgba(156,163,175,0.6)"
    if (altTrigger) ctx.fillText(`Trigger: ${altTrigger.slice(0, 18)}`, bx + 4, by + 24)
    ctx.restore()
  }
}

function drawLegend(
  ctx: CanvasRenderingContext2D, w: number, h: number,
  ov: Record<string, boolean>, norm: NormalizedAnalysis, confidence: number,
) {
  const items: { label: string; color: string; active: boolean }[] = [
    { label: "SR", color: confidence >= 70 ? TV_GREEN : TV_RED, active: ov.structure },
    { label: "CH", color: COL_PURPLE, active: ov.channel },
    { label: "BO", color: COL_PURPLE, active: ov.breakout },
    { label: "FB", color: COL_ORANGE, active: ov.fibonacci },
    { label: "PT", color: COL_ORANGE, active: ov.patterns },
    { label: "TR", color: TV_GREEN, active: ov.triggers },
    { label: "SC", color: TV_GREEN, active: ov.mainScenario },
    { label: "MC", color: COL_PURPLE, active: ov.smc },
    { label: "EW", color: COL_PURPLE, active: ov.elliott },
  ]
  const active = items.filter(i => i.active)
  if (active.length === 0) return

  const lh = 9; const pd = 3; const cols = 3
  const rows = Math.ceil(active.length / cols)
  const boxW = 116; const boxH = rows * lh + pd * 2 + 10
  const bx = Math.max(2, w - boxW - 4); const by = Math.max(2, h - boxH - 4)

  ctx.save(); ctx.globalAlpha = 0.75
  ctx.fillStyle = "rgba(11,17,23,0.85)"; ctx.strokeStyle = "rgba(55,65,81,0.4)"; ctx.lineWidth = 0.5
  ctx.beginPath(); ctx.roundRect(bx, by, boxW, boxH, 3); ctx.fill(); ctx.stroke()

  for (let i = 0; i < active.length; i++) {
    const col = i % cols; const row = Math.floor(i / cols)
    const ix = bx + pd + col * (boxW / cols); const iy = by + pd + row * lh + 7
    ctx.fillStyle = active[i].color; ctx.fillRect(ix, iy - 3, 4, 4)
    ctx.fillStyle = "rgba(156,163,175,0.8)"; ctx.font = "6px monospace"
    ctx.fillText(active[i].label, ix + 6, iy)
  }

  const extra = `İnam:${confidence}% ${norm.status}${norm.strongestPattern ? ` ${s(norm.strongestPattern.name)}` : ""}`
  ctx.fillStyle = "rgba(156,163,175,0.5)"; ctx.font = "6px monospace"
  ctx.fillText(extra, bx + pd, by + boxH - 6)
  ctx.restore()
}

function drawInv(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, invalLevel: number, w: number, lx: number, cw: number) {
  if (invalLevel <= 0) return
  const y = toY(invalLevel); if (y <= 0) return
  ctx.save(); ctx.strokeStyle = "rgba(242,54,69,0.5)"; ctx.lineWidth = 0.8; ctx.setLineDash([4, 4])
  ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
  ctx.font = "7px monospace"; ctx.fillStyle = "rgba(242,54,69,0.7)"; ctx.fillText(`Ləğvetmə $${invalLevel.toFixed(2)}`, lx + cw * 2, y - 3)
  ctx.restore()
}

function buildHover(
  price: number, ohlcv: Candle[],
  norm: NormalizedAnalysis,
  ew: Record<string, unknown> | undefined,
  fib: Record<string, unknown> | undefined,
): string[] {
  const lines: string[] = []
  const DP = (p: number) => "$" + p.toFixed(2)
  lines.push(`Qiymət: ${DP(price)} · ${norm.status} ${norm.confidence}%`)

  const idx = ohlcv.findIndex(d => Math.abs(d.close - price) / price < 0.01)
  if (idx >= 0) {
    const c = ohlcv[idx]
    lines.push(`Şam #${idx} A:${c.open.toFixed(2)} Y:${c.high.toFixed(2)} D:${c.low.toFixed(2)} B:${c.close.toFixed(2)} H:${(c.volume / 1000).toFixed(0)}K`)
  }

  // Triggers
  if (norm.longTrigger > 0 && Math.abs(norm.longTrigger - price) / price < 0.02)
    lines.push(`LONG təsdiqi: ${DP(norm.longTrigger)}`)
  if (norm.shortTrigger > 0 && Math.abs(norm.shortTrigger - price) / price < 0.02)
    lines.push(`SHORT təsdiqi: ${DP(norm.shortTrigger)}`)

  // Breakout
  if (norm.breakout.top > 0 && Math.abs(norm.breakout.top - price) / price < 0.02)
    lines.push(`Breakout üst: ${DP(norm.breakout.top)} Test: ${norm.breakout.testCount}x`)
  if (norm.breakout.bottom > 0 && Math.abs(norm.breakout.bottom - price) / price < 0.02)
    lines.push(`Breakout alt: ${DP(norm.breakout.bottom)} Test: ${norm.breakout.testCount}x`)

  // Targets
  for (const t of norm.targets.slice(0, 3)) {
    if (Math.abs(n(t.price) - price) / price < 0.02)
      lines.push(`${t.level} ${DP(n(t.price))} ${n(t.probability)}%`)
  }

  // Entry / SL
  if (norm.tradePlan?.trade_ready) {
    const entryMin = n((norm.tradePlan.entry_zone as Record<string, unknown>)?.min)
    const entryMax = n((norm.tradePlan.entry_zone as Record<string, unknown>)?.max)
    const sl = n(norm.tradePlan.stop_loss)
    if (entryMin > 0 && price >= entryMin && price <= entryMax) lines.push("Giriş zonası")
    if (sl > 0 && Math.abs(sl - price) / price < 0.02) lines.push(`Stop Loss: ${DP(sl)}`)
  }

  // Pattern
  if (norm.strongestPattern) {
    const pat = norm.strongestPattern
    if (n(pat.breakout_level) > 0 && Math.abs(n(pat.breakout_level) - price) / price < 0.03)
      lines.push(`${s(pat.name)} qırılma: ${DP(n(pat.breakout_level))} Hədəf: ${DP(n(pat.measured_target))}`)
  }

  // S/R
  for (const r of norm.resistances) {
    if (r.price > 0 && Math.abs(r.price - price) / price < 0.02) lines.push(`Müqavimət: ${DP(r.price)}`)
  }
  for (const s of norm.supports) {
    if (s.price > 0 && Math.abs(s.price - price) / price < 0.02) lines.push(`Dəstək: ${DP(s.price)}`)
  }

  // Fibonacci
  if (fib && fib.retracement_levels) {
    const levels = fib.retracement_levels as Record<string, number>
    for (const [k, v] of Object.entries(levels)) {
      if (Math.abs(v - price) / price < 0.02) lines.push(`Fib ${(Number(k) * 100).toFixed(1)}% ${DP(v)}`)
    }
  }

  // Elliott
  if (ew && ew.waves) {
    const waves = ew.waves as { type: string; label?: string }[]
    const lastW = waves[waves.length - 1]
    if (lastW) lines.push(`Elliott: Dalğa ${lastW.label || ""} ${lastW.type === "wave_up" ? "Yuxarı" : "Aşağı"}`)
  }

  // SMC near structures
  for (const ob of norm.smc.near_ob) {
    if (Math.abs(n(ob.price) - price) / price < 0.02) lines.push(`OB ${DP(n(ob.price))}`)
  }
  for (const f of norm.smc.near_fvg) {
    const p = n(f.gap_high) || n(f.price)
    if (p > 0 && Math.abs(p - price) / price < 0.02) lines.push(`FVG ${DP(p)}`)
  }

  return lines.slice(0, 10)
}

// ══════════════════════════════════════════════════
//  Legacy draw functions (kept for compatibility)
// ══════════════════════════════════════════════════


// ══════════════════════════════════════════════════
//  VIEWPORT-AWARE PRIMITIVE DRAW FUNCTIONS (2024)
//  Each returns { dataCount, drawnCount }
//  All use cs.priceToCoordinate directly (no toY wrappers)
// ══════════════════════════════════════════════════

function drawTriggersPrimitive(
  ctx: CanvasRenderingContext2D, w: number, h: number,
  norm: NormalizedAnalysis, cs: ISeriesApi<"Candlestick">,
): { dataCount: number; drawnCount: number } {
  let dc = 0; let vc = 0
  const log: { label: string; price: number; y: unknown; finite: boolean; inCanvas: boolean; stroked: boolean }[] = []

  const drawOne = (label: string, price: number, color: string, badgeColor: string) => {
    if (price <= 0) return
    dc++
    const y = cs.priceToCoordinate(price)
    const finite = y != null && Number.isFinite(y)
    const inCanvas = finite && (y as number) > 0 && (y as number) < h
    let stroked = false
    if (finite && inCanvas) {
      ctx.save()
      ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.setLineDash([8, 5])
      ctx.beginPath(); ctx.moveTo(0, y as number); ctx.lineTo(w, y as number)
      ctx.stroke()
      ctx.setLineDash([])
      // Label at right edge
      ctx.font = "bold 8px monospace"; ctx.fillStyle = badgeColor
      ctx.textAlign = "right"
      ctx.fillText(`${label} $${price.toFixed(2)}`, w - 4, (y as number) - 5)
      ctx.textAlign = "left"
      ctx.restore()
      stroked = true; vc++
    }
    log.push({ label, price, y, finite, inCanvas, stroked })
  }

  drawOne("LONG", norm.longTrigger, "rgba(34,197,94,1)", "rgba(34,197,94,1)")
  drawOne("SHORT", norm.shortTrigger, "rgba(239,68,68,1)", "rgba(239,68,68,1)")
  console.log("[SKHY] TRIGGER_DRAW", log)
  return { dataCount: dc, drawnCount: vc }
}

function drawBreakoutPrimitive(
  ctx: CanvasRenderingContext2D, w: number, h: number,
  norm: NormalizedAnalysis, cs: ISeriesApi<"Candlestick">, confidence: number,
): { dataCount: number; drawnCount: number } {
  const top = norm.breakout.top; const bot = norm.breakout.bottom
  if (top <= 0 || bot <= 0) return { dataCount: 0, drawnCount: 0 }
  const topY = cs.priceToCoordinate(top); const botY = cs.priceToCoordinate(bot)
  const log = { top, bot, topY, botY, topFinite: false, botFinite: false, filled: false, bordersStroked: false }
  if (topY == null || botY == null || !Number.isFinite(topY) || !Number.isFinite(botY)) {
    console.log("[SKHY] BREAKOUT_SKIP", log); return { dataCount: 1, drawnCount: 0 }
  }
  log.topFinite = true; log.botFinite = true
  const yMin = Math.min(topY, botY); const yMax = Math.max(topY, botY)
  const clipTop = Math.max(0, yMin); const clipBot = Math.min(h, yMax)
  if (clipBot <= clipTop) { console.log("[SKHY] BREAKOUT_SKIP_CLIP", log); return { dataCount: 1, drawnCount: 0 } }

  ctx.save()
  // High-alpha diagnostic fill
  ctx.fillStyle = "rgba(168,85,247,0.18)"
  ctx.fillRect(0, clipTop, w, clipBot - clipTop)
  log.filled = true

  // High-visibility borders
  ctx.strokeStyle = "rgba(168,85,247,1)"; ctx.lineWidth = 2
  ctx.beginPath(); ctx.moveTo(0, yMin); ctx.lineTo(w, yMin); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(0, yMax); ctx.lineTo(w, yMax); ctx.stroke()
  log.bordersStroked = true

  // Label
  ctx.font = "bold 8px monospace"; ctx.fillStyle = "rgba(168,85,247,1)"
  ctx.fillText(`BREAKOUT $${bot.toFixed(2)}–$${top.toFixed(2)}`, Math.max(4, w - 180), Math.max(14, clipTop - 6))
  ctx.restore()
  console.log("[SKHY] BREAKOUT_DRAW", log)
  return { dataCount: 1, drawnCount: 1 }
}

function drawSRPrimitive(
  ctx: CanvasRenderingContext2D, w: number, h: number,
  norm: NormalizedAnalysis, cs: ISeriesApi<"Candlestick">, confidence: number,
): { dataCount: number; drawnCount: number } {
  let dc = 0; let vc = 0
  const log: { type: string; price: number; y: unknown; finite: boolean; inCanvas: boolean; stroked: boolean }[] = []
  const items = [
    ...norm.resistances.slice(0, 2).map(r => ({ type: "RES" as const, price: r.price, color: "rgba(239,68,68,0.8)" as const })),
    ...norm.supports.slice(0, 2).map(s => ({ type: "SUP" as const, price: s.price, color: "rgba(34,197,94,0.8)" as const })),
  ]
  for (const item of items) {
    if (item.price <= 0) continue
    dc++
    const y = cs.priceToCoordinate(item.price)
    const finite = y != null && Number.isFinite(y)
    const inCanvas = finite && (y as number) > 0 && (y as number) < h
    let stroked = false
    if (finite && inCanvas) {
      ctx.save()
      ctx.strokeStyle = item.color; ctx.lineWidth = 1.5; ctx.setLineDash([4, 4])
      ctx.beginPath(); ctx.moveTo(0, y as number); ctx.lineTo(w, y as number); ctx.stroke()
      ctx.setLineDash([])
      // Label
      ctx.font = "bold 7px monospace"; ctx.fillStyle = item.color
      ctx.fillText(`${item.type === "RES" ? "MÜQAVİMƏT" : "DƏSTƏK"} $${item.price.toFixed(2)}`, w - 120, (y as number) - 4)
      ctx.restore()
      stroked = true; vc++
    }
    log.push({ type: item.type, price: item.price, y, finite, inCanvas, stroked })
  }
  console.log("[SKHY] SR_DRAW", log)
  return { dataCount: dc, drawnCount: vc }
}

function drawChannelPrimitive(
  ctx: CanvasRenderingContext2D, w: number, h: number,
  toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, confidence: number, data: Candle[], lx: number,
): { dataCount: number; drawnCount: number } {
  const ch = norm.channel
  const lines: { key: string; pts: { time: number; value: number }[] }[] = [
    { key: "upper", pts: ch.upper }, { key: "lower", pts: ch.lower }, { key: "mid", pts: ch.mid },
  ]
  let dc = 0; let vc = 0
  const log: { key: string; pts: { t: number; v: number; x: unknown; y: unknown; finX: boolean; finY: boolean; inCanvas: boolean }[] }[] = []

  for (const line of lines) {
    if (line.pts.length < 2) continue
    dc++
    const ptsLog: { t: number; v: number; x: unknown; y: unknown; finX: boolean; finY: boolean; inCanvas: boolean }[] = []
    ctx.save()
    const isMid = line.key === "mid"
    ctx.strokeStyle = isMid ? "rgba(255,255,255,0.7)" : "rgba(34,211,238,0.8)"
    ctx.lineWidth = isMid ? 2 : 3
    if (isMid) ctx.setLineDash([6, 4])
    ctx.beginPath()
    let started = false; let hasAny = false
    for (const p of line.pts) {
      const x = toX(p.time); const y = toY(p.value)
      const finX = Number.isFinite(x) && x > 0
      const finY = Number.isFinite(y) && y > 0
      const inCanvas = finX && finY && y < h
      ptsLog.push({ t: p.time, v: p.value, x, y, finX, finY, inCanvas })
      if (!inCanvas) continue
      if (!started) { ctx.moveTo(x, y); started = true } else ctx.lineTo(x, y)
      hasAny = true
    }
    // Extend to right edge via last valid point
    if (started && lx > 0) {
      const lastP = line.pts[line.pts.length - 1]; const lastX = toX(lastP.time)
      if (lastX > 0 && lx > lastX) {
        const lastY = toY(lastP.value)
        if (Number.isFinite(lastY) && lastY > 0) {
          ctx.lineTo(lx + 60, lastY)
          hasAny = true
        }
      }
    }
    if (hasAny) { ctx.stroke(); vc++ }
    ctx.setLineDash([]); ctx.restore()
    log.push({ key: line.key, pts: ptsLog })
  }
  console.log("[SKHY] CHANNEL_DRAW", log)
  return { dataCount: dc, drawnCount: vc }
}

function drawFibPrimitive(
  ctx: CanvasRenderingContext2D, w: number, h: number,
  norm: NormalizedAnalysis, cs: ISeriesApi<"Candlestick">, confidence: number,
): { dataCount: number; drawnCount: number } {
  const levels = norm.fibonacci.levels
  const keys = Object.keys(levels).sort((a, b) => Number(a) - Number(b))
  if (keys.length === 0) return { dataCount: 0, drawnCount: 0 }
  let dc = 0; let vc = 0
  const log: { ratio: string; price: number; y: unknown; finite: boolean; inCanvas: boolean; stroked: boolean }[] = []

  // Golden zone
  const g618 = levels["0.618"]; const g786 = levels["0.786"]
  if (g618 > 0 && g786 > 0) {
    const y618 = cs.priceToCoordinate(g618); const y786 = cs.priceToCoordinate(g786)
    if (y618 != null && y786 != null && Number.isFinite(y618) && Number.isFinite(y786)) {
      ctx.save()
      ctx.fillStyle = "rgba(245,158,11,0.08)"
      ctx.fillRect(0, Math.min(y618, y786), w, Math.abs(y618 - y786))
      ctx.font = "6px monospace"; ctx.fillStyle = "rgba(245,158,11,0.5)"
      ctx.fillText("QIZIL ZONA", 4, (y618 + y786) / 2 + 2)
      ctx.restore()
    }
  }

  for (const key of keys) {
    const price = levels[key]; if (price <= 0) continue
    dc++
    const y = cs.priceToCoordinate(price)
    const pct = (Number(key) * 100).toFixed(1)
    const finite = y != null && Number.isFinite(y)
    const inCanvas = finite && (y as number) > 0 && (y as number) < h
    let stroked = false
    if (finite && inCanvas) {
      ctx.save()
      ctx.strokeStyle = "rgba(245,158,11,0.65)"; ctx.lineWidth = 1.5; ctx.setLineDash([3, 4])
      ctx.beginPath(); ctx.moveTo(0, y as number); ctx.lineTo(w, y as number); ctx.stroke()
      ctx.setLineDash([])
      ctx.font = "bold 7px monospace"; ctx.fillStyle = "rgba(245,158,11,0.9)"
      ctx.fillText(`Fib ${pct}% $${price.toFixed(2)}`, w - 120, Math.max(12, (y as number) - 3))
      ctx.restore()
      stroked = true; vc++
    }
    log.push({ ratio: key, price, y, finite, inCanvas, stroked })
  }
  console.log("[SKHY] FIB_DRAW", log)
  return { dataCount: dc, drawnCount: vc }
}

function drawSMCPrimitive(
  ctx: CanvasRenderingContext2D, w: number,
  norm: NormalizedAnalysis, cs: ISeriesApi<"Candlestick">, confidence: number,
): { dataCount: number; drawnCount: number } {
  // Count all available SMC structures regardless of drawing
  const allItems = [
    ...norm.smc.near_ob.map(s2 => ({ cat: "OB", price: n(s2.price) })),
    ...norm.smc.near_fvg.map(s2 => ({ cat: "FVG", price: n(s2.price) || n(s2.gap_high) })),
    ...norm.smc.near_bos.map(s2 => ({ cat: "BOS", price: n(s2.price) })),
    ...norm.smc.near_choch.map(s2 => ({ cat: "CHoCH", price: n(s2.price) })),
    ...norm.smc.near_liq.map(s2 => ({ cat: "LIQ", price: n(s2.price) })),
    ...norm.smc.near_eq.map(s2 => ({ cat: "EQ", price: n(s2.price) })),
  ]
  let dc = allItems.length
  let vc = 0
  for (const item of allItems) {
    if (item.price <= 0) continue
    const y = cs.priceToCoordinate(item.price)
    if (y == null || !Number.isFinite(y) || y <= 0 || y >= 10000) continue
    ctx.save()
    ctx.strokeStyle = "rgba(168,85,247,0.6)"; ctx.lineWidth = 0.8; ctx.setLineDash([3, 3])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = "rgba(168,85,247,0.7)"
    ctx.fillText(item.cat, 4, Math.max(10, y - 2))
    ctx.restore()
    vc++
  }
  return { dataCount: Math.max(dc, 1), drawnCount: vc }
}

function drawPatternPrimitive(
  ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number,
  norm: NormalizedAnalysis, data: Candle[], w: number, confidence: number, lx: number, candleW: number,
): { dataCount: number; drawnCount: number } {
  const pat = norm.strongestPattern
  if (!pat) return { dataCount: 0, drawnCount: 0 }
  const prob = n(pat.probability); if (prob < 50) return { dataCount: 1, drawnCount: 0 }
  const name = s(pat.name); const bLv = n(pat.breakout_level) || n(pat.breakdown_level)
  const mTgt = n(pat.measured_target); const confirmed = s(pat.status) === "CONFIRMED"
  const lclr = confirmed ? "rgba(34,197,94,0.9)" : "rgba(245,158,11,0.8)"
  // Label only — no shape drawing to avoid clutter
  ctx.save(); ctx.font = "bold 7px monospace"; ctx.fillStyle = lclr; ctx.textAlign = "right"
  ctx.fillText(`${confirmed ? "✓" : "?"} ${name} ${prob}%`, w - 4, 12)
  ctx.textAlign = "left"; ctx.restore()
  return { dataCount: 1, drawnCount: 1 }
}

function drawFPPrimitive(
  ctx: CanvasRenderingContext2D, w: number, h: number,
  toX: (t: number) => number, toY: (p: number) => number,
  sp: Record<string, unknown> | undefined, cb: Record<string, unknown> | undefined,
  confidence: number, data: Candle[], lx: number, lp: number, candleW: number,
  fX: (off: number) => number, ov: Record<string, boolean>,
): { dataCount: number; drawnCount: number } {
  if (!sp || data.length === 0) return { dataCount: 0, drawnCount: 0 }
  // Draw a simple arrow if scenario has direction
  const main = (sp.main_scenario || sp.main || {}) as Record<string, unknown>
  const dir = s(main.direction_az || main.direction || "")
  const prob = n(main.probability) || 50
  if (!dir && !sp.path_points) return { dataCount: 1, drawnCount: 0 }
  const isLong = dir.includes("ALIŞ") || dir.includes("LONG") || dir.includes("UP")
  const fAlpha = Math.max(0.35, 0.5 * (confidence / 50))
  ctx.save(); ctx.globalAlpha = fAlpha
  if (lx > 0) {
    const futureX = lx + candleW * 5; const futureY = toY(isLong ? lp * 1.02 : lp * 0.98)
    if (Number.isFinite(futureX) && futureX > 0 && Number.isFinite(futureY) && futureY > 0) {
      ctx.strokeStyle = isLong ? "rgba(34,197,94,0.7)" : "rgba(239,68,68,0.7)"; ctx.lineWidth = 1.5; ctx.setLineDash([4, 4])
      ctx.beginPath(); ctx.moveTo(lx + candleW * 2, toY(lp)); ctx.lineTo(futureX, futureY); ctx.stroke(); ctx.setLineDash([])
      ctx.font = "7px monospace"; ctx.fillStyle = isLong ? "rgba(34,197,94,0.8)" : "rgba(239,68,68,0.8)"
      ctx.fillText(`${dir} ${prob}%`, lx + candleW * 2, Math.min(toY(lp), futureY) - 6)
    }
  }
  ctx.restore()
  return { dataCount: 1, drawnCount: 1 }
}

function drawVolProf(ctx: CanvasRenderingContext2D, _toX: (t: number) => number, toY: (p: number) => number, ohlcv: Candle[], w: number, h: number, ov: Record<string, boolean>) {
  if (ohlcv.length < 50) return
  const mn = Math.min(...ohlcv.map(d => d.low)); const mx = Math.max(...ohlcv.map(d => d.high))
  const rng = mx - mn; if (rng <= 0) return
  const B = 30; const bs = rng / B
  const bins = new Array(B).fill(0)
  for (const d of ohlcv) {
    for (let i = 0; i < B; i++) {
      const bi = mn + bs * i; const bt = mn + bs * (i + 1)
      if (d.close >= bi && d.close < bt) { bins[i] += d.volume; break }
    }
  }
  const maxVol = Math.max(...bins); if (maxVol <= 0) return
  const barW = Math.max(2, w / B * 0.3)
  ctx.save(); ctx.globalAlpha = 0.2
  for (let i = 0; i < B; i++) {
    const barH = (bins[i] / maxVol) * (h * 0.08); const x = (w / B) * i; const y = toY(mn + bs * i + bs / 2)
    if (bins[i] > 0 && y > 0) {
      ctx.fillStyle = bins[i] / maxVol > 0.7 ? TV_GREEN : "rgba(107,114,128,0.3)"
      ctx.fillRect(x, y - barH, barW, barH)
    }
  }
  ctx.restore()
}

function drawFP(
  ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number,
  sp: Record<string, unknown> | undefined, cb: Record<string, unknown> | undefined,
  confidence: number, ohlcv: Candle[], w: number, h: number,
  lx: number, lp: number, cw: number, fX: (off: number) => number,
  ov: Record<string, boolean>,
) {
  if (!sp || ohlcv.length === 0) return
  const avr = ohlcv.length >= 14 ? calcATR(ohlcv, 14) / lp : 0.01

  const getPaths = (key: string): Record<string, unknown> | undefined => {
    const direct = sp[key] as Record<string, unknown> | undefined
    if (direct) return direct
    const main = sp.main as Record<string, unknown> | undefined
    if (main && key === "main_scenario") return main
    if (key === "main_scenario") {
      const pts = sp.path_points as PathPoint[] | undefined
      if (pts) return { path_points: pts, direction: s(sp.direction), probability: n(sp.probability) }
    }
    const alt = sp.alternative as Record<string, unknown> | undefined
    if (alt && key === "alternative_scenario") return alt
    return undefined
  }

  const drawPath = (which: "main" | "alt" | "fakeout") => {
    const keys: Record<string, string> = { main: "main_scenario", alt: "alternative_scenario", fakeout: "fakeout_scenario" }
    const sc = getPaths(keys[which])
    if (!sc) return
    const pts = sc.path_points as PathPoint[] | undefined
    if (!pts || pts.length < 2) return
    const dir = s(sc.direction); const isLong = dir === "LONG" || dir === "BULLISH"
    const sigConf = cb ? n(cb.signal_confidence) : confidence
    const isMain = which === "main"

    let color: string; let lw: number; let dash: number[]; let alpha: number
    if (which === "main") {
      color = isLong ? TV_GREEN : TV_RED; lw = 2; dash = []
      alpha = Math.min(1, 0.3 + sigConf / 200)
      if (confidence < 40) { lw = 0.8; dash = [3, 5] }
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

  if (ov.cone) {
    const mainSc = getPaths("main_scenario")
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
          g.addColorStop(0, "rgba(8,153,129,0.12)"); g.addColorStop(0.5, "rgba(8,153,129,0.06)"); g.addColorStop(1, "rgba(8,153,129,0.12)")
          ctx.fillStyle = g; ctx.fill()
          ctx.strokeStyle = "rgba(8,153,129,0.1)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 6])
          ctx.beginPath(); ctx.moveTo(up[0].x, up[0].y)
          for (let i = 1; i < up.length; i++) ctx.lineTo(up[i].x, up[i].y); ctx.stroke()
          ctx.beginPath(); ctx.moveTo(dn[0].x, dn[0].y)
          for (let i = 1; i < dn.length; i++) ctx.lineTo(dn[i].x, dn[i].y); ctx.stroke()
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

  if (ov.mainScenario) drawPath("main")
  if (ov.altScenario) drawPath("alt")
  if (ov.fakeout) drawPath("fakeout")
}
