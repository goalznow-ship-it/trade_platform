"use client"

import { useEffect, useState, useCallback, memo } from "react"
import { api } from "@/lib/api"
import { cn, ago } from "@/lib/utils"
import {
  Activity, Wifi, WifiOff, RefreshCw,
  Server, Database, AlertCircle, Clock,
} from "lucide-react"

interface WsStats {
  total_clients?: number
  channel_subscriptions?: Record<string, number>
  authenticated_clients?: number
}

interface Health {
  status?: string
}

const StatusRow = memo(function StatusRow({ label, value, status, dot, icon: Icon }: {
  label: string; value: string; status: string; dot: string; icon: React.ElementType
}) {
  return (
    <div className="p-2.5 rounded-lg bg-gray-800/20">
      <div className="flex items-center gap-1.5 mb-1">
        <div className={cn("w-1.5 h-1.5 rounded-full animate-pulse-dot", dot)} />
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
  const [wsStats, setWsStats] = useState<WsStats | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<string>("")

  const load = useCallback(async () => {
    try {
      const [ws, h] = await Promise.all([
        api.getWsStats().catch(() => null),
        fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`)
          .then(r => r.json()).catch(() => null),
      ])
      setWsStats(ws)
      setHealth(h)
      setLastFetch(new Date().toISOString())
      setError(null)
    } catch {
      setError("Engine status unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(load, 0)
    const interval = setInterval(load, 30000)
    return () => {
      clearTimeout(timer)
      clearInterval(interval)
    }
  }, [load])

  if (loading) {
    return (
      <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-2">
          <div className="h-3 w-24 bg-gray-800 rounded" />
          <div className="grid grid-cols-2 gap-2">
            <div className="h-14 bg-gray-800 rounded" />
            <div className="h-14 bg-gray-800 rounded" />
            <div className="h-14 bg-gray-800 rounded" />
            <div className="h-14 bg-gray-800 rounded" />
          </div>
        </div>
      </div>
    )
  }

  const wsConnected = wsStats && wsStats.total_clients !== undefined
  const channels = wsStats?.channel_subscriptions || {}
  const subCount = Object.values(channels).reduce((a: number, b: number) => a + (typeof b === "number" ? b : 0), 0)

  const items = [
    {
      label: "WebSocket",
      value: wsConnected ? `${wsStats.total_clients} clients` : "Disconnected",
      icon: wsConnected ? Wifi : WifiOff,
      status: wsConnected ? "text-green-400" : "text-red-400",
      dot: wsConnected ? "bg-green-400" : "bg-red-400",
    },
    {
      label: "API Server",
      value: health?.status === "ok" ? "Running" : "Unknown",
      icon: Server,
      status: health?.status === "ok" ? "text-green-400" : "text-yellow-400",
      dot: health?.status === "ok" ? "bg-green-400" : "bg-yellow-400",
    },
    {
      label: "Active Subs",
      value: `${subCount} channel(s)`,
      icon: RefreshCw,
      status: "text-blue-400",
      dot: "bg-blue-400",
    },
    {
      label: "Auth'd Users",
      value: String(wsStats?.authenticated_clients || 0),
      icon: Database,
      status: "text-gray-400",
      dot: "bg-gray-500",
    },
  ]

  return (
    <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Engine Status</h3>
        </div>
        {lastFetch && (
          <span className="text-[9px] text-gray-600 flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" />{ago(lastFetch)}
          </span>
        )}
      </div>
      {error && (
        <div className="flex items-center gap-2 text-yellow-500 text-[10px] mb-2">
          <AlertCircle className="w-3 h-3" />
          {error}
        </div>
      )}
      <div className="grid grid-cols-2 gap-2">
        {items.map((item) => (
          <StatusRow key={item.label} {...item} />
        ))}
      </div>
    </div>
  )
}
