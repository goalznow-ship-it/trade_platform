"use client"

import { useEffect, useState } from "react"
import { useWS } from "@/components/WSProvider"
import { useMarketStore } from "@/store/market"
import { Wifi, WifiOff, Activity } from "lucide-react"
import { cn } from "@/lib/utils"

export function ConnectionQualityIndicator() {
  const { quality, isConnected } = useWS()

  return (
    <div className="flex items-center justify-between px-3 py-0.5 bg-gray-950 border-b border-gray-800">
      <div className="flex items-center gap-3 text-[10px] text-gray-500">
        <span className="flex items-center gap-1">
          {isConnected ? (
            <Wifi className={cn(
              "w-3 h-3",
              quality.latency < 50 ? "text-green-400" :
              quality.latency < 150 ? "text-yellow-400" : "text-red-400"
            )} />
          ) : (
            <WifiOff className="w-3 h-3 text-red-400 animate-pulse" />
          )}
          {isConnected ? `${quality.latency}ms` : "Offline"}
        </span>
        <span className="flex items-center gap-1">
          <Activity className="w-3 h-3" />
          {quality.uptime > 0
            ? `${Math.floor(quality.uptime / 60)}m ${Math.floor(quality.uptime % 60)}s`
            : "—"}
        </span>
        <span className="text-gray-600">
          {isConnected ? "Live" : `Reconnecting... (${quality.reconnects})`}
        </span>
      </div>
      <LastUpdateIndicator />
    </div>
  )
}

function LastUpdateIndicator() {
  const lastPerChannel = useMarketStore((s) => s.lastPerChannel)
  const [now, setNow] = useState(Date.now)

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 5000)
    return () => clearInterval(interval)
  }, [])

  const channels = [
    { key: "ticker", label: "Prices" },
    { key: "orderflow", label: "Flow" },
    { key: "derivatives", label: "Deriv" },
    { key: "news", label: "News" },
    { key: "sentiment", label: "Senti" },
    { key: "onchain", label: "Chain" },
    { key: "macro", label: "Macro" },
    { key: "brain", label: "Brain" },
    { key: "fear_greed", label: "F&G" },
    { key: "breadth", label: "Breadth" },
  ]

  return (
    <div className="flex items-center gap-2 text-[10px] text-gray-600">
      {channels.map((ch) => {
        const ts = lastPerChannel[ch.key]
        const ago = ts ? Math.floor((now - ts) / 1000) : null
        const stale = ago !== null && ago > 120
        return (
          <span
            key={ch.key}
            className={cn(
              "tabular-nums",
              stale ? "text-red-500" : ago !== null ? "text-gray-400" : "text-gray-700"
            )}
          >
            {ch.label}:{ago !== null ? `${ago}s` : "—"}
          </span>
        )
      })}
    </div>
  )
}
