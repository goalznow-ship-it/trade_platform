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
  mode: "paper" | "live"
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
  const [mode, setMode] = useState<"paper" | "live">("paper")
  const [liveConfirmation, setLiveConfirmation] = useState("")
  const [liveReady, setLiveReady] = useState(false)
  const [liveReason, setLiveReason] = useState("Binance API və server icazəsi tələb olunur")
  const [soak, setSoak] = useState<any>(null)

  async function load() {
    try {
      const [data, trading, soakStatus] = await Promise.all([
        api.getAutoScalperStatus(),
        api.getTradingStatus().catch(() => null),
        api.getAutoScalperSoakStatus().catch(() => null),
      ])
      setState(data)
      setSoak(soakStatus)
      if (!data.armed) setMode(data.mode ?? "paper")
      setCapital(data.config?.capital_usdt ?? 10)
      setMinScore(data.config?.min_score ?? 82)
      setRisk(data.config?.risk_per_trade_pct ?? 0.5)
      const ready = Boolean(
        trading?.accepting_live_orders
        && trading?.configured_exchanges?.includes("binance"),
      )
      setLiveReady(ready)
      setLiveReason(
        !trading?.configured_exchanges?.includes("binance")
          ? "Binance API qoşulmayıb"
          : trading?.kill_switch_active
            ? "Emergency kill-switch aktivdir"
            : !trading?.live_trading_enabled
              ? "Serverdə live trading bağlıdır"
              : ready ? "Live execution hazırdır" : "Live execution hazır deyil",
      )
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
    mode,
    capital_usdt: capital,
    risk_per_trade_pct: risk,
    daily_loss_limit_pct: 3,
    max_positions: 1,
    min_score: minScore,
    max_leverage: 3,
    scan_interval_seconds: 20,
    live_confirmation: mode === "live" ? liveConfirmation : undefined,
  }

  async function soakAction(fn: () => Promise<any>) {
    setBusy(true); setError(null)
    try {
      setSoak(await fn())
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Soak-test əməliyyatı tamamlanmadı")
    } finally { setBusy(false) }
  }

  return (
    <div className="h-full overflow-auto bg-[#0d1117] p-4">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h1 className="flex items-center gap-2 text-xl font-bold text-white"><Radar className="text-cyan-400" /> Auto Scalper</h1><p className="text-xs text-gray-500">Bütün Binance USDT perpetual bazarı · real data · iki ayrı execution rejimi</p></div>
          <div className="flex items-center gap-2"><Badge variant={state?.armed ? state.mode === "live" ? "danger" : "success" : "default"}>{state?.armed ? `ARMED · ${state.mode.toUpperCase()}` : "DISARMED"}</Badge>{state?.armed ? <Button variant="danger" disabled={busy} onClick={() => action(api.disarmAutoScalper)}><Power className="mr-1 h-4 w-4" /> STOP</Button> : <Button variant={mode === "live" ? "danger" : "primary"} disabled={busy || (mode === "live" && (!liveReady || liveConfirmation !== "REAL PULLA AUTO TRADE"))} onClick={() => action(() => api.armAutoScalper(config))}><Power className="mr-1 h-4 w-4" /> {mode.toUpperCase()} ARM</Button>}</div>
        </div>

        <div className="grid grid-cols-2 rounded-lg bg-gray-900 p-1">
          {(["paper", "live"] as const).map((item) => <button key={item} disabled={state?.armed} onClick={() => { setMode(item); setLiveConfirmation("") }} className={cn("rounded py-2 text-xs font-bold", mode === item ? item === "live" ? "bg-red-600 text-white" : "bg-blue-600 text-white" : "text-gray-500", state?.armed && "opacity-50")}>{item === "paper" ? "PAPER AUTO" : "LIVE AUTO"}</button>)}
        </div>

        {mode === "paper" ? <div className="rounded-lg border border-blue-500/30 bg-blue-500/5 p-3 text-xs text-blue-200"><Shield className="mr-2 inline h-4 w-4" />Real Binance məlumatı, virtual kapital. Uyğun namizəd yarananda avtomatik paper mövqe açılır və SL/TP ilə idarə olunur.</div> : <div className="space-y-2 rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-xs text-red-200"><div><AlertTriangle className="mr-2 inline h-4 w-4" /><b>REAL PUL REJİMİ.</b> {liveReason}</div><p>Aktivləşdirmək üçün aşağıya <b>REAL PULLA AUTO TRADE</b> yaz:</p><input value={liveConfirmation} onChange={(event) => setLiveConfirmation(event.target.value)} disabled={state?.armed || !liveReady} placeholder="REAL PULLA AUTO TRADE" className="w-full rounded border border-red-500/30 bg-black/30 p-2 font-mono text-white outline-none" /></div>}

        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-xs text-gray-400">Scalper kapitalı (USDT)<input type="number" min={5} value={capital} onChange={(e) => setCapital(Number(e.target.value))} disabled={state?.armed} className="mt-1 w-full rounded border border-gray-700 bg-gray-900 p-2 text-white" /></label>
          <label className="text-xs text-gray-400">Trade riski (%)<input type="number" min={0.1} max={2} step={0.1} value={risk} onChange={(e) => setRisk(Number(e.target.value))} disabled={state?.armed} className="mt-1 w-full rounded border border-gray-700 bg-gray-900 p-2 text-white" /></label>
          <label className="text-xs text-gray-400">Minimum score<input type="number" min={70} max={99} value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} disabled={state?.armed} className="mt-1 w-full rounded border border-gray-700 bg-gray-900 p-2 text-white" /></label>
        </div>

        <div className="rounded-xl border border-cyan-900/50 bg-cyan-950/10 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-white">72 saatlıq PAPER soak-test</h2>
              <p className="mt-1 text-[10px] text-gray-500">Real Binance datası, virtual kapital, avtomatik bitmə və ölçülmüş nəticə.</p>
            </div>
            {soak?.status === "running" ? (
              <Button variant="danger" disabled={busy} onClick={() => soakAction(api.stopAutoScalperSoak)}>Testi dayandır</Button>
            ) : (
              <Button variant="primary" disabled={busy || Boolean(state?.mode === "live" && state?.armed)} onClick={() => soakAction(() => api.startAutoScalperSoak({ duration_hours: 72, capital_usdt: capital, risk_per_trade_pct: risk, min_score: minScore }))}>72 saat başlat</Button>
            )}
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-800"><div className="h-full rounded-full bg-cyan-500" style={{ width: `${soak?.progress_pct ?? 0}%` }} /></div>
          <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-6">
            {[["Status", soak?.status ?? "başlamayıb"], ["İrəliləyiş", `${soak?.progress_pct ?? 0}%`], ["Bağlı trade", soak?.closed_trades ?? 0], ["Net PnL", `${soak?.net_pnl ?? 0} USDT`], ["Max DD", `${soak?.max_drawdown_usdt ?? 0} USDT`], ["Nəticə", soak?.verdict ?? "collecting"]].map(([label, value]) => <div key={String(label)} className="rounded border border-gray-800 bg-gray-950/50 p-2"><div className="text-[9px] uppercase text-gray-600">{label}</div><div className="mt-1 font-mono text-xs font-semibold text-white">{value}</div></div>)}
          </div>
          <p className="mt-2 text-[9px] text-gray-600">Yekun qərar üçün minimum {soak?.minimum_trades_for_verdict ?? 20} bağlanmış trade tələb olunur. Bu test LIVE order aça bilməz.</p>
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
