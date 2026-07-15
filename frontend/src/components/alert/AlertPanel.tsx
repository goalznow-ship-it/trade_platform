"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import {
  Bell, BellOff, Plus, Trash2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { Alert } from "@/types"

const ALERT_TYPES = ["price", "volume", "rsi", "macd", "ma_cross", "signal", "news", "volatility"]
const CONDITIONS = ["above", "below", "crosses_above", "crosses_below", "inside", "outside"]

const DEFAULT_FORM = {
  name: "", alert_type: "price", symbol: "BTC/USDT",
  condition: "above", value: 0, channels: ["in_app"],
}

export function AlertPanel() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ ...DEFAULT_FORM })

  async function loadAlerts() {
    try { setAlerts(await api.getAlerts()) } catch {}
  }

  useEffect(() => {
    const initialLoad = async () => {
      try { setAlerts(await api.getAlerts()) } catch {}
    }
    initialLoad()
  }, [])

  async function handleCreate() {
    await api.createAlert(form)
    setShowForm(false)
    setForm({ ...DEFAULT_FORM })
    loadAlerts()
  }

  async function handleToggle(a: Alert) {
    await api.updateAlert(a.id, { is_active: !a.is_active })
    loadAlerts()
  }

  async function handleDelete(id: number) {
    await api.deleteAlert(id)
    loadAlerts()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-gray-200">Alerts</span>
            <Badge variant="info">{alerts.length}</Badge>
          </div>
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            <Plus className="w-3 h-3 mr-1" /> Alert
          </Button>
        </div>
      </div>

      {showForm && (
        <div className="p-3 border-b border-gray-800 space-y-2 bg-gray-900/50">
          <input
            type="text" placeholder="Alert name" value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
          />
          <div className="flex gap-1 flex-wrap">
            {ALERT_TYPES.map((t) => (
              <button
                key={t}
                onClick={() => setForm({ ...form, alert_type: t })}
                className={cn(
                  "px-2 py-1 text-[10px] rounded",
                  form.alert_type === t ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400"
                )}
              >
                {t.replace("_", " ")}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              type="text" placeholder="BTC/USDT" value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value })}
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white font-mono"
            />
            <select
              value={form.condition}
              onChange={(e) => setForm({ ...form, condition: e.target.value })}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
            >
              {CONDITIONS.map((c) => (
                <option key={c} value={c}>{c.replace("_", " ")}</option>
              ))}
            </select>
            <input
              type="number" placeholder="Value" value={form.value}
              onChange={(e) => setForm({ ...form, value: parseFloat(e.target.value) })}
              className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white font-mono"
            />
          </div>
          <Button size="sm" onClick={handleCreate} className="w-full">Create Alert</Button>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        {alerts.length === 0 && (
          <div className="p-4 text-center text-gray-600 text-xs">No alerts configured</div>
        )}
        {alerts.map((a) => (
          <div key={a.id} className="flex items-center gap-3 px-3 py-2.5 border-b border-gray-800 hover:bg-gray-800/50 group">
            <button onClick={() => handleToggle(a)}>
              {a.is_active ? <Bell className="w-4 h-4 text-green-400" /> : <BellOff className="w-4 h-4 text-gray-600" />}
            </button>
            <div className="flex-1 min-w-0">
              <div className="text-xs text-gray-200 font-medium">{a.name}</div>
              <div className="text-[10px] text-gray-500">
                {a.symbol} - {a.condition} {a.value}
              </div>
            </div>
            <Badge variant={a.is_active ? "success" : "default"} className="text-[9px]">
              {a.alert_type}
            </Badge>
            <button onClick={() => handleDelete(a.id)} className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100">
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
