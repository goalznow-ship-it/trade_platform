"use client"

import { useEffect, useRef, useState } from "react"
import {
  createChart, ColorType, CrosshairMode, LineStyle,
  CandlestickSeries, HistogramSeries, createSeriesMarkers,
  type IChartApi, type ISeriesApi, type Time, type SeriesMarker,
} from "lightweight-charts"
import { api } from "@/lib/api"
import { useWebSocket } from "@/hooks/useWebSocket"
import { useMarketStore } from "@/store/market"
import {
  TrendingUp, Minus, Maximize2, Crosshair, MousePointer,
  Undo2, Redo2, Trash2, Move, Ruler, CircleDot,
  RectangleHorizontal, RotateCcw, ArrowUpFromLine,
} from "lucide-react"
import { cn } from "@/lib/utils"

const TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1H", "2H", "4H", "6H", "12H", "1D", "1W", "1M"]

const DRAWING_TOOLS = [
  { id: "trend", icon: TrendingUp, label: "Trend Line" },
  { id: "horizontal", icon: Minus, label: "Horizontal Line" },
  { id: "vertical", icon: RotateCcw, label: "Vertical Line" },
  { id: "arrow", icon: ArrowUpFromLine, label: "Arrow" },
  { id: "ray", icon: Ruler, label: "Ray" },
  { id: "rect", icon: RectangleHorizontal, label: "Rectangle" },
  { id: "circle", icon: CircleDot, label: "Circle" },
  { id: "fib", icon: Crosshair, label: "Fibonacci" },
  { id: "risk", icon: Move, label: "Risk/Reward" },
]

