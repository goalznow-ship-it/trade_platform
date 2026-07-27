"use client"

import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Activity, AlertTriangle, BarChart3, Flame, Radar, RefreshCw, Wallet } from "lucide-react"
import { DataQualityIndicator } from "@/components/data/DataQualityIndicator"

type Meta = {
  source?: string; last_updated?: string | null; data_freshness?: string
  error_reason?: string | null; provider_status?: string; is_stale?: boolean
}
type Intel = Meta & {
  btc_dominance?: Meta & { value?: number | null }
  prices?: Meta & { items?: Array<{symbol: string; price: number; change_24h: number; volume_24h: number}>; eth_btc_ratio?: Meta & {value?: number | null} }
  futures?: Meta & { items?: Array<{symbol: string; funding_rate?: number | null; open_interest_usd?: number | null; long_short_ratio?: number | null; oi_change?: number | null}> }
  liquidations?: Meta & { items?: Array<{symbol: string; price: number; notional: number; count: number; side: string}> }
  whale_transactions?: Meta & { items?: unknown[] }
  alerts?: Array<{type: string; symbol: string; message: string; last_updated: string; source: string}>
  provider_errors?: Record<string, string>
}

const money = (value?: number | null) => value == null ? "N/A" : new Intl.NumberFormat("en-US", {style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 2}).format(value)
const updated = (value?: string | null) => value ? new Date(value).toLocaleTimeString() : "N/A"

function providerMessage(meta?: Meta) {
  if (!meta || meta.provider_status === "available") return null
  if (meta.provider_status === "not_configured") return "Provider konfiqurasiya edilməyib"
  if (meta.source?.includes("CoinGecko")) return "Dominance provider-ə bağlantı yoxdur"
  if (meta.source?.includes("force orders")) return "Binance public liquidation feed hazırda deaktivdir"
  return "Provider müvəqqəti əlçatan deyil"
}

function MetaLine({meta, showMessage = true}: {meta?: Meta; showMessage?: boolean}) {
  const live = meta?.provider_status === "available" && meta?.data_freshness === "live"
  return <div className="text-[9px] text-gray-600 mt-1">
    {meta?.source || "Mənbə yoxdur"} · <span className={live ? "text-green-500" : "text-amber-500"}>{live ? "canlı" : "əlçatan deyil"}</span> · {updated(meta?.last_updated)}
    {showMessage && providerMessage(meta) && <div className="text-amber-500 mt-1">{providerMessage(meta)}</div>}
  </div>
}

