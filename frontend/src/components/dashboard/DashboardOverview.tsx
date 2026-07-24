"use client"

import { DashboardStats } from "@/components/dashboard/DashboardStats"
import { MarketOverview } from "@/components/dashboard/MarketOverview"
import { TopSignals } from "@/components/dashboard/TopSignals"
import { ActivePositions } from "@/components/dashboard/ActivePositions"
import { SentimentWidget } from "@/components/dashboard/SentimentWidget"
import { PortfolioSummary } from "@/components/dashboard/PortfolioSummary"
import { MarketSummary } from "@/components/dashboard/MarketSummary"
import { AIConfidencePanel } from "@/components/dashboard/AIConfidencePanel"
import { EngineStatus } from "@/components/dashboard/EngineStatus"
import { useEffect, useState, memo } from "react"
import { api } from "@/lib/api"
import { useMarketStore } from "@/store/market"
import { cn, formatPrice, formatPercent, formatVolume, getChangeColor } from "@/lib/utils"
import {
  BarChart3, TrendingUp, TrendingDown, Activity,
  Globe, Wallet, Coins, Percent, Clock, AlertCircle,
  Zap, Shield, Brain, GanttChart,
} from "lucide-react"

interface FearGreedData {
  value: number
  classification: string
}

interface MarketOverviewData {
  total_market_cap?: number
  total_volume_24h?: number
  btc_dominance?: number
  altcoin_dominance?: number
}

interface LiveTicker {
  symbol: string
  price?: number
  change_percent?: number
  volume_24h?: number
  high_24h?: number
  low_24h?: number
}

const InfoCard = memo(function InfoCard({
  icon: Icon, label, value, sub, color, loading,
}: {
  icon: React.ElementType; label: string; value: string; sub?: string; color?: string; loading?: boolean
}) {
  if (loading) {
    return (
      <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
        <div className="animate-pulse space-y-2">
          <div className="h-3 w-20 bg-gray-800 rounded" />
          <div className="h-5 w-16 bg-gray-800 rounded" />
        </div>
      </div>
    )
  }
  return (
    <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50 hover:bg-gray-900 hover:border-gray-700 transition-all cursor-default">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">{label}</span>
        <Icon className={cn("w-3.5 h-3.5", color || "text-gray-600")} />
      </div>
      <div className={cn("text-lg font-bold font-mono tracking-tight", color || "text-white")}>{value}</div>
      {sub && <div className="text-[9px] text-gray-600 mt-0.5">{sub}</div>}
    </div>
  )
})