interface CandleData {
  time: Time
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export function TradingChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null)
  const { selectedSymbol, selectedTimeframe, setTimeframe } = useMarketStore()
  const { isConnected } = useWebSocket(selectedSymbol)
  const [candleData, setCandleData] = useState<CandleData[]>([])
  const [activeTool, setActiveTool] = useState<string | null>(null)
  const [showDrawingTools, setShowDrawingTools] = useState(false)
  const [showIndicators, setShowIndicators] = useState(false)
  const latestCandle = candleData[candleData.length - 1]
  const candleDirection = !latestCandle
    ? "neutral"
    : latestCandle.close > latestCandle.open
      ? "bullish"
      : latestCandle.close < latestCandle.open ? "bearish" : "neutral"

  useEffect(() => {
    let cancelled = false
    async function loadChartData() {
      try {
        const data = await api.getOHLCV(selectedSymbol, selectedTimeframe, 300)
        if (Array.isArray(data) && !cancelled) {
          setCandleData(data.map((d: { time: number; open: number; high: number; low: number; close: number; volume: number }) => ({
            time: d.time as Time,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
            volume: d.volume,
          })))
        }
      } catch {}
    }
    loadChartData()
    return () => { cancelled = true }
  }, [selectedSymbol, selectedTimeframe])

  useEffect(() => {
    if (!containerRef.current || !candleData.length) return
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
    }

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0d1117" },
        textColor: "#9ca3af",
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
      rightPriceScale: { borderColor: "#1f2937" },
      timeScale: {
        borderColor: "#1f2937",
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 12,
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
    const latest = candleData[candleData.length - 1]
    if (latest) {
      const bullish = latest.close >= latest.open
      const markers: SeriesMarker<Time>[] = [{
        time: latest.time,
        position: bullish ? "belowBar" : "aboveBar",
        color: bullish ? "#4ade80" : "#f87171",
        shape: bullish ? "arrowUp" : "arrowDown",
        text: bullish ? "ŞAM ↑" : "ŞAM ↓",
      }]
      createSeriesMarkers(candleSeriesRef.current, markers)
    }

    volumeSeriesRef.current = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
      priceLineVisible: false,
    })
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })
    volumeSeriesRef.current.setData(
      candleData.map((d) => ({
        time: d.time,
        value: d.volume,
        color: d.close >= d.open ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)",
      }))
    )

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
      volumeSeriesRef.current = null
    }
  }, [candleData])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-1">
          <span className={cn(
            "mr-2 px-2 py-1 rounded border text-[10px] font-bold font-mono",
            candleDirection === "bullish"
              ? "text-green-300 bg-green-950/60 border-green-700/60"
              : candleDirection === "bearish"
                ? "text-red-300 bg-red-950/60 border-red-700/60"
                : "text-gray-300 bg-gray-800 border-gray-700"
          )}>
            {candleDirection === "bullish" ? "↑ BULLISH" : candleDirection === "bearish" ? "↓ BEARISH" : "→ NEUTRAL"}
          </span>
          <button
            onClick={() => setShowDrawingTools(!showDrawingTools)}
            className={cn("p-1.5 rounded text-gray-500 hover:text-gray-300 hover:bg-gray-800", showDrawingTools && "text-blue-400 bg-blue-600/20")}
            title="Drawing Tools"
          >
            <MousePointer className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowIndicators(!showIndicators)}
            className="p-1.5 rounded text-gray-500 hover:text-gray-300 hover:bg-gray-800"
            title="Indicators"
          >
            <TrendingUp className="w-4 h-4" />
          </button>
          <div className="w-px h-5 bg-gray-700 mx-1" />
          <button className="p-1.5 rounded text-gray-500 hover:text-gray-300 hover:bg-gray-800" title="Undo">
            <Undo2 className="w-4 h-4" />
          </button>
          <button className="p-1.5 rounded text-gray-500 hover:text-gray-300 hover:bg-gray-800" title="Redo">
            <Redo2 className="w-4 h-4" />
          </button>
          <button className="p-1.5 rounded text-gray-500 hover:text-gray-300 hover:bg-gray-800" title="Delete">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center gap-1 overflow-x-auto">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={cn(
                "px-2 py-1 text-xs rounded font-medium transition-colors whitespace-nowrap",
                selectedTimeframe === tf
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              )}
            >
              {tf}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-xs">
            <div className={cn("w-2 h-2 rounded-full", isConnected ? "bg-green-400" : "bg-red-400")} />
            <span className="text-gray-500">{isConnected ? "Live" : "Offline"}</span>
          </div>
          <button className="p-1.5 rounded text-gray-500 hover:text-gray-300" title="Fullscreen">
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {showDrawingTools && (
        <div className="flex items-center gap-0.5 px-3 py-1.5 bg-gray-900 border-b border-gray-800 overflow-x-auto">
          {DRAWING_TOOLS.map((tool) => (
            <button
              key={tool.id}
              onClick={() => setActiveTool(activeTool === tool.id ? null : tool.id)}
              className={cn(
                "p-1.5 rounded text-xs flex flex-col items-center gap-0.5 min-w-[48px]",
                activeTool === tool.id
                  ? "bg-blue-600/30 text-blue-400"
                  : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"
              )}
              title={tool.label}
            >
              <tool.icon className="w-4 h-4" />
              <span className="text-[10px] leading-none">{tool.label.split(" ")[0]}</span>
            </button>
          ))}
        </div>
      )}

      <div ref={containerRef} className="flex-1 min-h-0" />

      {showIndicators && (
        <div className="absolute left-48 top-24 bg-gray-900 border border-gray-700 rounded-lg shadow-xl p-3 w-48 z-10">
          <div className="text-xs font-medium text-gray-400 mb-2">Indicators</div>
          {["EMA 9", "EMA 21", "SMA 20", "SMA 50", "SMA 200", "VWAP", "RSI", "MACD", "Bollinger", "Ichimoku", "Supertrend"].map((ind) => (
            <label key={ind} className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-800 rounded cursor-pointer">
              <input type="checkbox" className="rounded border-gray-600" />
              <span className="text-xs text-gray-300">{ind}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}
