"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/hooks/useAuth"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import {
  Search,
  Menu,
  X,
  Wallet,
  Bell,
  Settings,
  LogOut,
  User,
  Clock,
  TrendingUp,
  Activity,
} from "lucide-react"
import { cn, formatPrice, formatPercent } from "@/lib/utils"

export function Navbar() {
  const { user, logout } = useAuth()
  const [overview, setOverview] = useState<any>(null)
  const [showMobileMenu, setShowMobileMenu] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [time, setTime] = useState(new Date())

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
          <div className="flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-blue-500" />
            <span className="text-lg font-bold text-white hidden sm:inline">TradeAnalyst</span>
            <span className="text-xs text-blue-400 font-medium">PRO</span>
          </div>

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
        </div>

        <div className="flex items-center gap-3">
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

          {user ? (
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" className="hidden sm:flex">
                <Bell className="w-4 h-4" />
              </Button>
              <div className="flex items-center gap-2 px-2 py-1 bg-gray-800/50 rounded">
                <Wallet className="w-3.5 h-3.5 text-green-400" />
                <span className="text-xs text-white font-mono">
                  {overview?.btc_price ? formatPrice(overview.btc_price * 0.1, 0) : "---"}
                </span>
              </div>
              <div className="relative group">
                <button className="flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-800">
                  <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center">
                    <span className="text-xs font-medium">{user.username[0].toUpperCase()}</span>
                  </div>
                  <span className="text-sm text-gray-300 hidden md:block">{user.username}</span>
                </button>
                <div className="absolute right-0 top-full mt-1 w-48 bg-gray-900 border border-gray-700 rounded-lg shadow-xl py-1 hidden group-hover:block">
                  <button className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 flex items-center gap-2">
                    <User className="w-4 h-4" /> Profile
                  </button>
                  <button className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 flex items-center gap-2">
                    <Settings className="w-4 h-4" /> Settings
                  </button>
                  <div className="border-t border-gray-700 my-1" />
                  <button
                    onClick={logout}
                    className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-gray-800 flex items-center gap-2"
                  >
                    <LogOut className="w-4 h-4" /> Logout
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => {}}>
                Sign In
              </Button>
              <Button size="sm" onClick={() => {}}>
                Get Started
              </Button>
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
          <div className="space-y-2 text-sm">
            <button className="w-full text-left px-3 py-2 text-gray-300 hover:bg-gray-800 rounded">Dashboard</button>
            <button className="w-full text-left px-3 py-2 text-gray-300 hover:bg-gray-800 rounded">Markets</button>
            <button className="w-full text-left px-3 py-2 text-gray-300 hover:bg-gray-800 rounded">Analysis</button>
            <button className="w-full text-left px-3 py-2 text-gray-300 hover:bg-gray-800 rounded">Portfolio</button>
            {user?.is_admin && (
              <button className="w-full text-left px-3 py-2 text-purple-400 hover:bg-gray-800 rounded">Admin</button>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
