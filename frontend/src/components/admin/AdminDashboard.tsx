"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import {
  Users, Activity, TrendingUp, Shield, Server, Cpu,
  HardDrive, Database, Trash2, UserX, Plus, BarChart3
} from "lucide-react"

export function AdminDashboard() {
  const [tab, setTab] = useState("overview")
  const [stats, setStats] = useState<any>(null)
  const [users, setUsers] = useState<any[]>([])
  const [symbols, setSymbols] = useState<any[]>([])
  const [signals, setSignals] = useState<any[]>([])
  const [logs, setLogs] = useState<any[]>([])
  const [newSymbol, setNewSymbol] = useState("")

  useEffect(() => { loadAll() }, [])

  async function loadAll() {
    try {
      const [s, u, sym, sig, l] = await Promise.all([
        api.getAdminStats(), api.getAdminUsers(), api.getAdminSymbols(),
        api.getAdminSignals(), api.getLogs(),
      ])
      setStats(s); setUsers(u); setSymbols(sym); setSignals(sig); setLogs(l)
    } catch {}
  }

  async function handleToggleAdmin(userId: number, isAdmin: boolean) {
    try { await api.updateUser(userId, { is_admin: !isAdmin }); loadAll() } catch {}
  }
  async function handleDeleteUser(userId: number) {
    try { await api.deleteUser(userId); loadAll() } catch {}
  }
  async function handleAddSymbol() {
    if (!newSymbol) return
    try { await api.addSymbol({ name: newSymbol.toUpperCase(), exchange: "binance", asset_type: "crypto" }); setNewSymbol(""); loadAll() } catch {}
  }
  async function handleDeleteSymbol(id: number) {
    try { await api.deleteSymbol(id); loadAll() } catch {}
  }
  async function handleDeleteSignal(id: number) {
    try { await api.deleteSignal(id); loadAll() } catch {}
  }

  const tabs = [
    { id: "overview", label: "Overview", icon: BarChart3 },
    { id: "users", label: "Users", icon: Users },
    { id: "symbols", label: "Symbols", icon: TrendingUp },
    { id: "signals", label: "Signals", icon: Activity },
    { id: "system", label: "System", icon: Server },
  ]

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Admin Panel</h1>
          <p className="text-sm text-gray-500">System Management Dashboard</p>
        </div>
        <Badge variant="info">Server Online</Badge>
      </div>

      <div className="flex gap-2 mb-6 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.id
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[
            { label: "Total Users", value: stats.total_users, icon: Users, color: "blue" },
            { label: "Active Users", value: stats.active_users, icon: Shield, color: "green" },
            { label: "Total Signals", value: stats.total_signals, icon: Activity, color: "yellow" },
            { label: "Active Signals", value: stats.active_signals, icon: TrendingUp, color: "purple" },
            { label: "Symbols", value: stats.total_symbols, icon: Database, color: "cyan" },
            { label: "Total Trades", value: stats.total_trades, icon: BarChart3, color: "orange" },
          ].map((s, i) => (
            <Card key={i} className="border-gray-700">
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-gray-500">{s.label}</div>
                    <div className="text-2xl font-bold text-white mt-1">{s.value}</div>
                  </div>
                  <s.icon className={`w-8 h-8 text-${s.color}-500 opacity-50`} />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {tab === "users" && (
        <Card>
          <CardHeader>
            <CardTitle>Users Management</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-800">
                    <th className="text-left py-3 px-2">ID</th>
                    <th className="text-left py-3 px-2">Username</th>
                    <th className="text-left py-3 px-2">Email</th>
                    <th className="text-left py-3 px-2">Role</th>
                    <th className="text-left py-3 px-2">Status</th>
                    <th className="text-left py-3 px-2">Trades</th>
                    <th className="text-left py-3 px-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-gray-800 text-gray-300">
                      <td className="py-3 px-2">{u.id}</td>
                      <td className="py-3 px-2 font-medium">{u.username}</td>
                      <td className="py-3 px-2 text-gray-500">{u.email}</td>
                      <td className="py-3 px-2">
                        <Badge variant={u.is_admin ? "info" : "default"}>
                          {u.is_admin ? "Admin" : "User"}
                        </Badge>
                      </td>
                      <td className="py-3 px-2">
                        <Badge variant={u.is_active ? "success" : "danger"}>
                          {u.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                      <td className="py-3 px-2">{u.total_trades}</td>
                      <td className="py-3 px-2 flex gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleToggleAdmin(u.id, u.is_admin)}>
                          <Shield className="w-3 h-3" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDeleteUser(u.id)}>
                          <Trash2 className="w-3 h-3 text-red-400" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {tab === "symbols" && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Symbols Management</CardTitle>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Add symbol (e.g. BTC/USDT)"
                  value={newSymbol}
                  onChange={(e) => setNewSymbol(e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white"
                />
                <Button size="sm" onClick={handleAddSymbol}>
                  <Plus className="w-3 h-3 mr-1" /> Add
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-800">
                    <th className="text-left py-3 px-2">ID</th>
                    <th className="text-left py-3 px-2">Symbol</th>
                    <th className="text-left py-3 px-2">Exchange</th>
                    <th className="text-left py-3 px-2">Type</th>
                    <th className="text-left py-3 px-2">Status</th>
                    <th className="text-left py-3 px-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {symbols.map((s) => (
                    <tr key={s.id} className="border-b border-gray-800 text-gray-300">
                      <td className="py-3 px-2">{s.id}</td>
                      <td className="py-3 px-2 font-medium">{s.name}</td>
                      <td className="py-3 px-2">{s.exchange}</td>
                      <td className="py-3 px-2">{s.asset_type}</td>
                      <td className="py-3 px-2">
                        <Badge variant={s.is_active ? "success" : "danger"}>
                          {s.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                      <td className="py-3 px-2">
                        <Button variant="ghost" size="sm" onClick={() => handleDeleteSymbol(s.id)}>
                          <Trash2 className="w-3 h-3 text-red-400" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {tab === "signals" && (
        <Card>
          <CardHeader>
            <CardTitle>Signals Management</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-800">
                    <th className="text-left py-3 px-2">ID</th>
                    <th className="text-left py-3 px-2">Symbol</th>
                    <th className="text-left py-3 px-2">Direction</th>
                    <th className="text-left py-3 px-2">Confidence</th>
                    <th className="text-left py-3 px-2">Entry</th>
                    <th className="text-left py-3 px-2">Status</th>
                    <th className="text-left py-3 px-2">Created</th>
                    <th className="text-left py-3 px-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.map((s) => (
                    <tr key={s.id} className="border-b border-gray-800 text-gray-300">
                      <td className="py-3 px-2">{s.id}</td>
                      <td className="py-3 px-2 font-medium">{s.symbol}</td>
                      <td className="py-3 px-2">
                        <Badge variant={s.direction === "long" ? "success" : "danger"}>
                          {s.direction?.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-2">{s.confidence}%</td>
                      <td className="py-3 px-2 font-mono">${s.entry_price?.toFixed(2)}</td>
                      <td className="py-3 px-2">
                        <Badge variant={s.is_active ? "success" : "default"}>
                          {s.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                      <td className="py-3 px-2 text-gray-500 text-xs">
                        {s.created_at ? new Date(s.created_at).toLocaleDateString() : "--"}
                      </td>
                      <td className="py-3 px-2">
                        <Button variant="ghost" size="sm" onClick={() => handleDeleteSignal(s.id)}>
                          <Trash2 className="w-3 h-3 text-red-400" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {tab === "system" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="w-4 h-4" /> Server Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: "CPU Usage", value: "23%", icon: Cpu, color: "green" },
                { label: "RAM Usage", value: "45%", icon: HardDrive, color: "blue" },
                { label: "Storage", value: "67%", icon: Database, color: "yellow" },
              ].map((m, i) => (
                <div key={i}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-400 flex items-center gap-1">
                      <m.icon className="w-3 h-3" /> {m.label}
                    </span>
                    <span className="text-gray-300">{m.value}</span>
                  </div>
                  <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full bg-${m.color}-500`} style={{ width: m.value }} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-4 h-4" /> Recent Logs
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1 max-h-48 overflow-auto">
                {logs.slice(0, 20).map((log, i) => (
                  <div key={i} className="text-[10px] font-mono text-gray-500">
                    <span className="text-gray-600">{log.created_at ? new Date(log.created_at).toLocaleTimeString() : ""}</span>{" "}
                    <span className="text-gray-400">{log.action}</span>
                  </div>
                ))}
                {logs.length === 0 && (
                  <div className="text-xs text-gray-600 text-center py-4">No logs yet</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
