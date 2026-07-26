export interface NormalizedAnalysis {
  longTrigger: number
  shortTrigger: number
  entry: number
  stopLoss: number
  targets: { level: string; price: number; probability: number; risk_reward?: number; time_estimate?: string }[]
  supports: { price: number; strength?: number }[]
  resistances: { price: number; strength?: number }[]
  breakout: { top: number; bottom: number; testCount: number; bullishReady: boolean; bearishReady: boolean; status: string }
  retest: { active: boolean; level: number; direction: string }
  channel: { upper: { time: number; value: number }[]; lower: { time: number; value: number }[]; mid: { time: number; value: number }[]; label: string; breakout_status: string; channel_top: number; channel_bottom: number }
  strongestPattern: Record<string, unknown> | null
  fibonacci: { status: string; levels: Record<string, number>; extensions_up: Record<string, number>; extensions_down: Record<string, number> }
  smc: { all_structures: Record<string, unknown>[]; near_ob: Record<string, unknown>[]; near_fvg: Record<string, unknown>[]; near_bos: Record<string, unknown>[]; near_choch: Record<string, unknown>[]; near_liq: Record<string, unknown>[]; near_eq: Record<string, unknown>[] }
  elliott: Record<string, unknown> | null
  scenarios: { main: Record<string, unknown> | null; alt: Record<string, unknown> | null; fakeout: Record<string, unknown> | null }
  confidence: number
  status: string
  longProb: number
  shortProb: number
  overallScore: number
  tradePlan: Record<string, unknown> | null
  invalidation: number
  scoreComponents: Record<string, number>
}

function n(v: unknown): number { return typeof v === "number" ? v : 0 }
function s(v: unknown): string { return v == null ? "" : String(v) }

function getRawArray(raw: Record<string, unknown>, ...keys: string[]): Record<string, unknown>[] | undefined {
  for (const k of keys) {
    const v = raw[k]
    if (Array.isArray(v)) return v as Record<string, unknown>[]
    if (v && typeof v === "object" && !Array.isArray(v)) {
      const obj = v as Record<string, unknown>
      for (const subKey of ["structures", "items", "levels", "data"]) {
        const sub = obj[subKey]
        if (Array.isArray(sub)) return sub as Record<string, unknown>[]
      }
    }
  }
  return undefined
}

function getRawNested(raw: Record<string, unknown>, ...paths: string[]): Record<string, unknown> {
  for (const p of paths) {
    if (p.includes(".")) {
      let obj: Record<string, unknown> = raw
      const parts = p.split(".")
      let found = true
      for (const part of parts) {
        if (obj && typeof obj === "object" && part in obj) obj = obj[part] as Record<string, unknown>
        else { found = false; break }
      }
      if (found) return obj as Record<string, unknown>
    } else {
      const v = raw[p]
      if (v && typeof v === "object") return v as Record<string, unknown>
    }
  }
  return {}
}

function extractPrices(items: Record<string, unknown>[] | undefined, priceKeys: string[]): { price: number; strength?: number }[] {
  if (!items) return []
  const result: { price: number; strength?: number }[] = []
  for (const item of items) {
    if (!item || typeof item !== "object") continue
    let p = 0
    for (const pk of priceKeys) {
      p = n(item[pk])
      if (p > 0) break
    }
    if (p > 0) {
      const str = n(item.strength) || n(item.weight) || n(item.importance) || 2
      result.push({ price: p, strength: Math.max(1, Math.min(5, str)) })
    }
  }
  return result.slice(0, 3)
}

