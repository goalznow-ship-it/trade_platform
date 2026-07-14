"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter, usePathname } from "next/navigation"
import { useAuth } from "@/hooks/useAuth"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import {
  Search, Menu, X, Wallet, Bell, BellRing,
  Settings, LogOut, User, Clock,
  Brain, Radio, BarChart3, Newspaper,
  LayoutDashboard, TrendingUp, Activity,
  Scan, Shield, ChevronDown, History, Radar,
} from "lucide-react"
import { cn, formatPrice, formatPercent } from "@/lib/utils"

const MODULES = [
  { href: "/terminal", label: "AI Terminal", icon: Brain, color: "text-blue-400" },
  { href: "/signals", label: "AI Signals", icon: Radio, color: "text-green-400" },
  { href: "/radar", label: "Market Radar", icon: Activity, color: "text-purple-400" },
  { href: "/scanner", label: "Scanner", icon: Scan, color: "text-cyan-400" },
  { href: "/futures", label: "Futures Intel", icon: BarChart3, color: "text-orange-400" },
  { href: "/news", label: "News Intel", icon: Newspaper, color: "text-yellow-400" },
  { href: "/backtest", label: "Backtest", icon: History, color: "text-green-400" },
  { href: "/dashboard", label: "Portfolio", icon: Shield, color: "text-gray-400" },
]

