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
      momentum?: string
      next_wave?: Record<string, unknown>
      wave_count?: number
      waves?: Array<Record<string, unknown>>
      current_wave?: Record<string, unknown>
      estimated_completion?: string
    }
    fibonacci?: {
      levels?: Array<Record<string, unknown>>
      golden_zone?: { low: number; high: number; current_price_in_zone?: boolean }
      direction?: string
      swing_high?: number
      swing_low?: number
      nearest_level?: Record<string, unknown>
      nearest_retracement?: Record<string, unknown>
      support_level?: Record<string, unknown>
      resistance_level?: Record<string, unknown>
      ai_targets?: Record<string, number>
    }
    liquidity_zones?: {
      total_zones?: number
      zones?: Array<Record<string, unknown>>
      nearest_support?: number
      nearest_resistance?: number
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
    direction?: string
    invalidation?: string
    projected_target?: number
    expected_move_pct?: number
  }
  institutional_score?: {
    abs_score?: number
    long_probability?: number
    short_probability?: number
    risk_level?: string
    scores?: Record<string, number>
    factor_scores?: Record<string, number>
  }
  multi_timeframe_alignment?: {
    major_aligned?: boolean
    aligned_tfs?: number
    aggregate_direction?: string
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
  timeframe_alignment: "TF Uyğunluğu",
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
  const isTradeReady = conf >= 70 && !isNeutral

  const scores = aiAnalysis?.institutional_score?.scores || analysis?.scores || {}
  const factorScores = aiAnalysis?.institutional_score?.factor_scores || analysis?.factor_scores || {}
  const projection = aiAnalysis?.projection
  const allScores = { ...scores, ...factorScores }
  const mtf = aiAnalysis?.multi_timeframe_alignment

  const patterns = aiAnalysis?.components?.candlestick_patterns
  const chartPatterns = aiAnalysis?.components?.chart_patterns
  const ew = aiAnalysis?.components?.elliott_wave
  const fib = aiAnalysis?.components?.fibonacci
  const liqZones = aiAnalysis?.components?.liquidity_zones

  const bestForming = chartPatterns?.forming_patterns?.[0] || chartPatterns?.patterns?.[0] || null

  const hasValidScore = (val: unknown): val is number =>
    typeof val === "number" && Number.isFinite(val) && val !== 0

  return (
    <div className="p-4 space-y-3">
      {/* AI Direction + Confidence */}
      <div className={cn(
        "p-4 rounded-xl border text-center transition-all",
        isTradeReady && isBullish && "bg-green-900/15 border-green-500/40",
        isTradeReady && isBearish && "bg-red-900/15 border-red-500/40",
        !isTradeReady && "bg-amber-900/10 border-amber-500/20",
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
              isTradeReady && isBullish && "text-green-400",
              isTradeReady && isBearish && "text-red-400",
              !isTradeReady && "text-amber-400",
            )}>
              {isTradeReady ? (isBullish ? "UZUN ↑" : "QISA ↓") : "GÖZLƏ →"}
            </div>
            <div className="text-[10px] text-gray-500">
              {isBullish ? "Yüksəliş gözlənilir" : isBearish ? "Eniş gözlənilir" : "Gözləmə rejimi"}
            </div>
          </div>
        </div>

        {/* Confidence Bar */}
        <div className="mt-3">
          <div className="flex justify-between text-[10px] text-gray-500 mb-1">
            <span>Siqnal Etibarı</span>
            <span className={cn("font-bold", conf >= 80 ? "text-green-400" : conf >= 60 ? "text-yellow-400" : "text-red-400")}>
              {conf.toFixed(0)}%
            </span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all", isBullish ? "bg-green-500" : isBearish ? "bg-red-500" : "bg-yellow-500")}
              style={{ width: `${Math.min(100, conf)}%` }}
            />
          </div>
          {conf < 70 && (
            <div className="mt-1.5 space-y-1">
              <div className="text-[9px] text-amber-400">
                Etibar 70% altındadır — ticarət tövsiyəsi aktiv deyil.
              </div>
              <div className="text-[8px] text-gray-500">
                İstiqamət ehtimalı: LONG {longProb.toFixed(0)}% / SHORT {shortProb.toFixed(0)}% (bu, <span className="text-amber-400">mümkün ssenarini</span> göstərir, siqnal deyil)
              </div>
            </div>
          )}
          {conf >= 70 && (
            <div className="mt-1.5 text-[9px] text-gray-500">
              İstiqamət ehtimalı: LONG {longProb.toFixed(0)}% / SHORT {shortProb.toFixed(0)}%
            </div>
          )}
        </div>

        {/* Long/Short Balance */}
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

        {/* Risk Level */}
        {risk !== "unknown" && (
          <div className="mt-2 text-[9px]">
            Risk səviyyəsi:{" "}
            <span className={cn(
              risk === "low" ? "text-green-400" : risk === "medium" ? "text-yellow-400" : "text-red-400"
            )}>{risk.toUpperCase()}</span>
          </div>
        )}
      </div>

      {/* Multi-Timeframe Alignment */}
      {mtf && (
        <div className="p-3 rounded-xl border border-indigo-800/30 bg-indigo-900/10">
          <h3 className="text-[10px] font-semibold text-indigo-400 uppercase tracking-wider mb-2">⏱ Multi-Timeframe</h3>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-400">Uyğunluq</span>
              <span className={cn("font-bold", mtf.major_aligned ? "text-green-400" : "text-yellow-400")}>
                {mtf.major_aligned ? "✓ Uyğun" : "✗ Uyğun deyil"}
              </span>
            </div>
            {mtf.aligned_tfs !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-400">Uyğun TF</span>
                <span className="font-mono text-white">{mtf.aligned_tfs}/6</span>
              </div>
            )}
            {mtf.aggregate_direction && (
              <div className="flex justify-between">
                <span className="text-gray-400">Konsensus</span>
                <span className={cn(
                  "font-mono",
                  mtf.aggregate_direction === "long" ? "text-green-400" :
                  mtf.aggregate_direction === "short" ? "text-red-400" : "text-yellow-400"
                )}>
                  {mtf.aggregate_direction === "long" ? "UZUN" : mtf.aggregate_direction === "short" ? "QISA" : "NEYTRAL"}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Chart Pattern */}
      {bestForming && (
        <div className="p-3 rounded-xl border border-amber-800/30 bg-amber-900/10">
          <h3 className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider mb-2">📐 Qrafik Forması</h3>
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="text-gray-400">Forma</span>
              <span className="font-bold text-white">{(bestForming as Record<string, unknown>).name as string}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-400">Status</span>
              <span className={cn("font-mono", (bestForming as Record<string, unknown>).is_forming ? "text-yellow-400" : "text-green-400")}>
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
            {Boolean((bestForming as Record<string, unknown>).entry_trigger) && (
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">Giriş Trigger</span>
                <span className="text-white text-right max-w-[60%]">{String((bestForming as Record<string, unknown>).entry_trigger || "")}</span>
              </div>
            )}
            {Boolean((bestForming as Record<string, unknown>).breakout_confirm) ? (
              <div className="text-[10px] text-green-400">✓ Breakout təsdiqləndi</div>
            ) : (
              <div className="text-[10px] text-yellow-400">⚠ Giriş etmə — breakout gözlə</div>
            )}
            {/* Retest status */}
            {Boolean((bestForming as Record<string, unknown>).is_forming) && (
              <div className="text-[10px] text-gray-500">↻ Retest gözlənilir: qiymət breakout səviyyəsinə qayıda bilər</div>
            )}
          </div>
        </div>
      )}

      {/* Candlestick Pattern */}
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

      {/* Projection Panel */}
      {projection && (
        <div className="p-3 rounded-xl border border-blue-800/30 bg-blue-900/10">
          <h3 className="text-[10px] font-semibold text-blue-400 uppercase tracking-wider mb-2">
            {projection.pattern_name || "Proyeksiya"}
            {projection.pattern_status === "forming" && <span className="ml-1 text-yellow-400">(Formalaşır)</span>}
            {projection.pattern_status === "confirmed" && <span className="ml-1 text-green-400">(Təsdiqləndi)</span>}
          </h3>
          <div className="space-y-1.5 text-xs">
            {conf >= 70 && (
              <>
                <div className="flex justify-between">
                  <span className="text-gray-500">Giriş Triggeri</span>
                  <span className="text-white text-right max-w-[60%]">{projection.entry_trigger || "Gözlənir"}</span>
                </div>
                {projection.entry_zone && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Giriş Zonası</span>
                    <span className="font-mono text-blue-400">${projection.entry_zone.min?.toFixed(2)}–${projection.entry_zone.max?.toFixed(2)}</span>
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
                {projection.invalidation && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">İnvalidasiya</span>
                    <span className="font-mono text-red-400 text-right max-w-[60%]">{projection.invalidation}</span>
                  </div>
                )}
                {projection.risk_reward_1 && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">R:R</span>
                    <span className="font-mono text-purple-400">1:{projection.risk_reward_1.toFixed(1)}</span>
                  </div>
                )}
                {projection.projected_target && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Proyeksiya Hədəfi</span>
                    <span className="font-mono text-purple-400">${projection.projected_target.toFixed(2)}</span>
                  </div>
                )}
                {projection.expected_move_pct && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Gözlənilən Hərəkət</span>
                    <span className={cn("font-mono", projection.expected_move_pct >= 0 ? "text-green-400" : "text-red-400")}>
                      {projection.expected_move_pct >= 0 ? "+" : ""}{projection.expected_move_pct.toFixed(1)}%
                    </span>
                  </div>
                )}
              </>
            )}
            {/* When WAIT, show potential trigger levels instead of trade plan */}
            {conf < 70 && (
              <>
                {projection.entry_trigger && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Bullish Trigger</span>
                    <span className="text-green-400 text-right max-w-[60%]">{projection.entry_trigger}</span>
                  </div>
                )}
                {projection.invalidation && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Bearish Trigger</span>
                    <span className="text-red-400 text-right max-w-[60%]">{projection.invalidation}</span>
                  </div>
                )}
                <div className="text-[9px] text-amber-400 mt-1">
                  Bu triggerlər potensial ssenarilərdir. Təsdiq üçün 70%+ etibar lazımdır.
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Elliott Wave + Fibonacci + Liquidity Zones */}
      {(ew || fib || liqZones) && (
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <h3 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Elliott Wave & Fibonacci</h3>
          <div className="space-y-1.5">
            {ew && ew.count !== "unknown" && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Elliott Wave</span>
                <span className={cn("font-mono font-medium", ew.count === "impulse" ? "text-purple-400" : "text-yellow-400")}>
                  {ew.count === "impulse" ? "İmpuls (1-5)" : "Korrektiv (A-B-C)"}
                </span>
              </div>
            )}
            {ew && ew.current_phase && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Cari Faza</span>
                <span className={cn("font-mono", ew.current_phase === "up" ? "text-green-400" : ew.current_phase === "down" ? "text-red-400" : "text-gray-400")}>
                  {ew.current_phase === "up" ? "Yüksəliş" : ew.current_phase === "down" ? "Eniş" : "Neytral"}
                </span>
              </div>
            )}
            {ew && ew.current_wave && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Cari Dalğa</span>
                <span className="font-mono text-white">Dalğa {(ew.current_wave as Record<string, unknown>).wave as string}</span>
              </div>
            )}
            {ew && ew.next_wave && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Növbəti Dalğa</span>
                <span className={cn("font-mono", (ew.next_wave as Record<string, unknown>).direction === "up" ? "text-green-400" : "text-red-400")}>
                  {(ew.next_wave as Record<string, unknown>).label as string} ({(ew.next_wave as Record<string, unknown>).direction === "up" ? "Yüksəliş" : "Eniş"})
                </span>
              </div>
            )}
            {fib?.golden_zone && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Qızıl Zona (0.382-0.618)</span>
                <span className="font-mono text-purple-400">
                  ${fib.golden_zone.low.toFixed(2)} - ${fib.golden_zone.high.toFixed(2)}
                  {fib.golden_zone.current_price_in_zone && <span className="ml-1 text-green-400">●</span>}
                </span>
              </div>
            )}
            {fib?.swing_high && fib?.swing_low && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Swing Yüksək/Aşağı</span>
                <span className="font-mono text-white">${fib.swing_high.toFixed(2)} / ${fib.swing_low.toFixed(2)}</span>
              </div>
            )}
            {fib?.ai_targets && Object.keys(fib.ai_targets).length > 0 && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Fib TP (1.618)</span>
                <span className="font-mono text-green-400">${Object.values(fib.ai_targets)[0]?.toFixed(2) || "N/A"}</span>
              </div>
            )}
            {liqZones && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Likvidlik Zonaları</span>
                <span className="font-mono text-cyan-400">{liqZones.total_zones || 0} zona</span>
              </div>
            )}
            {liqZones && liqZones.nearest_support && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Yaxın Dəstək</span>
                <span className="font-mono text-green-400">${liqZones.nearest_support.toFixed(2)}</span>
              </div>
            )}
            {liqZones && liqZones.nearest_resistance && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Yaxın Müqavimət</span>
                <span className="font-mono text-red-400">${liqZones.nearest_resistance.toFixed(2)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Factor Analysis */}
      <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
        <h3 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Faktor Analizi</h3>
        <div className="space-y-2">
          {(["trend", "momentum", "volume", "liquidity", "smc", "risk"] as const).map((key) => {
            const rawVal = allScores[key]
            const hasScore = typeof rawVal === "number" && Number.isFinite(rawVal) && rawVal !== 0
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
                    {hasScore ? `${displayPct.toFixed(0)}%` : "N/A"}
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
                {analysis.details.rsi?.toFixed(1) || "N/A"}
              </div>
            </div>
            <div className="p-2 rounded-lg bg-gray-800/30">
              <div className="text-[10px] text-gray-500">MACD</div>
              <div className={cn("text-sm font-bold font-mono", (analysis.details.macd || 0) > 0 ? "text-green-400" : "text-red-400")}>
                {analysis.details.macd?.toFixed(2) || "N/A"}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {/* Reasons block */}
      {analysis?.summary && (
        <div className="p-3 rounded-xl border border-gray-800 bg-gray-900/50">
          <div className="flex items-center gap-1 mb-1">
            <Brain className="w-3 h-3 text-purple-400" />
            <span className="text-[10px] text-gray-500 uppercase tracking-wider">AI Xülasə</span>
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">{analysis.summary}</p>
        </div>
      )}

      {/* Risks */}
      {analysis?.risk_level === "high" && (
        <div className="p-2 rounded bg-red-900/20 border border-red-800/30 text-xs text-red-300">
          ⚠ Yüksək risk səviyyəsi. Ehtiyatlı olun.
        </div>
      )}
    </div>
  )
}
