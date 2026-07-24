"use client"

import React from "react"
import { cn } from "@/lib/utils"
import {
  Brain, TrendingUp, TrendingDown, Activity,
  BarChart3, Volume2, Shield, ArrowUp, ArrowDown,
} from "lucide-react"

interface AnalysisDetails {
  rsi?: number
  macd?: number
  support?: number
  resistance?: number
  [key: string]: unknown
}

interface AnalysisData {
  prediction?: string
  confidence?: number
  long_probability?: number
  short_probability?: number
  risk_level?: string
  scores?: Record<string, number>
  factor_scores?: Record<string, number>
  details?: AnalysisDetails
  summary?: string
  current_price?: number
  [key: string]: unknown
}

interface AIAnalysisExtended {
  direction?: string
  combined_direction?: string
  confidence?: number
  components?: {
    candlestick_patterns?: {
      pattern_direction?: string
      pattern_score?: number
      bullish_count?: number
      bearish_count?: number
      latest_pattern?: { name: string; type: string; signal: string; strength: string }
    }
    chart_patterns?: {
      patterns?: Array<Record<string, unknown>>
      forming_patterns?: Array<Record<string, unknown>>
      count?: number
    }
    elliott_wave?: {
      count?: string
      current_phase?: string
      impulse_up?: Record<string, unknown>
      impulse_down?: Record<string, unknown>
    }
    fibonacci?: {
      golden_zone?: { low: number; high: number }
    }
    liquidity_zones?: {
      total_zones?: number
    }
  }
  projection?: {
    pattern_name?: string
    pattern_confidence?: number
    pattern_status?: string
    breakout_confirmed?: boolean
    entry_trigger?: string
    stop_loss?: number
    take_profit_1?: number
    take_profit_2?: number
    take_profit_3?: number
    risk_reward_1?: number
    expected_path?: Array<{ level: string; price: number }>
    entry_zone?: { min: number; max: number; mid: number }
  }
  institutional_score?: {
    abs_score?: number
    long_probability?: number
    short_probability?: number
    risk_level?: string
    scores?: Record<string, number>
    factor_scores?: Record<string, number>
  }
}

interface AIPredictionPanelProps {
  analysis?: AnalysisData | null
  aiAnalysis?: AIAnalysisExtended | null
  loading?: boolean
}

const FACTOR_LABELS_AZ: Record<string, string> = {
  trend: "Trend",
  momentum: "Momentum",
  volume: "Həcm",
  liquidity: "Likvidlik",
  smc: "Smart Money",
  risk: "Risk Keyfiyyəti",
  volatility: "Volatillik",
  structure: "Bazar Strukturu",
  funding: "Funding",
  open_interest: "Açıq Maraq",
  liquidation: "Likvidasiya",
  pattern_quality: "Naxış Keyfiyyəti",
  breakout: "Breakout Təsdiqi",
  retest: "Retest Təsdiqi",
}

