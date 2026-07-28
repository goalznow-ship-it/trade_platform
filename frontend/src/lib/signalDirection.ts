export type SignalDirection = "long" | "short" | "neutral"

export function normalizeSignalDirection(value: unknown): SignalDirection {
  const direction = String(value ?? "").trim().toLowerCase()
  if (["long", "buy", "bull", "bullish", "strong_long", "alış", "aliş", "alis", "yüksəliş", "yukselis"].includes(direction)) return "long"
  if (["short", "sell", "bear", "bearish", "strong_short", "satış", "satiş", "satis", "eniş", "enis"].includes(direction)) return "short"
  return "neutral"
}

export function directionLabel(value: unknown): "LONG" | "SHORT" | "WAIT" {
  const direction = normalizeSignalDirection(value)
  return direction === "long" ? "LONG" : direction === "short" ? "SHORT" : "WAIT"
}
