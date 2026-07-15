"use client"

import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  Users, Activity, Shield,
  TrendingUp, DollarSign,
  Server, Database, Wifi, Zap,
} from "lucide-react"

interface AdminStats {
  total_users?: number
  active_users?: number
  total_signals?: number
  active_signals?: number
  total_trades?: number
  total_symbols?: number
}

interface AdminUser {
  id: number
  username: string
  email: string
  subscription_tier?: string
  total_trades?: number
  win_rate?: number
  is_active: boolean
}

interface AdminSignal {
  id: number
  symbol: string
  direction?: string
  confidence?: number
  entry_price?: number
  reason?: string
  is_active?: boolean
}

interface AdminRevenue {
  total_revenue?: number
  monthly_recurring?: number
  paid_subscriptions?: number
}

export function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [signals, setSignals] = useState<AdminSignal[]>([])
  const [, setSubscriptions] = useState<AdminUser[]>([])
  const [revenue, setRevenue] = useState<AdminRevenue | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<string>("overview")

  const load = useCallback(async () => {
    try {
      const [s, u, sig, sub, rev] = await Promise.all([
        api.getAdminStats().catch(() => null),
        api.getAdminUsers().catch(() => []),
        api.getAdminSignals().catch(() => []),
        request("/api/v1/admin/subscriptions").catch(() => []),
        request("/api/v1/admin/revenue").catch(() => null),
      ])
      setStats(s)
      setUsers(Array.isArray(u) ? u : [])
      setSignals(Array.isArray(sig) ? sig : [])
      setSubscriptions(Array.isArray(sub) ? sub : [])
      setRevenue(rev)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) {
    return (
      <div className="h-full overflow-y-auto bg-[#0d1117] p-4 lg:p-6">
        <div className="max-w-7xl mx-auto space-y-4">
          <div className="animate-pulse grid grid-cols-4 gap-3">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-24 bg-gray-800 rounded-xl" />)}
          </div>
          <div className="h-64 bg-gray-800 rounded-xl" />
        </div>
      </div>
    )
  }

  const tabs = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "users", label: "Users", icon: Users },
    { id: "subscriptions", label: "Subscriptions", icon: DollarSign },
    { id: "signals", label: "Signals", icon: TrendingUp },
  ]

  return (
    <div className="h-full overflow-y-auto bg-[#0d1117]">
      <div className="max-w-7xl mx-auto p-4 lg:p-6 space-y-5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">Admin Panel</h1>
            <p className="text-xs text-gray-500">System management & monitoring</p>
          </div>
        </div>

        {/* Tab Bar */}
        <div className="flex gap-1 p-1 rounded-lg border border-gray-800 bg-gray-900/50">
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-1.5 px-4 py-2 text-xs rounded-md transition-all flex-1 justify-center",
                activeTab === tab.id ? "bg-gray-800 text-white" : "text-gray-500 hover:text-gray-300 hover:bg-gray-800/50"
              )}>
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "overview" && (
          <>
            {/* Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
                <Users className="w-4 h-4 text-blue-400 mb-2" />
                <div className="text-2xl font-bold text-white">{stats?.total_users || 0}</div>
                <div className="text-[10px] text-gray-500">Total Users</div>
                <div className="text-[10px] text-green-400 mt-1">{stats?.active_users || 0} active</div>
              </div>
              <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
                <TrendingUp className="w-4 h-4 text-green-400 mb-2" />
                <div className="text-2xl font-bold text-white">{stats?.total_signals || 0}</div>
                <div className="text-[10px] text-gray-500">Total Signals</div>
                <div className="text-[10px] text-green-400 mt-1">{stats?.active_signals || 0} active</div>
              </div>
              <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
                <DollarSign className="w-4 h-4 text-yellow-400 mb-2" />
                <div className="text-2xl font-bold text-white">${revenue?.total_revenue?.toFixed(0) || 0}</div>
                <div className="text-[10px] text-gray-500">Total Revenue</div>
                <div className="text-[10px] text-green-400 mt-1">${revenue?.monthly_recurring || 0}/mo MRR</div>
              </div>
              <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
                <Server className="w-4 h-4 text-purple-400 mb-2" />
                <div className="text-2xl font-bold text-white">{stats?.total_trades || 0}</div>
                <div className="text-[10px] text-gray-500">Total Trades</div>
                <div className="text-[10px] text-gray-400 mt-1">{stats?.total_symbols || 0} symbols</div>
              </div>
            </div>

            {/* System Health */}
            <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
              <div className="flex items-center gap-2 mb-3">
                <Server className="w-4 h-4 text-gray-400" />
                <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">System Status</h2>
              </div>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                  { label: "API", status: "operational", icon: Activity },
                  { label: "Database", status: "connected", icon: Database },
                  { label: "WebSocket", status: `${10} clients`, icon: Wifi },
                  { label: "Cache", status: "connected", icon: Zap },
                ].map((s) => (
                  <div key={s.label} className="flex items-center gap-2 p-2.5 rounded-lg bg-gray-800/30">
                    <div className="w-2 h-2 rounded-full bg-green-400" />
                    <div className="flex-1">
                      <div className="text-xs text-gray-400">{s.label}</div>
                      <div className="text-[10px] text-green-400">{s.status}</div>
                    </div>
                    <s.icon className="w-3.5 h-3.5 text-gray-600" />
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Users */}
            <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Recent Users</h2>
                <button onClick={() => setActiveTab("users")} className="text-[10px] text-blue-400 hover:text-blue-300">View All</button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-800">
                      <th className="text-left py-2 pr-3">User</th>
                      <th className="text-left py-2 pr-3">Email</th>
                      <th className="text-center py-2 pr-3">Plan</th>
                      <th className="text-center py-2 pr-3">Trades</th>
                      <th className="text-center py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.slice(0, 5).map((u) => (
                      <tr key={u.id} className="border-b border-gray-800/50 text-gray-400">
                        <td className="py-2 pr-3 font-medium text-white">{u.username}</td>
                        <td className="py-2 pr-3">{u.email}</td>
                        <td className="py-2 pr-3 text-center">
                          <span className={cn(
                            "px-1.5 py-0.5 rounded text-[9px] font-medium",
                            u.subscription_tier === "pro" ? "bg-blue-900/50 text-blue-400" :
                            u.subscription_tier === "elite" ? "bg-purple-900/50 text-purple-400" :
                            "bg-gray-800 text-gray-500"
                          )}>
                            {(u.subscription_tier || "free").toUpperCase()}
                          </span>
                        </td>
                        <td className="py-2 pr-3 text-center">{u.total_trades || 0}</td>
                        <td className="py-2 text-center">
                          <span className={cn("px-1.5 py-0.5 rounded text-[9px]",
                            u.is_active ? "bg-green-900/40 text-green-400" : "bg-red-900/40 text-red-400"
                          )}>
                            {u.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {activeTab === "users" && (
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
            <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3">All Users</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-800">
                    <th className="text-left py-2 pr-2">ID</th>
                    <th className="text-left py-2 pr-2">Username</th>
                    <th className="text-left py-2 pr-2">Email</th>
                    <th className="text-center py-2 pr-2">Plan</th>
                    <th className="text-center py-2 pr-2">Trades</th>
                    <th className="text-center py-2 pr-2">Win Rate</th>
                    <th className="text-center py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-gray-800/50 text-gray-400 hover:bg-gray-800/20">
                      <td className="py-2 pr-2 font-mono text-gray-500">{u.id}</td>
                      <td className="py-2 pr-2 font-medium text-white">{u.username}</td>
                      <td className="py-2 pr-2">{u.email}</td>
                      <td className="py-2 pr-2 text-center">
                        <span className={cn(
                          "px-1.5 py-0.5 rounded text-[9px] font-medium",
                          u.subscription_tier === "pro" ? "bg-blue-900/50 text-blue-400" :
                          u.subscription_tier === "elite" ? "bg-purple-900/50 text-purple-400" :
                          "bg-gray-800 text-gray-500"
                        )}>
                          {(u.subscription_tier || "free").toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 pr-2 text-center">{u.total_trades || 0}</td>
                      <td className="py-2 pr-2 text-center">{(u.win_rate || 0).toFixed(1)}%</td>
                      <td className="py-2 text-center">
                        <span className={cn("px-1.5 py-0.5 rounded text-[9px]",
                          u.is_active ? "bg-green-900/40 text-green-400" : "bg-red-900/40 text-red-400"
                        )}>
                          {u.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "subscriptions" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
              <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3">Revenue Breakdown</h2>
              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 rounded-lg bg-gray-800/30">
                  <span className="text-sm text-gray-300">Monthly Recurring Revenue</span>
                  <span className="text-lg font-bold text-green-400 font-mono">${revenue?.monthly_recurring || 0}/mo</span>
                </div>
                <div className="flex justify-between items-center p-3 rounded-lg bg-gray-800/30">
                  <span className="text-sm text-gray-300">Total Revenue</span>
                  <span className="text-lg font-bold text-white font-mono">${revenue?.total_revenue?.toFixed(0) || 0}</span>
                </div>
                <div className="flex justify-between items-center p-3 rounded-lg bg-gray-800/30">
                  <span className="text-sm text-gray-300">Paid Subscriptions</span>
                  <span className="text-lg font-bold text-white font-mono">{revenue?.paid_subscriptions || 0}</span>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
              <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3">Tier Distribution</h2>
              <div className="space-y-2">
                {[
                  { tier: "free", label: "Free", count: users.filter(u => !u.subscription_tier || u.subscription_tier === "free").length, color: "bg-gray-600" },
                  { tier: "pro", label: "Pro ($29/mo)", count: users.filter(u => u.subscription_tier === "pro").length, color: "bg-blue-500" },
                  { tier: "elite", label: "Elite ($99/mo)", count: users.filter(u => u.subscription_tier === "elite").length, color: "bg-purple-500" },
                ].map((t) => (
                  <div key={t.tier} className="p-3 rounded-lg bg-gray-800/30">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-300">{t.label}</span>
                      <span className="text-white font-mono">{t.count}</span>
                    </div>
                    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${t.color}`}
                        style={{ width: `${users.length > 0 ? (t.count / users.length) * 100 : 0}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === "signals" && (
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
            <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3">Generated Signals</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-800">
                    <th className="text-left py-2 pr-2">ID</th>
                    <th className="text-left py-2 pr-2">Symbol</th>
                    <th className="text-center py-2 pr-2">Direction</th>
                    <th className="text-center py-2 pr-2">Confidence</th>
                    <th className="text-right py-2 pr-2">Entry</th>
                    <th className="text-right py-2 pr-2">Reason</th>
                    <th className="text-right py-2">Active</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.slice(0, 20).map((s) => (
                    <tr key={s.id} className="border-b border-gray-800/50 text-gray-400 hover:bg-gray-800/20">
                      <td className="py-2 pr-2 font-mono text-gray-500">{s.id}</td>
                      <td className="py-2 pr-2 font-medium text-white font-mono">{s.symbol}</td>
                      <td className="py-2 pr-2 text-center">
                        <span className={cn("px-1.5 py-0.5 rounded text-[9px] font-medium",
                          s.direction === "long" || s.direction === "buy" ? "bg-green-900/50 text-green-400" :
                          s.direction === "short" || s.direction === "sell" ? "bg-red-900/50 text-red-400" :
                          "bg-gray-800 text-gray-500"
                        )}>
                          {(s.direction || "").toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 pr-2 text-center font-mono">{s.confidence || 0}%</td>
                      <td className="py-2 pr-2 text-right font-mono">${(s.entry_price || 0).toFixed(2)}</td>
                      <td className="py-2 pr-2 text-right text-gray-500 max-w-[200px] truncate">{s.reason || "--"}</td>
                      <td className="py-2 text-center">
                        <span className={s.is_active ? "text-green-400" : "text-gray-600"}>
                          {s.is_active ? "●" : "○"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

async function request(url: string) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null
  const headers: Record<string, string> = {}
  if (token) headers["Authorization"] = `Bearer ${token}`
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  const res = await fetch(`${base}${url}`, { headers })
  if (!res.ok) throw new Error("Request failed")
  return res.json()
}