export function DashboardOverview() {
  const isLive = useMarketStore((s) => s.isLive)
  const fearGreed = useMarketStore((s) => s.fearGreed)
  const tickers = useMarketStore((s) => s.tickers)
  const lastPerChannel = useMarketStore((s) => s.lastPerChannel)

  const [marketData, setMarketData] = useState<MarketOverviewData | null>(null)
  const [gainers, setGainers] = useState<LiveTicker[]>([])
  const [losers, setLosers] = useState<LiveTicker[]>([])
  const [oiData, setOiData] = useState<any[]>([])
  const [fundingData, setFundingData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [now, setNow] = useState(Date.now)

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    let mounted = true
    async function load() {
      try {
        const [overview, g, l, oi, fr] = await Promise.allSettled([
          api.getOverview(),
          api.getMarketGainers(5),
          api.getMarketLosers(5),
          api.getOpenInterest(5),
          api.getFundingRates(5),
        ])
        if (!mounted) return
        if (overview.status === "fulfilled") setMarketData(overview.value)
        if (g.status === "fulfilled") setGainers(g.value?.gainers || [])
        if (l.status === "fulfilled") setLosers(l.value?.losers || [])
        if (oi.status === "fulfilled") setOiData(oi.value?.open_interest || [])
        if (fr.status === "fulfilled") setFundingData(fr.value?.funding_rates || [])
      } catch { /* ignore */ }
      setLoading(false)
    }
    load()
    const interval = setInterval(load, isLive ? 60000 : 30000)
    return () => { mounted = false; clearInterval(interval) }
  }, [isLive])

  const btc = tickers["BTC/USDT"]
  const btcDom = marketData?.btc_dominance
  const altDom = marketData?.altcoin_dominance
  const marketCap = marketData?.total_market_cap
  const totalVol = marketData?.total_volume_24h
  const lastUpdate = lastPerChannel["ticker"]
  const ago = lastUpdate ? `${Math.floor((now - lastUpdate) / 1000)}s` : null

  return (
    <div className="h-full overflow-y-auto p-4 lg:p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-lg font-semibold text-white">İdarə Paneli</h1>
          <p className="text-xs text-gray-500 mt-0.5">Real-time portfel izləmə və bazar kəşfiyyatı</p>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-gray-500">
          {isLive && <span className="flex items-center gap-1 text-green-400"><Zap className="w-3 h-3" />CANLI</span>}
          {ago && <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{ago}</span>}
          {!lastUpdate && <span className="text-red-400 flex items-center gap-1"><AlertCircle className="w-3 h-3" />Köhnə məlumat</span>}
        </div>
      </div>

      {/* Market Stats - Real-time */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-8 gap-2">
        <InfoCard icon={Globe} label="Fear & Greed" value={fearGreed ? `${fearGreed.value} (${fearGreed.classification})` : "N/A"} loading={loading} color={fearGreed && fearGreed.value > 50 ? "text-green-400" : "text-red-400"} />
        <InfoCard icon={BarChart3} label="BTC Dominance" value={btcDom != null ? formatPercent(btcDom) : "--"} loading={loading} color="text-orange-400" />
        <InfoCard icon={Coins} label="Altcoin Dominance" value={altDom != null ? formatPercent(altDom) : "--"} loading={loading} color="text-purple-400" />
        <InfoCard icon={Wallet} label="Bazar Dəyəri" value={marketCap ? formatVolume(marketCap) : "--"} loading={loading} color="text-cyan-400" />
        <InfoCard icon={Activity} label="24h Həcm" value={totalVol ? formatVolume(totalVol) : "--"} loading={loading} />
        <InfoCard icon={TrendingUp} label="BTC 24h" value={btc?.change != null ? formatPercent(btc.change) : "--"} loading={loading} color={getChangeColor(btc?.change ?? null)} />
        <InfoCard icon={Percent} label="BTC Həcm" value={btc?.volume_24h ? formatVolume(btc.volume_24h) : "--"} loading={loading} />
        <InfoCard icon={Brain} label="AI Etibar" value={fearGreed ? `${fearGreed.value}%` : "--"} loading={loading} color="text-purple-400" />
      </div>

      {/* Gainers & Losers + Funding + OI */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
        {/* Top Gainers */}
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <h3 className="text-[10px] font-semibold text-green-400 uppercase tracking-wider mb-2">📈 Ən Çox Artanlar</h3>
          <div className="space-y-1">
            {gainers.length === 0 && <span className="text-[10px] text-gray-600">Məlumat yoxdur</span>}
            {gainers.slice(0, 5).map((g: any) => (
              <div key={g.symbol} className="flex items-center justify-between text-[11px]">
                <span className="text-gray-300 font-mono">{g.symbol}</span>
                <span className="text-green-400 font-mono">+{g.change_percent?.toFixed(2) || "0.00"}%</span>
              </div>
            ))}
          </div>
        </div>
        {/* Top Losers */}
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <h3 className="text-[10px] font-semibold text-red-400 uppercase tracking-wider mb-2">📉 Ən Çox Düşənlər</h3>
          <div className="space-y-1">
            {losers.length === 0 && <span className="text-[10px] text-gray-600">Məlumat yoxdur</span>}
            {losers.slice(0, 5).map((l: any) => (
              <div key={l.symbol} className="flex items-center justify-between text-[11px]">
                <span className="text-gray-300 font-mono">{l.symbol}</span>
                <span className="text-red-400 font-mono">{l.change_percent?.toFixed(2) || "0.00"}%</span>
              </div>
            ))}
          </div>
        </div>
        {/* Funding Rates */}
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <h3 className="text-[10px] font-semibold text-blue-400 uppercase tracking-wider mb-2">💧 Funding Rates</h3>
          <div className="space-y-1">
            {fundingData.length === 0 && <span className="text-[10px] text-gray-600">Məlumat yoxdur</span>}
            {fundingData.slice(0, 5).map((f: any) => (
              <div key={f.symbol} className="flex items-center justify-between text-[11px]">
                <span className="text-gray-300 font-mono">{f.symbol}</span>
                <span className={cn("font-mono", (f.funding_rate || 0) > 0 ? "text-green-400" : "text-red-400")}>
                  {(f.funding_rate * 100).toFixed(4)}%
                </span>
              </div>
            ))}
          </div>
        </div>
        {/* Open Interest */}
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <h3 className="text-[10px] font-semibold text-yellow-400 uppercase tracking-wider mb-2">📊 Açıq Maraq</h3>
          <div className="space-y-1">
            {oiData.length === 0 && <span className="text-[10px] text-gray-600">Məlumat yoxdur</span>}
            {oiData.slice(0, 5).map((o: any) => (
              <div key={o.symbol} className="flex items-center justify-between text-[11px]">
                <span className="text-gray-300 font-mono">{o.symbol}</span>
                <span className="font-mono text-gray-400">{o.open_interest_usd ? formatVolume(o.open_interest_usd) : "--"}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <DashboardStats />

      <MarketSummary />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 space-y-4">
          <MarketOverview />
          <TopSignals />
        </div>
        <div className="space-y-4">
          <AIConfidencePanel />
          <SentimentWidget />
          <EngineStatus />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ActivePositions />
        <PortfolioSummary />
      </div>
    </div>
  )
}
