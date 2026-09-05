"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"

type Tab = "overview" | "history" | "quality"

interface PerformanceStats {
  total_signals?: number
  resolved_signals?: number
  win_rate?: number
  avg_pnl_percent?: number
  sharpe?: number
  max_drawdown?: number
  profit_factor?: number
  total_pnl_percent?: number
}

interface AccuracyPoint {
  date: string
  hit_rate: number
  n_resolved: number
}

interface CalibrationReport {
  total_signals?: number
  bucket?: Array<{
    confidence_band: string
    predicted: number
    actual: number
    n: number
  }>
}

export function PerformanceDashboard() {
  const [tab, setTab] = useState<Tab>("overview")
  const [stats, setStats] = useState<PerformanceStats | null>(null)
  const [accuracy, setAccuracy] = useState<AccuracyPoint[]>([])
  const [calibration, setCalibration] = useState<CalibrationReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    Promise.all([
      api.getPerformanceStats(days),
      api.getAccuracyOverTime(days),
      api.getCalibrationReport(days),
    ])
      .then(([s, a, c]) => {
        if (cancelled) return
        setStats(s as PerformanceStats)
        setAccuracy((a as AccuracyPoint[]) || [])
        setCalibration(c as CalibrationReport)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err?.message || "Failed to load performance data")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [days])

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-white">Performance & History</h1>
        <p className="text-sm text-gray-400 mt-1">
          Track signal accuracy, calibration drift, and the per-engine
          quality gate in one place. The numbers are pulled from
          <code className="text-emerald-400 mx-1">/api/v1/performance/*</code>
          so what you see here is what the cron-driven quality
          gate is reading.
        </p>
      </header>

      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-2">
          <TabButton active={tab === "overview"} onClick={() => setTab("overview")}>
            Overview
          </TabButton>
          <TabButton active={tab === "history"} onClick={() => setTab("history")}>
            History
          </TabButton>
          <TabButton active={tab === "quality"} onClick={() => setTab("quality")}>
            Quality Gate
          </TabButton>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(parseInt(e.target.value, 10))}
          className="bg-[#161b22] border border-gray-700 text-white text-sm rounded-md px-3 py-1.5"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={180}>Last 180 days</option>
          <option value={365}>Last 365 days</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-300 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <Skeleton />
      ) : tab === "overview" ? (
        <OverviewTab stats={stats} accuracy={accuracy} calibration={calibration} />
      ) : tab === "history" ? (
        <HistoryTab accuracy={accuracy} />
      ) : (
        <QualityGateTab />
      )}
    </div>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
        active
          ? "bg-emerald-600 text-white"
          : "bg-[#161b22] text-gray-400 hover:text-white hover:bg-[#1c2128]"
      }`}
    >
      {children}
    </button>
  )
}

function Skeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="bg-[#161b22] border border-gray-800 rounded-lg p-4 h-24 animate-pulse"
        />
      ))}
    </div>
  )
}

function MetricCard({
  label,
  value,
  hint,
  color = "text-white",
}: {
  label: string
  value: string | number
  hint?: string
  color?: string
}) {
  return (
    <div className="bg-[#161b22] border border-gray-800 rounded-lg p-4">
      <div className="text-xs uppercase tracking-wide text-gray-500">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${color}`}>{value}</div>
      {hint && <div className="text-xs text-gray-500 mt-1">{hint}</div>}
    </div>
  )
}

function OverviewTab({
  stats,
  accuracy,
  calibration,
}: {
  stats: PerformanceStats | null
  accuracy: AccuracyPoint[]
  calibration: CalibrationReport | null
}) {
  if (!stats) {
    return (
      <div className="text-gray-500 text-center py-12">
        No performance data yet. The resolver needs resolved signals before
        these numbers become meaningful.
      </div>
    )
  }
  const hitRate = stats.win_rate ?? 0
  const hitColor =
    hitRate >= 0.55 ? "text-emerald-400" : hitRate >= 0.4 ? "text-yellow-400" : "text-red-400"
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Hit rate"
          value={`${(hitRate * 100).toFixed(1)}%`}
          hint={`${stats.resolved_signals ?? 0} resolved of ${stats.total_signals ?? 0}`}
          color={hitColor}
        />
        <MetricCard
          label="Avg forward return"
          value={`${(stats.avg_pnl_percent ?? 0).toFixed(2)}%`}
          hint="Mean across resolved signals"
        />
        <MetricCard
          label="Sharpe"
          value={(stats.sharpe ?? 0).toFixed(2)}
          hint="Risk-adjusted return"
        />
        <MetricCard
          label="Profit factor"
          value={(stats.profit_factor ?? 0).toFixed(2)}
          hint="Sum wins / |sum losses|"
        />
        <MetricCard
          label="Max drawdown"
          value={`${(stats.max_drawdown ?? 0).toFixed(2)}%`}
          hint="Worst peak-to-trough"
          color="text-red-400"
        />
        <MetricCard
          label="Total PnL"
          value={`${(stats.total_pnl_percent ?? 0).toFixed(2)}%`}
          hint="Cumulative across the window"
          color={(stats.total_pnl_percent ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}
        />
      </div>

      <section>
        <h2 className="text-lg font-semibold text-white mb-3">Calibration</h2>
        <p className="text-sm text-gray-400 mb-3">
          Predicted vs actual hit rate per confidence bucket. A well-calibrated
          engine has predicted ≈ actual in every row.
        </p>
        <div className="bg-[#161b22] border border-gray-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[#0d1117] text-gray-400">
              <tr>
                <th className="text-left px-4 py-2">Confidence band</th>
                <th className="text-right px-4 py-2">Predicted</th>
                <th className="text-right px-4 py-2">Actual</th>
                <th className="text-right px-4 py-2">n</th>
                <th className="text-right px-4 py-2">Drift</th>
              </tr>
            </thead>
            <tbody className="text-white">
              {(calibration?.bucket || []).map((row) => {
                const drift = row.actual - row.predicted
                const driftColor = Math.abs(drift) < 0.05 ? "text-gray-300" : drift > 0 ? "text-emerald-400" : "text-red-400"
                return (
                  <tr key={row.confidence_band} className="border-t border-gray-800">
                    <td className="px-4 py-2 font-mono text-xs">{row.confidence_band}</td>
                    <td className="px-4 py-2 text-right">{(row.predicted * 100).toFixed(1)}%</td>
                    <td className="px-4 py-2 text-right">{(row.actual * 100).toFixed(1)}%</td>
                    <td className="px-4 py-2 text-right text-gray-400">{row.n}</td>
                    <td className={`px-4 py-2 text-right ${driftColor}`}>
                      {drift > 0 ? "+" : ""}
                      {(drift * 100).toFixed(1)}%
                    </td>
                  </tr>
                )
              })}
              {(!calibration?.bucket || calibration.bucket.length === 0) && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                    Not enough resolved signals yet for calibration buckets.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-white mb-3">Accuracy over time</h2>
        <AccuracySparkline data={accuracy} />
      </section>
    </div>
  )
}

function HistoryTab({ accuracy }: { accuracy: AccuracyPoint[] }) {
  if (accuracy.length === 0) {
    return (
      <div className="text-gray-500 text-center py-12">
        No historical data points yet. The accuracy series fills in
        as the resolver walks forward through signals.
      </div>
    )
  }
  return (
    <div className="bg-[#161b22] border border-gray-800 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-[#0d1117] text-gray-400">
          <tr>
            <th className="text-left px-4 py-2">Date</th>
            <th className="text-right px-4 py-2">Hit rate</th>
            <th className="text-right px-4 py-2">Resolved</th>
          </tr>
        </thead>
        <tbody className="text-white">
          {accuracy.map((row, i) => {
            const color =
              row.hit_rate >= 0.55
                ? "text-emerald-400"
                : row.hit_rate >= 0.4
                ? "text-yellow-400"
                : "text-red-400"
            return (
              <tr key={i} className="border-t border-gray-800">
                <td className="px-4 py-2 font-mono text-xs">{row.date}</td>
                <td className={`px-4 py-2 text-right font-mono ${color}`}>
                  {(row.hit_rate * 100).toFixed(1)}%
                </td>
                <td className="px-4 py-2 text-right text-gray-400">{row.n_resolved}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function QualityGateTab() {
  // The quality gate has its own admin surface at /admin/quality.
  // The tab here is a thin pointer to that — full UI is in the
  // admin section so the read-only dashboard stays read-only.
  return (
    <div className="bg-[#161b22] border border-gray-800 rounded-lg p-6">
      <h2 className="text-lg font-semibold text-white">Engine quality gate</h2>
      <p className="text-sm text-gray-400 mt-2">
        Per-engine hit-rate, MAE, MFE and auto-disable state are surfaced
        in the admin dashboard. Operators can:
      </p>
      <ul className="text-sm text-gray-400 list-disc pl-6 mt-2 space-y-1">
        <li>View every engine&apos;s current status (ok / degraded / disabled).</li>
        <li>Read the disabled reason and the time the engine was tripped.</li>
        <li>Force a re-evaluation or re-enable an engine with a reason.</li>
        <li>See the in-process circuit breaker state per engine.</li>
      </ul>
      <a
        href="/admin"
        className="inline-block mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm rounded-md"
      >
        Open admin dashboard
      </a>
    </div>
  )
}

function AccuracySparkline({ data }: { data: AccuracyPoint[] }) {
  // A small inline SVG sparkline so we don't need a charting
  // dependency. The chart is intentionally minimal: x is the
  // index, y is the hit rate scaled to 0-100.
  if (data.length === 0) {
    return (
      <div className="text-gray-500 text-sm">No data yet for a sparkline.</div>
    )
  }
  const w = 600
  const h = 80
  const stepX = data.length > 1 ? w / (data.length - 1) : 0
  const points = data
    .map((d, i) => {
      const x = i * stepX
      const y = h - d.hit_rate * h
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(" ")
  return (
    <div className="bg-[#161b22] border border-gray-800 rounded-lg p-4">
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="h-24">
        {/* Reference line at 50% hit rate. */}
        <line x1="0" y1={h / 2} x2={w} y2={h / 2} stroke="#374151" strokeDasharray="4 4" />
        <polyline
          fill="none"
          stroke="#10b981"
          strokeWidth="2"
          points={points}
        />
      </svg>
      <div className="flex justify-between text-xs text-gray-500 mt-2">
        <span>{data[0]?.date}</span>
        <span>{data[data.length - 1]?.date}</span>
      </div>
    </div>
  )
}