export function Navbar() {
  const { user, logout } = useAuth()
  const router = useRouter()
  const pathname = usePathname()
  const [overview, setOverview] = useState<any>(null)
  const [showMobileMenu, setShowMobileMenu] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [time, setTime] = useState(new Date())
  const isDashboard = pathname?.startsWith("/dashboard") || pathname === "/terminal" || pathname === "/signals" || pathname === "/futures" || pathname === "/news" || pathname === "/scanner" || pathname === "/radar" || pathname === "/backtest" || pathname === "/admin" || pathname === "/pricing"

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
    <header className="sticky top-0 z-50 bg-gray-950/98 backdrop-blur-md">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 h-12 border-b border-gray-800/60">
        <div className="flex items-center gap-3">
          <button className="lg:hidden p-1 text-gray-400 hover:text-white" onClick={() => setShowMobileMenu(!showMobileMenu)}>
            {showMobileMenu ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          <Link href={isDashboard ? "/dashboard" : "/"} className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-bold text-white hidden sm:inline">TradeAnalyst</span>
            <span className="text-[10px] text-blue-400 font-semibold px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20">PRO</span>
          </Link>

          {isDashboard && (
            <div className="relative hidden md:block">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
              <input
                type="text"
                placeholder="Search markets..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-56 pl-8 pr-3 py-1.5 text-xs bg-gray-800/80 border border-gray-700/60 rounded-md text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500/60 focus:bg-gray-800"
              />
              {searchResults.length > 0 && (
                <div className="absolute top-full mt-1 w-full bg-gray-900 border border-gray-700 rounded-md shadow-xl max-h-60 overflow-auto">
                  {searchResults.map((s) => (
                    <button key={s.symbol}
                      className="w-full text-left px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-800 font-mono"
                      onClick={() => { setSearchQuery("") }}
                    >{s.symbol}</button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isDashboard && (
            <div className="hidden lg:flex items-center gap-2 text-[11px]">
              {overview?.btc_price && (
                <div className="flex items-center gap-1.5 px-2 py-1 bg-gray-800/40 rounded border border-gray-700/30">
                  <span className="text-orange-400 font-semibold">BTC</span>
                  <span className="text-white font-mono font-medium">{formatPrice(overview.btc_price, 0)}</span>
                  <span className={cn("font-mono", overview.btc_change >= 0 ? "text-green-400" : "text-red-400")}>
                    {formatPercent(overview.btc_change)}
                  </span>
                </div>
              )}
              {overview?.eth_price && (
                <div className="flex items-center gap-1.5 px-2 py-1 bg-gray-800/40 rounded border border-gray-700/30">
                  <span className="text-blue-400 font-semibold">ETH</span>
                  <span className="text-white font-mono font-medium">{formatPrice(overview.eth_price, 0)}</span>
                </div>
              )}
              <div className="flex items-center gap-1 px-2 py-1 bg-gray-800/40 rounded border border-gray-700/30 text-gray-400">
                <Clock className="w-3 h-3" />
                {time.toLocaleTimeString("en-US", { hour12: false })}
              </div>
            </div>
          )}

          {user ? (
            <div className="flex items-center gap-1.5">
              <NotificationBell />
              {isDashboard && (
                <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 bg-gray-800/40 rounded border border-gray-700/30">
                  <Wallet className="w-3 h-3 text-green-400" />
                  <span className="text-xs text-white font-mono font-medium">
                    {overview?.btc_price ? formatPrice(overview.btc_price * 0.1, 0) : "---"}
                  </span>
                </div>
              )}
              <div className="relative group">
                <button className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-gray-800/60 transition-colors">
                  <div className="w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center">
                    <span className="text-[10px] font-medium">{user.username[0].toUpperCase()}</span>
                  </div>
                  <span className="text-xs text-gray-300 hidden md:block">{user.username}</span>
                  <ChevronDown className="w-3 h-3 text-gray-500" />
                </button>
                <div className="absolute right-0 top-full mt-0.5 w-44 bg-gray-900 border border-gray-700/60 rounded-md shadow-xl py-1 hidden group-hover:block">
                  <Link href="/dashboard"
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-gray-300 hover:bg-gray-800">
                    <LayoutDashboard className="w-3.5 h-3.5" /> Dashboard
                  </Link>
                  <button className="w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-gray-800 flex items-center gap-2">
                    <User className="w-3.5 h-3.5" /> Profile
                  </button>
                  <button className="w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-gray-800 flex items-center gap-2">
                    <Settings className="w-3.5 h-3.5" /> Settings
                  </button>
                  <div className="border-t border-gray-700/60 my-1" />
                  <button onClick={() => { logout(); router.push("/") }}
                    className="w-full text-left px-3 py-2 text-xs text-red-400 hover:bg-gray-800 flex items-center gap-2">
                    <LogOut className="w-3.5 h-3.5" /> Logout
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-1.5">
              <Link href="/login"
                className="px-3 py-1.5 text-xs text-gray-400 hover:text-white transition-colors">
                Sign In
              </Link>
              <Link href="/register"
                className="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors">
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Module Tabs - Bloomberg Style */}
      {isDashboard && (
        <div className="hidden lg:flex items-center px-4 h-9 border-b border-gray-800/60 bg-gray-950/80">
          <nav className="flex items-center gap-0.5">
            {MODULES.map((mod) => {
              const isActive = pathname === mod.href || (
                mod.href === "/dashboard" && (
                  pathname === "/dashboard" ||
                  (pathname !== "/terminal" && pathname !== "/signals" && pathname !== "/futures" && pathname !== "/news" && pathname !== "/scanner")
                )
              )
              return (
                <Link key={mod.href} href={mod.href}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium rounded-t transition-colors relative",
                    isActive
                      ? "text-white bg-gray-800/60 border-t border-x border-gray-700/40"
                      : "text-gray-500 hover:text-gray-300 hover:bg-gray-800/30"
                  )}>
                  <mod.icon className={cn("w-3.5 h-3.5", isActive ? mod.color : "")} />
                  {mod.label}
                  {isActive && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500 rounded-full" />}
                </Link>
              )
            })}
          </nav>
          <div className="flex-1" />
          <div className="text-[10px] text-gray-600 flex items-center gap-2">
            <Activity className="w-3 h-3" />
            {overview?.market_status || "Market Open"}
          </div>
        </div>
      )}

      {showMobileMenu && (
        <div className="lg:hidden border-b border-gray-800 bg-gray-950 p-3">
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
            <input type="text" placeholder="Search..."
              className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-xs text-gray-200 focus:outline-none focus:border-blue-500" />
          </div>
          <div className="grid grid-cols-2 gap-1">
            {[
              { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
              { label: "AI Terminal", href: "/terminal", icon: Brain },
              { label: "AI Signals", href: "/signals", icon: Radio },
              { label: "Market Radar", href: "/radar", icon: Activity },
              { label: "Market Scanner", href: "/scanner", icon: Scan },
              { label: "Futures Intel", href: "/futures", icon: BarChart3 },
              { label: "News Intel", href: "/news", icon: Newspaper },
              { label: "Backtesting", href: "/backtest", icon: History },
              { label: "Pricing", href: "/pricing", icon: TrendingUp },
              { label: "Admin", href: "/admin", icon: Settings },
            ].map((item) => (
              <Link key={item.label} href={item.href}
                className="flex items-center gap-2 px-3 py-2 text-gray-300 hover:bg-gray-800 rounded text-xs"
                onClick={() => setShowMobileMenu(false)}>
                <item.icon className="w-3.5 h-3.5 text-gray-500" />
                {item.label}
              </Link>
            ))}
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
      <Button variant="ghost" size="sm" className="hidden sm:flex !px-1.5">
        {unread > 0 ? <BellRing className="w-4 h-4 text-yellow-400" /> : <Bell className="w-4 h-4 text-gray-400" />}
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-red-500 rounded-full text-[8px] flex items-center justify-center text-white font-bold">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </Button>
    </div>
  )
}
