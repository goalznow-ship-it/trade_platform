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
  const vwapRef = useRef<ISeriesApi<"Line"> | null>(null)
  const atrStopRef = useRef<ISeriesApi<"Line"> | null>(null)
  const [ohlcv, setOhlcv] = useState<Candle[]>([])
  const [tf, setTf] = useState("1h")
  const [projection, setProjection] = useState<Candle[]>([])
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null)
  const timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

  const scores = (analysis?.scores || {}) as Record<string, unknown>
  const scenarios = analysis?.scenarios as Record<string, unknown> | undefined
  const tfs = (analysis?.timeframes || {}) as Record<string, unknown>
  const alignment = (analysis?.alignment || {}) as Record<string, unknown>
  const allStructs = analysis?.all_structures as Record<string, unknown>[] | undefined
  const patterns = analysis?.patterns as Record<string, unknown>[] | undefined
  const ew = analysis?.elliott_wave as Record<string, unknown> | undefined
  const fib = analysis?.fibonacci as Record<string, unknown> | undefined
  const explanation = str(analysis?.explanation_az)
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
      layout: {
        background: { type: ColorType.Solid, color: "#0d1117" },
        textColor: "#6b7280", fontSize: 11,
      },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#374151", scaleMargins: { top: 0.05, bottom: 0.25 } },
      timeScale: { borderColor: "#374151", timeVisible: true, secondsVisible: false },
      autoSize: true,
    })
    chartRef.current = chart

    candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e", downColor: "#ef4444",
      borderDownColor: "#ef4444", borderUpColor: "#22c55e",
      wickDownColor: "#ef4444", wickUpColor: "#22c55e",
    })

    volSeriesRef.current = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" }, priceScaleId: "volume",
    })
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.88, bottom: 0 } })

    ema20Ref.current = chart.addSeries(LineSeries, {
      color: "#f59e0b", lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
    })
    ema50Ref.current = chart.addSeries(LineSeries, {
      color: "#3b82f6", lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
    })
    ema100Ref.current = chart.addSeries(LineSeries, {
      color: "#8b5cf6", lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
    })
    vwapRef.current = chart.addSeries(LineSeries, {
      color: "#ec4899", lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false,
    })
    atrStopRef.current = chart.addSeries(LineSeries, {
      color: "#f97316", lineWidth: 1, lineStyle: 3, priceLineVisible: false, lastValueVisible: false,
    })

    return () => { chart.remove() }
  }, [])

  useEffect(() => {
    if (!candleSeriesRef.current || !volSeriesRef.current || !ohlcv.length) return
    const candleData = ohlcv.map((d) => ({
      time: d.time as Time, open: d.open, high: d.high, low: d.low, close: d.close,
    }))
    const volData = ohlcv.map((d) => ({
      time: d.time as Time, value: d.volume,
      color: d.close >= d.open ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)",
    }))
    candleSeriesRef.current.setData(candleData)
    volSeriesRef.current.setData(volData)

    const closes = ohlcv.map((d) => d.close)
    const ema20 = calcEMA(closes, 20); const ema50 = calcEMA(closes, 50)
    const ema100 = calcEMA(closes, 100)
    const vwap = calcVWAP(ohlcv)
    const atrStop = calcATRStop(ohlcv, 14, 2.5)

    const ema20Data = ema20.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter((d) => d.value > 0)
    const ema50Data = ema50.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter((d) => d.value > 0)
    const ema100Data = ema100.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter((d) => d.value > 0)
    const vwapData = vwap.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter((d) => d.value > 0)
    const atrStopData = atrStop.map((v, i) => ({ time: ohlcv[i].time as Time, value: v })).filter((d) => d.value > 0)

    ema20Ref.current?.setData(ema20Data)
    if (ema50Data.length > 0) ema50Ref.current?.setData(ema50Data)
    if (ema100Data.length > 0) ema100Ref.current?.setData(ema100Data)
    if (vwapData.length > 0) vwapRef.current?.setData(vwapData)
    if (atrStopData.length > 0) atrStopRef.current?.setData(atrStopData)

    chartRef.current?.timeScale().fitContent()
    drawOverlay()
  }, [ohlcv])

  const drawOverlay = useCallback(() => {
    const canvas = overlayRef.current
    const chart = chartRef.current
    if (!canvas || !chart || !ohlcv.length) return
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * window.devicePixelRatio
    canvas.height = rect.height * window.devicePixelRatio
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
    ctx.clearRect(0, 0, rect.width, rect.height)

    const ts = chart.timeScale()
    const visibleRange = ts.getVisibleLogicalRange()
    if (!visibleRange) return

    const toX = (time: number) => ts.timeToCoordinate(time as Time) ?? 0
    const toY = (price: number) => candleSeriesRef.current?.priceToCoordinate(price) ?? 0

    drawHeatmap(ctx, toX, toY, rect.width, rect.height, ohlcv)
    drawSMCStructures(ctx, toX, toY, analysis, ohlcv)
    drawSR(ctx, toX, toY, sr, price, rect.width)
    drawPatterns(ctx, toX, toY, patterns, ohlcv, rect.width)
    drawScenarios(ctx, toX, toY, scenarios, price, rect.width, rect.height)
    drawTradeLevels(ctx, toX, toY, triggers, scores, rect.width)
    drawProjection(ctx, toX, toY, projection, ohlcv)
    drawCone(ctx, toX, toY, projection, confidence, rect.width, rect.height, ohlcv)
    drawVolumeProfile(ctx, toX, toY, ohlcv, rect.width, rect.height)
    drawSmartMoney(ctx, toX, toY, analysis, ohlcv)
    drawElliottWave(ctx, toX, toY, ew, rect.width, ohlcv)
    drawFibonacci(ctx, toX, toY, fib, rect.width, ohlcv)
  }, [ohlcv, analysis, triggers, scores, sr, scenarios, patterns, projection, confidence, price, ew, fib])

  useEffect(() => {
    drawOverlay()
    const interval = setInterval(drawOverlay, 1000)
    return () => clearInterval(interval)
  }, [drawOverlay])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const canvas = overlayRef.current
    const chart = chartRef.current
    if (!canvas || !chart) { setTooltip(null); return }
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const time = chart.timeScale().coordinateToTime(x)
    const pr = candleSeriesRef.current?.coordinateToPrice(y)
    if (time == null || pr == null) { setTooltip(null); return }
    const hovered = findNearestStructure(allStructs, time as number, pr, toCandleTime(ohlcv, x, chart))
    if (hovered) {
      setTooltip({ x: e.clientX - rect.left + 10, y: e.clientY - rect.top - 10, text: hovered })
    } else {
      setTooltip(null)
    }
  }, [allStructs, ohlcv])

  const handleMouseLeave = () => setTooltip(null)

  const statusLabel: Record<string, string> = {
    STRONG_TRADE_READY: "GÜCLÜ TİCARƏT HAZIRDIR",
    TRADE_READY: "TİCARƏT HAZIRDIR",
    WATCHLIST: "İZLƏMƏ SİYAHISI",
    WAIT: "GÖZLƏYİN",
  }

  return (
    <div className="h-full flex flex-col relative">
      <div className="flex items-center px-2 py-0.5 border-b border-gray-800/40 bg-gray-950/60 z-10 shrink-0">
        {timeframes.map((t) => {
          const sig = (tfs[t] as Record<string, unknown>)?.signal as string || ""
          const sigColor = sig.includes("LONG") ? "text-green-400 bg-green-500/10" :
            sig.includes("SHORT") ? "text-red-400 bg-red-500/10" : "text-gray-500 bg-gray-800/30"
          return (
            <button key={t} onClick={() => setTf(t)}
              className={cn("flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] font-mono rounded transition-colors mr-0.5",
                tf === t ? "bg-blue-600/20 border border-blue-500/30" : "hover:bg-gray-800/30",
              )}>
              <span className="text-gray-500">{t}</span>
              {sig && <span className={cn("px-0.5 rounded text-[8px] font-bold", sigColor)}>{sig.includes("LONG") ? "↑" : sig.includes("SHORT") ? "↓" : "−"}</span>}
            </button>
          )
        })}
        <div className="flex-1" />
        <div className="flex items-center gap-1.5 px-2">
          <span className="text-[9px] text-gray-500">AI</span>
          <div className="w-16 h-1.5 rounded-full bg-gray-800 overflow-hidden">
            <div className={cn("h-full rounded-full transition-all duration-500",
              confidence >= 70 ? "bg-green-500" : confidence >= 50 ? "bg-yellow-500" : "bg-red-500")}
              style={{ width: `${Math.min(confidence, 100)}%` }} />
          </div>
          <span className={cn("text-[10px] font-bold font-mono",
            confidence >= 70 ? "text-green-400" : confidence >= 50 ? "text-yellow-400" : "text-gray-500")}>
            {confidence}%
          </span>
          <span className={cn("text-[8px] px-1 py-0.5 rounded font-semibold",
            status === "STRONG_TRADE_READY" ? "bg-green-500/20 text-green-400" :
            status === "TRADE_READY" ? "bg-blue-500/20 text-blue-400" :
            status === "WATCHLIST" ? "bg-yellow-500/20 text-yellow-400" : "bg-gray-500/20 text-gray-400")}>
            {statusLabel[status] || status}
          </span>
        </div>
        <span className="text-[9px] text-gray-600 font-mono mr-1">{symbol}</span>
      </div>

      <div className="relative flex-1" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
        <div ref={containerRef} className="absolute inset-0" />
        <canvas ref={overlayRef} className="absolute inset-0 pointer-events-none z-[5]" />

        {tooltip && (
          <div className="absolute z-10 pointer-events-none bg-gray-900/95 border border-gray-700 rounded px-2 py-1 text-[9px] text-gray-200 shadow-xl max-w-[200px] whitespace-pre-line"
            style={{ left: tooltip.x, top: tooltip.y }}>
            {tooltip.text}
          </div>
        )}

        <div className="absolute top-2 right-2 z-[6] flex flex-col gap-1 text-[9px]">
          <div className={cn("px-2 py-0.5 rounded font-bold font-mono text-right",
            longProb > shortProb ? "bg-green-500/20 text-green-400" : "bg-gray-800/40 text-gray-600")}>
            ALIŞ {longProb}%
          </div>
          <div className={cn("px-2 py-0.5 rounded font-bold font-mono text-right",
            shortProb > longProb ? "bg-red-500/20 text-red-400" : "bg-gray-800/40 text-gray-600")}>
            SATIŞ {shortProb}%
          </div>
        </div>

        {confidence >= 70 && (
          <div className="absolute bottom-2 left-2 z-[6] bg-gray-950/90 border border-gray-700/60 rounded px-2 py-1 text-[9px] font-mono space-y-0.5 max-w-[200px]">
            {longProb > shortProb ? (
              <>
                <div className="text-green-400 font-bold text-[10px]">ALIŞ PLANI</div>
                <div className="text-gray-400">Giriş: <span className="text-white">${ltPrice.toFixed(2)}</span></div>
                <div className="text-gray-400">Zərər kəsmə: <span className="text-red-400">${inval.toFixed(2)}</span></div>
                <div className="text-gray-400">Hədəf: <span className="text-green-400">Sonra müəyyən ediləcək</span></div>
              </>
            ) : (
              <>
                <div className="text-red-400 font-bold text-[10px]">SATIŞ PLANI</div>
                <div className="text-gray-400">Giriş: <span className="text-white">${stPrice.toFixed(2)}</span></div>
                <div className="text-gray-400">Zərər kəsmə: <span className="text-red-400">${inval.toFixed(2)}</span></div>
                <div className="text-gray-400">Hədəf: <span className="text-red-400">Sonra müəyyən ediləcək</span></div>
              </>
            )}
            <div className={cn("text-[8px]", confidence >= 80 ? "text-green-400" : "text-yellow-400")}>
              Risk: {confidence >= 80 ? "Aşağı" : "Orta"} • RR: ~1:2
            </div>
          </div>
        )}

        {confidence < 70 && confidence > 0 && (
          <div className={cn("absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[6] text-center pointer-events-none",
            status === "WAIT" ? "opacity-100" : "opacity-60")}>
            <div className="text-[11px] font-bold text-yellow-500 mb-1">⏳ GÖZLƏYİN</div>
            <div className="text-[9px] text-gray-500">
              {longProb > shortProb
                ? `ALIŞ triggeri: $${ltPrice.toFixed(2)} üzərində təsdiq`
                : `SATIŞ triggeri: $${stPrice.toFixed(2)} altında təsdiq`
              }
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Helper Functions ───

function calcEMA(data: number[], period: number): number[] {
  if (data.length < period) return data.map(() => 0)
  const k = 2 / (period + 1)
  const result: number[] = []
  let ema = data.slice(0, period).reduce((a, b) => a + b, 0) / period
  result.push(ema)
  for (let i = period; i < data.length; i++) {
    ema = (data[i] - ema) * k + ema
    result.push(ema)
  }
  const pad = new Array(period - 1).fill(0)
  return [...pad, ...result]
}

function calcVWAP(data: Candle[]): number[] {
  let cumPV = 0, cumVol = 0
  return data.map((d) => {
    const tp = (d.high + d.low + d.close) / 3
    cumPV += tp * d.volume
    cumVol += d.volume
    return cumVol > 0 ? cumPV / cumVol : tp
  })
}

function calcATRStop(data: Candle[], period: number, multiplier: number): number[] {
  if (data.length < period + 1) return data.map(() => 0)
  const tr: number[] = []
  for (let i = 1; i < data.length; i++) {
    const hl = data[i].high - data[i].low
    const hcp = Math.abs(data[i].high - data[i - 1].close)
    const lcp = Math.abs(data[i].low - data[i - 1].close)
    tr.push(Math.max(hl, hcp, lcp))
  }
  let atr = tr.slice(0, period).reduce((a, b) => a + b, 0) / period
  const atrs: number[] = [atr]
  for (let i = period; i < tr.length; i++) {
    atr = (atr * (period - 1) + tr[i]) / period
    atrs.push(atr)
  }
  const pad = new Array(period).fill(0)
  const result: number[] = [...pad]
  for (let i = period; i < data.length; i++) {
    const stop = data[i].close - (atrs[i - period] * multiplier)
    result.push(Math.round(stop * 100) / 100)
  }
  return result
}

function toCandleTime(ohlcv: Candle[], x: number, chart: IChartApi): number {
  const t = chart.timeScale().coordinateToTime(x)
  if (t == null) return 0
  return t as number
}

function findNearestStructure(structs: Record<string, unknown>[] | undefined, time: number, price: number, candleTime: number): string | null {
  if (!structs) return null
  for (const s of structs) {
    const sIdx = num(s.index)
    if (Math.abs(sIdx - candleTime) < 5) {
      const sp = num(s.price) || num(s.gap_high) || 0
      if (Math.abs(sp - price) / price < 0.05) {
        const type = str(s.type)
        const cat = str(s.category)
        if (cat === "bos") return `BOS (Break of Structure)\nStruktur dəyişikliyi - bazar ${type.includes("bullish") ? "yuxarı" : "aşağı"} istiqamətə keçir.\nBu, trendin dəyişdiyinə işarədir.`
        if (cat === "choch") return `CHoCH (Change of Character)\nXarakter dəyişikliyi - trend ${type.includes("bullish") ? "yüksələn" : "enən"} ola bilər.\nSmart money yeni istiqamətə hazırlaşır.`
        if (cat === "fvg") return `FVG (Fair Value Gap)\nQiymət boşluğu - ${type.includes("bullish") ? "yuxarı" : "aşağı"} likvidite çəkə bilər.\nBoşluq adətən doldurulmağa meyllidir.`
        if (cat === "order_block") return `OB (Order Block)\nSmart money ${type.includes("bullish") ? "alış" : "satış"} əmri buraxıb.\nBöyük oyunçuların maraq zonası.`
        if (cat === "breaker_block") return `BB (Breaker Block)\nƏvvəlki OB-nin sındırılması.\nTrendin zəiflədiyini göstərə bilər.`
        if (cat === "mitigation_block") return `MB (Mitigation Block)\nOB zonasına qayıdış.\nLikvidite almaq üçün istifadə olunur.`
        if (cat === "swing") return `Swing ${type === "high" ? "Zirvə" : "Dip"}\nÖnəmli dönüş nöqtəsi.\nBurada qiymət istiqamət dəyişib.`
        if (cat === "liquidity") return `Likvidite zonası\n${type.includes("above") ? "Yuxarıda" : "Aşağıda"} likvidite toplanıb.\nStop-loss ovu üçün hədəf zona.`
        if (cat === "equal_highs" || cat === "equal_lows") return `EEQL (Equal ${cat === "equal_highs" ? "Highs" : "Lows"})\nBərabər ${cat === "equal_highs" ? "zirvələr" : "diplər"}.\nLikvidite zonası - sınaq gözlənilir.`
        if (cat === "inducement") return `Inducement\nTələyə salma hərəkəti.\nKiçik oyunçuları cəlb edib sonra əks istiqamət.`
        return `${type}\nSmart Money Concept strukturu.\nDaha ətraflı təhlil üçün sağ panelə baxın.`
      }
    }
  }
  return null
}

// ─── Drawing Functions ───

function drawHeatmap(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, w: number, h: number, ohlcv: Candle[]) {
  if (ohlcv.length < 20) return
  for (let i = 1; i < ohlcv.length; i++) {
    const x = toX(ohlcv[i].time)
    if (x < 0 || x > w) continue
    const body = Math.abs(ohlcv[i].close - ohlcv[i].open)
    const range = ohlcv[i].high - ohlcv[i].low
    if (range === 0) continue
    const intensity = Math.min(body / range * 0.3, 0.3)
    ctx.fillStyle = ohlcv[i].close >= ohlcv[i].open ? `rgba(34,197,94,${intensity})` : `rgba(239,68,68,${intensity})`
    ctx.fillRect(x - 2, 0, 4, h)
  }
}

function drawSMCStructures(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, analysis: Record<string, unknown> | null, ohlcv: Candle[]) {
  if (!analysis || ohlcv.length === 0) return
  const w = ctx.canvas.width / window.devicePixelRatio
  const chart = analysis as Record<string, unknown>
  const allStructs = chart.all_structures as Record<string, unknown>[] | undefined
  if (!allStructs) return

  const fvgs = allStructs.filter((s) => str(s.category) === "fvg")
  for (const fvg of fvgs.slice(-10)) {
    const idx = num(fvg.index)
    if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time)
    const top = toY(num(fvg.gap_high))
    const bottom = toY(num(fvg.gap_low))
    if (x <= 0 || top <= 0 || bottom <= 0) continue
    const isBullish = str(fvg.type).includes("bullish")
    ctx.fillStyle = isBullish ? "rgba(34,197,94,0.12)" : "rgba(239,68,68,0.12)"
    ctx.fillRect(x - 4, Math.min(top, bottom), 8, Math.abs(top - bottom))
    ctx.strokeStyle = isBullish ? "rgba(34,197,94,0.4)" : "rgba(239,68,68,0.4)"
    ctx.lineWidth = 0.5
    ctx.setLineDash([2, 2])
    ctx.strokeRect(x - 4, Math.min(top, bottom), 8, Math.abs(top - bottom))
    ctx.setLineDash([])
    ctx.font = "6px monospace"
    ctx.fillStyle = isBullish ? "rgba(34,197,94,0.6)" : "rgba(239,68,68,0.6)"
    ctx.fillText("FVG", x - 4, Math.max(top, bottom) + 10)
  }

  const obs = allStructs.filter((s) => str(s.category) === "order_block")
  for (const ob of obs.slice(-8)) {
    const idx = num(ob.index)
    if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time)
    const top = toY(num(ob.high))
    const bottom = toY(num(ob.low))
    if (x <= 0 || top <= 0 || bottom <= 0) continue
    const isBullish = str(ob.type).includes("bullish")
    ctx.fillStyle = isBullish ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)"
    ctx.fillRect(x - 6, Math.min(top, bottom), 12, Math.abs(top - bottom))
    ctx.strokeStyle = isBullish ? "#22c55e" : "#ef4444"
    ctx.lineWidth = 1
    ctx.strokeRect(x - 6, Math.min(top, bottom), 12, Math.abs(top - bottom))
    ctx.font = "7px monospace"
    ctx.fillStyle = isBullish ? "#22c55e" : "#ef4444"
    ctx.fillText("OB", x - 6, Math.min(top, bottom) - 3)
  }

  const bosList = allStructs.filter((s) => str(s.category) === "bos")
  for (const bos of bosList.slice(-6)) {
    const idx = num(bos.index)
    if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time)
    const y = toY(num(bos.price))
    if (x <= 0 || y <= 0) continue
    const isBullish = str(bos.type).includes("bullish")
    ctx.strokeStyle = isBullish ? "#22c55e" : "#ef4444"
    ctx.lineWidth = 1.5
    const sz = 5
    ctx.beginPath()
    if (isBullish) {
      ctx.moveTo(x - sz, y + sz); ctx.lineTo(x, y); ctx.lineTo(x + sz, y + sz)
    } else {
      ctx.moveTo(x - sz, y - sz); ctx.lineTo(x, y); ctx.lineTo(x + sz, y - sz)
    }
    ctx.stroke()
    ctx.font = "6px monospace"
    ctx.fillStyle = isBullish ? "#22c55e" : "#ef4444"
    ctx.fillText("BOS", x + sz + 1, y + (isBullish ? sz : -sz) + 2)
  }

  const chochList = allStructs.filter((s) => str(s.category) === "choch")
  for (const choch of chochList.slice(-4)) {
    const idx = num(choch.index)
    if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time)
    const y = toY(ohlcv[idx].high)
    if (x <= 0 || y <= 0) continue
    ctx.font = "6px monospace"
    ctx.fillStyle = "#a855f7"
    ctx.fillText("CHoCH", x + 2, y - 3)
  }

  const liqLevels = allStructs.filter((s) => str(s.category) === "liquidity")
  for (const liq of liqLevels.slice(0, 5)) {
    const p = num(liq.price)
    if (p <= 0) continue
    const y = toY(p)
    if (y <= 0) continue
    const isAbove = str(liq.type).includes("above")
    ctx.strokeStyle = isAbove ? "rgba(239,68,68,0.3)" : "rgba(34,197,94,0.3)"
    ctx.lineWidth = 0.5
    ctx.setLineDash([3, 3])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
    ctx.setLineDash([])
    ctx.font = "6px monospace"
    ctx.fillStyle = isAbove ? "rgba(239,68,68,0.5)" : "rgba(34,197,94,0.5)"
    ctx.fillText(`Likvidite ${isAbove ? "↑" : "↓"} $${p.toFixed(2)}`, 2, y - 2)
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
    const p = num(sr[l.key])
    if (p <= 0) continue
    const y = toY(p)
    if (y <= 0) continue
    ctx.strokeStyle = l.color
    ctx.lineWidth = 0.5
    ctx.setLineDash(l.key.startsWith("strongest") ? [4, 4] : [2, 2])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
    ctx.setLineDash([])
    ctx.font = "7px monospace"
    ctx.fillStyle = l.color
    ctx.fillText(`${l.label} $${p.toFixed(2)}`, w - 80, y - 2)
  }
}

