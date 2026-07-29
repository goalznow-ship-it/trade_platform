"use client"

import { AlertTriangle, ShieldCheck, Target, TrendingDown, TrendingUp } from "lucide-react"
import { cn } from "@/lib/utils"
import type { NormalizedAnalysis } from "@/lib/skhyChartNormalizer"

interface Props {
  symbol: string
  analysis: Record<string, unknown> | null
  normalizedAnalysis: NormalizedAnalysis
  ranking?: {
    rank: number
    quality: number
    confidence: number
    direction: "long" | "short" | "neutral"
  }
}

const number = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? value : 0

function price(value: number): string {
  if (value >= 1000) return value.toLocaleString("en-US", { maximumFractionDigits: 2 })
  if (value >= 1) return value.toFixed(3)
  return value.toFixed(6)
}

export function SKHYSignalPlan({ symbol, analysis, normalizedAnalysis, ranking }: Props) {
  const tradePlan = (analysis?.trade_plan || normalizedAnalysis.tradePlan || {}) as Record<string, unknown>
  const ready = tradePlan.trade_ready === true
  const rawDirection = String(tradePlan.direction || "").toUpperCase()
  const direction = rawDirection === "LONG" || rawDirection === "SHORT"
    ? rawDirection
    : normalizedAnalysis.longProb > normalizedAnalysis.shortProb ? "LONG" : "SHORT"
  const isLong = direction === "LONG"
  const entryZone = (tradePlan.entry_zone || {}) as Record<string, unknown>
  const entryMin = number(entryZone.min) || normalizedAnalysis.entry
  const entryMax = number(entryZone.max) || entryMin
  const stopLoss = number(tradePlan.stop_loss) || normalizedAnalysis.stopLoss
  const targets = ((tradePlan.take_profits as Record<string, unknown>[] | undefined) || normalizedAnalysis.targets)
  const tp1 = number(targets?.[0]?.price)
  const tp2 = number(targets?.[1]?.price)

  return (
    <div className="border-b border-gray-800/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <div className="text-[9px] uppercase tracking-wider text-gray-500">Seçilmiş bazar</div>
          <div className="flex items-center gap-2">
            <div className="font-mono text-sm font-bold text-white">{symbol}</div>
            {ranking && <span className="rounded bg-purple-500/10 px-1.5 py-0.5 font-mono text-[9px] text-purple-300">#{ranking.rank} · {ranking.confidence.toFixed(0)}% · Q{ranking.quality.toFixed(0)}</span>}
          </div>
        </div>
        <span className={cn("rounded border px-2 py-1 text-[9px] font-bold", ready
          ? isLong ? "border-green-500/40 bg-green-500/10 text-green-400" : "border-red-500/40 bg-red-500/10 text-red-400"
          : "border-yellow-500/30 bg-yellow-500/5 text-yellow-400")}>
          {ready ? `AKTİV ${direction}` : "TƏSDİQ GÖZLƏNİLİR"}
        </span>
      </div>

      {ready && entryMin > 0 && stopLoss > 0 && tp1 > 0 ? (
        <div className={cn("rounded-lg border p-2.5", isLong ? "border-green-500/30 bg-green-500/5" : "border-red-500/30 bg-red-500/5")}>
          <div className="mb-2 flex items-center gap-1.5">
            {isLong ? <TrendingUp className="h-4 w-4 text-green-400" /> : <TrendingDown className="h-4 w-4 text-red-400" />}
            <span className={cn("text-xs font-bold", isLong ? "text-green-400" : "text-red-400")}>{direction} SİQNALI</span>
            <span className="ml-auto font-mono text-[10px] text-gray-400">{normalizedAnalysis.confidence}% inam</span>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            <Level label="GİRİŞ" value={entryMax !== entryMin ? `$${price(entryMin)}–$${price(entryMax)}` : `$${price(entryMin)}`} color="text-blue-300" />
            <Level label="STOP LOSS" value={`$${price(stopLoss)}`} color="text-red-400" />
            <Level label="TP1" value={`$${price(tp1)}`} color="text-green-400" />
            <Level label="TP2" value={tp2 > 0 ? `$${price(tp2)}` : "Hazırlanır"} color="text-emerald-300" />
          </div>
          <div className="mt-2 flex items-center gap-1 text-[9px] text-gray-500">
            <ShieldCheck className="h-3 w-3" /> Yalnız təsdiqlənmiş trade plan göstərilir.
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-2.5">
          <div className="flex items-center gap-2 text-[10px] text-yellow-400">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> {symbol} üçün hazırda təsdiqlənmiş giriş siqnalı yoxdur.
          </div>
          <div className="mt-1 pl-5 text-[9px] text-gray-500">Entry, TP1, TP2 və SL yalnız confidence və execution şərtləri keçdikdə açılacaq.</div>
        </div>
      )}
    </div>
  )
}

function Level({ label, value, color }: { label: string; value: string; color: string }) {
  return <div className="rounded border border-gray-800 bg-gray-950/60 p-2">
    <div className="flex items-center gap-1 text-[8px] font-semibold text-gray-500"><Target className="h-2.5 w-2.5" />{label}</div>
    <div className={cn("mt-1 font-mono text-[11px] font-bold", color)}>{value}</div>
  </div>
}