export function AIPredictionPanel({ analysis, aiAnalysis, loading }: AIPredictionPanelProps) {
  if (loading) {
    return (
      <div className="p-4 space-y-3">
        <div className="animate-pulse space-y-3">
          <div className="h-24 bg-gray-800 rounded-xl" />
          <div className="h-20 bg-gray-800 rounded-xl" />
          <div className="h-32 bg-gray-800 rounded-xl" />
        </div>
      </div>
    )
  }

  if (!analysis && !aiAnalysis) {
    return (
      <div className="p-4 text-center text-gray-600 text-sm">
        <Brain className="w-8 h-8 mx-auto mb-2 text-gray-700" />
        AI təhlili görmək üçün simvol və zaman çərçivəsi seçin
      </div>
    )
  }

  const combinedDir = aiAnalysis?.combined_direction || analysis?.prediction || "neutral"
  const conf = aiAnalysis?.confidence || analysis?.confidence || 0
  const risk = aiAnalysis?.institutional_score?.risk_level || analysis?.risk_level || "unknown"
  const longProb = aiAnalysis?.institutional_score?.long_probability ?? analysis?.long_probability ?? 50
  const shortProb = aiAnalysis?.institutional_score?.short_probability ?? analysis?.short_probability ?? 50

  const isBullish = combinedDir === "long"
  const isBearish = combinedDir === "short"
  const isNeutral = combinedDir === "neutral"

  const scores = aiAnalysis?.institutional_score?.scores || analysis?.scores || {}
  const factorScores = aiAnalysis?.institutional_score?.factor_scores || analysis?.factor_scores || {}
  const projection = aiAnalysis?.projection
  const allScores = { ...scores, ...factorScores }

  // Pattern info
  const patterns = aiAnalysis?.components?.candlestick_patterns
  const chartPatterns = aiAnalysis?.components?.chart_patterns
  const ew = aiAnalysis?.components?.elliott_wave
  const fib = aiAnalysis?.components?.fibonacci
  const liqZones = aiAnalysis?.components?.liquidity_zones

  const bestForming = chartPatterns?.forming_patterns?.[0] || chartPatterns?.patterns?.[0] || null

  return (
    <div className="p-4 space-y-3">
      {/* Visual Direction Indicator */}
      <div className={cn(
        "p-4 rounded-xl border text-center",
        isBullish && "bg-green-900/15 border-green-500/40",
        isBearish && "bg-red-900/15 border-red-500/40",
        isNeutral && "bg-yellow-900/15 border-yellow-500/40",
      )}>
        <div className="text-[10px] text-gray-500 mb-1.5">AI Bazar İstiqaməti</div>
        <div className="flex items-center justify-center gap-3">
          <div className={cn(
            "w-12 h-12 rounded-full flex items-center justify-center",
            isBullish && "bg-green-500/20",
            isBearish && "bg-red-500/20",
            isNeutral && "bg-yellow-500/20",
          )}>
            {isBullish && <ArrowUp className="w-7 h-7 text-green-400" />}
            {isBearish && <ArrowDown className="w-7 h-7 text-red-400" />}
            {isNeutral && <BarChart3 className="w-6 h-6 text-yellow-400" />}
          </div>
          <div>
            <div className={cn(
              "text-xl font-bold",
              isBullish && "text-green-400",
              isBearish && "text-red-400",
              isNeutral && "text-yellow-400",
            )}>
              {isBullish ? "UZUN ↑" : isBearish ? "QISA ↓" : "NEYTRAL →"}
            </div>
            <div className="text-[10px] text-gray-500">
              {isBullish ? "Yüksəliş Gözlənilir" : isBearish ? "Eniş Gözlənilir" : "Gözləmə"}
            </div>
          </div>
        </div>

        {/* Confidence Bar */}
        <div className="mt-3">
          <div className="flex justify-between text-[10px] text-gray-500 mb-1">
            <span>Etibar Səviyyəsi</span>
            <span className={cn("font-bold", conf >= 80 ? "text-green-400" : conf >= 60 ? "text-yellow-400" : "text-red-400")}>
              {conf}%
            </span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all", isBullish ? "bg-green-500" : isBearish ? "bg-red-500" : "bg-yellow-500")}
              style={{ width: `${Math.min(100, conf)}%` }}
            />
          </div>
          {conf < 70 && (
            <div className="mt-1 text-[9px] text-amber-400">
              {isBullish ? "UZUN" : isBearish ? "SHORT" : ""} tövsiyəsi üçün etibar çox aşağıdır. Gözləyin.
            </div>
          )}
        </div>

        <div className="flex justify-center gap-6 mt-3">
          <div>
            <div className="text-base font-bold text-green-400 font-mono">{longProb.toFixed(0)}%</div>
            <div className="text-[10px] text-gray-500">UZUN</div>
          </div>
          <div className="w-px bg-gray-700" />
          <div>
            <div className="text-base font-bold text-red-400 font-mono">{shortProb.toFixed(0)}%</div>
            <div className="text-[10px] text-gray-500">QISA</div>
          </div>
        </div>
      </div>

      {/* Pattern Analysis Summary */}
      {bestForming && (
        <div className="p-3 rounded-xl border border-amber-800/30 bg-amber-900/10">
          <h3 className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider mb-2">Qrafik Forması</h3>
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="text-gray-400">Forma</span>
              <span className="font-bold text-white">{(bestForming as Record<string, unknown>).name as string}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-400">Status</span>
              <span className={cn(
                "font-mono",
                (bestForming as Record<string, unknown>).is_forming ? "text-yellow-400" : "text-green-400"
              )}>
                {(bestForming as Record<string, unknown>).is_forming ? "Formalaşır" : "Təsdiqləndi"}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-400">İstiqamət</span>
              <span className={(bestForming as Record<string, unknown>).projected_direction === "long" ? "text-green-400" : "text-red-400"}>
                {((bestForming as Record<string, unknown>).projected_direction as string) === "long" ? "Yüksəliş" : "Eniş"}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-400">Hədəf</span>
              <span className="font-mono text-white">${((bestForming as Record<string, unknown>).target as number)?.toFixed(2) || "N/A"}</span>
            </div>
            {Boolean((bestForming as Record<string, unknown>).breakout_confirm) && (
              <div className="text-[10px] text-green-400">✓ Breakout təsdiqləndi</div>
            )}
            {!Boolean((bestForming as Record<string, unknown>).breakout_confirm) && (
              <div className="text-[10px] text-yellow-400">⚠ Giriş etmə — breakout gözlə</div>
            )}
          </div>
        </div>
      )}

      {/* Latest candlestick pattern */}
      {patterns && patterns.latest_pattern && !bestForming && (
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <h3 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Son Şam Naxışı</h3>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={cn(
                "w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold",
                patterns.latest_pattern.type === "bullish" ? "bg-green-900/50 text-green-400" :
                patterns.latest_pattern.type === "bearish" ? "bg-red-900/50 text-red-400" :
                "bg-yellow-900/50 text-yellow-400"
              )}>
                {patterns.latest_pattern.name === "Hammer" ? "🔨" :
                 patterns.latest_pattern.name === "Bullish Engulfing" ? "⬆" :
                 patterns.latest_pattern.name === "Bearish Engulfing" ? "⬇" : "◆"}
              </div>
              <div>
                <div className="text-xs font-bold text-white">{patterns.latest_pattern.name}</div>
                <div className={cn(
                  "text-[10px]",
                  patterns.latest_pattern.type === "bullish" ? "text-green-400" :
                  patterns.latest_pattern.type === "bearish" ? "text-red-400" : "text-yellow-400"
                )}>
                  {patterns.latest_pattern.type === "bullish" ? "Yüksəliş siqnalı" :
                   patterns.latest_pattern.type === "bearish" ? "Eniş siqnalı" : "Neytral"}
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-gray-400">
                {patterns.bullish_count || 0}▲ {patterns.bearish_count || 0}▼
              </div>
              <div className="text-[10px] text-gray-500">Güc: {patterns.latest_pattern.strength}</div>
            </div>
          </div>
        </div>
      )}

      {/* Projection */}
      {projection && conf >= 60 && (
        <div className="p-3 rounded-xl border border-blue-800/30 bg-blue-900/10">
          <h3 className="text-[10px] font-semibold text-blue-400 uppercase tracking-wider mb-2">
            {projection.pattern_name || "Proyeksiya"}
            {projection.pattern_status === "forming" && <span className="ml-1 text-yellow-400">(Formalaşır)</span>}
            {projection.pattern_status === "confirmed" && <span className="ml-1 text-green-400">(Təsdiqləndi)</span>}
          </h3>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">Giriş Triggeri</span>
              <span className="text-white text-right max-w-[60%]">{projection.entry_trigger || "Gözlənir"}</span>
            </div>
            {projection.entry_zone && (
              <div className="flex justify-between">
                <span className="text-gray-500">Giriş Zonası</span>
                <span className="font-mono text-blue-400">
                  ${projection.entry_zone.min?.toFixed(2)}–${projection.entry_zone.max?.toFixed(2)}
                </span>
              </div>
            )}
            {projection.stop_loss && (
              <div className="flex justify-between">
                <span className="text-gray-500">Stop Loss</span>
                <span className="font-mono text-red-400">${projection.stop_loss.toFixed(2)}</span>
              </div>
            )}
            {projection.take_profit_1 && (
              <div className="flex justify-between">
                <span className="text-gray-500">TP1 / TP2 / TP3</span>
                <span className="font-mono text-green-400">
                  ${projection.take_profit_1.toFixed(2)}
                  {projection.take_profit_2 ? ` / $${projection.take_profit_2.toFixed(2)}` : ""}
                  {projection.take_profit_3 ? ` / $${projection.take_profit_3.toFixed(2)}` : ""}
                </span>
              </div>
            )}
            {projection.risk_reward_1 && (
              <div className="flex justify-between">
                <span className="text-gray-500">R:R</span>
                <span className="font-mono text-purple-400">1:{projection.risk_reward_1.toFixed(1)}</span>
              </div>
            )}
            {conf < 70 && (
              <div className="mt-1 text-[9px] text-yellow-400">
                Bu proqnoz ehtimal olunan ssenaridir, zəmanət deyil.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Elliott Wave + Fibonacci summary */}
      {(ew || fib) && (
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <h3 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Elliott Wave & Fibonacci</h3>
          <div className="space-y-1.5">
            {ew && ew.count !== "unknown" && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Elliott Wave</span>
                <span className={cn(
                  "font-mono font-medium",
                  ew.count === "impulse" ? "text-purple-400" : "text-yellow-400"
                )}>
                  {ew.count === "impulse" ? "İmpuls (1-5)" : "Korrektiv (A-B-C)"}
                </span>
              </div>
            )}
            {ew && ew.current_phase && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Cari Faza</span>
                <span className={cn(
                  "font-mono",
                  ew.current_phase === "up" ? "text-green-400" : ew.current_phase === "down" ? "text-red-400" : "text-gray-400"
                )}>
                  {ew.current_phase === "up" ? "Yüksəliş" : ew.current_phase === "down" ? "Eniş" : "Neytral"}
                </span>
              </div>
            )}
            {fib?.golden_zone && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Qızıl Zona (0.382-0.618)</span>
                <span className="font-mono text-purple-400">
                  ${fib.golden_zone.low.toFixed(2)} - ${fib.golden_zone.high.toFixed(2)}
                </span>
              </div>
            )}
            {liqZones && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Likvidlik Zonaları</span>
                <span className="font-mono text-cyan-400">{liqZones.total_zones || 0} zona</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Factor Scores (normalized -100 to +100) */}
      <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
        <h3 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Faktor Analizi</h3>
        <div className="space-y-2">
          {(["trend", "momentum", "volume", "liquidity", "smc", "risk"] as const).map((key) => {
            const rawVal = allScores[key]
            const hasScore = typeof rawVal === "number" && Number.isFinite(rawVal)
            let displayPct = 0
            let isPositive = false
            if (hasScore) {
              const val = rawVal as number
              displayPct = Math.min(100, Math.abs(val))
              isPositive = val >= 0
            }
            const IconMap: Record<string, React.FC<{ className?: string }>> = {
              trend: TrendingUp, momentum: Activity, volume: Volume2,
              liquidity: BarChart3, smc: Shield, risk: TrendingDown,
            }
            const IconComp = IconMap[key]
            return (
              <div key={key}>
                <div className="flex items-center justify-between text-[11px] mb-0.5">
                  <div className="flex items-center gap-1">
                    {IconComp && <IconComp className={cn("w-3 h-3", isPositive ? "text-green-400" : !isPositive && hasScore ? "text-red-400" : "text-gray-500")} />}
                    <span className="text-gray-400">{FACTOR_LABELS_AZ[key] || key}</span>
                  </div>
                  <span className={cn("font-mono font-medium", isPositive ? "text-green-400" : !isPositive && hasScore ? "text-red-400" : "text-gray-500")}>
                    {hasScore ? `${displayPct.toFixed(0)}%` : "YOX"}
                  </span>
                </div>
                <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all", isPositive ? "bg-green-500" : hasScore ? "bg-red-500" : "bg-gray-600")}
                    style={{ width: hasScore ? `${displayPct}%` : "0%" }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Key Levels */}
      {analysis?.details && (analysis.details.support || analysis.details.resistance) ? (
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <h3 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Əsas Səviyyələr</h3>
          <div className="grid grid-cols-2 gap-2">
            <div className="p-2 rounded-lg bg-gray-800/30">
              <div className="text-[10px] text-gray-500">Dəstək</div>
              <div className="text-sm font-bold text-green-400 font-mono">${analysis.details.support?.toFixed(2) || "--"}</div>
            </div>
            <div className="p-2 rounded-lg bg-gray-800/30">
              <div className="text-[10px] text-gray-500">Müqavimət</div>
              <div className="text-sm font-bold text-red-400 font-mono">${analysis.details.resistance?.toFixed(2) || "--"}</div>
            </div>
            <div className="p-2 rounded-lg bg-gray-800/30">
              <div className="text-[10px] text-gray-500">RSI</div>
              <div className={cn("text-sm font-bold font-mono", (analysis.details.rsi || 0) > 70 ? "text-red-400" : (analysis.details.rsi || 0) < 30 ? "text-green-400" : "text-white")}>
                {analysis.details.rsi?.toFixed(1) || "--"}
              </div>
            </div>
            <div className="p-2 rounded-lg bg-gray-800/30">
              <div className="text-[10px] text-gray-500">MACD</div>
              <div className={cn("text-sm font-bold font-mono", (analysis.details.macd || 0) > 0 ? "text-green-400" : "text-red-400")}>
                {analysis.details.macd?.toFixed(2) || "--"}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {/* AI Summary */}
      {analysis?.summary && (
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <div className="flex items-center gap-1 mb-1">
            <Brain className="w-3 h-3 text-purple-400" />
            <span className="text-[10px] text-gray-500 uppercase tracking-wider">AI Xülasə</span>
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">{analysis.summary}</p>
        </div>
      )}
    </div>
  )
}
