"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import { Brain, Smile, Frown, Meh, AlertTriangle } from "lucide-react"

export function SentimentWidget() {
  const [fearGreed, setFearGreed] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getFearGreed().then(setFearGreed).catch(() => {}).finally(() => setLoading(false))
  }, [])

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

  const value = fearGreed?.value ?? 50
  const classification = fearGreed?.classification || getClassification(value)

  function getClassification(v: number): string {
    if (v <= 25) return "Extreme Fear"
    if (v <= 45) return "Fear"
    if (v <= 55) return "Neutral"
    if (v <= 75) return "Greed"
    return "Extreme Greed"
  }

  const sentimentColor = value <= 25 ? "red" : value <= 45 ? "orange" : value <= 55 ? "yellow" : value <= 75 ? "green" : "emerald"
  const SentimentIcon = value <= 25 ? Frown : value <= 45 ? Meh : value <= 55 ? Meh : Smile

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Market Sentiment</h3>
        <Brain className="w-3.5 h-3.5 text-purple-400" />
      </div>
      <div className="flex items-center gap-4">
        <div className="relative w-16 h-16 flex items-center justify-center">
          <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="15.5" fill="none" stroke="#1f2937" strokeWidth="3" />
            <circle cx="18" cy="18" r="15.5" fill="none"
              stroke={value <= 25 ? "#ef4444" : value <= 45 ? "#f97316" : value <= 55 ? "#eab308" : value <= 75 ? "#22c55e" : "#34d399"}
              strokeWidth="3"
              strokeDasharray={`${(value / 100) * 97.4} 97.4`}
              strokeLinecap="round" />
          </svg>
          <span className={cn("absolute text-lg font-bold font-mono",
            sentimentColor === "red" && "text-red-400",
            sentimentColor === "orange" && "text-orange-400",
            sentimentColor === "yellow" && "text-yellow-400",
            sentimentColor === "green" && "text-green-400",
            sentimentColor === "emerald" && "text-emerald-400",
          )}>
            {value}
          </span>
        </div>
        <div>
          <div className="text-sm font-semibold text-white">{classification}</div>
          <div className="text-[11px] text-gray-500 mt-0.5">Fear & Greed Index</div>
          <div className="flex gap-1 mt-1.5">
            {[1, 2, 3, 4, 5].map((level) => (
              <div key={level}
                className={cn("w-2 h-4 rounded-sm transition-colors",
                  value / 20 >= level
                    ? level <= 1 ? "bg-red-500" : level <= 2 ? "bg-orange-500" : level === 3 ? "bg-yellow-500" : level === 4 ? "bg-green-500" : "bg-emerald-500"
                    : "bg-gray-800"
                )} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
