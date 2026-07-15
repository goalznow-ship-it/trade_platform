"use client"

import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  Brain, Activity, Server, Zap,
  TrendingUp, TrendingDown, AlertTriangle, BarChart3,
  Target, Cpu, RefreshCw,
} from "lucide-react"

interface BrainAssessment {
  overall_market_score?: number
  bull_probability?: number
  bear_probability?: number
  crash_probability?: number
  short_squeeze_probability?: number
  long_squeeze_probability?: number
  alt_season_probability?: number
  confidence?: number
  regime?: string
  contributing_factors?: string[]
  sub_scores?: Record<string, number>
  engine_results?: Record<string, unknown>
}

interface EngineStatus {
  engines?: Record<string, boolean>
  loaded_count?: number
  total_engines?: number
}

interface SelfLearningReport {
  current_weights?: Record<string, number>
  default_weights?: Record<string, number>
  weight_delta?: Record<string, number>
  performance_metrics?: {
    total_trades?: number
    win_rate?: number
    profit_factor?: number
    sharpe_ratio?: number
    max_drawdown_percent?: number
    avg_risk_reward?: number
  }
  recommendations?: string[]
  total_trades_recorded?: number
  total_weight_adjustments?: number
}

interface SystemStatus {
  websocket?: {
    total_clients?: number
    channels?: Record<string, number>
  }
  streaming?: {
    running?: boolean
    workers?: Record<string, { last_heartbeat_ago_secs: number; alive: boolean }>
    worker_count?: number
  }
}

function ScoreBar({ label, score, maxScore }: { label: string; score: number; maxScore?: number }) {
  const max = maxScore || 100
  const pct = Math.min(100, (score / max) * 100)
  const color = score >= 70 ? "bg-green-500" : score >= 45 ? "bg-yellow-500" : "bg-red-500"
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-gray-400 w-24 shrink-0 truncate">{label}</span>
      <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-mono text-gray-300 w-8 text-right">{score.toFixed(0)}</span>
    </div>
  )
}

function RegimeBadge({ regime }: { regime?: string }) {
  if (!regime) return null
  const colors: Record<string, string> = {
    strong_bullish: "bg-green-900/50 text-green-400 border-green-700",
    bullish: "bg-green-900/30 text-green-300 border-green-700/50",
    neutral: "bg-gray-800 text-gray-400 border-gray-700",
    bearish: "bg-red-900/30 text-red-300 border-red-700/50",
    strong_bearish: "bg-red-900/50 text-red-400 border-red-700",
    crash_risk: "bg-red-950/50 text-red-400 border-red-700 blink",
    squeeze_risk: "bg-orange-900/50 text-orange-400 border-orange-700",
  }
  return (
    <span className={cn(
      "px-2 py-0.5 rounded text-[10px] font-medium border",
      colors[regime] || "bg-gray-800 text-gray-400 border-gray-700"
    )}>
      {regime.replace(/_/g, " ").toUpperCase()}
    </span>
  )
}

