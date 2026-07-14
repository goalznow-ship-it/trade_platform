"use client"

import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import { Brain, Smile, Frown, Meh, AlertCircle } from "lucide-react"

interface FearGreed {
  value?: number
  value_classification?: string
}

export function SentimentWidget() {
  const [fearGreed, setFearGreed] = useState<FearGreed | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await api.getFearGreed()
      setFearGreed(data)
      setError(null)
    } catch {
      setError("Sentiment unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(load, 0)
    const interval = setInterval(load, 300000)
    return () => {
      clearTimeout(timer)
      clearInterval(interval)
    }
  }, [load])

  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-3">
          <div className="h-3 w-24 bg-gray-800 rounded" />
          <div className="h-16 bg-gray-800 rounded" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Market Sentiment</h3>
          <Brain className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <div className="flex items-center gap-2 text-yellow-400 text-xs">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          {error}
        </div>
      </div>
    )
  }

  const value = fearGreed?.value ?? 50
  const classification = fearGreed?.value_classification || getClassification(value)

  function getClassification(v: number): string {
    if (v <= 25) return "Extreme Fear"
    if (v <= 45) return "Fear"
    if (v <= 55) return "Neutral"
    if (v <= 75) return "Greed"
    return "Extreme Greed"
  }

  const isBullish = value > 55
  const SentimentIcon = value <= 25 ? Frown : value <= 45 ? Meh : value <= 55 ? Meh : Smile

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Market Sentiment</h3>
        <Brain className="w-3.5 h-3.5 text-purple-400" />
      </div>
      <div className="flex items-center gap-4">
        <div className="relative w-16 h-16 flex items-center justify-center flex-shrink-0">
          <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="15.5" fill="none" stroke="#1f2937" strokeWidth="3" />
            <circle cx="18" cy="18" r="15.5" fill="none"
              stroke={value <= 25 ? "#ef4444" : value <= 45 ? "#f97316" : value <= 55 ? "#eab308" : value <= 75 ? "#22c55e" : "#34d399"}
              strokeWidth="3"
              strokeDasharray={`${(value / 100) * 97.4} 97.4`}
              strokeLinecap="round"
              className="transition-all duration-700" />
          </svg>
          <span className={cn("absolute text-lg font-bold font-mono",
            value <= 25 && "text-red-400",
            value <= 45 && "text-orange-400",
            value <= 55 && "text-yellow-400",
            value <= 75 && "text-green-400",
            value > 75 && "text-emerald-400")}>
            {value}
          </span>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white">{classification}</span>
            <SentimentIcon className={cn("w-4 h-4",
              value <= 25 ? "text-red-400" : value <= 45 ? "text-orange-400" : value <= 55 ? "text-yellow-400" : "text-green-400")} />
          </div>
          <div className="text-[11px] text-gray-500 mt-0.5">Fear & Greed Index</div>
          <div className="flex gap-1 mt-2">
            <div className="flex-1 h-1.5 rounded bg-gradient-to-r from-red-500 via-yellow-500 to-green-500" />
          </div>
          <div className="flex justify-between text-[8px] text-gray-700 mt-0.5">
            <span>Fear</span>
            <span>Greed</span>
          </div>
          {isBullish && (
            <div className="mt-1.5 text-[10px] text-gray-500">
              Market sentiment suggests bullish conditions
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
