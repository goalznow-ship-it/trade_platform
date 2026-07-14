"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter, usePathname } from "next/navigation"
import { useAuth } from "@/hooks/useAuth"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import {
  Search,
  Menu,
  X,
  Wallet,
  Bell,
  BellRing,
  Settings,
  LogOut,
  User,
  Clock,
  TrendingUp,
  Activity,
  LayoutDashboard,
  Brain,
  Radio,
  BarChart3,
} from "lucide-react"
import { cn, formatPrice, formatPercent } from "@/lib/utils"

export function Navbar() {
  const { user, logout } = useAuth()
  const router = useRouter()
  const pathname = usePathname()
  const [overview, setOverview] = useState<any>(null)
  const [showMobileMenu, setShowMobileMenu] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [time, setTime] = useState(new Date())
  const isDashboard = pathname?.startsWith("/dashboard")

  useEffect(() => {
    api.getOverview().then(setOverview).catch(() => {})
    const interval = setInterval(() => {
      setTime(new Date())
      api.getOverview().then(setOverview).catch(() => {})
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (searchQuery.length >= 1) {
      api.searchSymbols(searchQuery).then(setSearchResults).catch(() => setSearchResults([]))
    } else {
      setSearchResults([])
    }
  }, [searchQuery])

  return (
      <header className="sticky top-0 z-50 border-b border-gray-800 bg-gray-950/95 backdrop-blur-md">
        <div className="flex items-center justify-between px-4 h-14">
          <div className="flex items-center gap-4">
            <button className="lg:hidden p-1 text-gray-400" onClick={() => setShowMobileMenu(!showMobileMenu)}>
              {showMobileMenu ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <Link href={isDashboard ? "/dashboard" : "/"} className="flex items-center gap-2">
              <TrendingUp className="w-6 h-6 text-blue-500" />
              <span className="text-lg font-bold text-white hidden sm:inline">TradeAnalyst</span>
              <span className="text-xs text-blue-400 font-medium">PRO</span>
            </Link>

            {isDashboard && (
              <div className="relative hidden md:block">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search markets..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-64 pl-9 pr-3 py-1.5 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
                />
                {searchResults.length > 0 && (
                  <div className="absolute top-full mt-1 w-full bg-gray-900 border border-gray-700 rounded-lg shadow-xl max-h-60 overflow-auto">
                    {searchResults.map((s) => (
                      <button
                        key={s.symbol}
                        className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
                        onClick={() => setSearchQuery("")}
                      >
                        {s.symbol}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Quick Nav Links */}
          {isDashboard && (
            <div className="hidden md:flex items-center gap-1 mr-2">
              <Link href="/terminal"
                className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
                <Brain className="w-3.5 h-3.5" /> Terminal
              </Link>
              <Link href="/signals"
                className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
                <Radio className="w-3.5 h-3.5" /> Signals
              </Link>
              <Link href="/futures"
                className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
                <BarChart3 className="w-3.5 h-3.5" /> Futures
              </Link>
            </div>
          )}

          <div className="flex items-center gap-3">
            {isDashboard && (
              <div className="hidden lg:flex items-center gap-3 text-xs">
                {overview?.btc_price && (
                  <div className="flex items-center gap-1 px-2 py-1 bg-gray-800/50 rounded">
                    <span className="text-orange-400 font-medium">BTC</span>
                    <span className="text-white font-mono">{formatPrice(overview.btc_price, 0)}</span>
                    <span className={overview.btc_change >= 0 ? "text-green-400" : "text-red-400"}>
                      {formatPercent(overview.btc_change)}
                    </span>
                  </div>
                )}
                {overview?.eth_price && (
                  <div className="flex items-center gap-1 px-2 py-1 bg-gray-800/50 rounded">
                    <span className="text-blue-400 font-medium">ETH</span>
                    <span className="text-white font-mono">{formatPrice(overview.eth_price, 0)}</span>
                  </div>
                )}
                <div className="flex items-center gap-1 px-2 py-1 bg-gray-800/50 rounded text-gray-400">
                  <Clock className="w-3 h-3" />
                  {time.toLocaleTimeString("en-US", { hour12: false })}
                </div>
              </div>
            )}

            {user ? (
              <div className="flex items-center gap-2">
                <NotificationBell />
                {isDashboard && (
                  <div className="flex items-center gap-2 px-2 py-1 bg-gray-800/50 rounded">
                    <Wallet className="w-3.5 h-3.5 text-green-400" />
                    <span className="text-xs text-white font-mono">
                      {overview?.btc_price ? formatPrice(overview.btc_price * 0.1, 0) : "---"}
                    </span>
                  </div>
                )}
                <div className="relative group">
                  <button className="flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-800">
                    <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center">
                      <span className="text-xs font-medium">{user.username[0].toUpperCase()}</span>
                    </div>
                    <span className="text-sm text-gray-300 hidden md:block">{user.username}</span>
                  </button>
                  <div className="absolute right-0 top-full mt-1 w-48 bg-gray-900 border border-gray-700 rounded-lg shadow-xl py-1 hidden group-hover:block">
                    <Link href="/dashboard"
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800">
                      <LayoutDashboard className="w-4 h-4" /> Dashboard
                    </Link>
                    <button className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 flex items-center gap-2">
                      <User className="w-4 h-4" /> Profile
                    </button>
                    <button className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 flex items-center gap-2">
                      <Settings className="w-4 h-4" /> Settings
                    </button>
                    <div className="border-t border-gray-700 my-1" />
                    <button
                      onClick={() => { logout(); router.push("/") }}
                      className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-gray-800 flex items-center gap-2"
                    >
                      <LogOut className="w-4 h-4" /> Logout
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link href="/login"
                  className="px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors">
                  Sign In
                </Link>
                <Link href="/register"
                  className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
                  Get Started
                </Link>
              </div>
            )}
          </div>
        </div>

        {showMobileMenu && (
        <div className="lg:hidden border-t border-gray-800 bg-gray-950 p-4">
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search..."
              className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200"
            />
          </div>
          <div className="grid grid-cols-2 gap-1 text-sm">
            {[
              { label: "Dashboard", href: "/dashboard" },
              { label: "AI Terminal", href: "/terminal" },
              { label: "Signals", href: "/signals" },
              { label: "Charts", href: "/dashboard" },
              { label: "Scanner", href: "/dashboard" },
              { label: "Watchlist", href: "/dashboard" },
              { label: "Alerts", href: "/dashboard" },
              { label: "Portfolio", href: "/dashboard" },
              { label: "Risk", href: "/dashboard" },
              { label: "Journal", href: "/dashboard" },
              { label: "Paper", href: "/dashboard" },
              { label: "Futures", href: "/futures" },
              { label: "Backtest", href: "/dashboard" },
              { label: "Notifications", href: "/dashboard" },
              { label: "News", href: "/dashboard" },
            ].map((item) => (
              <Link key={item.label} href={item.href}
                className="px-3 py-2 text-gray-300 hover:bg-gray-800 rounded text-xs">
                {item.label}
              </Link>
            ))}
            {user?.is_admin && (
              <Link href="/dashboard"
                className="px-3 py-2 text-purple-400 hover:bg-gray-800 rounded text-xs">
                Admin
              </Link>
            )}
          </div>
        </div>
      )}
    </header>
  )
}

function NotificationBell() {
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    api.getNotifications().then((n) => {
      const arr = Array.isArray(n) ? n : []
      setUnread(arr.filter((x: any) => !x.is_read).length)
    }).catch(() => {})
    const interval = setInterval(() => {
      api.getNotifications().then((n) => {
        const arr = Array.isArray(n) ? n : []
        setUnread(arr.filter((x: any) => !x.is_read).length)
      }).catch(() => {})
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="relative">
      <Button variant="ghost" size="sm" className="hidden sm:flex">
        {unread > 0 ? <BellRing className="w-4 h-4 text-yellow-400" /> : <Bell className="w-4 h-4" />}
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[9px] flex items-center justify-center text-white font-medium">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </Button>
    </div>
  )
}