function drawPatterns(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, patterns: Record<string, unknown>[] | undefined, ohlcv: Candle[], w: number) {
  if (!patterns || ohlcv.length === 0) return
  let yOff = 20
  for (const pat of patterns.slice(0, 4)) {
    const name = str(pat.name)
    const tf = str(pat.timeframe)
    const status = str(pat.status)
    const prob = num(pat.probability)
    const bLevel = num(pat.breakout_level) || num(pat.breakdown_level)
    const mTarget = num(pat.measured_target)
    const statusMap: Record<string, string> = { CONFIRMED: "TƏSDİQLƏNDİ", DETECTED: "AŞKAR EDİLDİ", FORMING: "FORMALAŞIR" }
    ctx.font = "7px monospace"
    ctx.fillStyle = status === "CONFIRMED" ? "#22c55e" : status === "DETECTED" ? "#f59e0b" : "#6b7280"
    ctx.fillText(`${name} [${tf}] ${statusMap[status] || status} ${prob}%`, 10, yOff + 10)
    if (bLevel > 0 && mTarget > 0) {
      const y1 = toY(bLevel); const y2 = toY(mTarget)
      if (y1 > 0 && y2 > 0) {
        ctx.strokeStyle = status === "CONFIRMED" ? "rgba(34,197,94,0.3)" : "rgba(245,158,11,0.3)"
        ctx.lineWidth = 0.5
        ctx.setLineDash([3, 3])
        ctx.beginPath(); ctx.moveTo(w - 40, y1); ctx.lineTo(w - 40, y2); ctx.stroke()
        ctx.setLineDash([])
        ctx.font = "6px monospace"
        ctx.fillStyle = status === "CONFIRMED" ? "rgba(34,197,94,0.5)" : "rgba(245,158,11,0.5)"
        ctx.fillText(`→$${mTarget.toFixed(1)}`, w - 38, (y1 + y2) / 2)
      }
    }
    yOff += 14
  }
}

