"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import { api } from "@/lib/api"
import { useMarketStore } from "@/store/market"
import { cn } from "@/lib/utils"
import {
  createChart, ColorType, CrosshairMode, LineStyle,
  CandlestickSeries, createSeriesMarkers,
  type IChartApi, type ISeriesApi, type Time, type SeriesMarker,
} from "lightweight-charts"

const TIMEFRAMES = [
  { id: "5m", label: "5m" },
  { id: "15m", label: "15m" },
  { id: "1h", label: "1H" },
  { id: "4h", label: "4H" },
  { id: "1d", label: "1D" },
  { id: "1w", label: "1W" },
]

const PATTERN_LABELS: Record<string, { az: string; color: string; icon: string }> = {
  "Doji": { az: "Doji", color: "#f59e0b", icon: "◆" },
  "Hammer": { az: "Çəkic", color: "#22c55e", icon: "🔨" },
  "Shooting Star": { az: "Axan Ulduz", color: "#ef4444", icon: "⭐" },
  "Bullish Engulfing": { az: "Yüksələn Uduş", color: "#22c55e", icon: "⬆" },
  "Bearish Engulfing": { az: "Enən Uduş", color: "#ef4444", icon: "⬇" },
  "Morning Star": { az: "Səhər Ulduzu", color: "#22c55e", icon: "🌟" },
  "Evening Star": { az: "Axşam Ulduzu", color: "#ef4444", icon: "🌆" },
  "Marubozu": { az: "Marubozu", color: "#a855f7", icon: "▮" },
  "Dragonfly Doji": { az: "İynəcə Doji", color: "#22c55e", icon: "⟂" },
  "Piercing Line": { az: "Deşici Xətt", color: "#22c55e", icon: "↗" },
  "Dark Cloud Cover": { az: "Qara Bulud", color: "#ef4444", icon: "↘" },
  "Volume Climax": { az: "Həcm Piki", color: "#f59e0b", icon: "📊" },
  "Three Black Crows": { az: "Üç Qara Qarğa", color: "#ef4444", icon: "▼" },
  "Three White Soldiers": { az: "Üç Ağ Əsgər", color: "#22c55e", icon: "▲" },
}

