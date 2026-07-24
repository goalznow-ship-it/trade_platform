/**
 * Unified Signal Types — canonical schema shared by Scanner, Futures Intel, AI Signals
 *
 * All modules parse the same backend response shape from the institutional scan endpoint.
 * This file provides the TypeScript types and normalization utilities.
 */

export interface UnifiedSignal {
  symbol: string
  timeframe: string
  generated_at: string
  last_updated: string
  current_price: number
  live_price: number
  direction: "long" | "short" | "neutral"
  confidence: number
  composite_score: number
  opportunity_score: number
  classification: string
  exchange: string
  entry_zone: { min: number; max: number; mid: number }
  stop_loss: number
  take_profit_1: number
  take_profit_2: number
  take_profit_3: number
  risk_reward_1: number
  risk_reward_2: number
  risk_reward_3: number
  risk_percent: number
  expected_hold_time: string
  invalidation: string
  reasons: string[]
  reasons_breakdown: Record<string, string>
  institutional_score: {
    abs_score: number
    long_probability: number
    short_probability: number
    risk_level: string
    scores: Record<string, number>
    details: Record<string, unknown>
  }
  futures: {
    funding_rate: number | null
    funding_rate_8h: number | null
    funding_pressure: string
    open_interest: number | null
    open_interest_usd: number | null
    oi_change?: number | null
    volume?: number | null
  } | null
  market_structure: {
    trend: string
    bos_count: number
    choch_count: number
    liquidity_sweep: Record<string, unknown> | null
    premium_discount: Record<string, unknown>
  }
  indicators: Record<string, unknown>
  execution: { approved: boolean; rejection_reasons?: string[] } | null
  alignment: { major_aligned: boolean } | null
}

export type SignalGrade = "trade_ready" | "watchlist" | "reject"

export function gradeSignal(confidence: number): SignalGrade {
  if (confidence >= 70) return "trade_ready"
  if (confidence >= 50) return "watchlist"
  return "reject"
}

export function isTradeReady(signal: UnifiedSignal): boolean {
  return signal.direction !== "neutral" && signal.confidence >= 70
}

export function isWatchlist(signal: UnifiedSignal): boolean {
  return signal.direction !== "neutral" && signal.confidence >= 50 && signal.confidence < 70
}

export function isReject(signal: UnifiedSignal): boolean {
  return signal.confidence < 50 || signal.direction === "neutral"
}

export function displayPrice(value: number | null | undefined): string {
  if (value === null || value === undefined || value <= 0) return "N/A"
  if (value >= 1000) return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  if (value >= 1) return `$${value.toFixed(2)}`
  return `$${value.toFixed(6)}`
}

export function displayConfidence(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A"
  return `${Math.round(value)}%`
}

export function displayPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A"
  const sign = value > 0 ? "+" : ""
  return `${sign}${(value * 100).toFixed(2)}%`
}

export function displayDate(iso: string | null | undefined): string {
  if (!iso) return "N/A"
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
  } catch {
    return "N/A"
  }
}

export function isStale(iso: string | null | undefined, maxAgeSec = 120): boolean {
  if (!iso) return true
  try {
    return (Date.now() - new Date(iso).getTime()) > maxAgeSec * 1000
  } catch {
    return true
  }
}

export function normalizeSignal(raw: Record<string, unknown>): UnifiedSignal {
  const inst = (raw.institutional_score as Record<string, unknown>) || {}
  const details = (inst.details as Record<string, unknown>) || {}
  const scores = (inst.scores as Record<string, number>) || {}
  const fut = (raw.futures as Record<string, unknown>) || null
  const ms = (raw.market_structure as Record<string, unknown>) || {}
  const ez = (raw.entry_zone as Record<string, number>) || {}
  const align = (raw.alignment as Record<string, unknown>) || null

  return {
    symbol: (raw.symbol as string) || "",
    timeframe: (raw.timeframe as string) || "1h",
    generated_at: (raw.generated_at as string) || "",
    last_updated: (raw.last_updated as string) || (raw.generated_at as string) || "",
    current_price: (raw.current_price as number) || 0,
    live_price: (raw.live_price as number) || (raw.current_price as number) || 0,
    direction: (raw.direction as "long" | "short" | "neutral") || "neutral",
    confidence: (raw.confidence as number) || 0,
    composite_score: (raw.composite_score as number) || (raw.confidence as number) || 0,
    opportunity_score: (raw.opportunity_score as number) || Math.round(((raw.confidence as number) || 0) * 0.5),
    classification: (raw.classification as string) || "reject",
    exchange: (raw.exchange as string) || "Binance",
    entry_zone: { min: ez.min || 0, max: ez.max || 0, mid: ez.mid || 0 },
    stop_loss: (raw.stop_loss as number) || 0,
    take_profit_1: (raw.take_profit_1 as number) || 0,
    take_profit_2: (raw.take_profit_2 as number) || 0,
    take_profit_3: (raw.take_profit_3 as number) || 0,
    risk_reward_1: (raw.risk_reward_1 as number) || 0,
    risk_reward_2: (raw.risk_reward_2 as number) || 0,
    risk_reward_3: (raw.risk_reward_3 as number) || 0,
    risk_percent: (raw.risk_percent as number) || 0,
    expected_hold_time: (raw.expected_hold_time as string) || "",
    invalidation: (raw.invalidation as string) || "",
    reasons: (raw.reasons as string[]) || [],
    reasons_breakdown: (raw.reasons_breakdown as Record<string, string>) || {},
    institutional_score: {
      abs_score: (inst.abs_score as number) || 0,
      long_probability: (inst.long_probability as number) || 50,
      short_probability: (inst.short_probability as number) || 50,
      risk_level: (inst.risk_level as string) || "unknown",
      scores,
      details,
    },
    futures: fut ? {
      funding_rate: (fut.funding_rate as number) ?? null,
      funding_rate_8h: (fut.funding_rate_8h as number) ?? null,
      funding_pressure: (fut.funding_pressure as string) || "neutral",
      open_interest: (fut.open_interest as number) ?? null,
      open_interest_usd: (fut.open_interest_usd as number) ?? null,
      oi_change: (fut.oi_change as number) ?? null,
      volume: (fut.volume as number) ?? null,
    } : null,
    market_structure: {
      trend: (ms.trend as string) || "unknown",
      bos_count: (ms.bos_count as number) || 0,
      choch_count: (ms.choch_count as number) || 0,
      liquidity_sweep: (ms.liquidity_sweep as Record<string, unknown>) || null,
      premium_discount: (ms.premium_discount as Record<string, unknown>) || {},
    },
    indicators: (raw.indicators as Record<string, unknown>) || {},
    execution: raw.execution ? {
      approved: !!(raw.execution as Record<string, unknown>).approved,
      rejection_reasons: (raw.execution as Record<string, unknown>).rejection_reasons as string[],
    } : null,
    alignment: align ? { major_aligned: !!(align as Record<string, unknown>).major_aligned } : null,
  }
}