function drawScenarios(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, scenarios: Record<string, unknown> | undefined, price: number, w: number, h: number) {
  if (!scenarios) return
  const main = scenarios.main_scenario as Record<string, unknown> | undefined
  const alt = scenarios.alternative_scenario as Record<string, unknown> | undefined
  const risk = scenarios.risk_fakeout_scenario as Record<string, unknown> | undefined

  if (main) {
    const dir = str(main.direction)
    const prob = num(main.probability)
    const isLong = dir === "LONG"
    const color = isLong ? "#22c55e" : "#ef4444"
    const startY = h / 2
    const endY = isLong ? h * 0.15 : h * 0.85
    ctx.strokeStyle = color
    ctx.lineWidth = 3
    ctx.beginPath()
    ctx.moveTo(w - 120, startY)
    ctx.lineTo(w - 120, endY)
    ctx.stroke()
    ctx.fillStyle = color
    ctx.beginPath()
    const headSize = 12
    if (isLong) {
      ctx.moveTo(w - 120, endY - headSize)
      ctx.lineTo(w - 120 - headSize / 2, endY)
      ctx.lineTo(w - 120 + headSize / 2, endY)
    } else {
      ctx.moveTo(w - 120, endY + headSize)
      ctx.lineTo(w - 120 - headSize / 2, endY)
      ctx.lineTo(w - 120 + headSize / 2, endY)
    }
    ctx.fill()
    ctx.font = "bold 9px monospace"
    ctx.fillStyle = color
    ctx.textAlign = "center"
    ctx.fillText(`ƏSAS ${dir} ${prob}%`, w - 120, endY + (isLong ? -14 : 18))
    ctx.textAlign = "left"
  }

  if (alt) {
    const dir = str(alt.direction)
    const prob = num(alt.probability)
    const isLong = dir === "LONG"
    const color = isLong ? "rgba(34,197,94,0.5)" : "rgba(239,68,68,0.5)"
    const y = isLong ? h * 0.12 : h * 0.88
    ctx.font = "7px monospace"
    ctx.fillStyle = color
    ctx.fillText(`Alt: ${dir} ${prob}%`, w - 120, y)
  }

  if (risk) {
    ctx.font = "7px monospace"
    ctx.fillStyle = "rgba(250,204,21,0.6)"
    ctx.fillText(`Risk: ${str(risk.direction)} ${num(risk.probability)}%`, w - 120, h - 10)
  }
}

