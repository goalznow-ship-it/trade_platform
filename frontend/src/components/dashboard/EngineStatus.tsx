"use client"

import { useEffect, useState, memo } from "react"
import { useWS } from "@/components/WSProvider"
import { useMarketStore } from "@/store/market"
import { cn } from "@/lib/utils"
import {
  Activity, Wifi, WifiOff, Server, Database, RefreshCw, Clock,
} from "lucide-react"

const StatusRow = memo(function StatusRow({ label, value, status, dot, icon: Icon }: {
  label: string; value: string; status: string; dot: string; icon: React.ElementType
}) {
  return (
    <div className="p-2.5 rounded-lg bg-gray-800/20">
      <div className="flex items-center gap-1.5 mb-1">
        <div className={cn("w-1.5 h-1.5 rounded-full", dot)} />
        <Icon className={cn("w-3 h-3", status)} />
        <span className="text-[10px] text-gray-500">{label}</span>
      </div>
      <div className={cn("text-xs font-medium font-mono", status)}>
        {value}
      </div>
    </div>
  )
})

export function EngineStatus() {
  const { quality, isConnected } = useWS()
  const isLive = useMarketStore((s) => s.isLive)
  const lastPerChannel = useMarketStore((s) => s.lastPerChannel)
  const [now, setNow] = useState(Date.now)
  const health = isConnected ? "operational" : "checking"

  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now())
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  const activeChannels = Object.entries(lastPerChannel)
    .filter(([, ts]) => now - ts < 120000)
    .length

  const items = [
    {
      label: "WebSocket",
      value: isConnected
        ? `${quality.latency}ms | ${Math.floor(quality.uptime / 60)}m up`
        : "Reconnecting...",
      icon: isConnected ? Wifi : WifiOff,
      status: isConnected ? "text-green-400" : "text-red-400",
      dot: isConnected ? "bg-green-400" : "bg-red-400",
    },
    {
      label: "API Server",
      value: health === "operational" ? "Operational" : "Checking",
      icon: Server,
      status: health === "operational" ? "text-green-400" : "text-yellow-400",
      dot: health === "operational" ? "bg-green-400" : "bg-yellow-400",
    },
    {
      label: "Active Streams",
      value: `${activeChannels}/${Object.keys(lastPerChannel).length || 10} channels`,
      icon: RefreshCw,
      status: isLive ? "text-blue-400" : "text-yellow-400",
      dot: isLive ? "bg-blue-400" : "bg-yellow-400",
    },
    {
      label: "Reconnects",
      value: String(quality.reconnects),
      icon: Database,
      status: quality.reconnects > 5 ? "text-red-400" : "text-gray-400",
      dot: quality.reconnects > 5 ? "bg-red-400" : "bg-gray-500",
    },
  ]

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Engine Status</h3>
        </div>
        <span className="text-[9px] text-gray-600 flex items-center gap-1">
          <Clock className="w-2.5 h-2.5" />
          {quality.uptime > 0 ? `${Math.floor(quality.uptime / 60)}m` : "—"}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {items.map((item) => (
          <StatusRow key={item.label} {...item} />
        ))}
      </div>
    </div>
  )
}
