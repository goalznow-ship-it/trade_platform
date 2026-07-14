"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { cn } from "@/lib/utils"
import {
  Bell, BellRing, CheckCheck, Archive, Trash2,
  Info, AlertTriangle, TrendingUp, TrendingDown, DollarSign,
} from "lucide-react"

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  info: Info,
  warning: AlertTriangle,
  alert: Bell,
  signal: TrendingUp,
  trade: DollarSign,
}

export function NotificationsPanel() {
  const [notifications, setNotifications] = useState<Record<string, unknown>[]>([])

  async function load() {
    try {
      const n = await api.getNotifications()
      setNotifications(Array.isArray(n) ? n : [])
    } catch {}
  }

  useEffect(() => { load() }, [])

  async function handleMarkRead(id: number) {
    await api.markNotificationRead(id)
    load()
  }

  async function handleMarkAllRead() {
    await api.markAllNotificationsRead()
    load()
  }

  async function handleArchive(id: number) {
    await api.archiveNotification(id)
    load()
  }

  const unread = notifications.filter((n) => !n.is_read).length

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BellRing className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-gray-200">Notifications</span>
            {unread > 0 && (
              <Badge variant="danger">{unread}</Badge>
            )}
          </div>
          {unread > 0 && (
            <Button variant="ghost" size="sm" onClick={handleMarkAllRead}>
              <CheckCheck className="w-3 h-3 mr-1" /> Mark All Read
            </Button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {notifications.length === 0 && (
          <div className="p-4 text-center text-gray-600 text-xs">No notifications</div>
        )}
        {notifications.map((n) => {
          const Icon = ICON_MAP[n.type] || Bell
          return (
            <div
              key={n.id}
              className={cn(
                "flex items-start gap-3 px-3 py-2.5 border-b border-gray-800 hover:bg-gray-800/50 group cursor-pointer",
                !n.is_read && "bg-blue-900/5"
              )}
              onClick={() => !n.is_read && handleMarkRead(n.id)}
            >
              <Icon className={cn("w-4 h-4 mt-0.5", {
                "text-blue-400": n.type === "info" || !n.type,
                "text-yellow-400": n.type === "warning",
                "text-red-400": n.type === "alert",
                "text-green-400": n.type === "signal",
                "text-purple-400": n.type === "trade",
              })} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={cn(
                    "text-xs",
                    n.is_read ? "text-gray-500" : "text-gray-200 font-medium"
                  )}>
                    {n.title}
                  </span>
                  {!n.is_read && <span className="w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />}
                </div>
                {n.message && (
                  <div className="text-[10px] text-gray-500 line-clamp-2 mt-0.5">{n.message}</div>
                )}
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[9px] text-gray-600">
                    {n.created_at ? new Date(n.created_at).toLocaleDateString() : ""}
                  </span>
                </div>
              </div>
              <div className="flex gap-1 opacity-0 group-hover:opacity-100">
                {!n.is_read && (
                  <button onClick={(e) => { e.stopPropagation(); handleMarkRead(n.id) }}
                    className="p-1 text-gray-500 hover:text-blue-400">
                    <CheckCheck className="w-3 h-3" />
                  </button>
                )}
                <button onClick={(e) => { e.stopPropagation(); handleArchive(n.id) }}
                  className="p-1 text-gray-500 hover:text-yellow-400">
                  <Archive className="w-3 h-3" />
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