function drawTradeLevels(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, triggers: Record<string, unknown>, scores: Record<string, unknown>, w: number) {
  const confidence = num(scores.signal_confidence)
  const ltPrice = num(triggers.long_trigger_price)
  const stPrice = num(triggers.short_trigger_price)
  const inval = num(triggers.bullish_invalidation) || num(triggers.bearish_invalidation)

  if (ltPrice > 0) {
    const y = toY(ltPrice)
    if (y > 0) {
      ctx.strokeStyle = confidence >= 70 ? "rgba(34,197,94,0.6)" : "rgba(34,197,94,0.2)"
      ctx.lineWidth = confidence >= 70 ? 1.5 : 0.5
      ctx.setLineDash(confidence >= 70 ? [] : [4, 4])
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
      ctx.setLineDash([])
      ctx.font = "7px monospace"
      ctx.fillStyle = confidence >= 70 ? "#22c55e" : "rgba(34,197,94,0.4)"
      ctx.fillText(`ALIŞ $${ltPrice.toFixed(2)}`, 2, y - 2)
    }
  }

  if (stPrice > 0) {
    const y = toY(stPrice)
    if (y > 0) {
      ctx.strokeStyle = confidence >= 70 ? "rgba(239,68,68,0.6)" : "rgba(239,68,68,0.2)"
      ctx.lineWidth = confidence >= 70 ? 1.5 : 0.5
      ctx.setLineDash(confidence >= 70 ? [] : [4, 4])
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
      ctx.setLineDash([])
      ctx.font = "7px monospace"
      ctx.fillStyle = confidence >= 70 ? "#ef4444" : "rgba(239,68,68,0.4)"
      ctx.fillText(`SATIŞ $${stPrice.toFixed(2)}`, 2, y - 2)
    }
  }

  if (inval > 0) {
    const y = toY(inval)
    if (y > 0) {
      ctx.strokeStyle = "rgba(168,85,247,0.4)"
      ctx.lineWidth = 0.5
      ctx.setLineDash([3, 3])
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
      ctx.setLineDash([])
      ctx.font = "6px monospace"
      ctx.fillStyle = "rgba(168,85,247,0.5)"
      ctx.fillText(`Ləğv $${inval.toFixed(2)}`, 2, y - 2)
    }
  }
}

