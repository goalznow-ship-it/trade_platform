"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn, formatTime } from "@/lib/utils"
import {
  Newspaper, TrendingUp, TrendingDown, Shield,
  AlertTriangle, ExternalLink, RefreshCw,
  Globe, Building2, DollarSign, Activity,
} from "lucide-react"

export function NewsIntelligence() {
  const [news, setNews] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>("all")

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const data = await api.getNewsIntelligence()
        setNews(Array.isArray(data) ? data : [])
      } catch {
        setNews([])
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 120000)
    return () => clearInterval(interval)
  }, [])

  const categories = [
    { id: "all", label: "All News", icon: Newspaper },
    { id: "macro", label: "Macro/FED", icon: DollarSign },
    { id: "regulation", label: "Regulation", icon: Building2 },
    { id: "whale", label: "Whale Activity", icon: Activity },
    { id: "security", label: "Security", icon: Shield },
  ]

  const filtered = filter === "all" ? news : news.filter((n) => (n.category || n.type) === filter)

  function getCategoryIcon(cat: string) {
    switch (cat) {
      case "macro": return <DollarSign className="w-3.5 h-3.5" />
      case "regulation": return <Building2 className="w-3.5 h-3.5" />
      case "whale": return <Activity className="w-3.5 h-3.5" />
      case "security": return <Shield className="w-3.5 h-3.5" />
      default: return <Globe className="w-3.5 h-3.5" />
    }
  }

  return (
    <div className="h-full overflow-y-auto bg-[#0d1117]">
      <div className="max-w-6xl mx-auto p-4 lg:p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white">News Intelligence</h1>
            <p className="text-xs text-gray-500 mt-0.5">AI-powered news monitoring with impact analysis</p>
          </div>
          <button onClick={() => window.location.reload()} className="flex items-center gap-1 px-2.5 py-1.5 text-xs text-gray-400 hover:text-white bg-gray-800 rounded-md hover:bg-gray-700 transition-colors">
            <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} /> Refresh
          </button>
        </div>

        {/* Category Filters */}
        <div className="flex flex-wrap items-center gap-1.5 p-2 rounded-lg border border-gray-800 bg-gray-900/50">
          {categories.map((cat) => (
            <button key={cat.id} onClick={() => setFilter(cat.id)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-md transition-colors",
                filter === cat.id
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
              )}>
              <cat.icon className="w-3.5 h-3.5" />
              {cat.label}
            </button>
          ))}
        </div>

        {/* News Feed */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="p-4 rounded-lg border border-gray-800 bg-gray-900/30">
                <div className="animate-pulse space-y-2">
                  <div className="h-4 w-3/4 bg-gray-800 rounded" />
                  <div className="h-3 w-1/2 bg-gray-800 rounded" />
                  <div className="flex gap-2">
                    <div className="h-6 w-16 bg-gray-800 rounded" />
                    <div className="h-6 w-24 bg-gray-800 rounded" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-gray-600">
            <Newspaper className="w-8 h-8 mx-auto mb-2" />
            <div className="text-sm">No news items match current filter</div>
          </div>
        ) : (
          <div className="space-y-2.5">
            {filtered.map((item, i) => {
              const impact = item.impact || item.sentiment || "neutral"
              const isPositive = impact === "positive" || impact === "bullish"
              const isNegative = impact === "negative" || impact === "bearish"
              const score = item.score || item.impact_score || 0
              const cat = item.category || item.type || "general"

              return (
                <div key={i} className="p-4 rounded-lg border border-gray-800 bg-gray-900/30 hover:border-gray-700 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
                      isPositive ? "bg-green-900/30 text-green-400" :
                      isNegative ? "bg-red-900/30 text-red-400" :
                      "bg-gray-800 text-gray-400"
                    )}>
                      {getCategoryIcon(cat)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h3 className="text-sm font-medium text-white line-clamp-2">{item.title || item.headline || "Untitled"}</h3>
                          {item.source && (
                            <div className="flex items-center gap-1 mt-0.5">
                              <span className="text-[10px] text-gray-600">{item.source}</span>
                              {item.timestamp && (
                                <>
                                  <span className="text-gray-700">·</span>
                                  <span className="text-[10px] text-gray-600">
                                    {formatTime(typeof item.timestamp === "number" ? item.timestamp : Date.parse(item.timestamp) / 1000)}
                                  </span>
                                </>
                              )}
                            </div>
                          )}
                        </div>
                        {/* Impact Score */}
                        <div className="flex flex-col items-center flex-shrink-0">
                          <div className={cn(
                            "text-base font-bold font-mono",
                            isPositive ? "text-green-400" :
                            isNegative ? "text-red-400" :
                            "text-gray-400"
                          )}>
                            {score}
                          </div>
                          <div className="text-[9px] text-gray-600 uppercase tracking-wider">Impact</div>
                        </div>
                      </div>

                      {/* Summary */}
                      {item.summary && (
                        <p className="text-xs text-gray-400 mt-1.5 line-clamp-2 leading-relaxed">{item.summary}</p>
                      )}

                      {/* Tags & Links */}
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <span className={cn(
                          "text-[10px] font-medium px-1.5 py-0.5 rounded",
                          cat === "macro" ? "bg-yellow-900/30 text-yellow-400" :
                          cat === "regulation" ? "bg-purple-900/30 text-purple-400" :
                          cat === "whale" ? "bg-cyan-900/30 text-cyan-400" :
                          cat === "security" ? "bg-red-900/30 text-red-400" :
                          "bg-gray-800 text-gray-400"
                        )}>
                          {cat.toUpperCase()}
                        </span>

                        {item.assets && Array.isArray(item.assets) && item.assets.length > 0 && (
                          <div className="flex gap-1">
                            {item.assets.slice(0, 3).map((a: string) => (
                              <span key={a} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">{a}</span>
                            ))}
                          </div>
                        )}

                        {isPositive && <span className="text-[10px] text-green-400 font-medium flex items-center gap-0.5"><TrendingUp className="w-3 h-3" /> Bullish</span>}
                        {isNegative && <span className="text-[10px] text-red-400 font-medium flex items-center gap-0.5"><TrendingDown className="w-3 h-3" /> Bearish</span>}

                        <div className="flex-1" />

                        {item.url && (
                          <a href={item.url} target="_blank" rel="noopener noreferrer"
                            className="text-[10px] text-gray-500 hover:text-gray-300 flex items-center gap-0.5">
                            <ExternalLink className="w-3 h-3" /> Source
                          </a>
                        )}
                      </div>

                      {/* Impact Bar */}
                      <div className="mt-2 h-1 bg-gray-800 rounded-full overflow-hidden">
                        <div className={cn(
                          "h-full rounded-full transition-all",
                          isPositive ? "bg-green-500" : isNegative ? "bg-red-500" : "bg-gray-600"
                        )} style={{ width: `${Math.min(score, 100)}%` }} />
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}


