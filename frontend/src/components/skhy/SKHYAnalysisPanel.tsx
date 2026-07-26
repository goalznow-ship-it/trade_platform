"use client"

import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus, Activity, BarChart3, Volume2, Zap, Shield, Brain, AlertTriangle, Target, Clock, RefreshCw, DollarSign, Users, Eye } from "lucide-react"
import { type NormalizedAnalysis } from "@/lib/skhyChartNormalizer"

interface Props {
  timeframes: Record<string, unknown>
  scores: Record<string, unknown>
  alignment: Record<string, unknown>
  sr: Record<string, unknown>
  analysis: Record<string, unknown> | null
  normalizedAnalysis: NormalizedAnalysis | null
}

function numVal(v: unknown): number {
  return typeof v === "number" ? v : 0
}

function safeVal(v: unknown, fallback: string = "—"): string {
  if (v == null) return fallback
  return String(v)
}

function parseLastUpdated(v: unknown): Date | null {
  if (v == null) return null
  if (typeof v === "number") return new Date(v > 1e12 ? v : v * 1000)
  if (typeof v === "string") {
    const d = new Date(v)
    if (!isNaN(d.getTime())) return d
    const num = Number(v)
    if (!isNaN(num)) return new Date(num > 1e12 ? num : num * 1000)
  }
  if (v instanceof Date) return v
  return null
}