function drawProjection(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, projection: Candle[], ohlcv: Candle[]) {
  if (!projection.length || !ohlcv.length) return
  for (let i = 0; i < projection.length; i++) {
    const p = projection[i]
    const x = toX(p.time)
    const o = toY(p.open); const c = toY(p.close)
    const h = toY(p.high); const l = toY(p.low)
    if (x <= 0 || o <= 0 || c <= 0) continue
    ctx.strokeStyle = "rgba(255,255,255,0.15)"
    ctx.lineWidth = 0.5
    ctx.setLineDash([2, 2])
    ctx.beginPath(); ctx.moveTo(x, h); ctx.lineTo(x, l); ctx.stroke()
    ctx.setLineDash([])
    const bodyTop = Math.min(o, c); const bodyBot = Math.max(o, c)
    ctx.strokeStyle = p.close >= p.open ? "rgba(34,197,94,0.25)" : "rgba(239,68,68,0.25)"
    ctx.lineWidth = 0.5
    ctx.strokeRect(x - 3, bodyTop, 6, bodyBot - bodyTop)
  }
}

function drawCone(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, projection: Candle[], confidence: number, w: number, h: number, ohlcv: Candle[]) {
  if (confidence < 30 || ohlcv.length === 0) return
  const lastPrice = ohlcv[ohlcv.length - 1].close
  const spread = (1 - confidence / 100) * 0.15 * lastPrice
  const steps = 20
  const startX = toX(ohlcv[ohlcv.length - 1].time)
  if (startX <= 0) return
  const sliceW = (w - startX) / steps
  ctx.beginPath()
  ctx.moveTo(startX, toY(lastPrice + spread))
  for (let i = 1; i <= steps; i++) {
    const ratio = i / steps
    const coneSpread = spread * (0.5 + ratio * 2)
    const x = startX + sliceW * i
    ctx.lineTo(x, toY(lastPrice + coneSpread))
  }
  for (let i = steps; i >= 0; i--) {
    const ratio = i / steps
    const coneSpread = spread * (0.5 + ratio * 2)
    const x = startX + sliceW * i
    ctx.lineTo(x, toY(lastPrice - coneSpread))
  }
  ctx.closePath()
  ctx.fillStyle = `rgba(168,85,247,${Math.max(0.03, (confidence / 100) * 0.08)})`
  ctx.fill()
  ctx.strokeStyle = "rgba(168,85,247,0.1)"
  ctx.lineWidth = 0.5
  ctx.stroke()
}

