"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { cn, formatPrice } from "@/lib/utils"
import { Activity, AlertTriangle, Power, Radar, Shield } from "lucide-react"

interface Candidate {
  symbol: string
  direction: string
  price: number
  confidence: number
  pre_score: number
  net_edge_pct: number
  eligible: boolean
  execution_approved: boolean
  reasons: string[]
  rejection_reasons: string[]
}

interface ScalperState {
  armed: boolean
  mode: "paper"
  last_scan?: string | null
  market_count?: number
  deep_analyzed?: number
  eligible_count?: number
  error?: string | null
  candidates: Candidate[]
  config: {
    capital_usdt: number
    risk_per_trade_pct: number
    daily_loss_limit_pct: number
    max_positions: number
    min_score: number
    max_leverage: number
    scan_interval_seconds: number
  }
}

export function AutoScalperPanel() {
  const [state, setState] = useState<ScalperState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [capital, setCapital] = useState(10)
  const [minScore, setMinScore] = useState(82)
  const [risk, setRisk] = useState(0.5)

  async function load() {
    try {
      const data = await api.getAutoScalperStatus()
      setState(data)
      setCapital(data.config?.capital_usdt ?? 10)
      setMinScore(data.config?.min_score ?? 82)
      setRisk(data.config?.risk_per_trade_pct ?? 0.5)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Auto Scalper statusu alınmadı")
    }
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 10000)
    return () => clearInterval(interval)
  }, [])

  async function action(fn: () => Promise<ScalperState>) {
    setBusy(true); setError(null)
    try { setState(await fn()) } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Əməliyyat tamamlanmadı")
    } finally { setBusy(false) }
  }

  const config = {
    mode: "paper",
    capital_usdt: capital,
    risk_per_trade_pct: risk,
    daily_loss_limit_pct: 3,
    max_positions: 1,
    min_score: minScore,
    max_leverage: 3,
    scan_interval_seconds: 20,
  }

  return (
    <div className="h-full overflow-auto bg-[#0d1117] p-4">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h1 className="flex items-center gap-2 text-xl font-bold text-white"><Radar className="text-cyan-400" /> Auto Scalper</h1><p className="text-xs text-gray-500">Bütün Binance USDT perpetual bazarı · real data · Paper execution lock</p></div>
          <div className="flex items-center gap-2"><Badge variant={state?.armed ? "success" : "default"}>{state?.armed ? "ARMED · PAPER" : "DISARMED"}</Badge>{state?.armed ? <Button variant="danger" disabled={busy} onClick={() => action(api.disarmAutoScalper)}><Power className="mr-1 h-4 w-4" /> STOP</Button> : <Button disabled={busy} onClick={() => action(() => api.armAutoScalper(config))}><Power className="mr-1 h-4 w-4" /> PAPER ARM</Button>}</div>
        </div>

        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200"><AlertTriangle className="mr-2 inline h-4 w-4" />Live order icrası kilidlidir. Bu mərhələ real bazarı skan edir və paper üçün uyğun namizədləri müəyyənləşdirir.</div>

        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-xs text-gray-400">Scalper kapitalı (USDT)<input type="number" min={5} value={capital} onChange={(e) => setCapital(Number(e.target.value))} disabled={state?.armed} className="mt-1 w-full rounded border border-gray-700 bg-gray-900 p-2 text-white" /></label>
          <label className="text-xs text-gray-400">Trade riski (%)<input type="number" min={0.1} max={2} step={0.1} value={risk} onChange={(e) => setRisk(Number(e.target.value))} disabled={state?.armed} className="mt-1 w-full rounded border border-gray-700 bg-gray-900 p-2 text-white" /></label>
          <label className="text-xs text-gray-400">Minimum score<input type="number" min={70} max={99} value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} disabled={state?.armed} className="mt-1 w-full rounded border border-gray-700 bg-gray-900 p-2 text-white" /></label>
        </div>

        <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
          {[["Bazar", state?.market_count ?? 0], ["Dərin analiz", state?.deep_analyzed ?? 0], ["Uyğun", state?.eligible_count ?? 0], ["Max mövqe", 1], ["Max leverage", "3x"]].map(([label, value]) => <div key={String(label)} className="rounded border border-gray-800 bg-gray-900 p-3"><div className="text-[10px] uppercase text-gray-500">{label}</div><div className="text-lg font-bold text-white">{value}</div></div>)}
        </div>

        <div className="flex items-center justify-between"><div className="text-xs text-gray-500">Son scan: {state?.last_scan ? new Date(state.last_scan).toLocaleTimeString() : "hələ yoxdur"}</div><Button variant="ghost" disabled={busy} onClick={() => action(api.scanAutoScalper)}><Activity className="mr-1 h-4 w-4" />{busy ? "Skan edilir..." : "İndi skan et"}</Button></div>
        {error || state?.error ? <div className="rounded border border-red-500/30 bg-red-500/5 p-2 text-xs text-red-300">{error || state?.error}</div> : null}

        <div className="overflow-hidden rounded-lg border border-gray-800">
          <div className="grid grid-cols-[1.2fr_.7fr_.7fr_.7fr_.7fr] bg-gray-900 px-3 py-2 text-[10px] uppercase text-gray-500"><span>Coin</span><span>İstiqamət</span><span>AI score</span><span>Net edge</span><span>Status</span></div>
          {!state?.candidates?.length ? <div className="p-8 text-center text-sm text-gray-600">Skan başladıldıqdan sonra real namizədlər burada görünəcək</div> : state.candidates.map((item) => <div key={item.symbol} className="grid grid-cols-[1.2fr_.7fr_.7fr_.7fr_.7fr] items-center border-t border-gray-800 px-3 py-2 text-xs"><span><b className="text-white">{item.symbol}</b><small className="block text-gray-600">{formatPrice(item.price)}</small></span><span className={item.direction === "long" ? "text-green-400" : item.direction === "short" ? "text-red-400" : "text-gray-500"}>{item.direction.toUpperCase()}</span><span className="text-white">{item.confidence.toFixed(1)}</span><span className={cn(item.net_edge_pct > 0 ? "text-green-400" : "text-red-400")}>{item.net_edge_pct.toFixed(3)}%</span><span><Badge variant={item.eligible ? "success" : "default"}>{item.eligible ? "ELIGIBLE" : "WAIT"}</Badge></span></div>)}
        </div>
        <div className="flex items-center gap-2 text-[11px] text-gray-600"><Shield className="h-4 w-4" />Execution gate, minimum net edge, spread və liquidity filtrləri keçməyən heç bir namizəd trade-eligible sayılmır.</div>
      </div>
    </div>
  )
}
