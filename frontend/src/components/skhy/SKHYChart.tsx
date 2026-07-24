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
}

interface Candle { time: number; open: number; high: number; low: number; close: number; volume: number }

function num(v: unknown): number { return typeof v === "number" ? v : 0 }
function str(v: unknown): string { return v == null ? "" : String(v) }

export function SKHYChart({ symbol, snapshot, analysis, triggers, sr }: Props) {
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
  const [tf, setTf] = useState("1h")
  const [projection] = useState<Candle[]>([])
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null)
  const timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

  const scores = (analysis?.scores || {}) as Record<string, unknown>
  const scenarios = analysis?.scenarios as Record<string, unknown> | undefined
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

  const confidence = num(scores.signal_confidence)
  const longProb = num(scores.long_probability)
  const shortProb = num(scores.short_probability)
  const status = str(scores.status)
  const ltPrice = num(triggers.long_trigger_price)
  const stPrice = num(triggers.short_trigger_price)
  const inval = num(triggers.bullish_invalidation) || num(triggers.bearish_invalidation)
  const price = num(snapshot?.live_price)

  useEffect(() => {
    api.getSkhyOHLCV(tf, 240).then((res) => { if (res?.data) setOhlcv(res.data) }).catch(() => {})
  }, [tf])

  useEffect(() => {
    if (!containerRef.current) return
    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: "#0d1117" }, textColor: "#6b7280", fontSize: 11 },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#374151", scaleMargins: { top: 0.05, bottom: 0.25 } },
      timeScale: { borderColor: "#374151", timeVisible: true, secondsVisible: false },
      autoSize: true,
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
    const closes = ohlcv.map((d) => d.close)
    const ema20 = calcEMA(closes, 20); const ema50 = calcEMA(closes, 50); const ema100 = calcEMA(closes, 100)
    const atrStop = calcATRStop(ohlcv, 14, 2.5)
    ema20Ref.current?.setData(ema20.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter(d => d.value > 0))
    ema50Ref.current?.setData(ema50.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter(d => d.value > 0))
    ema100Ref.current?.setData(ema100.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter(d => d.value > 0))
    atrStopRef.current?.setData(atrStop.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter(d => d.value > 0))
    chartRef.current?.timeScale().fitContent()
    drawOverlay()
  }, [ohlcv])

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
    drawHeatmap(ctx, toX, toY, w, h, ohlcv)
    drawChannel(ctx, toX, toY, cl, w, ohlcv)
    drawBreakoutZone(ctx, toX, toY, bz, w, h, ohlcv)
    drawFibonacciLevels(ctx, toX, toY, fib, w, ohlcv)
    drawScenarioPath(ctx, toX, toY, sp, w, h, cb, ohlcv)
    drawTargets(ctx, toX, toY, th, w, ohlcv)
    drawSMCStructures(ctx, toX, toY, analysis, ohlcv)
    drawSR(ctx, toX, toY, sr, price, w)
    drawPatterns(ctx, toX, toY, patterns, ohlcv, w)
    drawTradeLevels(ctx, toX, toY, triggers, scores, w)
    drawVolumeProfile(ctx, toX, toY, ohlcv, w, h)
    drawSmartMoney(ctx, toX, toY, analysis, ohlcv)
    drawElliottWave(ctx, toX, toY, ew, w, ohlcv)
    drawCone(ctx, toX, toY, projection, confidence, w, h, ohlcv)
  }, [ohlcv, analysis, triggers, scores, sr, scenarios, patterns, projection, confidence, price, ew, fib, ds, cl, bz, sp, th, cb])

  useEffect(() => { drawOverlay(); const i = setInterval(drawOverlay, 1000); return () => clearInterval(i) }, [drawOverlay])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const canvas = overlayRef.current; const chart = chartRef.current
    if (!canvas || !chart) { setTooltip(null); return }
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left; const y = e.clientY - rect.top
    const t = chart.timeScale().coordinateToTime(x); const pr = candleSeriesRef.current?.coordinateToPrice(y)
    if (t == null || pr == null) { setTooltip(null); return }
    const hovered = findNearestStructure(allStructs, t as number, pr, toCandleTime(ohlcv, x, chart))
    if (hovered) setTooltip({ x: e.clientX - rect.left + 10, y: e.clientY - rect.top - 10, text: hovered })
    else setTooltip(null)
  }, [allStructs, ohlcv])
  const handleMouseLeave = () => setTooltip(null)

  const statusLabel: Record<string, string> = { STRONG_TRADE_READY: "GÜCLÜ HAZIR", TRADE_READY: "HAZIRDIR", WATCHLIST: "İZLƏMƏ", WAIT: "GÖZLƏYİN" }

  return (
    <div className="h-full flex flex-col relative">
      <div className="flex items-center px-2 py-0.5 border-b border-gray-800/40 bg-gray-950/60 z-10 shrink-0">
        {timeframes.map((t) => {
          const sig = ((tfs[t] as Record<string, unknown>)?.signal as string) || ""
          const sigColor = sig.includes("LONG") ? "text-green-400 bg-green-500/10" : sig.includes("SHORT") ? "text-red-400 bg-red-500/10" : "text-gray-500 bg-gray-800/30"
          return (
            <button key={t} onClick={() => setTf(t)}
              className={cn("flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] font-mono rounded transition-colors mr-0.5", tf === t ? "bg-blue-600/20 border border-blue-500/30" : "hover:bg-gray-800/30")}>
              <span className="text-gray-500">{t}</span>
              {sig && <span className={cn("px-0.5 rounded text-[8px] font-bold", sigColor)}>{sig.includes("LONG") ? "↑" : sig.includes("SHORT") ? "↓" : "−"}</span>}
            </button>
          )
        })}
        <div className="flex-1" />
        <div className="flex items-center gap-1.5 px-2">
          <span className="text-[9px] text-gray-500">AI</span>
          <div className="w-16 h-1.5 rounded-full bg-gray-800 overflow-hidden">
            <div className={cn("h-full rounded-full transition-all duration-500", confidence >= 70 ? "bg-green-500" : confidence >= 50 ? "bg-yellow-500" : "bg-red-500")} style={{ width: `${Math.min(confidence, 100)}%` }} />
          </div>
          <span className={cn("text-[10px] font-bold font-mono", confidence >= 70 ? "text-green-400" : confidence >= 50 ? "text-yellow-400" : "text-gray-500")}>{confidence}%</span>
          <span className={cn("text-[8px] px-1 py-0.5 rounded font-semibold",
            status === "STRONG_TRADE_READY" ? "bg-green-500/20 text-green-400" : status === "TRADE_READY" ? "bg-blue-500/20 text-blue-400" : status === "WATCHLIST" ? "bg-yellow-500/20 text-yellow-400" : "bg-gray-500/20 text-gray-400")}>{statusLabel[status] || status}</span>
        </div>
        <span className="text-[9px] text-gray-600 font-mono mr-1">{symbol}</span>
      </div>
      <div className="relative flex-1" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
        <div ref={containerRef} className="absolute inset-0" />
        <canvas ref={overlayRef} className="absolute inset-0 pointer-events-none z-[5]" />
        {tooltip && (
          <div className="absolute z-10 pointer-events-none bg-gray-900/95 border border-gray-700 rounded px-2 py-1 text-[9px] text-gray-200 shadow-xl max-w-[220px] whitespace-pre-line" style={{ left: tooltip.x, top: tooltip.y }}>
            {tooltip.text}
          </div>
        )}
        <div className="absolute top-2 right-2 z-[6] flex flex-col gap-1 text-[9px]">
          <div className={cn("px-2 py-0.5 rounded font-bold font-mono text-right", longProb > shortProb ? "bg-green-500/20 text-green-400" : "bg-gray-800/40 text-gray-600")}>ALIŞ {longProb}%</div>
          <div className={cn("px-2 py-0.5 rounded font-bold font-mono text-right", shortProb > longProb ? "bg-red-500/20 text-red-400" : "bg-gray-800/40 text-gray-600")}>SATIŞ {shortProb}%</div>
        </div>
        {confidence >= 70 && (
          <div className="absolute bottom-2 left-2 z-[6] bg-gray-950/90 border border-gray-700/60 rounded px-2 py-1 text-[9px] font-mono space-y-0.5 max-w-[200px]">
            {longProb > shortProb ? (
              <><div className="text-green-400 font-bold text-[10px]">ALIŞ PLANI</div><div className="text-gray-400">Giriş: <span className="text-white">${ltPrice.toFixed(2)}</span></div><div className="text-gray-400">Zərər kəsmə: <span className="text-red-400">${inval.toFixed(2)}</span></div></>
            ) : (
              <><div className="text-red-400 font-bold text-[10px]">SATIŞ PLANI</div><div className="text-gray-400">Giriş: <span className="text-white">${stPrice.toFixed(2)}</span></div><div className="text-gray-400">Zərər kəsmə: <span className="text-red-400">${inval.toFixed(2)}</span></div></>
            )}
          </div>
        )}
        {confidence < 70 && confidence > 0 && (
          <div className={cn("absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[6] text-center pointer-events-none", status === "WAIT" ? "opacity-100" : "opacity-60")}>
            <div className="text-[11px] font-bold text-yellow-500 mb-1">⏳ GÖZLƏYİN</div>
            <div className="text-[9px] text-gray-500">{longProb > shortProb ? `ALIŞ triggeri: $${ltPrice.toFixed(2)} üzərində təsdiq` : `SATIŞ triggeri: $${stPrice.toFixed(2)} altında təsdiq`}</div>
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
function calcATRStop(data: Candle[], period: number, mult: number): number[] {
  if (data.length < period + 1) return data.map(() => 0)
  const tr: number[] = []
  for (let i = 1; i < data.length; i++) tr.push(Math.max(data[i].high - data[i].low, Math.abs(data[i].high - data[i - 1].close), Math.abs(data[i].low - data[i - 1].close)))
  let atr = tr.slice(0, period).reduce((a, b) => a + b, 0) / period; const atrs: number[] = [atr]
  for (let i = period; i < tr.length; i++) { atr = (atr * (period - 1) + tr[i]) / period; atrs.push(atr) }
  const pad = new Array(period).fill(0); return [...pad, ...atrs.map((a, i) => Math.round((data[i + period].close - a * mult) * 100) / 100)]
}
function toCandleTime(ohlcv: Candle[], x: number, chart: IChartApi): number { const t = chart.timeScale().coordinateToTime(x); return t == null ? 0 : t as number }

function findNearestStructure(structs: Record<string, unknown>[] | undefined, time: number, price: number, candleTime: number): string | null {
  if (!structs) return null
  for (const s of structs) {
    const sIdx = num(s.index)
    if (Math.abs(sIdx - candleTime) < 5) {
      const sp = num(s.price) || num(s.gap_high) || 0
      if (Math.abs(sp - price) / price < 0.05) {
        const type = str(s.type); const cat = str(s.category)
        if (cat === "bos") return `BOS (Struktur dəyişikliyi)\nBazar ${type.includes("bullish") ? "yuxarı" : "aşağı"} istiqamətə keçir. Trend dəyişir.`
        if (cat === "choch") return `CHoCH (Xarakter dəyişikliyi)\nTrend ${type.includes("bullish") ? "yüksələn" : "enən"} ola bilər. Smart money yeni istiqamət hazırlayır.`
        if (cat === "fvg") return `FVG (Qiymət boşluğu)\n${type.includes("bullish") ? "Yuxarı" : "Aşağı"} likvidite çəkə bilər. Boşluq doldurulmağa meyllidir.`
        if (cat === "order_block") return `OB (Order Block)\nSmart money ${type.includes("bullish") ? "alış" : "satış"} əmri buraxıb. Böyük oyunçu zonası.`
        if (cat === "liquidity") return `Likvidite zonası\n${type.includes("above") ? "Yuxarıda" : "Aşağıda"} stop-loss toplanıb. Hədəf zona.`
        if (cat === "swing") return `Swing ${type === "high" ? "Zirvə" : "Dip"}\nÖnəmli dönüş nöqtəsi.`
        return `${type}\nStruktur elementi.`
      }
    }
  }
  return null
}
function num(v: unknown): number { return typeof v === "number" ? v : 0 }
function str(v: unknown): string { return v == null ? "" : String(v) }

// ─── DRAWING FUNCTIONS ───

function drawHeatmap(ctx: CanvasRenderingContext2D, toX: (t: number) => number, _toY: (p: number) => number, w: number, h: number, ohlcv: Candle[]) {
  if (ohlcv.length < 20) return
  for (let i = 1; i < ohlcv.length; i++) {
    const x = toX(ohlcv[i].time); if (x < 0 || x > w) continue
    const body = Math.abs(ohlcv[i].close - ohlcv[i].open); const range = ohlcv[i].high - ohlcv[i].low
    if (range === 0) continue
    const intensity = Math.min(body / range * 0.3, 0.3)
    ctx.fillStyle = ohlcv[i].close >= ohlcv[i].open ? `rgba(34,197,94,${intensity})` : `rgba(239,68,68,${intensity})`
    ctx.fillRect(x - 2, 0, 4, h)
  }
}

function drawChannel(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, cl: Record<string, unknown> | undefined, w: number, ohlcv: Candle[]) {
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
    for (const p of pts) {
      const x = toX(p.time); const y = toY(p.value)
      if (x <= 0 || y <= 0) continue
      if (!started) { ctx.moveTo(x, y); started = true } else ctx.lineTo(x, y)
    }
    ctx.stroke(); ctx.setLineDash([])
  }

  drawLine(upper, "rgba(168,85,247,0.5)", [4, 4])
  drawLine(lower, "rgba(168,85,247,0.5)", [4, 4])
  if (mid) drawLine(mid, "rgba(168,85,247,0.2)", [2, 6])

  if (upper.length > 0) {
    const last = upper[upper.length - 1]; const x = toX(last.time); const y = toY(last.value)
    if (x > 0 && y > 0) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.6)"; ctx.fillText("Üst kanal", x + 3, y - 2) }
  }
  if (lower.length > 0) {
    const last = lower[lower.length - 1]; const x = toX(last.time); const y = toY(last.value)
    if (x > 0 && y > 0) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(168,85,247,0.6)"; ctx.fillText("Alt kanal", x + 3, y + 10) }
  }
}

function drawBreakoutZone(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, bz: Record<string, unknown> | undefined, w: number, h: number, ohlcv: Candle[]) {
  if (!bz || bz.status !== "calculated" || !ohlcv.length) return
  const zoneTop = num(bz.zone_top); const zoneBottom = num(bz.zone_bottom)
  if (zoneTop <= 0 || zoneBottom <= 0) return
  const yTop = toY(zoneTop); const yBottom = toY(zoneBottom)
  if (yTop <= 0 || yBottom <= 0) return
  const firstX = toX(ohlcv[0].time); const lastX = toX(ohlcv[ohlcv.length - 1].time)
  if (firstX <= 0 || lastX <= 0) return

  ctx.fillStyle = "rgba(168,85,247,0.08)"
  ctx.fillRect(firstX, Math.min(yTop, yBottom), lastX - firstX, Math.abs(yTop - yBottom))
  ctx.strokeStyle = "rgba(168,85,247,0.3)"; ctx.lineWidth = 0.5; ctx.setLineDash([3, 3])
  ctx.strokeRect(firstX, Math.min(yTop, yBottom), lastX - firstX, Math.abs(yTop - yBottom))
  ctx.setLineDash([])

  ctx.font = "7px monospace"
  ctx.fillStyle = "rgba(168,85,247,0.7)"
  ctx.fillText(`BO ${zoneTop.toFixed(2)}`, lastX + 3, yTop - 2)
  ctx.fillText(`BO ${zoneBottom.toFixed(2)}`, lastX + 3, yBottom + 10)

  const testCount = num(bz.test_count)
  if (testCount > 0) {
    ctx.font = "6px monospace"
    ctx.fillStyle = "rgba(168,85,247,0.4)"
    ctx.fillText(`${testCount}x test`, lastX + 3, (yTop + yBottom) / 2)
  }
}

function drawFibonacciLevels(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, fib: Record<string, unknown> | undefined, w: number, ohlcv: Candle[]) {
  if (!fib || fib.status !== "calculated" || !ohlcv.length) return
  const levels = fib.retracement_levels as Record<string, number> | undefined
  if (!levels) return
  const keyLevels = ["0", "0.236", "0.382", "0.5", "0.618", "0.786", "1"]
  const colors: Record<string, string> = {
    "0": "rgba(255,255,255,0.1)", "0.236": "rgba(34,197,94,0.2)", "0.382": "rgba(34,197,94,0.25)",
    "0.5": "rgba(245,158,11,0.25)", "0.618": "rgba(239,68,68,0.25)", "0.786": "rgba(239,68,68,0.2)", "1": "rgba(255,255,255,0.1)"
  }
  const labels: Record<string, string> = {
    "0": "0%", "0.236": "23.6%", "0.382": "38.2%", "0.5": "50%", "0.618": "61.8%", "0.786": "78.6%", "1": "100%"
  }

  for (const k of keyLevels) {
    const p = levels[k]; if (!p) continue
    const y = toY(p); if (y <= 0) continue
    ctx.strokeStyle = colors[k] || "rgba(255,255,255,0.1)"; ctx.lineWidth = 0.5
    ctx.setLineDash(k === "0.5" ? [4, 4] : [2, 4])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = colors[k] || "rgba(255,255,255,0.2)"
    ctx.fillText(`Fib ${labels[k]} $${p.toFixed(2)}`, w - 95, y - 2)
  }

  const extUp = fib.extension_up as Record<string, number> | undefined
  if (extUp) {
    for (const [k, v] of Object.entries(extUp)) {
      const y = toY(v); if (y <= 0) continue
      ctx.strokeStyle = "rgba(34,197,94,0.15)"; ctx.lineWidth = 0.5; ctx.setLineDash([1, 6])
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
      ctx.font = "6px monospace"; ctx.fillStyle = "rgba(34,197,94,0.35)"
      ctx.fillText(`Ext ${k} $${v.toFixed(2)}`, w - 95, y - 2)
    }
  }
  const extDn = fib.extension_down as Record<string, number> | undefined
  if (extDn) {
    for (const [k, v] of Object.entries(extDn)) {
      const y = toY(v); if (y <= 0) continue
      ctx.strokeStyle = "rgba(239,68,68,0.15)"; ctx.lineWidth = 0.5; ctx.setLineDash([1, 6])
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
      ctx.font = "6px monospace"; ctx.fillStyle = "rgba(239,68,68,0.35)"
      ctx.fillText(`Ext ${k} $${v.toFixed(2)}`, w - 95, y - 2)
    }
  }
}

function drawScenarioPath(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, sp: Record<string, unknown> | undefined, w: number, h: number, cb: Record<string, unknown> | undefined, ohlcv: Candle[]) {
  if (!sp || !ohlcv.length) return
  const main = sp.main_scenario as Record<string, unknown> | undefined
  const alt = sp.alternative_scenario as Record<string, unknown> | undefined
  const fake = sp.fakeout_scenario as Record<string, unknown> | undefined
  const lastCandle = ohlcv[ohlcv.length - 1]; const startX = toX(lastCandle.time)
  const startY = toY(lastCandle.close)
  if (startX <= 0 || startY <= 0) return

  const drawPath = (pts: { time_offset: number; price: number; label: string; phase: string }[] | undefined, color: string, lineWidth: number, dash: number[], alpha: number) => {
    if (!pts || pts.length < 2) return
    const lastTime = lastCandle.time
    ctx.strokeStyle = color; ctx.lineWidth = lineWidth; ctx.setLineDash(dash)
    ctx.globalAlpha = alpha; ctx.beginPath()
    let started = false; let prevX = startX; let prevY = startY
    for (const p of pts) {
      if (p.time_offset === 0) continue
      const x = startX + p.time_offset * 8
      const y = toY(p.price)
      if (y <= 0) continue
      if (!started) { ctx.moveTo(startX, startY); x > 0 && ctx.lineTo(x, y); started = true }
      else { ctx.lineTo(x, y) }
      prevX = x; prevY = y
    }
    ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1
  }

  const drawPathLabels = (pts: { time_offset: number; price: number; label: string; phase: string }[] | undefined, color: string, alpha: number) => {
    if (!pts) return
    ctx.globalAlpha = alpha
    for (const p of pts) {
      if (p.time_offset === 0) continue
      const x = startX + p.time_offset * 8; const y = toY(p.price)
      if (y <= 0) continue
      ctx.font = "6px monospace"; ctx.fillStyle = color
      ctx.fillText(p.label, x + 2, y - 2)
      ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill()
    }
    ctx.globalAlpha = 1
  }

  const signalConf = cb ? num(cb.signal_confidence) : 50
  const baseAlpha = Math.max(0.2, Math.min(1, signalConf / 70))
  const mainAlpha = Math.max(0.3, baseAlpha)
  const altAlpha = Math.max(0.15, baseAlpha * 0.5)
  const fakeAlpha = Math.max(0.15, baseAlpha * 0.4)

  const mainPts = main?.path_points as { time_offset: number; price: number; label: string; phase: string }[] | undefined
  const altPts = alt?.path_points as { time_offset: number; price: number; label: string; phase: string }[] | undefined
  const fakePts = fake?.path_points as { time_offset: number; price: number; label: string; phase: string }[] | undefined

  if (signalConf >= 50) {
    drawPath(mainPts, "#22c55e", 2, [], mainAlpha)
    drawPathLabels(mainPts, "rgba(34,197,94,0.8)", mainAlpha)
    if (mainPts && mainPts.length > 2) {
      const last = mainPts[mainPts.length - 1]; const lx = startX + last.time_offset * 8; const ly = toY(last.price)
      if (ly > 0) {
        ctx.font = "bold 8px monospace"; ctx.fillStyle = `rgba(34,197,94,${mainAlpha})`
        ctx.fillText("ƏSAS SSENARİ", lx - 30, ly - 12)
      }
    }
  }

  drawPath(altPts, "#ef4444", 1, [4, 4], altAlpha)
  drawPathLabels(altPts, "rgba(239,68,68,0.5)", altAlpha)

  drawPath(fakePts, "#f97316", 1, [2, 4], fakeAlpha)
  drawPathLabels(fakePts, "rgba(249,115,22,0.5)", fakeAlpha)
  if (fakePts && fakePts.length > 2) {
    const last = fakePts[fakePts.length - 1]; const lx = startX + last.time_offset * 8; const ly = toY(last.price)
    if (ly > 0) { ctx.font = "6px monospace"; ctx.fillStyle = `rgba(249,115,22,${fakeAlpha})`; ctx.fillText("FAKEOUT", lx - 20, ly + 10) }
  }
}

function drawTargets(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, th: Record<string, unknown> | undefined, w: number, ohlcv: Candle[]) {
  if (!th || !ohlcv.length) return
  const targets = th.targets as { level: string; price: number; type: string; probability: number; time_estimate: string }[] | undefined
  if (!targets) return
  const lastCandle = ohlcv[ohlcv.length - 1]
  for (const tgt of targets) {
    const y = toY(tgt.price); if (y <= 0) continue
    ctx.strokeStyle = "rgba(245,158,11,0.2)"; ctx.lineWidth = 0.5; ctx.setLineDash([3, 6])
    ctx.beginPath(); ctx.moveTo(toX(lastCandle.time), y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = "rgba(245,158,11,0.5)";
    ctx.fillText(`${tgt.level} ${tgt.type} $${tgt.price.toFixed(2)} ${tgt.probability}% ${tgt.time_estimate}`, w - 150, y - 2)
  }
}

function drawSMCStructures(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, analysis: Record<string, unknown> | null, ohlcv: Candle[]) {
  if (!analysis || !ohlcv.length) return
  const w = ctx.canvas.width / window.devicePixelRatio
  const chart = analysis as Record<string, unknown>
  const allStructs = chart.all_structures as Record<string, unknown>[] | undefined
  if (!allStructs) return

  const fvgs = allStructs.filter((s) => str(s.category) === "fvg")
  for (const fvg of fvgs.slice(-10)) {
    const idx = num(fvg.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const top = toY(num(fvg.gap_high)); const bot = toY(num(fvg.gap_low))
    if (x <= 0 || top <= 0 || bot <= 0) continue
    const isBullish = str(fvg.type).includes("bullish")
    ctx.fillStyle = isBullish ? "rgba(34,197,94,0.12)" : "rgba(239,68,68,0.12)"
    ctx.fillRect(x - 4, Math.min(top, bot), 8, Math.abs(top - bot))
    ctx.strokeStyle = isBullish ? "rgba(34,197,94,0.4)" : "rgba(239,68,68,0.4)"; ctx.lineWidth = 0.5; ctx.setLineDash([2, 2])
    ctx.strokeRect(x - 4, Math.min(top, bot), 8, Math.abs(top - bot)); ctx.setLineDash([])
    ctx.font = "6px monospace"; ctx.fillStyle = isBullish ? "rgba(34,197,94,0.6)" : "rgba(239,68,68,0.6)"; ctx.fillText("FVG", x - 4, Math.max(top, bot) + 10)
  }

  const obs = allStructs.filter((s) => str(s.category) === "order_block")
  for (const ob of obs.slice(-8)) {
    const idx = num(ob.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const top = toY(num(ob.high)); const bot = toY(num(ob.low))
    if (x <= 0 || top <= 0 || bot <= 0) continue
    const isBullish = str(ob.type).includes("bullish")
    ctx.fillStyle = isBullish ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)"
    ctx.fillRect(x - 6, Math.min(top, bot), 12, Math.abs(top - bot))
    ctx.strokeStyle = isBullish ? "#22c55e" : "#ef4444"; ctx.lineWidth = 1
    ctx.strokeRect(x - 6, Math.min(top, bot), 12, Math.abs(top - bot))
    ctx.font = "7px monospace"; ctx.fillStyle = isBullish ? "#22c55e" : "#ef4444"; ctx.fillText("OB", x - 6, Math.min(top, bot) - 3)
  }

  const bosList = allStructs.filter((s) => str(s.category) === "bos")
  for (const bos of bosList.slice(-6)) {
    const idx = num(bos.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const y = toY(num(bos.price))
    if (x <= 0 || y <= 0) continue
    const isBullish = str(bos.type).includes("bullish"); const sz = 5
    ctx.strokeStyle = isBullish ? "#22c55e" : "#ef4444"; ctx.lineWidth = 1.5; ctx.beginPath()
    if (isBullish) { ctx.moveTo(x - sz, y + sz); ctx.lineTo(x, y); ctx.lineTo(x + sz, y + sz) }
    else { ctx.moveTo(x - sz, y - sz); ctx.lineTo(x, y); ctx.lineTo(x + sz, y - sz) }
    ctx.stroke(); ctx.font = "6px monospace"; ctx.fillStyle = isBullish ? "#22c55e" : "#ef4444"
    ctx.fillText("BOS", x + sz + 1, y + (isBullish ? sz : -sz) + 2)
  }

  const chochList = allStructs.filter((s) => str(s.category) === "choch")
  for (const choch of chochList.slice(-4)) {
    const idx = num(choch.index); if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); const y = toY(ohlcv[idx].high); if (x <= 0 || y <= 0) continue
    ctx.font = "6px monospace"; ctx.fillStyle = "#a855f7"; ctx.fillText("CHoCH", x + 2, y - 3)
  }
}

function drawSR(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, sr: Record<string, unknown>, price: number, w: number) {
  const levels = [
    { key: "nearest_support", label: "D", color: "rgba(34,197,94,0.6)" },
    { key: "nearest_resistance", label: "Q", color: "rgba(239,68,68,0.6)" },
    { key: "strongest_support", label: "GD", color: "rgba(34,197,94,0.3)" },
    { key: "strongest_resistance", label: "GQ", color: "rgba(239,68,68,0.3)" },
  ]
  for (const l of levels) {
    const p = num(sr[l.key]); if (p <= 0) continue
    const y = toY(p); if (y <= 0) continue
    ctx.strokeStyle = l.color; ctx.lineWidth = 0.5
    ctx.setLineDash(l.key.startsWith("strongest") ? [4, 4] : [2, 2])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "7px monospace"; ctx.fillStyle = l.color
    ctx.fillText(`${l.label} $${p.toFixed(2)}`, w - 80, y - 2)
  }
}

function drawPatterns(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, patterns: Record<string, unknown>[] | undefined, ohlcv: Candle[], w: number) {
  if (!patterns || !ohlcv.length) return
  let yOff = 20; const st: Record<string,string> = { CONFIRMED:"TƏSDİQLƏNDİ", DETECTED:"AŞKAR EDİLDİ", FORMING:"FORMALAŞIR" }
  for (const pat of patterns.slice(0, 3)) {
    const name = str(pat.name); const prob = num(pat.probability)
    const bLevel = num(pat.breakout_level) || num(pat.breakdown_level); const mTarget = num(pat.measured_target)
    ctx.font = "7px monospace"; ctx.fillStyle = str(pat.status) === "CONFIRMED" ? "#22c55e" : str(pat.status) === "DETECTED" ? "#f59e0b" : "#6b7280"
    ctx.fillText(`${name} ${st[str(pat.status)]||str(pat.status)} ${prob}%`, 10, yOff + 10)
    if (bLevel > 0 && mTarget > 0) {
      const y1 = toY(bLevel); const y2 = toY(mTarget)
      if (y1 > 0 && y2 > 0) {
        ctx.strokeStyle = str(pat.status) === "CONFIRMED" ? "rgba(34,197,94,0.3)" : "rgba(245,158,11,0.3)"; ctx.lineWidth = 0.5; ctx.setLineDash([3, 3])
        ctx.beginPath(); ctx.moveTo(w - 40, y1); ctx.lineTo(w - 40, y2); ctx.stroke(); ctx.setLineDash([])
        ctx.font = "6px monospace"; ctx.fillStyle = str(pat.status) === "CONFIRMED" ? "rgba(34,197,94,0.5)" : "rgba(245,158,11,0.5)"
        ctx.fillText(`→$${mTarget.toFixed(1)}`, w - 38, (y1 + y2) / 2)
      }
    }
    yOff += 14
  }
}

function drawTradeLevels(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, triggers: Record<string, unknown>, scores: Record<string, unknown>, w: number) {
  const conf = num(scores.signal_confidence); const ltP = num(triggers.long_trigger_price); const stP = num(triggers.short_trigger_price)
  const inv = num(triggers.bullish_invalidation) || num(triggers.bearish_invalidation)
  const drawLine = (price: number, color: string, label: string, dash: number[], width: number) => {
    const y = toY(price); if (y <= 0) return
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash)
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.setLineDash([])
    ctx.font = "7px monospace"; ctx.fillStyle = color; ctx.fillText(label, 2, y - 2)
  }
  if (ltP > 0) drawLine(ltP, conf >= 70 ? "rgba(34,197,94,0.6)" : "rgba(34,197,94,0.2)", `ALIŞ $${ltP.toFixed(2)}`, conf >= 70 ? [] : [4, 4], conf >= 70 ? 1.5 : 0.5)
  if (stP > 0) drawLine(stP, conf >= 70 ? "rgba(239,68,68,0.6)" : "rgba(239,68,68,0.2)", `SATIŞ $${stP.toFixed(2)}`, conf >= 70 ? [] : [4, 4], conf >= 70 ? 1.5 : 0.5)
  if (inv > 0) drawLine(inv, "rgba(168,85,247,0.4)", `Ləğv $${inv.toFixed(2)}`, [3, 3], 0.5)
}

function drawVolumeProfile(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, ohlcv: Candle[], w: number, h: number) {
  if (ohlcv.length < 50) return
  const priceRange = Math.max(...ohlcv.map(d => d.high)) - Math.min(...ohlcv.map(d => d.low)); if (priceRange <= 0) return
  const buckets = 30; const bs = priceRange / buckets; const minP = Math.min(...ohlcv.map(d => d.low))
  const volB = new Array(buckets).fill(0)
  for (const d of ohlcv) volB[Math.min(buckets-1, Math.max(0, Math.floor((d.close - minP) / bs)))] += d.volume
  const maxV = Math.max(...volB); if (maxV <= 0) return
  for (let i = 0; i < buckets; i++) {
    const y = toY(minP + bs * (i + 0.5)); if (y <= 0) continue
    const bw = (volB[i] / maxV) * 40
    ctx.fillStyle = volB[i] >= maxV * 0.7 ? "rgba(245,158,11,0.2)" : volB[i] >= maxV * 0.3 ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.03)"
    ctx.fillRect(w - bw, y - bs * 100 / 2, bw, Math.max(1, 2))
  }
  const pocIdx = volB.indexOf(maxV); const pocP = minP + bs * (pocIdx + 0.5); const pocY = toY(pocP)
  if (pocY > 0) { ctx.font = "6px monospace"; ctx.fillStyle = "rgba(245,158,11,0.5)"; ctx.textAlign = "right"; ctx.fillText(`POC $${pocP.toFixed(2)}`, w, pocY - 2); ctx.textAlign = "left" }
}

function drawSmartMoney(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, analysis: Record<string, unknown> | null, ohlcv: Candle[]) {
  if (!analysis || ohlcv.length < 30) return
  const allStructs = (analysis as Record<string, unknown>).all_structures as Record<string, unknown>[] | undefined
  if (!allStructs) return
  let bc = 0, sc = 0
  for (const s of allStructs) {
    if (str(s.category) === "order_block" && str(s.type).includes("bullish")) bc++
    if (str(s.category) === "order_block" && str(s.type).includes("bearish")) sc++
  }
  if (bc > sc * 1.5) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(34,197,94,0.3)"; ctx.fillText("Yığım Zonası", 10, 50) }
  else if (sc > bc * 1.5) { ctx.font = "7px monospace"; ctx.fillStyle = "rgba(239,68,68,0.3)"; ctx.fillText("Paylanma Zonası", 10, 50) }
}

function drawElliottWave(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, ew: Record<string, unknown> | undefined, w: number, ohlcv: Candle[]) {
  if (!ew || ew.status === "insufficient_data" || !ohlcv.length) return
  const waves = ew.waves as { type: string; start: number; end: number; index: number }[] | undefined
  if (!waves || waves.length < 3) return
  const numLabels = ["1", "2", "3", "4", "5", "A", "B", "C"]
  for (let i = 0; i < Math.min(waves.length, 8); i++) {
    const wave = waves[i]; const idx = wave.index; if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time); if (x <= 0) continue
    const isUp = wave.type === "wave_up"; const y = toY(isUp ? wave.end : wave.start); if (y <= 0) continue
    ctx.fillStyle = isUp ? "#22c55e" : "#ef4444"; const sz = 4; ctx.beginPath()
    if (isUp) { ctx.moveTo(x, y - sz); ctx.lineTo(x - sz, y); ctx.lineTo(x + sz, y) }
    else { ctx.moveTo(x, y + sz); ctx.lineTo(x - sz, y); ctx.lineTo(x + sz, y) }
    ctx.fill(); ctx.fillStyle = isUp ? "rgba(34,197,94,0.8)" : "rgba(239,68,68,0.8)"
    ctx.fillText(numLabels[i] || String(i+1), x + sz + 2, y + 3)
  }
}

function drawCone(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, projection: Candle[], confidence: number, w: number, h: number, ohlcv: Candle[]) {
  if (confidence < 30 || !ohlcv.length) return
  const lastPrice = ohlcv[ohlcv.length - 1].close; const spread = (1 - confidence / 100) * 0.15 * lastPrice
  const steps = 20; const startX = toX(ohlcv[ohlcv.length - 1].time); if (startX <= 0) return
  const sliceW = (w - startX) / steps
  ctx.beginPath(); ctx.moveTo(startX, toY(lastPrice + spread))
  for (let i = 1; i <= steps; i++) { const r = i / steps; const cs = spread * (0.5 + r * 2); ctx.lineTo(startX + sliceW * i, toY(lastPrice + cs)) }
  for (let i = steps; i >= 0; i--) { const r = i / steps; const cs = spread * (0.5 + r * 2); ctx.lineTo(startX + sliceW * i, toY(lastPrice - cs)) }
  ctx.closePath(); ctx.fillStyle = `rgba(168,85,247,${Math.max(0.03, (confidence / 100) * 0.08)})`; ctx.fill()
  ctx.strokeStyle = "rgba(168,85,247,0.1)"; ctx.lineWidth = 0.5; ctx.stroke()
}
