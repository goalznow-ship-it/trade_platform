"use client"

import { useEffect, useRef, useState, useCallback, useMemo } from "react"
import { api } from "@/lib/api"
import { useMarketStore } from "@/store/market"
import { cn } from "@/lib/utils"
import {
  createChart, ColorType, CrosshairMode, LineStyle,
  CandlestickSeries, LineSeries, createSeriesMarkers,
  type IChartApi, type ISeriesApi, type Time, type SeriesMarker,
} from "lightweight-charts"

// ─── Types ──────────────────────────────────────────────────────────
interface RawOHLCVItem { time: number; open: number; high: number; low: number; close: number; volume: number }
interface OHLCVItem { time: Time; open: number; high: number; low: number; close: number; volume: number }

interface EWPoint { index: number; price: number; type: string }
interface WaveSegment { wave: string; type: string; price: number; index: number; start_index?: number }

const OVERLAY_KEYS = [
  "elliot", "fibonacci", "pattern", "projection", "trade",
  "sr", "liquidity", "ob", "fvg", "breaker", "bos", "smc",
] as const
type OverlayKey = typeof OVERLAY_KEYS[number]

function toUTCTime(ts: number): Time { return ts as Time }

// ─── Zone canvas overlay helper ─────────────────────────────────────
function drawZoneCanvas(
  canvas: HTMLCanvasElement,
  series: ISeriesApi<"Candlestick">,
  zones: Array<{ top: number; bottom: number; color: string; label?: string }>,
) {
  const ctx = canvas.getContext("2d")
  if (!ctx) return
  const rect = canvas.getBoundingClientRect()
  canvas.width = rect.width * window.devicePixelRatio
  canvas.height = rect.height * window.devicePixelRatio
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
  ctx.clearRect(0, 0, rect.width, rect.height)

  for (const z of zones) {
    const yTop = series.priceToCoordinate(z.top)
    const yBottom = series.priceToCoordinate(z.bottom)
    if (yTop == null || yBottom == null) continue
    const y1 = Math.min(yTop, yBottom)
    const h = Math.abs(yTop - yBottom)
    ctx.fillStyle = z.color
    ctx.fillRect(0, y1, rect.width, h)
    if (z.label) {
      ctx.fillStyle = "#ffffffcc"
      ctx.font = "9px JetBrains Mono, monospace"
      ctx.fillText(z.label, 4, y1 + 10)
    }
  }
}

// ─── Hover Tooltip ──────────────────────────────────────────────────
function HoverTooltip({
  data,
  candle,
  indicators,
}: {
  data: { x: number; y: number } | null
  candle?: Record<string, unknown>
  indicators?: Record<string, unknown>
}) {
  if (!data || !candle) return null
  const lines: string[] = []
  const o = candle.open as number
  const h = candle.high as number
  const l = candle.low as number
  const c = candle.close as number
  const v = candle.volume as number
  lines.push(`A ${o.toFixed(2)}  Y ${h.toFixed(2)}`)
  lines.push(`D ${l.toFixed(2)}  B ${c.toFixed(2)}`)
  lines.push(`Fərq ${(((c - o) / o) * 100).toFixed(2)}%  Həcm ${(v / 1000).toFixed(0)}K`)
  if (indicators) {
    const rsi = indicators.rsi
    const macd = indicators.macd_histogram
    const atr = indicators.atr
    const adx = indicators.adx
    const mom = indicators.momentum
    const trend = indicators.supertrend
    const conf = indicators.confidence
    const pat = indicators.pattern
    if (rsi != null) lines.push(`RSI ${typeof rsi === "number" ? rsi.toFixed(1) : rsi}`)
    if (macd != null) lines.push(`MACD ${typeof macd === "number" ? macd.toFixed(2) : macd}`)
    if (atr != null) lines.push(`ATR ${typeof atr === "number" ? atr.toFixed(2) : atr}`)
    if (adx != null) lines.push(`ADX ${typeof adx === "number" ? adx.toFixed(1) : adx}`)
    if (mom != null) lines.push(`Mom ${typeof mom === "number" ? mom.toFixed(2) : mom}`)
    if (trend) lines.push(`Trend ${trend}`)
    if (conf != null) lines.push(`Güvən ${conf}%`)
    if (pat) lines.push(`Pattern ${pat}`)
  }
  return (
    <div
      className="absolute z-50 pointer-events-none bg-gray-900/95 border border-gray-700 rounded-lg px-2.5 py-1.5 text-[9px] text-gray-200 shadow-xl font-mono leading-relaxed min-w-[140px]"
      style={{ left: Math.min(data.x + 14, window.innerWidth - 180), top: Math.max(data.y - 10, 4) }}
    >
      {lines.map((ln, i) => (
        <div key={i} className={i === 0 ? "text-gray-400" : ""}>{ln}</div>
      ))}
    </div>
  )
}

