"use client"

import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle, XCircle } from "lucide-react"

interface Props {
  triggers: Record<string, unknown>
  scores: Record<string, unknown>
}

function numVal(v: unknown): number {
  return typeof v === "number" ? v : 0
}

function strVal(v: unknown): string {
  if (v == null) return ""
  return String(v)
}

export function SKHYTriggerPanel({ triggers, scores }: Props) {
  const status = strVal(scores.status)
  const confidence = numVal(scores.signal_confidence)
  const showTradePlan = confidence >= 70 && status !== "WAIT"
  const longProb = numVal(scores.long_probability)
  const shortProb = numVal(scores.short_probability)
  const entryReady = triggers.entry_ready === true
  const longActive = entryReady && longProb > shortProb
  const shortActive = entryReady && shortProb > longProb

  return (
    <div className="border-b border-gray-800/60 p-3">
      <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-2">Triggerlər</div>

      <div className={cn("rounded border p-2 mb-2", longActive ? "border-green-500/40 bg-green-500/5" : "border-gray-700/40 bg-gray-800/20")}>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-1">
            <TrendingUp className={cn("w-3 h-3", longActive ? "text-green-400" : "text-gray-500")} />
            <span className="text-[11px] font-semibold text-gray-300">ALIŞ (LONG)</span>
          </div>
          {triggers.long_trigger_price != null && (
            <span className={cn("text-[11px] font-mono font-bold", longActive ? "text-green-400" : "text-gray-500")}>
              ${numVal(triggers.long_trigger_price).toFixed(2)}
            </span>
          )}
        </div>
        {Array.isArray(triggers.long_trigger_conditions) && (
          <div className="space-y-0.5">
            {(triggers.long_trigger_conditions as string[]).slice(0, 4).map((c: string, i: number) => (
              <div key={i} className="flex items-start gap-1 text-[10px] text-gray-400">
                <CheckCircle className="w-2 h-2 mt-0.5 text-green-500/50 shrink-0" />
                <span>{c}</span>
              </div>
            ))}
          </div>
        )}
        {triggers.bullish_invalidation != null && (
          <div className="flex items-center gap-1 mt-1 text-[10px] text-red-400/70">
            <XCircle className="w-2.5 h-2.5" />
            <span>Ləğvetmə: ${numVal(triggers.bullish_invalidation).toFixed(2)}</span>
          </div>
        )}
      </div>

      <div className={cn("rounded border p-2 mb-2", shortActive ? "border-red-500/40 bg-red-500/5" : "border-gray-700/40 bg-gray-800/20")}>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-1">
            <TrendingDown className={cn("w-3 h-3", shortActive ? "text-red-400" : "text-gray-500")} />
            <span className="text-[11px] font-semibold text-gray-300">SATIŞ (SHORT)</span>
          </div>
          {triggers.short_trigger_price != null && (
            <span className={cn("text-[11px] font-mono font-bold", shortActive ? "text-red-400" : "text-gray-500")}>
              ${numVal(triggers.short_trigger_price).toFixed(2)}
            </span>
          )}
        </div>
        {Array.isArray(triggers.short_trigger_conditions) && (
          <div className="space-y-0.5">
            {(triggers.short_trigger_conditions as string[]).slice(0, 4).map((c: string, i: number) => (
              <div key={i} className="flex items-start gap-1 text-[10px] text-gray-400">
                <CheckCircle className="w-2 h-2 mt-0.5 text-red-500/50 shrink-0" />
                <span>{c}</span>
              </div>
            ))}
          </div>
        )}
        {triggers.bearish_invalidation != null && (
          <div className="flex items-center gap-1 mt-1 text-[10px] text-red-400/70">
            <XCircle className="w-2.5 h-2.5" />
            <span>Ləğvetmə: ${numVal(triggers.bearish_invalidation).toFixed(2)}</span>
          </div>
        )}
      </div>

      {showTradePlan && longActive && (
        <div className="rounded border border-green-500/30 bg-green-500/5 p-2">
          <div className="text-[11px] font-semibold text-green-400 mb-1">⚡ ALIŞ PLANI</div>
          <div className="text-[10px] text-gray-400 space-y-0.5">
            <div className="flex justify-between"><span>Giriş Zonası</span><span className="font-mono text-gray-300">${numVal(triggers.long_trigger_price).toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Zərər Kəsmə</span><span className="font-mono text-red-400">${numVal(triggers.bullish_invalidation).toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Risk/Mükafat</span><span className="font-mono text-green-400">~1:2</span></div>
          </div>
        </div>
      )}

      {showTradePlan && shortActive && (
        <div className="rounded border border-red-500/30 bg-red-500/5 p-2">
          <div className="text-[11px] font-semibold text-red-400 mb-1">⚡ SATIŞ PLANI</div>
          <div className="text-[10px] text-gray-400 space-y-0.5">
            <div className="flex justify-between"><span>Giriş Zonası</span><span className="font-mono text-gray-300">${numVal(triggers.short_trigger_price).toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Zərər Kəsmə</span><span className="font-mono text-red-400">${numVal(triggers.bearish_invalidation).toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Risk/Mükafat</span><span className="font-mono text-green-400">~1:2</span></div>
          </div>
        </div>
      )}

      {!showTradePlan && (
        <div className="flex items-center gap-1.5 px-2 py-1.5 rounded bg-yellow-500/5 border border-yellow-500/20">
          <AlertTriangle className="w-3 h-3 text-yellow-400 shrink-0" />
          <div>
            <span className="text-[10px] text-yellow-400 font-semibold">{status === "WAIT" ? "Gözləyin" : "İzləmə"}</span>
            {confidence > 0 && <p className="text-[9px] text-gray-500">İnam {confidence}% - təsdiq gözlənilir</p>}
          </div>
        </div>
      )}
    </div>
  )
}