interface RawOHLCVItem {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface OHLCVItem {
  time: Time
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface AnalysisDetails {
  rsi?: number
  macd?: number
  support?: number
  resistance?: number
  [key: string]: unknown
}

interface AnalysisData {
  prediction?: string
  confidence?: number
  long_probability?: number
  short_probability?: number
  risk_level?: string
  scores?: Record<string, number>
  details?: AnalysisDetails
  summary?: string
  current_price?: number
  [key: string]: unknown
}

interface ExplainSuggestions {
  entry?: number
  stop_loss?: number
  take_profit?: number
  suggested_leverage?: number
  position_size?: number
  [key: string]: unknown
}

interface ExplainKeyLevels {
  support?: number
  resistance?: number
  [key: string]: unknown
}

interface ExplainData {
  reasons?: string[]
  warnings?: string[]
  suggestions?: ExplainSuggestions
  key_levels?: ExplainKeyLevels
  [key: string]: unknown
}

interface AIChartProps {
  analysis?: AnalysisData | null
  explain?: ExplainData | null
  signal?: {
    error?: string
    direction?: string
    confidence?: number
    entry_zone?: { min?: number; max?: number; mid?: number }
    stop_loss?: number
    take_profit_1?: number
    take_profit_2?: number
    take_profit_3?: number
    execution?: { approved?: boolean }
  } | null
  livePrice?: number
  aiAnalysis?: {
    confidence?: number
    direction?: string
    combined_direction?: string
    components?: {
      candlestick_patterns?: {
        patterns?: Array<{ name: string; type: string; signal: string; price: number; strength: string }>
        pattern_direction?: string
        pattern_score?: number
        total_count?: number
      }
      fibonacci?: {
        retracements?: Array<{ level: number; price: number }>
        all_levels?: Array<{ level: number; price: number; type: string }>
        golden_zone?: { low: number; high: number }
        nearest_bullish_target?: { level: number; price: number }
        nearest_bearish_target?: { level: number; price: number }
      }
      elliott_wave?: {
        count?: string
        waves?: Array<{ name: string; type: string; description: string }>
        current_phase?: string
      }
      liquidity_zones?: {
        zones?: Array<{ type: string; price?: number; price_low?: number; price_high?: number; source: string; strength: string }>
        nearest_support?: number
        nearest_resistance?: number
      }
      trend_lines?: {
        support_lines?: Array<Record<string, unknown>>
        resistance_lines?: Array<Record<string, unknown>>
      }
    }
  } | null
}

export function AIChart({ analysis, explain, signal, livePrice, aiAnalysis }: AIChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const { selectedSymbol, selectedTimeframe, setSymbol, setTimeframe } = useMarketStore()
  const [candleData, setCandleData] = useState<OHLCVItem[]>([])
  const [loading, setLoading] = useState(true)
  const [price, setPrice] = useState<string>("")
  const latestCandle = candleData[candleData.length - 1]
  const candleDirection = !latestCandle
    ? "neutral"
    : latestCandle.close > latestCandle.open
      ? "bullish"
      : latestCandle.close < latestCandle.open ? "bearish" : "neutral"

  const loadChartData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getOHLCV(selectedSymbol, selectedTimeframe, 200)
      if (Array.isArray(data)) {
        const formatted = (data as RawOHLCVItem[]).map((d: RawOHLCVItem) => ({
          time: (d.time as number) as Time,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
          volume: d.volume,
        }))
        setCandleData(formatted)
        if (formatted.length > 0) {
          setPrice(formatted[formatted.length - 1].close.toFixed(2))
        }
      }
    } catch {} finally {
      setLoading(false)
    }
  }, [selectedSymbol, selectedTimeframe])

  useEffect(() => { queueMicrotask(() => loadChartData()) }, [loadChartData])

  useEffect(() => {
    if (!containerRef.current || !candleData.length) return

    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
      candleSeriesRef.current = null
    }

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0d1117" },
        textColor: "#9ca3af",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: "#1f2937" },
        horzLines: { color: "#1f2937" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#3b82f6", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#3b82f6" },
        horzLine: { color: "#3b82f6", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#3b82f6" },
      },
      rightPriceScale: { borderColor: "#1f2937", scaleMargins: { top: 0.05, bottom: 0.1 } },
      timeScale: {
        borderColor: "#1f2937",
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 15,
      },
      handleScroll: { vertTouchDrag: false },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    })

    candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderDownColor: "#ef4444",
      borderUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      wickUpColor: "#22c55e",
    })
    candleSeriesRef.current.setData(candleData)

    const lastCandle = candleData[candleData.length - 1]
    if (lastCandle && candleSeriesRef.current) {
      const candleBullish = lastCandle.close >= lastCandle.open
      createSeriesMarkers(candleSeriesRef.current, [{
        time: lastCandle.time,
        position: candleBullish ? "belowBar" : "aboveBar",
        color: candleBullish ? "#4ade80" : "#f87171",
        shape: candleBullish ? "arrowUp" : "arrowDown",
        text: candleBullish ? "ŞAM ↑" : "ŞAM ↓",
      }])
    }

    // Pattern markers
    const patterns = aiAnalysis?.components?.candlestick_patterns?.patterns || []
    const patternMarkers: SeriesMarker<Time>[] = []
    for (const p of patterns) {
      const idx = candleData.length - 1 + (p as unknown as Record<string, number>).index
      if (idx >= 0 && idx < candleData.length) {
        const pl = PATTERN_LABELS[p.name]
        patternMarkers.push({
          time: candleData[idx].time,
          position: p.type === "bullish" ? "belowBar" : p.type === "bearish" ? "aboveBar" : "aboveBar",
          color: pl?.color || "#9ca3af",
          shape: p.type === "bullish" ? "arrowUp" : "arrowDown" as "arrowUp" | "arrowDown",
          text: pl?.az || p.name,
        })
      }
    }
    if (patternMarkers.length > 0 && candleSeriesRef.current) {
      createSeriesMarkers(candleSeriesRef.current, patternMarkers)
    }

    // Fibonacci levels
    const fib = aiAnalysis?.components?.fibonacci
    if (fib && candleSeriesRef.current) {
      const fibLevels = fib.retracements || []
      for (const lvl of fibLevels) {
        if (lvl.price > 0) {
          candleSeriesRef.current.createPriceLine({
            price: lvl.price,
            color: lvl.level === 0.618 ? "#a855f7" : "#6366f1",
            lineWidth: lvl.level === 0.618 || lvl.level === 0.382 ? 1 : 1,
            lineStyle: LineStyle.Dotted,
            axisLabelVisible: true,
            title: `Fib ${(lvl.level * 100).toFixed(0)}%`,
          })
        }
      }
    }

    // Liquidity zones
    const liqZones = aiAnalysis?.components?.liquidity_zones
    if (liqZones && candleSeriesRef.current) {
      if (liqZones.nearest_support && liqZones.nearest_support > 0) {
        candleSeriesRef.current.createPriceLine({
          price: liqZones.nearest_support,
          color: "#22c55e",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: "Likvidlik Dəstək",
        })
      }
      if (liqZones.nearest_resistance && liqZones.nearest_resistance > 0) {
        candleSeriesRef.current.createPriceLine({
          price: liqZones.nearest_resistance,
          color: "#ef4444",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: "Likvidlik Müqavimət",
        })
      }
    }

    // Signal levels
    if (lastCandle && signal && !signal.error && signal.confidence !== undefined
        && signal.confidence >= 70 && candleSeriesRef.current) {
      const lastTime = lastCandle.time
      const levels = [
        { price: signal.entry_zone?.min, title: "GİRİŞ AŞAĞI", color: "#3b82f6", style: LineStyle.Dashed },
        { price: signal.entry_zone?.max, title: "GİRİŞ YUXARI", color: "#60a5fa", style: LineStyle.Dashed },
        { price: signal.stop_loss, title: "ZƏRƏR KƏS", color: "#ef4444", style: LineStyle.Solid },
        { price: signal.take_profit_1, title: "MH1", color: "#22c55e", style: LineStyle.Solid },
        { price: signal.take_profit_2, title: "MH2", color: "#16a34a", style: LineStyle.Dashed },
        { price: signal.take_profit_3, title: "MH3", color: "#15803d", style: LineStyle.Dotted },
      ]
      levels.forEach((level) => {
        if (level.price && level.price > 0) {
          candleSeriesRef.current?.createPriceLine({
            price: level.price,
            color: level.color,
            lineWidth: level.title === "ZƏRƏR KƏS" || level.title === "MH1" ? 2 : 1,
            lineStyle: level.style,
            axisLabelVisible: true,
            title: level.title,
          })
        }
      })
      if (aiAnalysis?.combined_direction) {
        const isBullish = aiAnalysis.combined_direction === "long"
        const finalConf = aiAnalysis.confidence || signal.confidence || 0
        const markers: SeriesMarker<Time>[] = [{
          time: lastTime,
          position: isBullish ? "belowBar" : "aboveBar",
          color: isBullish ? "#22c55e" : "#ef4444",
          shape: "circle" as const,
          text: `${isBullish ? "UZUN" : "QISA"} ${finalConf}%`,
        }]
        createSeriesMarkers(candleSeriesRef.current, markers)
      }
    }

    chartRef.current = chart

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth, height: containerRef.current.clientHeight })
      }
    }
    window.addEventListener("resize", handleResize)
    return () => {
      window.removeEventListener("resize", handleResize)
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
    }
  }, [candleData, signal, aiAnalysis])

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <select
            value={selectedSymbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
          >
            {["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "AVAX/USDT"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <div className="text-base font-bold text-white font-mono">
            {livePrice && livePrice > 0 ? `$${livePrice.toFixed(2)}` : price ? `$${price}` : "N/A"}
          </div>
          <div className={cn(
            "px-2 py-1 rounded border text-[10px] font-bold font-mono",
            candleDirection === "bullish"
              ? "text-green-300 bg-green-950/60 border-green-700/60"
              : candleDirection === "bearish"
                ? "text-red-300 bg-red-950/60 border-red-700/60"
                : "text-gray-300 bg-gray-800 border-gray-700"
          )}>
            {candleDirection === "bullish"
              ? "ŞAM ↑ YÜKSƏLİŞ"
              : candleDirection === "bearish"
                ? "ŞAM ↓ ENİŞ"
                : "ŞAM → NEYTRAL"}
          </div>
          {/* Pattern indicators */}
          {aiAnalysis?.components?.candlestick_patterns?.patterns && aiAnalysis.components.candlestick_patterns.patterns.length > 0 && (
            <div className="hidden md:flex items-center gap-1 text-[10px]">
              {aiAnalysis.components.candlestick_patterns.patterns.slice(0, 3).map((p, i) => {
                const pl = PATTERN_LABELS[p.name]
                return (
                  <span key={i} className="px-1.5 py-0.5 rounded font-mono" style={{
                    backgroundColor: (pl?.color || "#9ca3af") + "20",
                    color: pl?.color || "#9ca3af",
                  }}>
                    {pl?.az || p.name}
                  </span>
                )
              })}
            </div>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          {TIMEFRAMES.map((tf) => (
            <button key={tf.id} onClick={() => setTimeframe(tf.id)}
              className={cn(
                "px-2 py-1 text-[10px] rounded font-medium transition-colors",
                selectedTimeframe === tf.id
                  ? "bg-blue-600 text-white"
                  : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"
              )}>
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Info bar */}
      {(analysis || aiAnalysis) && (
        <div className="flex items-center gap-4 px-3 py-1 bg-gray-900/80 border-b border-gray-800 text-[10px]">
          <span className="text-gray-400">Real Binance OHLCV</span>
          {aiAnalysis?.components?.elliott_wave?.count && aiAnalysis.components.elliott_wave.count !== "unknown" && (
            <span className="text-purple-400">
              Elliott: {aiAnalysis.components.elliott_wave.count === "impulse" ? "İmpuls" : "Korrektiv"}
            </span>
          )}
          {aiAnalysis?.components?.candlestick_patterns && (
            <span className={cn(
              aiAnalysis.components.candlestick_patterns.pattern_direction === "long" ? "text-green-400" :
              aiAnalysis.components.candlestick_patterns.pattern_direction === "short" ? "text-red-400" : "text-yellow-400"
            )}>
              Naxış: {aiAnalysis.components.candlestick_patterns.pattern_direction === "long" ? "YÜKSƏLİŞ" :
                       aiAnalysis.components.candlestick_patterns.pattern_direction === "short" ? "ENİŞ" : "NEYTRAL"}
              ({aiAnalysis.components.candlestick_patterns.total_count})
            </span>
          )}
          {signal && !signal.error && (
            <span className={signal.execution?.approved ? "text-green-400" : "text-amber-400"}>
              {signal.execution?.approved ? "Ticarət uyğun" : "Doğrulama tələb olunur"}
            </span>
          )}
          <div className="flex-1" />
          <div className={cn("font-medium",
            (aiAnalysis?.combined_direction || analysis?.prediction) === "long" ? "text-green-400" :
            (aiAnalysis?.combined_direction || analysis?.prediction) === "short" ? "text-red-400" : "text-yellow-400"
          )}>
            {aiAnalysis?.combined_direction
              ? (aiAnalysis.combined_direction === "long" ? "UZUN" : aiAnalysis.combined_direction === "short" ? "QISA" : "NEYTRAL")
              : (analysis?.prediction?.toUpperCase() || "NEYTRAL")}
            {" · "}{aiAnalysis?.confidence || analysis?.confidence || 0}%
          </div>
        </div>
      )}

      {/* Chart */}
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  )
}
