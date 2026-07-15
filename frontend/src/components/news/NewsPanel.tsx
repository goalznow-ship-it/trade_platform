"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Badge } from "@/components/ui/Badge"
import { Newspaper, ExternalLink } from "lucide-react"

interface NewsArticle {
  url?: string
  title?: string
  source?: string
  sentiment?: string
  impact_score?: number
}

export function NewsPanel() {
  const [news, setNews] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getNews()
      .then(data => setNews(data))
      .catch(() => {})
      .finally(() => setLoading(false))
    const interval = setInterval(() => {
      api.getNews()
        .then(data => setNews(data))
        .catch(() => {})
    }, 120000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Newspaper className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-medium text-gray-200">News Feed</span>
          <Badge variant="info">{news.length}</Badge>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="p-4 text-center text-gray-500 text-sm">Loading news...</div>
        ) : news.length === 0 ? (
          <div className="p-4 text-center text-gray-600 text-sm">No news available</div>
        ) : (
          news.map((article, i) => (
            <a
              key={i}
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 border-b border-gray-800 hover:bg-gray-800/50 transition-colors group"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-300 line-clamp-2 group-hover:text-white transition-colors">
                    {article.title}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-gray-600">{article.source}</span>
                    <Badge
                      variant={
                        article.sentiment === "bullish"
                          ? "success"
                          : article.sentiment === "bearish"
                          ? "danger"
                          : "default"
                      }
                      className="text-[9px] px-1 py-0"
                    >
                      {article.sentiment || "neutral"}
                    </Badge>
                    {article.impact_score && (
                      <span className="text-[10px] text-gray-600">
                        Impact: {article.impact_score}/10
                      </span>
                    )}
                  </div>
                </div>
                <ExternalLink className="w-3 h-3 text-gray-600 flex-shrink-0 mt-0.5" />
              </div>
            </a>
          ))
        )}
      </div>
    </div>
  )
}