export function AIBrainDashboard() {
  const [assessment, setAssessment] = useState<BrainAssessment | null>(null)
  const [engines, setEngines] = useState<EngineStatus | null>(null)
  const [selfLearning, setSelfLearning] = useState<SelfLearningReport | null>(null)
  const [system, setSystem] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedSymbol, setSelectedSymbol] = useState("BTCUSDT")

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const [assess, eng, sl, sys] = await Promise.all([
        api.getBrainAssessment(selectedSymbol).catch(() => null),
        api.getBrainEngines().catch(() => null),
        api.getBrainSelfLearning().catch(() => null),
        api.getBrainSystem().catch(() => null),
      ])
      setAssessment(assess)
      setEngines(eng)
      setSelfLearning(sl)
      setSystem(sys)
    } catch {
      setError("Failed to load brain data")
    } finally {
      setLoading(false)
    }
  }, [selectedSymbol])

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load() }, [load])

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="animate-pulse grid grid-cols-4 gap-3">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-24 bg-gray-800 rounded-xl" />)}
        </div>
        <div className="h-48 bg-gray-800 rounded-xl" />
        <div className="h-32 bg-gray-800 rounded-xl" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8 text-center text-gray-500">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-yellow-500" />
        <p className="text-sm">{error}</p>
        <button onClick={load} className="mt-3 text-xs text-blue-400 hover:text-blue-300">
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-400" />
          <h2 className="text-sm font-semibold text-gray-300">AI Brain Monitor</h2>
          <RegimeBadge regime={assessment?.regime} />
          {assessment?.confidence !== undefined && (
            <span className={cn(
              "text-[10px] px-1.5 py-0.5 rounded font-mono",
              assessment.confidence >= 60 ? "text-green-400 bg-green-900/30" :
              assessment.confidence >= 40 ? "text-yellow-400 bg-yellow-900/30" :
              "text-red-400 bg-red-900/30"
            )}>
              {assessment.confidence.toFixed(0)}% confidence
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedSymbol}
            onChange={e => setSelectedSymbol(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg text-[10px] text-gray-300 px-2 py-1"
          >
            <option value="BTCUSDT">BTC/USDT</option>
            <option value="ETHUSDT">ETH/USDT</option>
            <option value="BNBUSDT">BNB/USDT</option>
            <option value="SOLUSDT">SOL/USDT</option>
            <option value="XRPUSDT">XRP/USDT</option>
          </select>
          <button onClick={load} className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-500 hover:text-gray-300">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/40">
          <Activity className="w-4 h-4 text-blue-400 mb-1.5" />
          <div className="text-lg font-bold text-white">
            {assessment?.overall_market_score?.toFixed(1) || "--"}
          </div>
          <div className="text-[10px] text-gray-500">Market Score</div>
        </div>
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/40">
          <TrendingUp className="w-4 h-4 text-green-400 mb-1.5" />
          <div className="text-lg font-bold text-white">{assessment?.bull_probability?.toFixed(0) || "--"}%</div>
          <div className="text-[10px] text-gray-500">Bull Probability</div>
        </div>
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/40">
          <TrendingDown className="w-4 h-4 text-red-400 mb-1.5" />
          <div className="text-lg font-bold text-white">{assessment?.bear_probability?.toFixed(0) || "--"}%</div>
          <div className="text-[10px] text-gray-500">Bear Probability</div>
        </div>
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/40">
          <AlertTriangle className="w-4 h-4 text-orange-400 mb-1.5" />
          <div className="text-lg font-bold text-white">{assessment?.crash_probability?.toFixed(0) || "--"}%</div>
          <div className="text-[10px] text-gray-500">Crash Risk</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Sub-Engine Scores */}
        <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-gray-400" />
            <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Sub-Engine Scores</h3>
          </div>
          <div className="space-y-1.5">
            {assessment?.sub_scores && Object.entries(assessment.sub_scores).map(([key, val]) => (
              <ScoreBar key={key} label={key.replace(/_/g, " ")} score={val} />
            ))}
          </div>
        </div>

        {/* Engine Status & System Health */}
        <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
          <div className="flex items-center gap-2 mb-3">
            <Server className="w-4 h-4 text-gray-400" />
            <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Engine Status</h3>
          </div>
          <div className="space-y-1">
            {engines?.engines && Object.entries(engines.engines).map(([key, online]) => (
              <div key={key} className="flex items-center justify-between py-1">
                <span className="text-[11px] text-gray-400">{key.replace(/_/g, " ")}</span>
                <span className={cn(
                  "text-[9px] px-1.5 py-0.5 rounded font-mono",
                  online ? "text-green-400 bg-green-900/30" : "text-red-400 bg-red-900/30"
                )}>
                  {online ? "ONLINE" : "OFFLINE"}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-gray-800">
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2 rounded-lg bg-gray-800/30">
                <div className="text-[10px] text-gray-500">Streaming Workers</div>
                <div className="text-sm font-bold text-white">{system?.streaming?.worker_count || 0}</div>
              </div>
              <div className="p-2 rounded-lg bg-gray-800/30">
                <div className="text-[10px] text-gray-500">WS Clients</div>
                <div className="text-sm font-bold text-white">{system?.websocket?.total_clients || 0}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Factors & Probabilities */}
        <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-gray-400" />
            <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Signal Probabilities</h3>
          </div>
          <div className="space-y-2">
            {[
              { label: "Short Squeeze", value: assessment?.short_squeeze_probability || 0, color: "text-purple-400" },
              { label: "Long Squeeze", value: assessment?.long_squeeze_probability || 0, color: "text-orange-400" },
              { label: "Alt Season", value: assessment?.alt_season_probability || 0, color: "text-pink-400" },
            ].map(item => (
              <div key={item.label} className="flex items-center justify-between p-2 rounded-lg bg-gray-800/30">
                <span className="text-[10px] text-gray-400">{item.label}</span>
                <span className={`text-xs font-mono font-bold ${item.color}`}>
                  {item.value.toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
          {assessment?.contributing_factors && assessment.contributing_factors.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-800">
              <h4 className="text-[10px] text-gray-500 mb-2">Contributing Factors</h4>
              <div className="space-y-1">
                {assessment.contributing_factors.map((f, i) => (
                  <div key={i} className="text-[9px] text-gray-400 leading-relaxed">• {f}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Self-Learning Report */}
      {selfLearning && (
        <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-4 h-4 text-gray-400" />
            <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Self-Learning Engine</h3>
            <span className="text-[9px] text-gray-500">
              {selfLearning.total_trades_recorded || 0} trades · {selfLearning.total_weight_adjustments || 0} adjustments
            </span>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Performance Metrics */}
            <div className="space-y-1.5">
              <h4 className="text-[9px] text-gray-500 uppercase tracking-wider mb-2">Performance</h4>
              {selfLearning.performance_metrics && (
                <>
                  {[
                    { label: "Win Rate", value: `${selfLearning.performance_metrics.win_rate?.toFixed(1) || "0"}%` },
                    { label: "Profit Factor", value: selfLearning.performance_metrics.profit_factor?.toFixed(2) || "0" },
                    { label: "Sharpe Ratio", value: selfLearning.performance_metrics.sharpe_ratio?.toFixed(2) || "0" },
                    { label: "Max DD", value: `${selfLearning.performance_metrics.max_drawdown_percent?.toFixed(1) || "0"}%` },
                    { label: "Avg R:R", value: selfLearning.performance_metrics.avg_risk_reward?.toFixed(2) || "0" },
                    { label: "Total Trades", value: String(selfLearning.performance_metrics.total_trades || 0) },
                  ].map(m => (
                    <div key={m.label} className="flex justify-between text-[11px]">
                      <span className="text-gray-400">{m.label}</span>
                      <span className={cn(
                        "font-mono font-medium",
                        m.label === "Win Rate" && (selfLearning.performance_metrics?.win_rate || 0) >= 50 ? "text-green-400" :
                        m.label === "Win Rate" ? "text-red-400" :
                        m.label === "Max DD" && (selfLearning.performance_metrics?.max_drawdown_percent || 0) > 10 ? "text-red-400" : "text-white"
                      )}>{m.value}</span>
                    </div>
                  ))}
                </>
              )}
            </div>

            {/* Weights */}
            <div className="space-y-1.5">
              <h4 className="text-[9px] text-gray-500 uppercase tracking-wider mb-2">Current Weights</h4>
              {selfLearning.current_weights && Object.entries(selfLearning.current_weights).map(([key, val]) => {
                const delta = selfLearning.weight_delta?.[key] || 0
                return (
                  <div key={key} className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-400 w-20 truncate">{key}</span>
                    <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-purple-500" style={{ width: `${val * 100}%` }} />
                    </div>
                    <span className="text-[10px] font-mono text-gray-300 w-10 text-right">{(val * 100).toFixed(0)}%</span>
                    {delta !== 0 && (
                      <span className={cn(
                        "text-[9px] font-mono w-10 text-right",
                        delta > 0 ? "text-green-500" : "text-red-500"
                      )}>
                        {delta > 0 ? "+" : ""}{(delta * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Recommendations */}
            <div className="space-y-1.5">
              <h4 className="text-[9px] text-gray-500 uppercase tracking-wider mb-2">Recommendations</h4>
              {selfLearning.recommendations && selfLearning.recommendations.length > 0 ? (
                selfLearning.recommendations.map((r, i) => (
                  <div key={i} className="flex gap-1.5 text-[10px] text-gray-400 leading-relaxed">
                    <span className="text-yellow-500 mt-0.5 shrink-0">◆</span>
                    <span>{r}</span>
                  </div>
                ))
              ) : (
                <div className="text-[10px] text-gray-500">No recommendations yet</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Streaming Worker Status */}
      {system?.streaming?.workers && (
        <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
          <div className="flex items-center gap-2 mb-3">
            <Cpu className="w-4 h-4 text-gray-400" />
            <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Streaming Workers</h3>
            <span className={cn(
              "text-[9px] px-1.5 py-0.5 rounded font-mono",
              system.streaming.running ? "text-green-400 bg-green-900/30" : "text-red-400 bg-red-900/30"
            )}>
              {system.streaming.running ? "RUNNING" : "STOPPED"}
            </span>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
            {Object.entries(system.streaming.workers).map(([name, status]) => (
              <div key={name} className="p-2 rounded-lg bg-gray-800/30">
                <div className="flex items-center gap-1.5 mb-1">
                  <div className={cn("w-1.5 h-1.5 rounded-full", status.alive ? "bg-green-400" : "bg-red-400")} />
                  <span className="text-[10px] text-gray-300 capitalize">{name}</span>
                </div>
                <div className="text-[9px] text-gray-500 font-mono">{status.last_heartbeat_ago_secs}s ago</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
