"use client"

import { useEffect, useRef, useState } from "react"
import { createChart, ColorType, CandlestickSeries, HistogramSeries, type IChartApi, type ISeriesApi, type Time } from "lightweight-charts"
import { api } from "@/lib/api"

interface Props {
  symbol: string
  snapshot: Record<string, unknown> | null
  analysis: Record<string, unknown> | null
  triggers: Record<string, unknown>
  sr: Record<string, unknown>
}

interface Candle {
  time: number; open: number; high: number; low: number; close: number; volume: number
}

export function SKHYChart({ symbol, snapshot, analysis, triggers, sr }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const volSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null)
  const [ohlcv, setOhlcv] = useState<Candle[]>([])
  const [tf, setTf] = useState("1h")
  const timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

  useEffect(() => {
    api.getSkhyOHLCV(tf, 200).then((res) => {
      if (res?.data) setOhlcv(res.data)
    }).catch(() => {})
  }, [tf])

  useEffect(() => {
    if (!containerRef.current) return
    chartRef.current = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0d1117" },
        textColor: "#6b7280",
        fontSize: 11,
      },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#374151" },
      timeScale: { borderColor: "#374151", timeVisible: true, secondsVisible: false },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      autoSize: true,
    })

    candleSeriesRef.current = chartRef.current.addSeries(CandlestickSeries, {
      upColor: "#22c55e", downColor: "#ef4444",
      borderDownColor: "#ef4444", borderUpColor: "#22c55e",
      wickDownColor: "#ef4444", wickUpColor: "#22c55e",
    })

    volSeriesRef.current = chartRef.current.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    })
    chartRef.current.priceScale("volume").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } })

    return () => {
      chartRef.current?.remove()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!candleSeriesRef.current || !volSeriesRef.current || !ohlcv.length) return
    const candleData = ohlcv.map((d) => ({
      time: d.time as Time,
      open: d.open, high: d.high, low: d.low, close: d.close,
    }))
    const volData = ohlcv.map((d) => ({
      time: d.time as Time,
      value: d.volume,
      color: d.close >= d.open ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)",
    }))
    candleSeriesRef.current.setData(candleData)
    volSeriesRef.current.setData(volData)
    chartRef.current?.timeScale().fitContent()
  }, [ohlcv])

  return (
    <div className="h-full flex flex-col relative">
      <div className="flex items-center gap-0.5 px-2 py-1 border-b border-gray-800/40 bg-gray-950/60 z-10">
        {timeframes.map((t) => (
          <button key={t} onClick={() => setTf(t)}
            className={`px-2 py-0.5 text-[10px] font-mono rounded transition-colors ${
              tf === t ? "bg-blue-600/20 text-blue-400 border border-blue-500/30" : "text-gray-500 hover:text-gray-300"
            }`}>{t}</button>
        ))}
        <div className="flex-1" />
        <span className="text-[10px] text-gray-600">{symbol} • {tf}</span>
      </div>
      <div ref={containerRef} className="flex-1" />
    </div>
  )
}