export function SKHYAnalysisPanel({ timeframes, scores, alignment, sr, analysis, normalizedAnalysis }: Props) {
  const tfList = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
  const hasAnalysis = analysis !== null && Object.keys(scores).length > 0

  const scoreItems = [
    { label: "Trend", key: "trend_score", icon: TrendingUp },
    { label: "Struktur", key: "structure_score", icon: BarChart3 },
    { label: "Momentum", key: "momentum_score", icon: Zap },
    { label: "Həcm", key: "volume_score", icon: Volume2 },
    { label: "Likvidite", key: "liquidity_score", icon: Activity },
    { label: "Pattern", key: "pattern_score", icon: BarChart3 },
    { label: "Fyuçers", key: "futures_score", icon: BarChart3 },
    { label: "OrderFlow", key: "orderflow_score", icon: Activity },
    { label: "MTF", key: "multitimeframe_score", icon: BarChart3 },
    { label: "Risk", key: "risk_score", icon: Shield },
  ]

  const explanation = hasAnalysis ? safeVal(analysis?.explanation_az) : "Məlumat hazırlanır..."
  const triggers = (analysis?.triggers || {}) as Record<string, unknown>
  const ltPrice = numVal(triggers.long_trigger_price)
  const stPrice = numVal(triggers.short_trigger_price)
  const longConditions = triggers.long_trigger_conditions as string[] | undefined
  const shortConditions = triggers.short_trigger_conditions as string[] | undefined
  const bullishInvalidation = numVal(triggers.bullish_invalidation)
  const bearishInvalidation = numVal(triggers.bearish_invalidation)
  const ds = (analysis?.detected_structure || {}) as Record<string, unknown>
  const bz = (analysis?.breakout_zone || {}) as Record<string, unknown>
  const th = (analysis?.target_hierarchy || {}) as Record<string, unknown>
  const cb = (analysis?.confidence_breakdown || {}) as Record<string, unknown>
  const whale = (analysis?.whale_analysis || {}) as Record<string, unknown>
  const tf = (analysis?.time_forecast || {}) as Record<string, unknown>
  const sp = (analysis?.scenario_paths || {}) as Record<string, unknown>
  const mainSc = sp?.main_scenario as Record<string, unknown> | undefined
  const dataFreshness = hasAnalysis ? safeVal(analysis?.data_freshness, "bilinmir") : "gözlənilir"
  const lastUpdated = parseLastUpdated(analysis?.last_updated || analysis?.timestamp)
  const activePatterns = analysis?.active_patterns as Record<string, unknown>[] | undefined
  const tradePlan = analysis?.trade_plan as Record<string, unknown> | undefined
  const patternCompletion = analysis?.pattern_completion as Record<string, number> | undefined

  const showStructure = hasAnalysis && safeVal(ds.status) === "detected"
  const showBreakout = hasAnalysis && safeVal(bz.status) === "calculated"
  const showTargets = hasAnalysis && th && Array.isArray(th.targets) && (th.targets as unknown[]).length > 0
  const dsAccum = !!ds.accumulation_zone
  const dsDistrib = !!ds.distribution_zone
  const structLabel = safeVal(ds.label_az)
  const structBreakout = safeVal(ds.breakout_status)
  const structChannelTop = numVal(ds.channel_top)
  const structChannelBot = numVal(ds.channel_bottom)
  const bzBot = numVal(bz.zone_bottom)
  const bzTop = numVal(bz.zone_top)
  const bzTest = numVal(bz.test_count)
  const bzPriceZone = safeVal(bz.current_price_zone)
  const bzBullish = !!bz.bullish_breakout_ready
  const bzBearish = !!bz.bearish_breakout_ready
  const overallScore = numVal(scores.overall)
  const longProb = numVal(scores.long_probability)
  const shortProb = numVal(scores.short_probability)
  const status = safeVal(scores.status)
  const confidence = numVal(scores.signal_confidence)

  const mainDir = mainSc?.direction === "LONG" ? "ALIŞ" : mainSc?.direction === "SHORT" ? "SATIŞ" : safeVal(mainSc?.direction_az || mainSc?.direction || "")
  const mainProb = numVal(mainSc?.probability)
  const mainConf = numVal(mainSc?.confidence)

  return (
    <div className="border-b border-gray-800/60">
      <div className="px-3 py-1.5 border-b border-gray-800/40 flex items-center justify-between text-[9px]">
        <div className="flex items-center gap-1 text-gray-500">
          <RefreshCw className="w-2.5 h-2.5" />
          <span>Məlumat: {dataFreshness}</span>
        </div>
        <div className="flex items-center gap-1 text-gray-500">
          <Clock className="w-2.5 h-2.5" />
          <span>{lastUpdated ? lastUpdated.toLocaleTimeString() : "--:--:--"}</span>
        </div>
      </div>

      {/* 1. Hazırda nə baş verir? */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="flex items-center gap-1.5 text-[11px] text-blue-400 font-semibold uppercase tracking-wider mb-2">
          <Eye className="w-3 h-3" /> Hazırda nə baş verir?
        </div>
        <div className="text-[10px] text-gray-400 leading-relaxed">
          {hasAnalysis ? explanation : "Məlumat hazırlanır..."}
        </div>
        {showStructure && (
          <div className="mt-1.5 flex items-center gap-1.5">
            <span className={cn("text-[9px] px-1 py-0.5 rounded font-mono", dsAccum ? "bg-green-500/10 text-green-400" : dsDistrib ? "bg-red-500/10 text-red-400" : "bg-gray-700/30 text-gray-500")}>
              {dsAccum ? "Yığım" : dsDistrib ? "Paylanma" : "Neytral"}
            </span>
            <span className="text-[9px] text-gray-600">{structLabel}{structBreakout ? ` · ${structBreakout}` : ""}</span>
          </div>
        )}
      </div>

      {/* 2. Ən güclü ssenari */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="flex items-center gap-1.5 text-[11px] text-yellow-400 font-semibold uppercase tracking-wider mb-2">
          <Target className="w-3 h-3" /> Ən güclü ssenari
        </div>
        {mainSc ? (
          <div className="space-y-1">
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20 text-[10px]">
              <span className="text-gray-400">İstiqamət</span>
              <span className={cn("font-bold font-mono", mainSc.direction === "LONG" ? "text-green-400" : "text-red-400")}>{mainDir}</span>
            </div>
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20 text-[10px]">
              <span className="text-gray-400">Ehtimal</span>
              <span className="font-mono text-yellow-400">{mainProb}%</span>
            </div>
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20 text-[10px]">
              <span className="text-gray-400">İnam</span>
              <span className={cn("font-mono", mainConf >= 70 ? "text-green-400" : mainConf >= 50 ? "text-yellow-400" : "text-gray-400")}>{mainConf}%</span>
            </div>
            {mainSc?.activation_trigger != null && safeVal(mainSc.activation_trigger) && (
              <div className="flex items-start gap-1 text-[9px] text-gray-500 px-2">
                <Zap className="w-2 h-2 mt-0.5 shrink-0" />
                <span>{safeVal(mainSc.activation_trigger)}</span>
              </div>
            )}
            {tradePlan?.trade_ready ? (
              <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-green-500/10 border border-green-500/30 text-[9px]">
                <Target className="w-2.5 h-2.5 text-green-400" />
                <span className="text-green-400">Trade plan hazırdır: {safeVal(tradePlan.direction_az)} · TP1 ${numVal(((tradePlan.take_profits as unknown[])?.[0] as Record<string, unknown> | undefined)?.price || 0).toFixed(2)}</span>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="text-[10px] text-gray-500 italic">Ssenari məlumatı gözlənilir...</div>
        )}
      </div>

      {/* 3. LONG nə vaxt aktivləşəcək? */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="flex items-center gap-1.5 text-[11px] text-green-400 font-semibold uppercase tracking-wider mb-2">
          <TrendingUp className="w-3 h-3" /> ALIŞ (LONG) nə vaxt aktivləşər?
        </div>
        <div className="text-[10px] text-gray-400 space-y-1">
          {longConditions && longConditions.length > 0 ? (
            longConditions.slice(0, 4).map((c, i) => (
              <div key={i} className="flex items-start gap-1">
                <span className="text-green-500/60 mt-0.5">•</span>
                <span>{String(c)}</span>
              </div>
            ))
          ) : (
            <span>{hasAnalysis ? "ALIŞ üçün hələ şərtlər formalaşmayıb" : "Məlumat gözlənilir..."}</span>
          )}
          {ltPrice > 0 && (
            <div className="mt-1 text-[11px] font-mono text-green-400">
              Giriş: ${ltPrice.toFixed(2)}
            </div>
          )}
          {bullishInvalidation > 0 && (
            <div className="flex items-center gap-1 text-[10px] text-red-400/70">
              <AlertTriangle className="w-2.5 h-2.5" />
              Ləğv: ${bullishInvalidation.toFixed(2)} altında
            </div>
          )}
        </div>
      </div>

      {/* 4. SHORT nə vaxt aktivləşəcək? */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="flex items-center gap-1.5 text-[11px] text-red-400 font-semibold uppercase tracking-wider mb-2">
          <TrendingDown className="w-3 h-3" /> SATIŞ (SHORT) nə vaxt aktivləşər?
        </div>
        <div className="text-[10px] text-gray-400 space-y-1">
          {shortConditions && shortConditions.length > 0 ? (
            shortConditions.slice(0, 4).map((c, i) => (
              <div key={i} className="flex items-start gap-1">
                <span className="text-red-500/60 mt-0.5">•</span>
                <span>{String(c)}</span>
              </div>
            ))
          ) : (
            <span>{hasAnalysis ? "SATIŞ üçün hələ şərtlər formalaşmayıb" : "Məlumat gözlənilir..."}</span>
          )}
          {stPrice > 0 && (
            <div className="mt-1 text-[11px] font-mono text-red-400">
              Giriş: ${stPrice.toFixed(2)}
            </div>
          )}
          {bearishInvalidation > 0 && (
            <div className="flex items-center gap-1 text-[10px] text-red-400/70">
              <AlertTriangle className="w-2.5 h-2.5" />
              Ləğv: ${bearishInvalidation.toFixed(2)} üzərində
            </div>
          )}
        </div>
      </div>

      {/* Trade Plan (confidence >= 70) */}
      {tradePlan?.trade_ready ? (
        <div className="p-3 border-b border-gray-800/40">
          <div className="flex items-center gap-1.5 text-[11px] text-green-400 font-semibold uppercase tracking-wider mb-2">
            <Zap className="w-3 h-3" /> Trade Plan — {safeVal(tradePlan.direction_az)}
          </div>
          <div className="space-y-1 text-[10px]">
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-400">Giriş zonası</span>
              <span className="font-mono text-green-400">
                ${numVal((tradePlan.entry_zone as Record<string, unknown>)?.min || 0).toFixed(2)}–${numVal((tradePlan.entry_zone as Record<string, unknown>)?.max || 0).toFixed(2)}
              </span>
            </div>
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-400">Stop Loss</span>
              <span className="font-mono text-red-400">${numVal(tradePlan.stop_loss).toFixed(2)}</span>
            </div>
            {(tradePlan.take_profits as { level: string; price: number; risk_reward: number; probability: number }[] || []).slice(0, 5).map((tp, i) => (
              <div key={i} className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20">
                <span className="text-gray-400">{tp.level}</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-yellow-400">${tp.price.toFixed(2)}</span>
                  <span className="text-[8px] text-gray-500">R:{tp.risk_reward.toFixed(1)}</span>
                  <span className={cn("text-[8px] px-1 rounded", tp.probability >= 70 ? "bg-green-500/20 text-green-400" : tp.probability >= 50 ? "bg-yellow-500/20 text-yellow-400" : "bg-gray-500/20 text-gray-400")}>{tp.probability}%</span>
                </div>
              </div>
            ))}
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-400">Risk/Mükafat</span>
              <span className="font-mono text-green-400">1:{numVal(tradePlan.risk_reward).toFixed(1)}</span>
            </div>
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-400">Gözlənilən müddət</span>
              <span className="font-mono text-gray-300">{safeVal(tradePlan.expected_holding_time)}</span>
            </div>
            <div className="text-[9px] text-gray-500 px-2 mt-1">{safeVal(tradePlan.message_az)}</div>
          </div>
        </div>
      ) : null}

      {/* 5. Növbəti 1-2-4-12 saat üçün ehtimal */}
      {hasAnalysis && tf && (tf.forecasts as unknown[])?.length > 0 && (
        <div className="p-3 border-b border-gray-800/40">
          <div className="flex items-center gap-1.5 text-[11px] text-cyan-400 font-semibold uppercase tracking-wider mb-2">
            <Clock className="w-3 h-3" /> Növbəti 1-2-4-12 saat üçün ehtimal
          </div>
          <div className="space-y-1">
            {(tf.forecasts as { period: string; bullish_prob: number; bearish_prob: number; action: string; confidence: number }[]).map((f, i) => (
              <div key={i} className="flex items-center gap-2 px-2 py-1 rounded bg-gray-800/20">
                <span className="text-[10px] font-mono text-gray-400 w-12 shrink-0">{f.period}</span>
                <div className="flex-1 flex items-center gap-1">
                  <div className="flex-1 h-1.5 rounded-full bg-gray-800 overflow-hidden flex">
                    <div className="h-full bg-green-500/40 rounded-l-full transition-all" style={{ width: `${f.bullish_prob}%` }} />
                    <div className="h-full bg-red-500/40 rounded-r-full transition-all" style={{ width: `${f.bearish_prob}%` }} />
                  </div>
                  <span className={cn("text-[9px] font-mono w-8 text-right", f.bullish_prob >= f.bearish_prob ? "text-green-400" : "text-red-400")}>
                    {Math.max(f.bullish_prob, f.bearish_prob)}%
                  </span>
                </div>
                <span className="text-[8px] text-gray-500 w-20 text-right truncate" title={f.action}>{f.action}</span>
              </div>
            ))}
          </div>
          <div className="mt-1 text-[9px] text-gray-600 px-2">
            Ən güclü vaxt: {safeVal(tf.best_period)} · {safeVal(tf.description_az)}
          </div>
        </div>
      )}

      {/* 6. Ən yaxın risk nədir? */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="flex items-center gap-1.5 text-[11px] text-orange-400 font-semibold uppercase tracking-wider mb-2">
          <AlertTriangle className="w-3 h-3" /> Ən yaxın risk nədir?
        </div>
        <div className="text-[10px] text-gray-400 space-y-1">
          {sr && numVal(sr.nearest_support) > 0 && (
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20">
              <span>Dəstək səviyyəsi</span>
              <span className="font-mono text-green-400">${numVal(sr.nearest_support).toFixed(2)}</span>
            </div>
          )}
          {sr && numVal(sr.nearest_resistance) > 0 && (
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20">
              <span>Müqavimət səviyyəsi</span>
              <span className="font-mono text-red-400">${numVal(sr.nearest_resistance).toFixed(2)}</span>
            </div>
          )}
          <div className="flex items-center gap-1 px-2 py-1 text-yellow-400/60">
            <AlertTriangle className="w-2.5 h-2.5" />
            <span className="text-[9px]">
              {bullishInvalidation > 0 ? `ALIŞ ləğvi: $${bullishInvalidation.toFixed(2)}` : ""}
              {bullishInvalidation > 0 && bearishInvalidation > 0 ? " | " : ""}
              {bearishInvalidation > 0 ? `SATIŞ ləğvi: $${bearishInvalidation.toFixed(2)}` : ""}
            </span>
          </div>
          <div className="flex items-center gap-1 px-2 py-1 text-gray-500">
            <span className="text-[9px]">
              {sr && numVal(sr.distance_to_support) > 0 ? `Dəstəyə məsafə: $${numVal(sr.distance_to_support).toFixed(2)}` : ""}
              {sr && numVal(sr.distance_to_support) > 0 && numVal(sr.distance_to_resistance) > 0 ? " | " : ""}
              {sr && numVal(sr.distance_to_resistance) > 0 ? `Müqavimətə məsafə: $${numVal(sr.distance_to_resistance).toFixed(2)}` : ""}
            </span>
          </div>
        </div>
      </div>

      {/* 7. Böyük oyunçular nə edir */}
      {hasAnalysis && whale && Object.keys(whale).length > 0 && (
        <div className="p-3 border-b border-gray-800/40">
          <div className="flex items-center gap-1.5 text-[11px] text-purple-400 font-semibold uppercase tracking-wider mb-2">
            <Users className="w-3 h-3" /> Böyük oyunçular nə edir?
          </div>
          <div className="space-y-1 text-[10px]">
            <div className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-400">İstiqamət</span>
              <span className={cn("font-mono font-bold", whale.whale_direction === "bullish" ? "text-green-400" : whale.whale_direction === "bearish" ? "text-red-400" : "text-gray-400")}>
                {whale.whale_direction === "bullish" ? "Alış" : whale.whale_direction === "bearish" ? "Satış" : "Neytral"}
              </span>
            </div>
            <div className="text-[9px] text-gray-500 px-2">{safeVal(whale.whale_description_az)}</div>
            {(whale.signals as string[])?.slice(0, 3).map((s, i) => (
              <div key={i} className="flex items-start gap-1 px-2">
                <span className="text-gray-600 mt-0.5">•</span>
                <span className="text-[9px] text-gray-400">{s}</span>
              </div>
            ))}
            <div className="grid grid-cols-2 gap-1 mt-1">
              {whale.taker_buy_sell_ratio != null && (
                <div className="px-1.5 py-1 rounded bg-gray-800/20 text-center">
                  <div className="text-[7px] text-gray-600">Taker Al/Sat</div>
                  <div className="text-[9px] font-mono text-gray-300">{numVal(whale.taker_buy_sell_ratio).toFixed(2)}</div>
                </div>
              )}
              {whale.long_short_ratio != null && (
                <div className="px-1.5 py-1 rounded bg-gray-800/20 text-center">
                  <div className="text-[7px] text-gray-600">L/S Ratio</div>
                  <div className="text-[9px] font-mono text-gray-300">{numVal(whale.long_short_ratio).toFixed(2)}</div>
                </div>
              )}
              {whale.funding_rate != null && (
                <div className="px-1.5 py-1 rounded bg-gray-800/20 text-center">
                  <div className="text-[7px] text-gray-600">Funding</div>
                  <div className={cn("text-[9px] font-mono", numVal(whale.funding_rate) > 0 ? "text-green-400" : "text-red-400")}>
                    {(numVal(whale.funding_rate) * 100).toFixed(4)}%
                  </div>
                </div>
              )}
              {whale.retail_sentiment != null && (
                <div className="px-1.5 py-1 rounded bg-gray-800/20 text-center">
                  <div className="text-[7px] text-gray-600">Retail</div>
                  <div className="text-[9px] font-mono text-gray-400">{safeVal(whale.retail_sentiment)}</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 8. Hansı struktur formalaşır? */}
      {showStructure && (
        <div className="p-3 border-b border-gray-800/40">
          <div className="flex items-center gap-1.5 text-[11px] text-purple-400 font-semibold uppercase tracking-wider mb-2">
            <BarChart3 className="w-3 h-3" /> Hansı struktur formalaşır?
          </div>
          <div className="space-y-1 text-[10px]">
            <div className="flex justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-400">Tip</span>
              <span className="font-mono text-purple-400">{structLabel}</span>
            </div>
            <div className="flex justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-400">Vəziyyət</span>
              <span className={cn("font-mono", structBreakout.includes("breakout") ? "text-yellow-400" : "text-gray-300")}>{structBreakout}</span>
            </div>
            {structChannelTop > 0 && (
              <div className="flex justify-between px-2 py-1 rounded bg-gray-800/20">
                <span className="text-gray-400">Kanal üst</span>
                <span className="font-mono text-purple-400">${structChannelTop.toFixed(2)}</span>
              </div>
            )}
            {structChannelBot > 0 && (
              <div className="flex justify-between px-2 py-1 rounded bg-gray-800/20">
                <span className="text-gray-400">Kanal alt</span>
                <span className="font-mono text-purple-400">${structChannelBot.toFixed(2)}</span>
              </div>
            )}
            <div className="flex items-center gap-1 px-2 py-1">
              <span className={cn("w-2 h-2 rounded-full", dsAccum ? "bg-green-400" : dsDistrib ? "bg-red-400" : "bg-gray-600")} />
              <span className="text-gray-500">{dsAccum ? "Yığım zonası - ağıllı pul yığır" : dsDistrib ? "Paylanma zonası - ağıllı pul paylayır" : "Neytral zona"}</span>
            </div>
          </div>
        </div>
      )}

      {/* Pattern Completion */}
      {activePatterns && activePatterns.length > 0 && (
        <div className="p-3 border-b border-gray-800/40">
          <div className="flex items-center gap-1.5 text-[11px] text-cyan-400 font-semibold uppercase tracking-wider mb-2">
            <Activity className="w-3 h-3" /> Aşkarlanan Patternlər
          </div>
          <div className="space-y-1">
            {activePatterns.slice(0, 4).map((p, i) => {
              const pConf = numVal(p.probability)
              const pComp = numVal(p.completion_pct || p.completion)
              const pName = safeVal(p.name)
              const pTf = safeVal(p.timeframe)
              const pReason = safeVal(p.detection_reason)
              const pStatus = safeVal(p.status)
              const pInv = safeVal(p.invalidation_condition)
              return (
                <div key={i} className="px-2 py-1 rounded bg-gray-800/20 text-[9px]">
                  <div className="flex items-center justify-between mb-0.5">
                    <div className="flex items-center gap-1">
                      <span className={cn("font-semibold", pConf >= 70 ? "text-green-400" : pConf >= 50 ? "text-yellow-400" : "text-gray-500")}>{pName}</span>
                      <span className="text-gray-600">{pTf}</span>
                    </div>
                    <span className={cn("text-[8px] px-1 rounded", pConf >= 70 ? "bg-green-500/20 text-green-400" : pConf >= 50 ? "bg-yellow-500/20 text-yellow-400" : "bg-gray-500/20 text-gray-400")}>{pConf}%</span>
                  </div>
                  {pComp > 0 && (
                    <div className="flex items-center gap-1 mt-0.5">
                      <div className="flex-1 h-1 rounded-full bg-gray-800 overflow-hidden">
                        <div className={cn("h-full rounded-full", pComp >= 80 ? "bg-green-500" : pComp >= 50 ? "bg-yellow-500" : "bg-blue-500")} style={{ width: `${pComp}%` }} />
                      </div>
                      <span className="text-[7px] text-gray-500 w-8 text-right">{pComp}%</span>
                    </div>
                  )}
                  {pReason && <div className="text-[8px] text-gray-500 mt-0.5">{pReason}</div>}
                  {pInv && <div className="text-[8px] text-red-400/60 mt-0.5">Ləğv: {pInv}</div>}
                  {pStatus && (
                    <span className={cn("text-[7px] px-1 rounded mt-0.5 inline-block",
                      pStatus === "CONFIRMED" ? "bg-green-500/15 text-green-400" :
                      pStatus === "DETECTED" ? "bg-yellow-500/15 text-yellow-400" :
                      pStatus === "FORMING" ? "bg-blue-500/15 text-blue-400" : "bg-gray-500/15 text-gray-400"
                    )}>{pStatus}</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 9. Breakout ehtimalı */}
      {showBreakout && (
        <div className="p-3 border-b border-gray-800/40">
          <div className="flex items-center gap-1.5 text-[11px] text-violet-400 font-semibold uppercase tracking-wider mb-2">
            <Zap className="w-3 h-3" /> Breakout ehtimalı
          </div>
          <div className="space-y-1 text-[10px]">
            <div className="flex justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-400">Zona</span>
              <span className="font-mono text-purple-400">${bzBot.toFixed(2)}-${bzTop.toFixed(2)}</span>
            </div>
            <div className="flex justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-400">Test sayı</span>
              <span className="font-mono text-gray-300">{bzTest}x</span>
            </div>
            <div className="flex justify-between px-2 py-1 rounded bg-gray-800/20">
              <span className="text-gray-400">Qiymət</span>
              <span className={cn("font-mono", bzPriceZone.includes("above") ? "text-green-400" : bzPriceZone.includes("below") ? "text-red-400" : "text-yellow-400")}>{bzPriceZone}</span>
            </div>
            <div className="grid grid-cols-2 gap-1 mt-1">
              <div className={cn("px-1.5 py-1 rounded border text-center", bzBullish ? "border-green-500/40 bg-green-500/10" : "border-gray-700/30 bg-gray-800/20")}>
                <div className="text-[7px] text-gray-500">Yuxarı breakout</div>
                <div className={cn("text-[9px] font-bold", bzBullish ? "text-green-400" : "text-gray-500")}>{bzBullish ? "Hazırdır ✓" : "Gözlə"}</div>
              </div>
              <div className={cn("px-1.5 py-1 rounded border text-center", bzBearish ? "border-red-500/40 bg-red-500/10" : "border-gray-700/30 bg-gray-800/20")}>
                <div className="text-[7px] text-gray-500">Aşağı breakout</div>
                <div className={cn("text-[9px] font-bold", bzBearish ? "text-red-400" : "text-gray-500")}>{bzBearish ? "Hazırdır ✓" : "Gözlə"}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Targets Section */}
      {showTargets && (
        <div className="p-3 border-b border-gray-800/40">
          <div className="flex items-center gap-1.5 text-[11px] text-yellow-400 font-semibold uppercase tracking-wider mb-2">
            <Target className="w-3 h-3" /> Hədəflər
          </div>
          <div className="space-y-1">
            {(th.targets as { level: string; price: number; probability: number; type: string; time_estimate: string }[]).slice(0, 6).map((t, i) => (
              <div key={i} className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/20 text-[10px]">
                <div className="flex items-center gap-1.5">
                  <span className={cn("font-mono text-[9px]", String(t.level).startsWith("TP") ? "text-yellow-400" : "text-gray-500")}>{String(t.level)}</span>
                  <span className="text-gray-400">{String(t.type)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-gray-200">${Number(t.price).toFixed(2)}</span>
                  <span className={cn("text-[8px] px-1 rounded", Number(t.probability) >= 70 ? "bg-green-500/20 text-green-400" : Number(t.probability) >= 50 ? "bg-yellow-500/20 text-yellow-400" : "bg-gray-500/20 text-gray-400")}>{Number(t.probability)}%</span>
                  <span className="text-gray-600 text-[8px]">{String(t.time_estimate)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Confidence Breakdown */}
      {hasAnalysis && cb && Object.keys(cb).length > 0 && (
        <div className="p-3 border-b border-gray-800/40">
          <div className="flex items-center gap-1.5 text-[11px] text-blue-400 font-semibold uppercase tracking-wider mb-2">
            <Shield className="w-3 h-3" /> İnam Bölgüsü
          </div>
          <div className="grid grid-cols-2 gap-1">
            {[
              { label: "Trend", key: "trend_confidence" },
              { label: "Struktur", key: "structure_confidence" },
              { label: "Momentum", key: "momentum_confidence" },
              { label: "Həcm", key: "volume_confidence" },
              { label: "Fyuçers", key: "futures_confidence" },
              { label: "Likvidlik", key: "liquidity_confidence" },
              { label: "Pattern", key: "pattern_confidence" },
              { label: "Breakout", key: "breakout_confidence" },
              { label: "MTF", key: "multitimeframe_confidence" },
              { label: "Risk", key: "risk_confidence" },
            ].map(({ label, key }) => {
              const v = numVal(cb[key])
              return (
                <div key={key} className="flex items-center justify-between px-1.5 py-1 rounded bg-gray-800/20 text-[9px]">
                  <span className="text-gray-500">{label}</span>
                  <span className={cn("font-mono font-bold", v >= 70 ? "text-green-400" : v >= 50 ? "text-yellow-400" : "text-red-400")}>{v}</span>
                </div>
              )
            })}
          </div>
          <div className="mt-1 text-center text-[9px] text-gray-600">
            Ümumi: {numVal(cb.signal_confidence)}% - {safeVal(cb.overall_assessment)}
          </div>
        </div>
      )}

      {/* Score System */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="flex items-center gap-1.5 text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-2">
          <Shield className="w-3 h-3 text-blue-400" /> Bal Sistemi
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          {scoreItems.map((s) => (
            <div key={s.key} className="flex items-center justify-between px-2 py-1 rounded bg-gray-800/30">
              <div className="flex items-center gap-1">
                <s.icon className="w-2.5 h-2.5 text-gray-500" />
                <span className="text-[10px] text-gray-400">{s.label}</span>
              </div>
              <span className={cn("text-[10px] font-mono font-bold", getScoreColor(numVal(scores[s.key])))}>
                {numVal(scores[s.key])}
              </span>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between px-2 py-1.5 mt-1 rounded bg-gray-800/40">
          <span className="text-xs font-semibold text-gray-300">Ümumi</span>
          <div className="flex items-center gap-2">
            <span className={cn("text-sm font-bold font-mono", getScoreColor(overallScore))}>
              {overallScore}
            </span>
            <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-semibold", getStatusBadge(status))}>
              {status}
            </span>
          </div>
        </div>
      </div>

      {/* MTF Alignment */}
      {hasAnalysis && alignment && (
        <div className="p-3 border-b border-gray-800/40">
          <div className={cn("flex items-center justify-between gap-1.5 text-[11px] px-2 py-1 rounded",
            alignment.status === "ALIGNED" ? "bg-green-500/10 text-green-400" :
            alignment.status === "CONFLICTING" ? "bg-red-500/10 text-red-400" : "bg-yellow-500/10 text-yellow-400")}>
            <div className="flex items-center gap-1">
              {alignment.status === "ALIGNED" ? <TrendingUp className="w-3 h-3" /> :
               alignment.status === "CONFLICTING" ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
              <span>MTF: {safeVal(alignment.status)}</span>
            </div>
            <span className="font-mono">{typeof alignment.confidence === "number" ? alignment.confidence : 0}%</span>
          </div>
          <div className="mt-1 text-[9px] text-gray-500 px-2">
            {alignment.primary_direction === "long" ? "Üstünlük: ALIŞ" : alignment.primary_direction === "short" ? "Üstünlük: SATIŞ" : "Neytral"}
            {typeof alignment.long_timeframes === "number" && typeof alignment.short_timeframes === "number" && ` (${alignment.long_timeframes}L / ${alignment.short_timeframes}S)`}
          </div>
          {Array.isArray(alignment.conflicts) && alignment.conflicts.length > 0 && (
            <div className="mt-1 space-y-0.5">
              {alignment.conflicts.slice(0, 2).map((c: string, i: number) => (
                <div key={i} className="text-[10px] text-red-400/80 px-2">⚠ {String(c)}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Timeframe Table */}
      <div className="p-3 border-b border-gray-800/40">
        <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-1.5">Zaman Çərçivələri</div>
        <div className="overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800/40">
                <th className="text-left py-1 pr-2">TF</th>
                <th className="text-left py-1 pr-2">Siqnal</th>
                <th className="text-left py-1 pr-2">Trend</th>
                <th className="text-right py-1 pr-2">Alış</th>
                <th className="text-right py-1 pr-2">Satış</th>
                <th className="text-right py-1 pr-2">BOS</th>
              </tr>
            </thead>
            <tbody>
              {tfList.map((tf) => {
                const d = timeframes[tf] as Record<string, unknown> | undefined
                if (!d || d.error) return null
                return (
                  <tr key={tf} className="border-b border-gray-800/20 hover:bg-gray-800/10">
                    <td className="py-1 pr-2 font-mono text-gray-300">{tf}</td>
                    <td className="py-1 pr-2">
                      <span className={cn("font-semibold", getSignalColor(safeVal(d.signal)))}>
                        {safeVal(d.signal)}
                      </span>
                    </td>
                    <td className="py-1 pr-2">
                      <span className={cn("flex items-center gap-0.5", 
                        d.trend === "bullish" ? "text-green-400" : d.trend === "bearish" ? "text-red-400" : "text-gray-500")}>
                        {d.trend === "bullish" ? <TrendingUp className="w-2.5 h-2.5" /> :
                         d.trend === "bearish" ? <TrendingDown className="w-2.5 h-2.5" /> : <Minus className="w-2.5 h-2.5" />}
                        {d.trend === "bullish" ? "Yüksələn" : d.trend === "bearish" ? "Enən" : "Neytral"}
                      </span>
                    </td>
                    <td className="py-1 pr-2 text-right text-green-400 font-mono">{typeof d.bullish_score === "number" ? d.bullish_score : "-"}</td>
                    <td className="py-1 pr-2 text-right text-red-400 font-mono">{typeof d.bearish_score === "number" ? d.bearish_score : "-"}</td>
                    <td className="py-1 pr-2 text-right font-mono text-gray-400">{typeof d.bos === "number" ? d.bos : 0}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function getScoreColor(v: number): string {
  if (v >= 80) return "text-green-400"
  if (v >= 60) return "text-blue-400"
  if (v >= 40) return "text-yellow-400"
  return "text-red-400"
}

function getStatusBadge(status: string): string {
  switch (status) {
    case "STRONG_TRADE_READY": return "bg-green-500/20 text-green-400 border border-green-500/30"
    case "TRADE_READY": return "bg-blue-500/20 text-blue-400 border border-blue-500/30"
    case "WATCHLIST": return "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30"
    default: return "bg-gray-500/20 text-gray-400 border border-gray-500/30"
  }
}

function getSignalColor(signal: string): string {
  switch (signal) {
    case "STRONG_LONG": return "text-green-400"
    case "LONG": return "text-green-300"
    case "STRONG_SHORT": return "text-red-400"
    case "SHORT": return "text-red-300"
    default: return "text-gray-500"
  }
}