function drawVolumeProfile(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, ohlcv: Candle[], w: number, h: number) {
  if (ohlcv.length < 50) return
  const priceRange = Math.max(...ohlcv.map(d => d.high)) - Math.min(...ohlcv.map(d => d.low))
  if (priceRange <= 0) return
  const buckets = 30
  const bucketSize = priceRange / buckets
  const minPrice = Math.min(...ohlcv.map(d => d.low))
  const volBuckets = new Array(buckets).fill(0)
  for (const d of ohlcv) {
    const idx = Math.min(buckets - 1, Math.max(0, Math.floor((d.close - minPrice) / bucketSize)))
    volBuckets[idx] += d.volume
  }
  const maxVol = Math.max(...volBuckets)
  if (maxVol <= 0) return
  for (let i = 0; i < buckets; i++) {
    const y = toY(minPrice + bucketSize * (i + 0.5))
    if (y <= 0) continue
    const barW = (volBuckets[i] / maxVol) * 40
    ctx.fillStyle = volBuckets[i] >= maxVol * 0.7 ? "rgba(245,158,11,0.2)" :
      volBuckets[i] >= maxVol * 0.3 ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.03)"
    ctx.fillRect(w - barW, y - bucketSize * 100 / 2, barW, Math.max(1, 2))
  }
  const pocIdx = volBuckets.indexOf(maxVol)
  const pocPrice = minPrice + bucketSize * (pocIdx + 0.5)
  const pocY = toY(pocPrice)
  if (pocY > 0) {
    ctx.font = "6px monospace"
    ctx.fillStyle = "rgba(245,158,11,0.5)"
    ctx.textAlign = "right"
    ctx.fillText(`POC $${pocPrice.toFixed(2)}`, w, pocY - 2)
    ctx.textAlign = "left"
  }
}