export function MarketRadar() {
  const [intel, setIntel] = useState<Intel | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setIntel(await api.getMarketIntelligence()) }
    catch (exc) { setError(exc instanceof Error ? exc.message : "Market məlumatı alınmadı") }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load(); const timer = setInterval(load, 30000); return () => clearInterval(timer) }, [load])

  const futures = intel?.futures?.items || []
  const prices = intel?.prices?.items || []
  const ratios = futures.map(row => row.long_short_ratio).filter((v): v is number => v != null)
  const averageRatio = ratios.length ? ratios.reduce((a, b) => a + b, 0) / ratios.length : null
  const funding = futures.map(row => row.funding_rate).filter((v): v is number => v != null)
  const averageFunding = funding.length ? funding.reduce((a, b) => a + b, 0) / funding.length : null
  const cards = [
    ["BTC Dominantlığı", intel?.btc_dominance?.value == null ? "N/A" : `${intel.btc_dominance.value.toFixed(2)}%`, intel?.btc_dominance],
    ["ETH/BTC nisbəti", intel?.prices?.eth_btc_ratio?.value?.toFixed(6) || "N/A", intel?.prices?.eth_btc_ratio],
    ["Orta funding", averageFunding == null ? "N/A" : `${averageFunding >= 0 ? "+" : ""}${(averageFunding * 100).toFixed(4)}%`, intel?.futures],
    ["Long/Short nisbəti", averageRatio?.toFixed(3) || "N/A", intel?.futures],
  ] as const

  return <div className="h-full overflow-y-auto bg-[#0d1117] p-4 lg:p-6">
    <div className="max-w-7xl mx-auto space-y-5">
      <div className="flex justify-between items-center">
        <div><h1 className="text-lg font-semibold text-white flex items-center gap-2"><Radar className="w-5 h-5 text-purple-400"/>Market Radar</h1><p className="text-xs text-gray-500">Real qiymət, derivativ axını və bazar anomaliyaları</p></div>
        <button onClick={load} disabled={loading} className="flex items-center gap-1 px-3 py-2 text-xs bg-gray-800 rounded text-gray-300 disabled:opacity-50"><RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`}/>Yenilə</button>
      </div>
      {error && <div className="p-3 border border-red-900 bg-red-950/30 text-red-300 text-xs">{error}</div>}
      <DataQualityIndicator meta={intel} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">{cards.map(([label, value, meta]) =>
        <div key={label} className="p-4 rounded-xl border border-gray-800 bg-gray-900/50"><div className="text-[10px] text-gray-500 uppercase">{label}</div><div className="text-lg font-bold font-mono text-white mt-2">{value}</div><MetaLine meta={meta}/></div>)}
      </div>
      <section className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
        <h2 className="text-xs text-cyan-400 uppercase flex items-center gap-2 mb-3"><Activity className="w-4 h-4"/>Canlı bazar xəritəsi</h2>
        {prices.length ? (
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2">
            {prices.map((row) => <div key={row.symbol} className="rounded-lg border border-gray-800 bg-gray-950/40 p-2">
              <div className="text-[10px] text-gray-400 font-mono">{row.symbol}</div>
              <div className="text-sm font-bold text-white font-mono mt-1">{money(row.price)}</div>
              <div className={`text-[10px] font-mono ${row.change_24h >= 0 ? "text-green-400" : "text-red-400"}`}>
                {row.change_24h >= 0 ? "+" : ""}{row.change_24h.toFixed(2)}%
              </div>
              <div className="text-[9px] text-gray-600">Həcm {money(row.volume_24h)}</div>
            </div>)}
          </div>
        ) : <p className="text-xs text-gray-500">{providerMessage(intel?.prices) || "Qiymət məlumatı yoxdur"}</p>}
        <MetaLine meta={intel?.prices} showMessage={prices.length > 0}/>
      </section>
      <section className="p-4 rounded-xl border border-yellow-900/30 bg-yellow-900/5">
        <h2 className="text-xs text-yellow-400 uppercase flex items-center gap-2 mb-3"><AlertTriangle className="w-4 h-4"/>Canlı xəbərdarlıqlar</h2>
        {intel?.alerts?.length ? <div className="space-y-2">{intel.alerts.map((alert, i) => <div key={`${alert.type}-${alert.symbol}-${i}`} className="p-2 bg-gray-900/50 text-xs text-gray-300"><b>{alert.type.replaceAll("_", " ").toUpperCase()}</b> · {alert.symbol} · {alert.message}<div className="text-[9px] text-gray-600">{alert.source} · {updated(alert.last_updated)}</div></div>)}</div> : <div className="text-xs text-gray-500">Hazırda real hədləri keçən anomaliya aşkarlanmayıb.</div>}
      </section>
      <div className="grid lg:grid-cols-3 gap-4">
        <section className="p-4 rounded-xl border border-gray-800 bg-gray-900/40"><h2 className="text-xs text-blue-400 flex gap-2 mb-3"><BarChart3 className="w-4 h-4"/>AÇIQ MÖVQELƏR (OI)</h2>{futures.length ? futures.map(row => <div key={row.symbol} className="flex justify-between text-xs py-1"><span>{row.symbol}</span><span className="font-mono">{money(row.open_interest_usd)}{row.oi_change != null ? ` (${row.oi_change > 0 ? "+" : ""}${row.oi_change}%)` : ""}</span></div>) : <p className="text-xs text-gray-500">{providerMessage(intel?.futures) || "OI məlumatı yoxdur"}</p>}<MetaLine meta={intel?.futures} showMessage={futures.length > 0}/></section>
        <section className="p-4 rounded-xl border border-gray-800 bg-gray-900/40"><h2 className="text-xs text-red-400 flex gap-2 mb-3"><Flame className="w-4 h-4"/>LİKVİDASİYA AXINI</h2>{intel?.liquidations?.items?.length ? intel.liquidations.items.map((row, i) => <div key={i} className="flex justify-between text-xs py-1"><span>{row.symbol} {row.side}</span><span>{money(row.notional)} @ {money(row.price)}</span></div>) : <p className="text-xs text-gray-500">{providerMessage(intel?.liquidations) || "Son axında klaster yoxdur"}</p>}<MetaLine meta={intel?.liquidations} showMessage={!!intel?.liquidations?.items?.length}/></section>
        <section className="p-4 rounded-xl border border-gray-800 bg-gray-900/40"><h2 className="text-xs text-purple-400 flex gap-2 mb-3"><Wallet className="w-4 h-4"/>BÖYÜK TRANSFERLƏR</h2><p className="text-xs text-gray-500">{providerMessage(intel?.whale_transactions) || "Hazırda böyük transfer aşkarlanmayıb"}</p><MetaLine meta={intel?.whale_transactions} showMessage={false}/></section>
      </div>
      {intel?.is_stale && <div className="text-xs text-amber-400 flex gap-2"><Activity className="w-4 h-4"/>Məlumat köhnədir; provider statusunu yoxlayın.</div>}
    </div>
  </div>
}