export function normalizeSkhyAnalysis(analysis: Record<string, unknown> | null | undefined): NormalizedAnalysis {
  const raw = analysis || {}
  const scores = (raw.scores || {}) as Record<string, unknown>
  const triggers = (raw.triggers || {}) as Record<string, unknown>
  const sr = getRawNested(raw, "support_resistance", "sr")
  const bzRaw = getRawNested(raw, "breakout_zone", "breakout")
  const ds = getRawNested(raw, "detected_structure", "structure")
  const clRaw = getRawNested(raw, "channel_lines", "channel")
  const sp = getRawNested(raw, "scenario_paths", "scenarios")
  const th = getRawNested(raw, "target_hierarchy", "targets")
  const fibRaw = getRawNested(raw, "fibonacci", "fib")
  const ewRaw = raw.elliott_wave as Record<string, unknown> | undefined
  const activePatterns = getRawArray(raw, "active_patterns", "patterns")
  const tradePlanRaw = raw.trade_plan as Record<string, unknown> | undefined
  const confidence = n(scores.signal_confidence)

  // Triggers
  const longTrigger = n(triggers.long_trigger_price) || n(triggers.long_price) || n(triggers.long_trigger)
  const shortTrigger = n(triggers.short_trigger_price) || n(triggers.short_price) || n(triggers.short_trigger)

  // Trade plan
  const entry = n(tradePlanRaw?.entry_zone ? n((tradePlanRaw.entry_zone as Record<string, unknown>).min || (tradePlanRaw.entry_zone as Record<string, unknown>).max) : 0)
  const stopLoss = n(tradePlanRaw?.stop_loss)
  const tpList = (tradePlanRaw?.take_profits as { level: string; price: number; risk_reward?: number; probability: number; time_estimate?: string }[] | undefined) || []
  const targets = (th.targets as { level: string; price: number; probability: number; risk_reward?: number; time_estimate?: string }[] | undefined) || tpList

  // S/R — try multiple field sources
  const allSupports: { price: number; strength?: number }[] = []
  const allResistances: { price: number; strength?: number }[] = []

  // 1. From support_resistance object
  const srSupport = n(sr.nearest_support) || n(sr.support) || n(sr.support_price)
  if (srSupport > 0) allSupports.push({ price: srSupport, strength: n(sr.support_strength) || 2 })
  const srStrong = n(sr.strongest_support)
  if (srStrong > 0 && srStrong !== srSupport) allSupports.push({ price: srStrong, strength: 3 })
  const srResist = n(sr.nearest_resistance) || n(sr.resistance) || n(sr.resistance_price)
  if (srResist > 0) allResistances.push({ price: srResist, strength: n(sr.resistance_strength) || 2 })
  const srStrongR = n(sr.strongest_resistance)
  if (srStrongR > 0 && srStrongR !== srResist) allResistances.push({ price: srStrongR, strength: 3 })

  // 2. From array fields
  const supItems = getRawArray(raw, "supports", "support_levels", "support_zones", "levels.support")
  allSupports.push(...extractPrices(supItems, ["price", "level", "value", "support"]))
  const resItems = getRawArray(raw, "resistances", "resistance_levels", "resistance_zones", "levels.resistance")
  allResistances.push(...extractPrices(resItems, ["price", "level", "value", "resistance"]))

  // 3. From zone objects
  const supZone = getRawNested(raw, "support_zone", "support")
  if (supZone && Object.keys(supZone).length > 0) {
    const p = n(supZone.bottom) || n(supZone.top) || n(supZone.price)
    if (p > 0) allSupports.push({ price: p, strength: 2 })
  }
  const resZone = getRawNested(raw, "resistance_zone", "resistance")
  if (resZone && Object.keys(resZone).length > 0) {
    const p = n(resZone.bottom) || n(resZone.top) || n(resZone.price)
    if (p > 0) allResistances.push({ price: p, strength: 2 })
  }

  // Deduplicate by price proximity
  const dedup = (items: { price: number; strength?: number }[]): { price: number; strength?: number }[] => {
    const out: { price: number; strength?: number }[] = []
    for (const item of items) {
      if (out.some(e => Math.abs(e.price - item.price) / item.price < 0.002)) continue
      out.push(item)
    }
    return out.slice(0, 2)
  }
  const supports = dedup(allSupports)
  const resistances = dedup(allResistances)

  // Breakout
  const bzTop = n(bzRaw.zone_top) || n(bzRaw.top) || n(bzRaw.upper) || n(bzRaw.breakout_top)
  const bzBot = n(bzRaw.zone_bottom) || n(bzRaw.bottom) || n(bzRaw.lower) || n(bzRaw.breakout_bottom)
  const breakout = {
    top: Math.max(bzTop, bzBot),
    bottom: Math.min(bzTop, bzBot),
    testCount: n(bzRaw.test_count) || n(bzRaw.retest_count) || n(bzRaw.tests),
    bullishReady: !!bzRaw.bullish_breakout_ready || !!bzRaw.bullish_ready,
    bearishReady: !!bzRaw.bearish_breakout_ready || !!bzRaw.bearish_ready,
    status: s(bzRaw.status) || (bzTop > 0 ? "calculated" : ""),
  }

  // Retest
  const retest = {
    active: !!ds.retest_zone || !!ds.retest,
    level: n(ds.retest_price) || n(ds.retest_level) || n(ds.channel_top) || n(ds.channel_bottom),
    direction: s(ds.retest_direction) || s(ds.breakout_status),
  }

  // Channel — try multiple field variants
  const normalizePoints = (v: unknown): { time: number; value: number }[] => {
    if (Array.isArray(v)) return v as { time: number; value: number }[]
    if (v && typeof v === "object" && !Array.isArray(v)) {
      const obj = v as Record<string, unknown>
      const pts = obj.points || obj.values || obj.data
      if (Array.isArray(pts)) return pts as { time: number; value: number }[]
      // Try as a single point with time/value
      if (n(obj.time) > 0 && n(obj.value) > 0) return [{ time: n(obj.time), value: n(obj.value) }]
    }
    return []
  }
  const getChannelLine = (...keys: string[]): { time: number; value: number }[] => {
    for (const key of keys) {
      const linesObj = (clRaw.lines || {}) as Record<string, unknown>
      const v = (clRaw[key] || linesObj[key]) as unknown
      const pts = normalizePoints(v)
      if (pts.length >= 2) return pts
    }
    return []
  }
  let chUpper = getChannelLine("upper", "upper_line", "top_line")
  let chLower = getChannelLine("lower", "lower_line", "bottom_line")
  let chMid = getChannelLine("mid", "median", "median_line", "mid_line")

  // Calculate median from upper+lower if mid missing
  if (chMid.length < 2 && chUpper.length >= 2 && chLower.length >= 2) {
    const minLen = Math.min(chUpper.length, chLower.length)
    chMid = []
    for (let i = 0; i < minLen; i++) {
      if (chUpper[i].time !== chLower[i].time) continue
      chMid.push({ time: chUpper[i].time, value: (chUpper[i].value + chLower[i].value) / 2 })
    }
  }

  const channel = {
    upper: chUpper,
    lower: chLower,
    mid: chMid,
    label: s(ds.label_az) || s(ds.channel_type) || s(ds.structure_type) || s(clRaw.label) || "",
    breakout_status: s(ds.breakout_status) || s(ds.status) || "",
    channel_top: n(ds.channel_top) || n(ds.upper_price) || n(ds.top),
    channel_bottom: n(ds.channel_bottom) || n(ds.lower_price) || n(ds.bottom),
  }

  // Strongest pattern
  let strongestPattern: Record<string, unknown> | null = null
  if (activePatterns && activePatterns.length > 0) {
    const sorted = [...activePatterns].sort((a, b) => n(b.probability) - n(a.probability))
    strongestPattern = sorted[0] || null
    if (strongestPattern && n(strongestPattern.probability) < 50) strongestPattern = null
  } else if (raw.patterns && Array.isArray(raw.patterns)) {
    const sorted = [...(raw.patterns as Record<string, unknown>[])].sort((a, b) => n(b.probability) - n(a.probability))
    const best = sorted[0]
    if (best && n(best.probability) >= 50) strongestPattern = best
  }

  // Fibonacci — normalize any key format
  const fibLevels: Record<string, number> = {}
  const rl = fibRaw.retracement_levels as Record<string, unknown> | undefined
  if (rl) {
    for (const [k, v] of Object.entries(rl)) {
      const cleanKey = String(k).replace("%", "").trim()
      let pctKey = ""
      if (["0.382", "38.2", "38.20"].includes(cleanKey)) pctKey = "0.382"
      else if (["0.5", "50", "50.0", "50.00"].includes(cleanKey)) pctKey = "0.5"
      else if (["0.618", "61.8", "61.80"].includes(cleanKey)) pctKey = "0.618"
      else if (["0.786", "78.6", "78.60"].includes(cleanKey)) pctKey = "0.786"
      else if (["0.236", "23.6", "23.60"].includes(cleanKey)) pctKey = "0.236"
      else if (["0.886", "88.6", "88.60"].includes(cleanKey)) pctKey = "0.886"
      if (pctKey) {
        const numV = typeof v === "number" ? v : Number(v)
        if (numV > 0 && isFinite(numV)) fibLevels[pctKey] = numV
      }
    }
  }
  // Also check direct level keys
  for (const pct of ["0.382", "0.5", "0.618", "0.786"]) {
    if (!(pct in fibLevels)) {
      const direct = n(fibRaw[pct]) || n(fibRaw[String(Number(pct) * 100)]) || n(fibRaw[String(Number(pct) * 100) + "%"])
      if (direct > 0) fibLevels[pct] = direct
    }
  }
  const extUp = fibRaw.extension_up as Record<string, number> | undefined || fibRaw.extensions_up as Record<string, number> | undefined || {}
  const extDn = fibRaw.extension_down as Record<string, number> | undefined || fibRaw.extensions_down as Record<string, number> | undefined || {}
  const fibonacci = { status: s(fibRaw.status) || "calculated", levels: fibLevels, extensions_up: extUp, extensions_down: extDn }

  // SMC — collect from multiple sources
  const allStructSources = getRawArray(raw, "all_structures", "smc.structures", "smc_structures", "structures", "smc")

  // Also collect from dedicated arrays
  const extraOB = getRawArray(raw, "order_blocks", "orderblocks")
  const extraFVG = getRawArray(raw, "fair_value_gaps", "fvg", "fvgs")
  const extraBOS = getRawArray(raw, "bos", "break_of_structure")
  const extraCHOCH = getRawArray(raw, "choch", "change_of_character")
  const extraLiq = getRawArray(raw, "liquidity_sweeps", "liquidity", "liq_sweeps")
  const extraEQ = getRawArray(raw, "equal_highs", "equal_lows", "equal_high_low")

  const categorize = (structs: Record<string, unknown>[], cat: string, typeIncludes: string[]): Record<string, unknown>[] =>
    structs.filter(s2 => s2 && typeof s2 === "object" && (s(s2.category) === cat || typeIncludes.some(t => s(s2.type).includes(t))))

  const allStructs = [...(allStructSources || []), ...(extraOB || []), ...(extraFVG || []), ...(extraBOS || []), ...(extraCHOCH || []), ...(extraLiq || []), ...(extraEQ || [])]

  const addWithCategory = (items: Record<string, unknown>[] | undefined, category: string): void => {
    if (!items) return
    for (const item of items) {
      if (item && typeof item === "object" && !s(item.category)) item.category = category
    }
  }
  if (extraOB) addWithCategory(extraOB, "order_block")
  if (extraFVG) addWithCategory(extraFVG, "fvg")
  if (extraBOS) addWithCategory(extraBOS, "bos")
  if (extraCHOCH) addWithCategory(extraCHOCH, "choch")
  if (extraLiq) addWithCategory(extraLiq, "liquidity_sweep")
  if (extraEQ) addWithCategory(extraEQ, "equal_high")

  const smc = {
    all_structures: allStructs,
    near_ob: categorize(allStructs, "order_block", ["order_block"]).slice(-2),
    near_fvg: categorize(allStructs, "fvg", ["fvg", "fair_value_gap"]).slice(-2),
    near_bos: categorize(allStructs, "bos", ["bos", "break_of_structure"]).slice(-2),
    near_choch: categorize(allStructs, "choch", ["choch", "change_of_character"]).slice(-2),
    near_liq: categorize(allStructs, "liquidity", ["liquidity", "liquidity_sweep", "liq", "sweep"]).slice(-3),
    near_eq: categorize(allStructs, "equal_high", ["equal", "equal_high", "equal_low", "eqh", "eql"]).slice(-2),
  }

  // Elliott
  const elliott = ewRaw && s(ewRaw.status) !== "insufficient_data" ? ewRaw : null

  // Scenarios
  const scenarios = {
    main: (sp.main_scenario || sp.main || null) as Record<string, unknown> | null,
    alt: (sp.alternative_scenario || sp.alternative || null) as Record<string, unknown> | null,
    fakeout: (sp.fakeout_scenario || sp.fakeout || null) as Record<string, unknown> | null,
  }

  // Score components
  const scoreComponents: Record<string, number> = {}
  for (const key of ["trend_score", "momentum_score", "volume_score", "liquidity_score", "pattern_score", "futures_score", "orderflow_score", "multitimeframe_score", "risk_score", "structure_score", "overall"]) {
    if (scores[key] !== undefined) scoreComponents[key] = n(scores[key])
  }

  // Invalidation
  const invalidation = n(triggers.bullish_invalidation) || n(triggers.bearish_invalidation) || n(raw.invalidation_level)

  return {
    longTrigger,
    shortTrigger,
    entry,
    stopLoss,
    targets,
    supports,
    resistances,
    breakout,
    retest,
    channel,
    strongestPattern,
    fibonacci,
    smc,
    elliott,
    scenarios,
    confidence,
    status: s(scores.status),
    longProb: n(scores.long_probability),
    shortProb: n(scores.short_probability),
    overallScore: n(scores.overall),
    tradePlan: tradePlanRaw || null,
    invalidation,
    scoreComponents,
  }
}
