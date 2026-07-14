"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { cn, formatPercent } from "@/lib/utils"
import {
  Shield, AlertTriangle, TrendingUp, TrendingDown,
  DollarSign, Target, BarChart3, Edit3,
} from "lucide-react"

export function RiskPanel() {
  const [dashboard, setDashboard] = useState<any>(null)
  const [editMode, setEditMode] = useState(false)
  const [profile, setProfile] = useState<any>({})

  async function load() {
    try {
      const d = await api.getRiskDashboard()
      setDashboard(d)
      setProfile(d.profile || {})
    } catch {}
  }

  useEffect(() => { load() }, [])

  async function handleSave() {
    await api.updateRiskProfile(profile)
    setEditMode(false)
    load()
  }

  if (!dashboard) {
    return <div className="p-4 text-center text-gray-500 text-sm">Loading risk dashboard...</div>
  }

  const c = dashboard.current || {}
  const metrics = [
    { label: "Sharpe", value: c.sharpe_ratio, color: (c.sharpe_ratio || 0) >= 1 ? "green" : (c.sharpe_ratio || 0) >= 0 ? "yellow" : "red" },
    { label: "Sortino", value: c.sortino_ratio, color: (c.sortino_ratio || 0) >= 1 ? "green" : (c.sortino_ratio || 0) >= 0 ? "yellow" : "red" },
    { label: "Profit Factor", value: c.profit_factor, color: (c.profit_factor || 0) >= 1.5 ? "green" : (c.profit_factor || 0) >= 1 ? "yellow" : "red" },
    { label: "Kelly %", value: c.kelly_percentage, color: (c.kelly_percentage || 0) > 0 ? "green" : "red", suffix: "%" },
    { label: "VaR (95%)", value: c.value_at_risk, color: (c.value_at_risk || 0) < 0.02 ? "green" : (c.value_at_risk || 0) < 0.05 ? "yellow" : "red", prefix: "$" },
    { label: "Win Rate", value: c.win_rate, color: (c.win_rate || 0) >= 50 ? "green" : "red", suffix: "%" },
  ]

  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-400" />
          <h2 className="text-sm font-semibold text-white">Risk Management</h2>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setEditMode(!editMode)}>
          <Edit3 className="w-3 h-3 mr-1" /> {editMode ? "Cancel" : "Edit Profile"}
        </Button>
      </div>

      {editMode && (
        <Card>
          <CardHeader>
            <CardTitle>Risk Profile Settings</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            {[
              { key: "max_daily_loss", label: "Max Daily Loss", type: "number" },
              { key: "max_leverage", label: "Max Leverage", type: "number" },
              { key: "max_open_positions", label: "Max Open Positions", type: "number" },
              { key: "risk_per_trade", label: "Risk Per Trade", type: "number", step: 0.01 },
              { key: "max_drawdown", label: "Max Drawdown", type: "number", step: 0.01 },
              { key: "max_position_size", label: "Max Position Size", type: "number" },
            ].map((f) => (
              <div key={f.key}>
                <label className="text-[10px] text-gray-500">{f.label}</label>
                <input
                  type={f.type}
                  value={(profile as any)[f.key] ?? ""}
                  onChange={(e) => setProfile({ ...profile, [f.key]: parseFloat(e.target.value) || 0 })}
                  step={f.step}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white font-mono"
                />
              </div>
            ))}
            <div className="col-span-2">
              <Button size="sm" onClick={handleSave} className="w-full">Save Profile</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-2">
        {metrics.map((m) => (
          <Card key={m.label} className="border-gray-700 p-3">
            <div className="text-[10px] text-gray-500">{m.label}</div>
            <div className={cn("text-lg font-bold font-mono", {
              "text-green-400": m.color === "green",
              "text-yellow-400": m.color === "yellow",
              "text-red-400": m.color === "red",
            })}>
              {m.prefix || ""}{m.value?.toFixed(2) || "0.00"}{m.suffix || ""}
            </div>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Risk Limits</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {[
            { label: "Daily Loss", current: c.current_daily_loss, max: profile.max_daily_loss, color: "red" },
            { label: "Drawdown", current: c.current_drawdown, max: profile.max_drawdown, color: "yellow" },
            { label: "Open Positions", current: c.open_positions, max: profile.max_open_positions, color: "blue" },
            { label: "Exposure", current: c.current_exposure, max: profile.max_position_size, color: "orange", prefix: "$" },
          ].map((item) => {
            const pct = item.max ? Math.min(100, ((item.current || 0) / item.max) * 100) : 0
            return (
              <div key={item.label}>
                <div className="flex justify-between text-[10px] mb-0.5">
                  <span className="text-gray-500">{item.label}</span>
                  <span className="text-gray-300 font-mono">
                    {item.prefix || ""}{(item.current || 0).toFixed(2)} / {item.prefix || ""}{item.max?.toFixed(2) || "∞"}
                  </span>
                </div>
                <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all", {
                      "bg-red-500": pct > 80,
                      "bg-yellow-500": pct > 50 && pct <= 80,
                      "bg-green-500": pct <= 50,
                    })}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}