// ─── Overlay Toggle Bar ─────────────────────────────────────────────
const OVERLAY_BUTTONS: Array<{ key: OverlayKey; label: string; color: string }> = [
  { key: "elliot", label: "Elliott", color: "#8b5cf6" },
  { key: "fibonacci", label: "Fib", color: "#a855f7" },
  { key: "pattern", label: "Pattern", color: "#f59e0b" },
  { key: "projection", label: "Proyeksiya", color: "#3b82f6" },
  { key: "trade", label: "Entry/SL/TP", color: "#22c55e" },
  { key: "sr", label: "S/R", color: "#f97316" },
  { key: "liquidity", label: "Likvidlik", color: "#14b8a6" },
  { key: "ob", label: "OB", color: "#06b6d4" },
  { key: "fvg", label: "FVG", color: "#d946ef" },
  { key: "breaker", label: "Breaker", color: "#ec4899" },
  { key: "bos", label: "BOS", color: "#f43f5e" },
  { key: "smc", label: "SMC", color: "#6366f1" },
]

function OverlayToggles({ active, onChange }: { active: Record<string, boolean>; onChange: (k: OverlayKey) => void }) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto px-3 py-0.5 bg-gray-900/50 border-b border-gray-800">
      {OVERLAY_BUTTONS.map((ob) => {
        const isOn = active[ob.key]
        return (
          <button key={ob.key} onClick={() => onChange(ob.key)}
            className={cn("text-[8px] px-1.5 py-0.5 rounded font-medium border shrink-0 transition-all",
              isOn ? "border-current" : "border-transparent text-gray-600 hover:text-gray-400")}
            style={isOn ? { color: ob.color, borderColor: ob.color + "60", backgroundColor: ob.color + "15" } : undefined}
          >
            {ob.label}
          </button>
        )
      })}
    </div>
  )
}

// ─── Scenario Labels ────────────────────────────────────────────────
function ScenarioLabels({ projection, lastCandle, overlays }: {
  projection?: Record<string, unknown>
  lastCandle?: OHLCVItem
  overlays: Record<string, boolean>
}) {
  if (!overlays.projection || !projection || !lastCandle) return null
  const pDir = (projection.direction as string) || "long"
  const conf = (projection.pattern_confidence as number) || 50
  const altDir = pDir === "long" ? "short" : "long"
  const altConf = 100 - conf
  return (
    <div className="absolute bottom-2 left-2 right-2 flex gap-2 text-[9px] z-10 pointer-events-none">
      <div className={cn("flex-1 p-1.5 rounded border pointer-events-auto", pDir === "long" ? "bg-green-950/70 border-green-700/50" : "bg-red-950/70 border-red-700/50")}>
        <div className={cn("font-bold", pDir === "long" ? "text-green-400" : "text-red-400")}>
          {pDir === "long" ? "↑ UZUN" : "↓ QISA"} {conf}%
        </div>
        {projection.entry_trigger && <div className="text-gray-400 mt-0.5">{projection.entry_trigger as string}</div>}
        {projection.invalidation && <div className="text-gray-600 mt-0.5">✕ {projection.invalidation as string}</div>}
      </div>
      <div className={cn("flex-1 p-1.5 rounded border opacity-60 pointer-events-auto", altDir === "long" ? "bg-green-950/70 border-green-700/50" : "bg-red-950/70 border-red-700/50")}>
        <div className={cn("font-bold", altDir === "long" ? "text-green-400" : "text-red-400")}>
          {altDir === "long" ? "↑ UZUN" : "↓ QISA"} {altConf}%
        </div>
        <div className="text-gray-500 mt-0.5">Alternativ</div>
      </div>
    </div>
  )
}

