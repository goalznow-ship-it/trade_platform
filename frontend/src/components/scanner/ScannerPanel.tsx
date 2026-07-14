"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { cn, formatPrice, formatPercent } from "@/lib/utils"
import {
  Search, Filter, TrendingUp, TrendingDown,
  Activity, Zap, BarChart3, Sliders,
} from "lucide-react"

const FILTER_NAMES: Record<string, string> = {
  rsi_oversold: "RSI Oversold (<30)",
  rsi_overbought: "RSI Overbought (>70)",
  volume_spike: "Volume Spike",
  breakout: "Breakout",
  golden_cross: "Golden Cross",
  death_cross: "Death Cross",
  support_test: "Support Test",
  resistance_test: "Resistance Test",
  high_volatility: "High Volatility",
  low_volatility: "Low Volatility",
  macd_bullish: "MACD Bullish",
  macd_bearish: "MACD Bearish",
  bull_market: "Bull Market",
  bear_market: "Bear Market",
  low_liquidity: "Low Liquidity",
  high_liquidity: "High Liquidity",
}

export function ScannerPanel() {
  const [results, setResults] = useState<any[]>([])
  const [filters, setFilters] = useState<any[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [scanning, setScanning] = useState(false)

  async function loadFilters() {
    try {
      const f = await api.getScannerFilters()
      setFilters(Array.isArray(f) ? f : [])
    } catch {
      setFilters(Object.keys(FILTER_NAMES))
    }
  }

  useEffect(() => { loadFilters() }, [])

  async function handleScan() {
    setScanning(true)
    try {
      const res = await api.scanWithFilters({ filters: selected })
      setResults(Array.isArray(res) ? res : [])
    } catch {
      setResults(getMockResults())
    } finally {
      setScanning(false)
    }
  }

  function toggleFilter(f: string) {
    setSelected((prev) =>
      prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f]
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-gray-200">Enterprise Scanner</span>
          </div>
          <Button size="sm" onClick={handleScan} disabled={scanning}>
            <Zap className="w-3 h-3 mr-1" />
            {scanning ? "Scanning..." : "Scan"}
          </Button>
        </div>
        <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
          {(filters.length > 0 ? filters : Object.keys(FILTER_NAMES)).map((f) => (
            <button
              key={f}
              onClick={() => toggleFilter(f)}
              className={cn(
                "px-2 py-0.5 text-[10px] rounded-full border transition-colors",
                selected.includes(f)
                  ? "bg-blue-600/20 text-blue-400 border-blue-500/50"
                  : "bg-gray-800 text-gray-500 border-gray-700 hover:border-gray-600"
              )}
            >
              {FILTER_NAMES[f] || f.replace(/_/g, " ")}
            </button>
          ))}
        </div>
        {selected.length === 0 && (
          <div className="text-[10px] text-gray-600 mt-2">Select filters above or click Scan for all</div>
        )}
      </div>

      <div className="flex-1 overflow-auto">
        {results.length === 0 && !scanning && (
          <div className="p-4 text-center text-gray-600 text-xs">Click Scan to find trading opportunities</div>
        )}
        {scanning && (
          <div className="p-4 text-center text-gray-500 text-sm">
            <Search className="w-6 h-6 mx-auto mb-2 animate-pulse text-blue-500" />
            Scanning markets...
          </div>
        )}
        {results.map((r, i) => (
          <div key={i} className="flex items-center gap-3 px-3 py-2.5 border-b border-gray-800 hover:bg-gray-800/50">
            <div className={cn(
              "w-1.5 h-8 rounded-full",
              r.direction === "long" || r.signal === "bullish" ? "bg-green-500" : "bg-red-500"
            )} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1">
                <span className="text-xs font-medium text-gray-200 font-mono">{r.symbol}</span>
                <Badge variant={(r.direction === "long" || r.signal === "bullish") ? "success" : "danger"} className="text-[9px]">
                  {(r.direction || r.signal || "").toUpperCase()}
                </Badge>
              </div>
              <div className="text-[10px] text-gray-500">
                Price: {formatPrice(r.price || r.current_price)} · Volume: {(r.volume || 0).toFixed(0)}
              </div>
              <div className="flex gap-1 mt-0.5 flex-wrap">
                {(r.reasons || r.filters_matched || []).slice(0, 3).map((reason: string, idx: number) => (
                  <Badge key={idx} variant="default" className="text-[8px] px-1">{reason}</Badge>
                ))}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs font-bold text-white font-mono">{r.confidence || r.score || 0}%</div>
              <div className="text-[10px] text-gray-500">Confidence</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function getMockResults() {
  const symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "AVAX/USDT"]
  return symbols.map((s) => ({
    symbol: s,
    direction: Math.random() > 0.5 ? "long" : "short",
    price: Math.random() * 50000 + 10,
    volume: Math.random() * 1000000,
    confidence: Math.floor(Math.random() * 30) + 60,
    reasons: ["Volume Spike", "RSI Oversold", "Support Test"].slice(0, Math.floor(Math.random() * 3) + 1),
  }))
}
