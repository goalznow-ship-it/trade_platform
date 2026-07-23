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
}

export function AIChart({ analysis, explain, signal, livePrice }: AIChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const { selectedSymbol, selectedTimeframe, setSymbol, setTimeframe } = useMarketStore()
  const [candleData, setCandleData] = useState<OHLCVItem[]>([])
  // state setter only — loading value not used in render
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [loading, setLoading] = useState(true)
  const [price, setPrice] = useState<string>("")

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
    if (lastCandle && signal && !signal.error && candleSeriesRef.current) {
      const isBullish = signal.direction === "long"
      const lastTime = lastCandle.time
      const levels = [
        { price: signal.entry_zone?.min, title: "ENTRY LOW", color: "#3b82f6", style: LineStyle.Dashed },
        { price: signal.entry_zone?.max, title: "ENTRY HIGH", color: "#60a5fa", style: LineStyle.Dashed },
        { price: signal.stop_loss, title: "STOP LOSS", color: "#ef4444", style: LineStyle.Solid },
        { price: signal.take_profit_1, title: "TP1", color: "#22c55e", style: LineStyle.Solid },
        { price: signal.take_profit_2, title: "TP2", color: "#16a34a", style: LineStyle.Dashed },
        { price: signal.take_profit_3, title: "TP3", color: "#15803d", style: LineStyle.Dotted },
      ]
      levels.forEach((level) => {
        if (level.price && level.price > 0) {
          candleSeriesRef.current?.createPriceLine({
            price: level.price,
            color: level.color,
            lineWidth: level.title === "STOP LOSS" || level.title === "TP1" ? 2 : 1,
            lineStyle: level.style,
            axisLabelVisible: true,
            title: level.title,
          })
        }
      })
      const markers: SeriesMarker<Time>[] = [{
        time: lastTime,
        position: isBullish ? "belowBar" : "aboveBar",
        color: isBullish ? "#22c55e" : "#ef4444",
        shape: isBullish ? "arrowUp" : "arrowDown",
        text: `${isBullish ? "LONG" : "SHORT"} ${signal.confidence || 0}%`,
      }]
      createSeriesMarkers(candleSeriesRef.current, markers)
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
  }, [candleData, signal])

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
          {(analysis?.details?.rsi) && (
            <div className="hidden sm:flex items-center gap-1.5 text-[10px]">
              <span className={cn("px-1.5 py-0.5 rounded font-mono", (analysis.details.rsi || 0) > 70 ? "bg-red-900/50 text-red-400" : (analysis.details.rsi || 0) < 30 ? "bg-green-900/50 text-green-400" : "bg-gray-800 text-gray-400")}>
                RSI: {analysis.details.rsi?.toFixed(0)}
              </span>
              <span className={cn("px-1.5 py-0.5 rounded font-mono", (analysis.details.macd || 0) > 0 ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400")}>
                MACD: {analysis.details.macd?.toFixed(1)}
              </span>
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

      {/* Institutional signal levels sourced from the backend engine */}
      {analysis && (
        <div className="flex items-center gap-4 px-3 py-1 bg-gray-900/80 border-b border-gray-800 text-[10px]">
          <span className="text-gray-400">Real Binance OHLCV</span>
          {signal && !signal.error && (
            <span className={signal.execution?.approved ? "text-green-400" : "text-amber-400"}>
              {signal.execution?.approved ? "Trade eligible" : "Validation required"}
            </span>
          )}
          {signal && !signal.error && signal.confidence !== undefined && signal.confidence >= 70 && (
            <>
              <div className="flex items-center gap-1">
                <span className="text-green-400 font-medium">Entry</span>
                <span className="text-white font-mono">
                  {signal.entry_zone?.mid ? `$${signal.entry_zone.mid.toFixed(2)}` : "N/A"}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-red-400 font-medium">SL</span>
                <span className="text-red-400 font-mono">
                  {signal.stop_loss ? `$${signal.stop_loss.toFixed(2)}` : "N/A"}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-green-400 font-medium">TP</span>
                <span className="text-green-400 font-mono">
                  {signal.take_profit_1 ? `$${signal.take_profit_1.toFixed(2)}` : "N/A"}
                </span>
              </div>
            </>
          )}
          <div className="flex-1" />
          <div className={cn("font-medium",
            analysis.prediction === "long" ? "text-green-400" : analysis.prediction === "short" ? "text-red-400" : "text-yellow-400"
          )}>
            {analysis.prediction?.toUpperCase() || "NEUTRAL"} · {analysis.confidence || 0}%
          </div>
        </div>
      )}

      {/* Chart */}
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  )
}