function drawSmartMoney(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, analysis: Record<string, unknown> | null, ohlcv: Candle[]) {
  if (!analysis || ohlcv.length < 30) return
  const allStructs = analysis.all_structures as Record<string, unknown>[] | undefined
  if (!allStructs) return
  let bullishCount = 0; let bearishCount = 0
  for (const s of allStructs) {
    const cat = str(s.category)
    if (cat === "order_block" && str(s.type).includes("bullish")) bullishCount++
    if (cat === "order_block" && str(s.type).includes("bearish")) bearishCount++
  }
  if (bullishCount > bearishCount * 1.5) {
    ctx.font = "7px monospace"
    ctx.fillStyle = "rgba(34,197,94,0.3)"
    ctx.fillText("Yığım Zonası (Accumulation)", 10, 50)
  } else if (bearishCount > bullishCount * 1.5) {
    ctx.font = "7px monospace"
    ctx.fillStyle = "rgba(239,68,68,0.3)"
    ctx.fillText("Paylanma Zonası (Distribution)", 10, 50)
  }
}

function drawElliottWave(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, ew: Record<string, unknown> | undefined, w: number, ohlcv: Candle[]) {
  if (!ew || ew.status === "insufficient_data" || ohlcv.length === 0) return
  const waves = ew.waves as { type: string; start: number; end: number; index: number }[] | undefined
  if (!waves || waves.length < 3) return
  ctx.font = "bold 8px monospace"
  for (let i = 0; i < Math.min(waves.length, 8); i++) {
    const wave = waves[i]
    const idx = wave.index
    if (idx <= 0 || idx >= ohlcv.length) continue
    const x = toX(ohlcv[idx].time)
    if (x <= 0) continue
    const numLabels = ["1", "2", "3", "4", "5", "A", "B", "C"]
    const label = numLabels[i] || String(i + 1)
    const isUp = wave.type === "wave_up"
    const y = toY(isUp ? wave.end : wave.start)
    if (y <= 0) continue
    ctx.fillStyle = isUp ? "#22c55e" : "#ef4444"
    const sz = 4
    ctx.beginPath()
    if (isUp) {
      ctx.moveTo(x, y - sz); ctx.lineTo(x - sz, y); ctx.lineTo(x + sz, y)
    } else {
      ctx.moveTo(x, y + sz); ctx.lineTo(x - sz, y); ctx.lineTo(x + sz, y)
    }
    ctx.fill()
    ctx.fillStyle = isUp ? "rgba(34,197,94,0.8)" : "rgba(239,68,68,0.8)"
    ctx.fillText(label, x + sz + 2, y + 3)
  }
  const desc = str(ew.description_az)
  if (desc) {
    ctx.font = "7px monospace"
    ctx.fillStyle = "rgba(168,85,247,0.6)"
    ctx.fillText(`Elliott: ${desc}`, 10, 80)
  }
}