// ─── MAIN COMPONENT ─────────────────────────────────────────────────
export function AIChart({ analysis: _analysis, explain: _explain, signal, livePrice, aiAnalysis }: {
  analysis?: Record<string, unknown> | null
  explain?: Record<string, unknown> | null
  signal?: Record<string, unknown> | null
  livePrice?: number
  aiAnalysis?: Record<string, unknown> | null
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const lineSeriesRef = useRef<ISeriesApi<"Line"> | null>(null)
  const { selectedSymbol, selectedTimeframe, setSymbol, setTimeframe } = useMarketStore()

  const [candleData, setCandleData] = useState<OHLCVItem[]>([])
  const [loading, setLoading] = useState(true)
  const [dataStatus, setDataStatus] = useState("")
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null)
  const [hoverCandle, setHoverCandle] = useState<Record<string, unknown> | null>(null)
  const [hoverIndicators, setHoverIndicators] = useState<Record<string, unknown> | undefined>(undefined)
  const [overlays, setOverlays] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {}
    OVERLAY_KEYS.forEach((k) => { init[k] = true })
    return init
  })
  const [nowStr, setNowStr] = useState("")
  const [mtfData, setMtfData] = useState<Record<string, unknown> | null>(null)

  const ai = aiAnalysis as Record<string, unknown> | null
  const components = ai?.components as Record<string, unknown> | undefined
  const projection = ai?.projection as Record<string, unknown> | undefined
  const lastCandle = candleData[candleData.length - 1]
  const finalConf = (ai?.confidence as number) || (signal?.confidence as number) || 0
  const finalDir = (ai?.combined_direction as string) || (signal?.direction as string) || "neutral"
  const isTradeReady = finalConf >= 70 && finalDir !== "neutral"
  const price = livePrice || (candleData.length > 0 ? candleData[candleData.length - 1].close : 0)

  // ── Load OHLCV ──
  const loadChartData = useCallback(async () => {
    setLoading(true)
    setDataStatus("")
    try {
      const data = await api.getOHLCV(selectedSymbol, selectedTimeframe, 200)
      if (Array.isArray(data) && data.length > 0) {
        setCandleData((data as RawOHLCVItem[]).map((d) => ({
          time: toUTCTime(d.time), open: d.open, high: d.high, low: d.low, close: d.close, volume: d.volume,
        })))
      } else {
        const err = !Array.isArray(data) ? ((data as Record<string, unknown>)?.error as string || "") : ""
        setDataStatus(err ? "Binance xətası: " + err : "Binance OHLCV alınmadı — boş cavab")
      }
    } catch { setDataStatus("Backend bağlantısı yoxdur") }
    setLoading(false)
  }, [selectedSymbol, selectedTimeframe])

  useEffect(() => { queueMicrotask(() => loadChartData()) }, [loadChartData])
  useEffect(() => { const i = setInterval(() => setNowStr(new Date().toLocaleTimeString("az")), 1000); return () => clearInterval(i) }, [])
  useEffect(() => { api.getMultiTimeframe(selectedSymbol).then((d) => setMtfData(d as Record<string, unknown>)).catch(() => {}) }, [selectedSymbol])

  // ── Chart render ──
  useEffect(() => {
    if (!containerRef.current || !candleData.length) return
    if (chartRef.current) { chartRef.current.remove(); chartRef.current = null; candleSeriesRef.current = null }

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: "#0d1117" }, textColor: "#9ca3af", fontSize: 10 },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      crosshair: { mode: CrosshairMode.Normal, vertLine: { color: "#3b82f680", width: 1, labelBackgroundColor: "#3b82f6" }, horzLine: { color: "#3b82f680", width: 1, labelBackgroundColor: "#3b82f6" } },
      rightPriceScale: { borderColor: "#1f2937", scaleMargins: { top: 0.08, bottom: 0.15 } },
      timeScale: { borderColor: "#1f2937", timeVisible: true, secondsVisible: false, rightOffset: 25 },
      handleScroll: { vertTouchDrag: false },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    })
    chartRef.current = chart

    // Candlestick series
    const cs = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e", downColor: "#ef4444", borderDownColor: "#ef4444", borderUpColor: "#22c55e",
      wickDownColor: "#ef4444", wickUpColor: "#22c55e",
    })
    cs.setData(candleData)
    candleSeriesRef.current = cs

    // Line series for EW, trends, etc.
    const ls = chart.addSeries(LineSeries, { color: "#6366f160", lineWidth: 1, lineStyle: LineStyle.Dashed, lastValueVisible: false, priceLineVisible: false })
    lineSeriesRef.current = ls

    const markers: SeriesMarker<Time>[] = []
    const lct = lastCandle?.time

    // ── 1. Candlestick pattern markers ──
    if (overlays.pattern) {
      const cp = components?.candlestick_patterns as Record<string, unknown> | undefined
      const pats = (cp?.patterns || []) as Array<Record<string, unknown>>
      for (const p of pats) {
        const idx = candleData.length - 1 + (p.index as number)
        if (idx >= 0 && idx < candleData.length) {
          const t = p.type as string
          markers.push({
            time: candleData[idx].time, position: t === "bullish" ? "belowBar" : "aboveBar",
            color: t === "bullish" ? "#4ade80" : "#f87171",
            shape: t === "bullish" ? "arrowUp" : "arrowDown",
            text: (p.name as string).slice(0, 12),
          })
        }
      }
      // Chart pattern
      const chartPats = components?.chart_patterns as Record<string, unknown> | undefined
      const bestP = ((chartPats?.forming_patterns || chartPats?.patterns) as Array<Record<string, unknown>>)?.[0]
      if (bestP && lct) {
        const isF = bestP.is_forming as boolean
        markers.push({
          time: lct, position: "aboveBar", color: isF ? "#f59e0b" : "#22c55e", shape: "circle",
          text: isF ? `📐 ${bestP.name} FORMALAŞIR` : `📐 ${bestP.name} TƏSDİQ`,
        })
      }
    }

    // ── 2. Elliott Wave labels ──
    if (overlays.elliot) {
      const ew = components?.elliott_wave as Record<string, unknown> | undefined
      if (ew && (ew.count as string) !== "unknown" && (ew.count as string) !== "unclear" && (ew.count as string) !== "insufficient_data") {
        const waves = (ew.waves || []) as Array<WaveSegment>
        for (const w of waves) {
          const idx = (w.index as number) || 0
          if (idx >= 0 && idx < candleData.length) {
            const isUp = (w.type as string) === "up"
            markers.push({
              time: candleData[idx].time, position: isUp ? "belowBar" : "aboveBar",
              color: isUp ? "#8b5cf6" : "#a78bfa", shape: "circle", text: `${w.wave}`,
            })
          }
        }
        // EW line: connect swing points
        if (waves.length >= 2 && lastCandle) {
          const first = waves[0]
          const lastWave = waves[waves.length - 1]
          const fIdx = (first.index as number) || 0
          const lIdx = (lastWave.index as number) || candleData.length - 1
          if (fIdx >= 0 && fIdx < candleData.length && lIdx >= 0 && lIdx < candleData.length) {
            // Draw via line data using a second line series
            try {
              const ewLineData = waves.map((w) => ({
                time: candleData[(w.index as number) || 0]?.time || lastCandle.time,
                value: w.price as number,
              }))
              const ewLine = chart.addSeries(LineSeries, {
                color: "#8b5cf680", lineWidth: 1, lineStyle: LineStyle.Dashed, lastValueVisible: false, priceLineVisible: false,
              })
              ewLine.setData(ewLineData)
            } catch {}
          }
        }
      } else if (lct) {
        markers.push({ time: lct, position: "aboveBar", color: "#9ca3af60", shape: "circle", text: "EW qeyri-müəyyən" })
      }
    }

    // ── 3. SMC / BOS / CHoCH markers ──
    if (overlays.smc || overlays.bos) {
      const smcRaw = components?.smc as Record<string, unknown> | undefined
      if (smcRaw && lct) {
        if (overlays.bos && smcRaw.bos_count) {
          markers.push({ time: lct, position: "aboveBar", color: "#f43f5e", shape: "circle", text: `BOS ${smcRaw.bos_count}` })
        }
        if (overlays.smc && smcRaw.choch_count) {
          markers.push({ time: lct, position: "aboveBar", color: "#6366f1", shape: "circle", text: `CHoCH ${smcRaw.choch_count}` })
        }
      }
    }

    // ── 4. Projection scenario markers ──
    if (overlays.projection && projection && lct) {
      const pDir = (projection.direction as string) || "long"
      const cScore = (projection.pattern_confidence as number) || finalConf
      const altDir = pDir === "long" ? "short" : "long"
      markers.push({
        time: (Number(lct) + 7200) as Time, position: pDir === "long" ? "belowBar" : "aboveBar",
        color: pDir === "long" ? "#22c55e" : "#ef4444", shape: pDir === "long" ? "arrowUp" : "arrowDown",
        text: `ESAS ${pDir === "long" ? "↑" : "↓"} ${cScore}%`,
      })
      markers.push({
        time: (Number(lct) + 14400) as Time, position: altDir === "long" ? "belowBar" : "aboveBar",
        color: altDir === "long" ? "#22c55e60" : "#ef444460", shape: altDir === "long" ? "arrowUp" : "arrowDown",
        text: `ALT ${altDir === "long" ? "↑" : "↓"} ${100 - cScore}%`,
      })
      if ((projection.pattern_status as string) === "confirmed" || (projection.breakout_confirmed as boolean)) {
        markers.push({ time: (Number(lct) + 800) as Time, position: "aboveBar", color: "#22c55e", shape: "circle", text: "✓ TƏSDİQLƏNDİ" })
      } else if ((projection.pattern_status as string) === "forming") {
        markers.push({ time: (Number(lct) + 800) as Time, position: "aboveBar", color: "#f59e0b", shape: "circle", text: "⏳ BREAKOUT GÖZLƏNİR" })
      }
      if (projection.entry_trigger) {
        markers.push({ time: (Number(lct) + 7200) as Time, position: "aboveBar", color: "#3b82f690", shape: "circle", text: ((projection.entry_trigger as string) || "").slice(0, 28) })
      }
    }

    if (markers.length > 0) createSeriesMarkers(cs, markers)

    // ── Price lines: Entry / SL / TP ──
    if (overlays.trade && signal && !(signal.error as string)) {
      if (isTradeReady) {
        const levels: Array<{ price?: number; title: string; color: string; style: LineStyle }> = [
          { price: (signal.entry_zone as Record<string, unknown>)?.min as number, title: "GİRİŞ ↓", color: "#3b82f6", style: LineStyle.Dashed },
          { price: (signal.entry_zone as Record<string, unknown>)?.max as number, title: "GİRİŞ ↑", color: "#60a5fa", style: LineStyle.Dashed },
          { price: signal.stop_loss as number, title: "SL", color: "#ef4444", style: LineStyle.Solid },
          { price: signal.take_profit_1 as number, title: "TP1", color: "#22c55e", style: LineStyle.Solid },
          { price: signal.take_profit_2 as number, title: "TP2", color: "#16a34a", style: LineStyle.Dashed },
          { price: signal.take_profit_3 as number, title: "TP3", color: "#15803d", style: LineStyle.Dotted },
        ]
        levels.forEach((l) => {
          if (l.price && l.price > 0) {
            cs.createPriceLine({ price: l.price, color: l.color, lineWidth: 1, lineStyle: l.style, axisLabelVisible: true, title: l.title })
          }
        })
        // RR label
        const sl = signal.stop_loss as number
        const tp1 = signal.take_profit_1 as number
        const entryMid = ((signal.entry_zone as Record<string, unknown>)?.mid as number) || ((signal.entry_zone as Record<string, unknown>)?.min as number) || 0
        if (sl && tp1 && entryMid) {
          const rr = Math.abs((tp1 - entryMid) / (entryMid - sl))
          cs.createPriceLine({ price: entryMid, color: "#3b82f6", lineWidth: 2, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: `RR ${rr.toFixed(2)}` })
        }
      } else {
        // WAIT: only trigger levels
        const eMin = (signal.entry_zone as Record<string, unknown>)?.min as number
        const tp1 = signal.take_profit_1 as number
        if (eMin) cs.createPriceLine({ price: eMin, color: "#22c55e60", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "↑ trigger" })
        if (tp1) cs.createPriceLine({ price: tp1, color: "#ef444460", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "↓ trigger" })
      }
    }

    // ── Fibonacci price levels ──
    if (overlays.fibonacci) {
      const fib = components?.fibonacci as Record<string, unknown> | undefined
      if (fib) {
        const rets = (fib.retracements || fib.all_levels || fib.levels || []) as Array<{ level: number; price: number }>
        const showLevels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.618]
        for (const lvl of rets) {
          const level = lvl.level as number
          if (showLevels.includes(level) && (lvl.price as number) > 0) {
            const color = level === 0.618 ? "#a855f780" : level === 0.5 || level === 0.786 ? "#a855f760" : "#6366f140"
            const width = level === 0.618 ? 2 : 1
            cs.createPriceLine({ price: lvl.price as number, color, lineWidth: width, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: `Fib ${(level * 100).toFixed(1)}%` })
          }
        }
      }
    }

    // ── S/R price lines ──
    if (overlays.sr) {
      const tl = components?.trend_lines as Record<string, unknown> | undefined
      if (tl) {
        for (const sl of (tl.support_lines || []) as Array<Record<string, unknown>>) {
          const ep = sl.end_price as number
          if (ep > 0) cs.createPriceLine({ price: ep, color: "#22c55e40", lineWidth: 2, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: "DƏSTƏK" })
        }
        for (const rl of (tl.resistance_lines || []) as Array<Record<string, unknown>>) {
          const ep = rl.end_price as number
          if (ep > 0) cs.createPriceLine({ price: ep, color: "#ef444440", lineWidth: 2, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: "MÜQAVİMƏT" })
        }
      }
    }

    // ── Liquidity / OB / FVG / Breaker ──
    if (overlays.liquidity || overlays.ob || overlays.fvg || overlays.breaker) {
      const lz = components?.liquidity_zones as Record<string, unknown> | undefined
      if (lz) {
        if (overlays.liquidity) {
          const ns = lz.nearest_support as number
          const nr = lz.nearest_resistance as number
          if (ns > 0) cs.createPriceLine({ price: ns, color: "#14b8a660", lineWidth: 2, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "Likvidlik D" })
          if (nr > 0) cs.createPriceLine({ price: nr, color: "#14b8a660", lineWidth: 2, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "Likvidlik M" })
        }
        const zones = (lz.zones || []) as Array<Record<string, unknown>>
        for (const z of zones) {
          const src = (z.source as string) || ""
          if (overlays.ob && src === "order_block") {
            const p = (z.price as number) || (z.price_low as number) || 0
            if (p > 0) cs.createPriceLine({ price: p, color: "#06b6d480", lineWidth: 2, lineStyle: LineStyle.Solid, axisLabelVisible: true, title: "OB" })
          }
          if (overlays.fvg && src === "fvg") {
            const p = (z.price as number) || (z.price_low as number) || 0
            if (p > 0) cs.createPriceLine({ price: p, color: "#d946ef80", lineWidth: 2, lineStyle: LineStyle.Solid, axisLabelVisible: true, title: "FVG" })
          }
          if (overlays.breaker && (src === "breaker_block" || src === "mitigation_block")) {
            const p = (z.price as number) || (z.price_low as number) || 0
            if (p > 0) cs.createPriceLine({ price: p, color: "#ec489980", lineWidth: 2, lineStyle: LineStyle.Solid, axisLabelVisible: true, title: "Breaker" })
          }
        }
      }
    }

    // ── Projection expected path lines ──
    if (overlays.projection && projection) {
      const path = (projection.expected_path || []) as Array<{ level: string; price: number }>
      for (const item of path) {
        if (item.price > 0) {
          cs.createPriceLine({
            price: item.price, color: item.level === "Entry" ? "#3b82f6" : item.level.startsWith("TP") ? "#22c55e" : "#a855f7",
            lineWidth: item.level === "Entry" ? 2 : 1, lineStyle: item.level === "Target" ? LineStyle.Dotted : LineStyle.Dashed,
            axisLabelVisible: true, title: `${item.level} ${item.level === "Target" ? "🎯" : ""}`,
          })
        }
      }
      if ((projection.stop_loss as number) > 0) {
        cs.createPriceLine({ price: projection.stop_loss as number, color: "#ef4444", lineWidth: 2, lineStyle: LineStyle.Solid, axisLabelVisible: true, title: "SL" })
      }
    }

    // ── Hover tooltip ──
    chart.subscribeCrosshairMove((param) => {
      if (!param.point || !param.time) { setHoverPos(null); setHoverCandle(null); return }
      const sd = param.seriesData?.get(cs) as Record<string, unknown> | undefined
      if (sd?.open) {
        setHoverPos({ x: param.point.x, y: param.point.y })
        setHoverCandle(sd)
        // Build indicators from candle data + components
        const ind: Record<string, unknown> = {}
        const cp = components?.candlestick_patterns as Record<string, unknown> | undefined
        const pats = (cp?.patterns || []) as Array<Record<string, unknown>>
        const barTime = Number(param.time)
        const matchPat = pats.find((p) => {
          const idx = candleData.length - 1 + (p.index as number)
          return idx >= 0 && idx < candleData.length && Number(candleData[idx].time) === barTime
        })
        if (matchPat) ind.pattern = matchPat.name as string
        // Pull indicators from institutional_score details if available
        const score = ai?.institutional_score as Record<string, unknown> | undefined
        const det = score?.details as Record<string, unknown> | undefined
        if (det?.rsi != null) ind.rsi = det.rsi
        if (det?.macd_histogram != null) ind.macd_histogram = det.macd_histogram
        if (det?.atr != null) ind.atr = det.atr
        if (det?.adx != null) ind.adx = det.adx
        if (det?.supertrend != null) ind.supertrend = det.supertrend
        ind.volume = sd.volume as number
        ind.confidence = finalConf
        setHoverIndicators(ind)
      } else {
        setHoverCandle(null)
      }
    })

    chartRef.current = chart

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth, height: containerRef.current.clientHeight })
        requestAnimationFrame(() => drawZonesOnCanvas())
      }
    }
    window.addEventListener("resize", handleResize)
    return () => {
      window.removeEventListener("resize", handleResize)
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      lineSeriesRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candleData, signal, aiAnalysis, selectedTimeframe, overlays])

  // ── Canvas zone drawing ──
  const drawZonesOnCanvas = useCallback(() => {
    const canvas = canvasRef.current
    const chart = chartRef.current
    if (!canvas || !chart || !candleData.length) return
    const zones: Array<{ top: number; bottom: number; color: string; label?: string }> = []

    // Fibonacci golden zone
    if (overlays.fibonacci) {
      const fib = components?.fibonacci as Record<string, unknown> | undefined
      if (fib) {
        const rets = (fib.retracements || fib.all_levels || fib.levels || []) as Array<{ level: number; price: number }>
        const fibMap = new Map(rets.map((r) => [r.level, r.price]))
        const gz = fib.golden_zone as Record<string, unknown> | undefined
        if (gz?.low && gz?.high) {
          zones.push({ top: gz.low as number, bottom: gz.high as number, color: "#a855f720", label: "Qızıl Zona" })
        }
        // Bands between consecutive levels
        const drawLevels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]
        for (let i = 0; i < drawLevels.length - 1; i++) {
          const l1 = fibMap.get(drawLevels[i])
          const l2 = fibMap.get(drawLevels[i + 1])
          if (l1 != null && l2 != null) {
            const alpha = drawLevels[i] === 0.382 || drawLevels[i] === 0.618 ? "30" : "15"
            zones.push({ top: l1, bottom: l2, color: `#a855f7${alpha}` })
          }
        }
      }
    }

    // S/R zones
    if (overlays.sr) {
      const tl = components?.trend_lines as Record<string, unknown> | undefined
      if (tl) {
        for (const sl of (tl.support_lines || []) as Array<Record<string, unknown>>) {
          const ep = sl.end_price as number
          if (ep > 0) zones.push({ top: ep * 0.998, bottom: ep * 1.002, color: "#22c55e15", label: "S" })
        }
        for (const rl of (tl.resistance_lines || []) as Array<Record<string, unknown>>) {
          const ep = rl.end_price as number
          if (ep > 0) zones.push({ top: ep * 0.998, bottom: ep * 1.002, color: "#ef444415", label: "R" })
        }
      }
    }

    // Liquidity zones
    if (overlays.liquidity) {
      const lz = components?.liquidity_zones as Record<string, unknown> | undefined
      if (lz) {
        const zonesArr = (lz.zones || []) as Array<Record<string, unknown>>
        for (const z of zonesArr) {
          const pLow = (z.price_low as number) || (z.price as number) || 0
          const pHigh = (z.price_high as number) || (z.price as number) || 0
          if (pLow > 0 && pHigh > 0) {
            zones.push({ top: pLow, bottom: pHigh, color: "#14b8a620", label: z.type as string })
          } else if (pLow > 0) {
            zones.push({ top: pLow * 0.999, bottom: pLow * 1.001, color: "#14b8a620", label: z.type as string })
          }
        }
      }
    }

    drawZoneCanvas(canvas, chart, zones)
  }, [candleData, overlays, components])

  useEffect(() => {
    if (chartRef.current && candleData.length > 0) {
      drawZonesOnCanvas()
    }
  }, [drawZonesOnCanvas])

  // ── Toggle handler ──
  const toggleOverlay = (key: OverlayKey) => setOverlays((prev) => ({ ...prev, [key]: !prev[key] }))

  // ── Status flags ──
  const sm = dataStatus || ""
  const showNoData = !candleData.length && !loading
  const showLoading = loading && candleData.length === 0

  // ── Render ──
  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center justify-between px-3 py-1 bg-gray-900 border-b border-gray-800 overflow-x-auto shrink-0">
        <div className="flex items-center gap-2">
          <select value={selectedSymbol} onChange={(e) => setSymbol(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white font-mono focus:outline-none focus:border-blue-500">
            {["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "SUI/USDT", "ADA/USDT", "DOGE/USDT",
              "INJ/USDT", "SKY/USDT", "SKH/USDT"].map((s) => (<option key={s} value={s}>{s}</option>))}
          </select>
          <div className="text-sm font-bold text-white font-mono">${typeof price === "number" ? price.toFixed(2) : "0.00"}</div>
          <span className="text-[9px] text-gray-600">{nowStr}</span>
        </div>
        <div className="flex items-center gap-1">
          {[{ id: "5m", label: "5m" }, { id: "15m", label: "15m" }, { id: "1h", label: "1H" }, { id: "4h", label: "4H" }, { id: "1d", label: "1D" }, { id: "1w", label: "1W" }].map((tf) => (
            <button key={tf.id} onClick={() => setTimeframe(tf.id)}
              className={cn("px-1.5 py-0.5 text-[9px] rounded font-medium transition-colors",
                selectedTimeframe === tf.id ? "bg-blue-600 text-white" : "text-gray-500 hover:text-gray-300 hover:bg-gray-800")}>
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* MTF badges */}
      {mtfData?.timeframes && (
        <div className="flex items-center gap-1.5 px-3 py-0.5 bg-gray-900/80 border-b border-gray-800 overflow-x-auto shrink-0">
          {Object.entries((mtfData.timeframes as Record<string, Record<string, unknown>>) || {}).slice(0, 6).map(([tf, td]) => {
            const d = (td.direction as string) || "neutral"
            return (
              <span key={tf} className={cn("text-[8px] px-1 py-0.5 rounded font-mono font-bold",
                d === "long" ? "bg-green-900/40 text-green-400" : d === "short" ? "bg-red-900/40 text-red-400" : "bg-gray-800 text-gray-500")}>
                {tf} {d === "long" ? "↑" : d === "short" ? "↓" : "→"}
              </span>
            )
          })}
          <span className={cn("text-[8px] font-bold ml-1",
            (mtfData.alignment as Record<string, unknown>)?.major_aligned ? "text-green-400" : "text-yellow-400")}>
            {(mtfData.aggregated as Record<string, unknown>)?.timeframe_count || 0}/6
          </span>
        </div>
      )}

      {/* Overlay toggles */}
      <OverlayToggles active={overlays} onChange={toggleOverlay} />

      {/* Chart */}
      <div className="relative flex-1 min-h-0">
        <div ref={containerRef} className="absolute inset-0" />
        <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none z-[5]" />

        {showLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center z-10 bg-[#0d1117]">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-2" />
            <div className="text-xs text-gray-600">Məlumat yüklənir...</div>
          </div>
        )}

        {showNoData && (
          <div className="absolute inset-0 flex flex-col items-center justify-center z-10 bg-[#0d1117]">
            <div className="flex flex-col items-center max-w-xs text-center">
              {sm.includes("Binance") || sm.includes("boş") ? (
                <><div className="w-12 h-12 mb-2 rounded-full bg-amber-900/30 flex items-center justify-center"><span className="text-2xl">📡</span></div>
                  <p className="text-xs text-amber-400 font-medium mb-1">Binance OHLCV alınmadı</p>
                  <p className="text-[10px] text-gray-500">API limiti və ya simvol mövcud deyil.</p></>
              ) : sm.includes("Backend") ? (
                <><div className="w-12 h-12 mb-2 rounded-full bg-red-900/30 flex items-center justify-center"><span className="text-2xl">⚠️</span></div>
                  <p className="text-xs text-red-400 font-medium mb-1">Backend bağlantısı kəsildi</p>
                  <p className="text-[10px] text-gray-500">Server cavab vermir.</p></>
              ) : (
                <><div className="w-12 h-12 mb-2 rounded-full bg-gray-800 flex items-center justify-center"><span className="text-2xl">📊</span></div>
                  <p className="text-xs text-gray-500 font-medium mb-1">Məlumat yoxdur</p>
                  <p className="text-[10px] text-gray-600">Simvol seçin.</p></>
              )}
            </div>
          </div>
        )}

        <HoverTooltip data={hoverPos} candle={hoverCandle as Record<string, unknown> | undefined} indicators={hoverIndicators} />
        <ScenarioLabels projection={projection} lastCandle={lastCandle} overlays={overlays} />
      </div>
    </div>
  )
}
