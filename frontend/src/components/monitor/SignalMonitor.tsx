"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Activity, BellRing, Clock, RefreshCw, TrendingDown, TrendingUp } from "lucide-react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

interface MonitorSignal {
  symbol: string
  direction: "long" | "short" | "neutral"
  confidence: number
  quality_score: number
  stage: "confirmed" | "watch" | "reject"
  type?: string
}

interface MonitorSnapshot {
  status: "active" | "starting"
  scan_interval_seconds: number
  watch_threshold: number
  confirmation_threshold: number
  last_updated?: string | null
  signals: MonitorSignal[]
  watching: MonitorSignal[]
  confirmed: MonitorSignal[]
  last_transitions: MonitorSignal[]
  count: number
  performance?: {
    completed_signals: number
    pending_signals: number
    win_rate: number
    long_accuracy: number
    short_accuracy: number
  }
}

export function SignalMonitor() {
  const router = useRouter()
  const [data, setData] = useState<MonitorSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [calibration, setCalibration] = useState<any>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [monitor, report] = await Promise.all([
        api.getSignalMonitor(),
        api.getSignalCalibration(90).catch(() => null),
      ])
      setData(monitor)
      setCalibration(report)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Monitor məlumatı alınmadı")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [load])

  const visible = (data?.signals || []).filter((signal) => signal.stage !== "reject")
  const performance = data?.performance
  const hasMeasuredResults = (performance?.completed_signals ?? 0) > 0

  return (
    <div className="h-full overflow-y-auto bg-[#0d1117] p-4 lg:p-6">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-semibold text-white">
              <BellRing className="h-5 w-5 text-yellow-400" /> Siqnal Monitoru
              <span className="rounded bg-blue-950 px-1.5 py-0.5 text-[9px] text-blue-300">YENİ FUNKSİYA</span>
            </h1>
            <p className="mt-1 text-xs text-gray-500">Bazarı daimi izləyir, erkən LONG/SHORT güclənməsini və təsdiqlənmiş siqnalları bildirir.</p>
          </div>
          <button onClick={load} disabled={loading} className="flex items-center gap-1.5 rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-xs text-gray-400 hover:text-white disabled:opacity-50">
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} /> Yenilə
          </button>
        </div>

        {error && <div className="rounded-lg border border-red-900/50 bg-red-950/20 p-3 text-xs text-red-300">{error}</div>}

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Metric label="Monitor statusu" value={data?.status === "active" ? "AKTİV" : "BAŞLAYIR"} color="text-green-400" />
          <Metric label="İzlənən bazar" value={data?.count ?? 0} />
          <Metric label="Erkən izləmə" value={data?.watching?.length ?? 0} color="text-yellow-400" />
          <Metric label="Təsdiqlənmiş" value={data?.confirmed?.length ?? 0} color="text-green-400" />
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="text-xs font-semibold uppercase text-gray-300">Ölçülmüş siqnal nəticələri · 90 gün</h2>
              <p className="mt-1 text-[10px] text-gray-600">
                Yalnız real bazarda entry-yə toxunmuş və TP/SL ilə bağlanmış siqnallar hesablanır.
              </p>
            </div>
            {!hasMeasuredResults && (
              <span className="rounded-md border border-yellow-900/60 bg-yellow-950/30 px-2 py-1 text-[9px] font-semibold text-yellow-400">
                MƏLUMAT TOPLANIR
              </span>
            )}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Metric label="Tamamlanmış" value={performance?.completed_signals ?? 0} />
            <Metric label="Gözləyən" value={performance?.pending_signals ?? 0} color="text-yellow-400" />
            <Metric label="Win rate" value={hasMeasuredResults ? `${performance?.win_rate.toFixed(1)}%` : "—"} color="text-green-400" />
            <Metric label="LONG dəqiqliyi" value={hasMeasuredResults ? `${performance?.long_accuracy.toFixed(1)}%` : "—"} />
            <Metric label="SHORT dəqiqliyi" value={hasMeasuredResults ? `${performance?.short_accuracy.toFixed(1)}%` : "—"} />
          </div>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="text-xs font-semibold uppercase text-gray-300">İnam kalibrasiyası · 90 gün</h2>
              <p className="mt-1 text-[10px] text-gray-600">AI inamı ilə real TP/SL nəticəsinin uyğunluğu ölçülür.</p>
            </div>
            <span className={cn("rounded px-2 py-1 text-[9px] font-semibold", calibration?.status === "measured" ? "bg-green-950 text-green-400" : "bg-yellow-950 text-yellow-400")}>
              {calibration?.status === "measured" ? "ÖLÇÜLÜB" : "MƏLUMAT TOPLANIR"} · {calibration?.sample_size ?? 0}/{calibration?.minimum_samples ?? 30}
            </span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Metric label="Gözlənən win rate" value={calibration?.expected_win_rate != null ? `${calibration.expected_win_rate}%` : "—"} />
            <Metric label="Real win rate" value={calibration?.observed_win_rate != null ? `${calibration.observed_win_rate}%` : "—"} color="text-green-400" />
            <Metric label="Kalibrasiya xətası" value={calibration?.calibration_error != null ? `${calibration.calibration_error} p.p.` : "—"} color="text-yellow-400" />
            <Metric label="Brier score" value={calibration?.brier_score ?? "—"} />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-5">
            {(calibration?.buckets ?? []).map((bucket: any) => (
              <div key={bucket.range} className="rounded border border-gray-800 bg-gray-950/50 p-2">
                <div className="text-[9px] text-gray-500">{bucket.range}% inam · n={bucket.sample_size}</div>
                <div className="mt-1 font-mono text-xs text-white">{bucket.win_rate == null ? "—" : `${bucket.win_rate}% nəticə`}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-4 lg:col-span-2">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase text-gray-300">Keyfiyyətə görə aktiv namizədlər</h2>
              <span className="flex items-center gap-1 text-[9px] text-gray-600">
                <Clock className="h-3 w-3" /> hər {data?.scan_interval_seconds ?? 60} saniyə
              </span>
            </div>
            {loading && !data ? (
              <div className="py-10 text-center text-xs text-gray-600">Monitor vəziyyəti yüklənir...</div>
            ) : visible.length === 0 ? (
              <div className="py-10 text-center text-xs text-gray-600">
                Hazırda 50% həddini keçən real namizəd yoxdur. Monitor işləməyə davam edir.
              </div>
            ) : (
              <div className="space-y-1.5">
                {visible.map((signal) => <SignalRow key={signal.symbol} signal={signal} onOpen={() => router.push(`/skhy-terminal?symbol=${encodeURIComponent(signal.symbol.replace(/[^A-Za-z0-9]/g, ""))}`)} />)}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-4">
            <h2 className="mb-3 text-xs font-semibold uppercase text-gray-300">Monitor qaydaları</h2>
            <div className="space-y-3 text-xs text-gray-400">
              <Rule color="bg-yellow-500" title={`Erkən izləmə · ${data?.watch_threshold ?? 50}%+`} text="İstiqamət güclənir, amma trade plan hələ aktiv deyil." />
              <Rule color="bg-green-500" title={`Təsdiqlənmiş · ${data?.confirmation_threshold ?? 70}%+`} text="Execution gate keçilib; entry, SL və TP Terminalda yoxlanır." />
              <Rule color="bg-blue-500" title="Spam qoruması" text="Bildiriş yalnız mərhələ və ya istiqamət dəyişəndə yaranır." />
            </div>
            <div className="mt-4 border-t border-gray-800 pt-3 text-[9px] text-gray-600">
              Son scan: {data?.last_updated ? new Date(data.last_updated).toLocaleString("az") : "gözlənilir"}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value, color = "text-white" }: { label: string; value: string | number; color?: string }) {
  return <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-4">
    <div className="text-[9px] uppercase text-gray-600">{label}</div>
    <div className={cn("mt-2 font-mono text-xl font-bold", color)}>{value}</div>
  </div>
}

function SignalRow({ signal, onOpen }: { signal: MonitorSignal; onOpen: () => void }) {
  const long = signal.direction === "long"
  return <button type="button" onClick={onOpen} className="flex w-full items-center gap-3 rounded-lg border border-gray-800 bg-gray-950/40 p-3 text-left transition-colors hover:border-blue-500/40 hover:bg-blue-950/10">
    <div className={cn("rounded-lg p-2", long ? "bg-green-950 text-green-400" : "bg-red-950 text-red-400")}>
      {long ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
    </div>
    <div className="min-w-0 flex-1">
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs font-bold text-white">{signal.symbol}</span>
        <span className={long ? "text-[9px] font-bold text-green-400" : "text-[9px] font-bold text-red-400"}>{signal.direction.toUpperCase()}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-800">
        <div className={cn("h-full rounded-full", signal.stage === "confirmed" ? "bg-green-500" : "bg-yellow-500")} style={{ width: `${signal.quality_score}%` }} />
      </div>
    </div>
    <div className="text-right">
      <div className="font-mono text-xs font-bold text-white">Q{signal.quality_score.toFixed(0)}</div>
      <div className="text-[9px] text-gray-500">{signal.confidence.toFixed(0)}% inam</div>
      <div className="mt-1 text-[9px] font-medium text-blue-400">Ətraflı bax →</div>
    </div>
  </button>
}

function Rule({ color, title, text }: { color: string; title: string; text: string }) {
  return <div className="flex gap-2">
    <span className={cn("mt-1 h-2 w-2 shrink-0 rounded-full", color)} />
    <div><div className="font-medium text-gray-300">{title}</div><div className="mt-0.5 text-[10px] text-gray-600">{text}</div></div>
  </div>
}