function drawFibonacci(ctx: CanvasRenderingContext2D, toX: (t: number) => number, toY: (p: number) => number, fib: Record<string, unknown> | undefined, w: number, ohlcv: Candle[]) {
  if (!fib || fib.status !== "calculated" || ohlcv.length === 0) return
  const levels = fib.retracement_levels as Record<string, number> | undefined
  if (!levels) return
  const high = num(fib.high)
  const low = num(fib.low)
  if (high <= 0 || low <= 0) return

  const keyLevels = ["0", "0.236", "0.382", "0.5", "0.618", "0.786", "1"]
  const fibColors: Record<string, string> = {
    "0": "rgba(255,255,255,0.15)", "0.236": "rgba(34,197,94,0.2)",
    "0.382": "rgba(34,197,94,0.3)", "0.5": "rgba(245,158,11,0.3)",
    "0.618": "rgba(239,68,68,0.3)", "0.786": "rgba(239,68,68,0.2)",
    "1": "rgba(255,255,255,0.15)",
  }

  for (const k of keyLevels) {
    const p = levels[k]
    if (!p) continue
    const y = toY(p)
    if (y <= 0) continue
    ctx.strokeStyle = fibColors[k] || "rgba(255,255,255,0.1)"
    ctx.lineWidth = 0.5
    ctx.setLineDash(k === "0.5" ? [4, 4] : [2, 4])
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
    ctx.setLineDash([])
    ctx.font = "6px monospace"
    ctx.fillStyle = fibColors[k] || "rgba(255,255,255,0.2)"
    ctx.fillText(`Fib ${k} $${p.toFixed(2)}`, w - 90, y - 2)
  }
}
