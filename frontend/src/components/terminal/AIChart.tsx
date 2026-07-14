"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import { api } from "@/lib/api"
import { useMarketStore } from "@/store/market"
import { cn } from "@/lib/utils"
import {
  createChart, ColorType, CrosshairMode, LineStyle,
  CandlestickSeries,
  type IChartApi, type ISeriesApi, type Time,
} from "lightweight-charts"

const TIMEFRAMES = [
  { id: "5m", label: "5m" },
  { id: "15m", label: "15m" },
  { id: "1h", label: "1H" },
  { id: "4h", label: "4H" },
  { id: "1d", label: "1D" },
]

interface AIChartProps {
  analysis?: any
  explain?: any
}

export function AIChart({ analysis, explain }: AIChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const { selectedSymbol, selectedTimeframe, setSymbol, setTimeframe } = useMarketStore()
  const [candleData, setCandleData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [price, setPrice] = useState<string>("")

  const loadChartData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getOHLCV(selectedSymbol, selectedTimeframe, 200)
      if (Array.isArray(data)) {
        const formatted = data.map((d: any) => ({
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

  useEffect(() => { loadChartData() }, [loadChartData])

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
  }, [candleData])

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-900 border-b border-gray-800">
        {/* Symbol + Price */}
        <div className="flex items-center gap-3">
          <select
            value={selectedSymbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
          >
            {["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "AVAX/USDT"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <div className="text-lg font-bold text-white font-mono">${price || "--"}</div>
          {(analysis?.details?.rsi) && (
            <div className="hidden sm:flex items-center gap-2 text-xs">
              <span className={cn("px-1.5 py-0.5 rounded font-mono", (analysis.details.rsi || 0) > 70 ? "bg-red-900/50 text-red-400" : (analysis.details.rsi || 0) < 30 ? "bg-green-900/50 text-green-400" : "bg-gray-800 text-gray-400")}>
                RSI: {analysis.details.rsi?.toFixed(0)}
              </span>
              <span className={cn("px-1.5 py-0.5 rounded font-mono", (analysis.details.macd || 0) > 0 ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400")}>
                MACD: {analysis.details.macd?.toFixed(1)}
              </span>
            </div>
          )}
        </div>

        {/* Timeframes */}
        <div className="flex items-center gap-0.5">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.id}
              onClick={() => setTimeframe(tf.id)}
              className={cn(
                "px-2.5 py-1 text-xs rounded font-medium transition-colors",
                selectedTimeframe === tf.id
                  ? "bg-blue-600 text-white"
                  : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"
              )}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* AI Overlay Info - Entry / SL / TP */}
      {(explain?.suggestions?.stop_loss || analysis?.details?.support) && (
        <div className="flex items-center gap-3 px-3 py-1 bg-gray-900/80 border-b border-gray-800 text-[11px]">
          <div className="flex items-center gap-1">
            <span className="text-green-400 font-medium">Entry</span>
            <span className="text-white font-mono">${(analysis?.details?.support || 0).toFixed(2)}</span>
          </div>
          <div className="w-px h-3 bg-gray-700" />
          <div className="flex items-center gap-1">
            <span className="text-red-400 font-medium">SL</span>
            <span className="text-red-400 font-mono">${(explain?.suggestions?.stop_loss || 0).toFixed(2)}</span>
          </div>
          <div className="w-px h-3 bg-gray-700" />
          <div className="flex items-center gap-1">
            <span className="text-green-400 font-medium">TP</span>
            <span className="text-green-400 font-mono">${(explain?.suggestions?.take_profit || 0).toFixed(2)}</span>
          </div>
          <div className="w-px h-3 bg-gray-700" />
          <div className={cn("flex items-center gap-1 font-medium",
            analysis?.prediction === "long" ? "text-green-400" : analysis?.prediction === "short" ? "text-red-400" : "text-yellow-400"
          )}>
            {analysis?.prediction?.toUpperCase() || "NEUTRAL"} · {analysis?.confidence || 0}%
          </div>
        </div>
      )}

      {/* Chart */}
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  )
}
