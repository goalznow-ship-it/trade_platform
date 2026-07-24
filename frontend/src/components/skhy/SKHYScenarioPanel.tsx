"use client"

import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, AlertTriangle, Target, Shield, Info } from "lucide-react"

interface Props {
  scenarios: Record<string, unknown> | null
}

function strVal(v: unknown): string {
  if (v == null) return ""
  return String(v)
}

function numVal(v: unknown): number {
  return typeof v === "number" ? v : 0
}

export function SKHYScenarioPanel({ scenarios }: Props) {
  if (!scenarios) return null

  const main = scenarios.main_scenario as Record<string, unknown> | undefined
  const alt = scenarios.alternative_scenario as Record<string, unknown> | undefined
  const risk = scenarios.risk_fakeout_scenario as Record<string, unknown> | undefined

  return (
    <div className="border-b border-gray-800/60 p-3">
      <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-2">Ssenarilər</div>
      <div className="space-y-2">
        <ScenarioCard
          title="Əsas Ssenari"
          scenario={main}
          color={main?.direction === "LONG" ? "green" : "red"}
          icon={main?.direction === "LONG" ? TrendingUp : TrendingDown}
        />
        <ScenarioCard
          title="Alternativ Ssenari"
          scenario={alt}
          color={alt?.direction === "LONG" ? "green" : "red"}
          icon={TrendingUp}
          muted
        />
        <ScenarioCard
          title="Risk / Yalançı Çıxış"
          scenario={risk}
          color="yellow"
          icon={AlertTriangle}
          muted
        />
      </div>

      {/* Pattern izahları */}
      {main && (
        <div className="mt-3 pt-2 border-t border-gray-800/40">
          <div className="flex items-center gap-1 text-[10px] text-gray-500 mb-1">
            <Info className="w-2.5 h-2.5" />
            <span>Pattern izahı:</span>
          </div>
          <div className="text-[9px] text-gray-500 leading-relaxed">
            <strong className="text-gray-400">BOS</strong> (Break of Structure) - struktur dəyişikliyi, trendin istiqamət dəyişdirdiyini göstərir.
          </div>
          <div className="text-[9px] text-gray-500 leading-relaxed mt-0.5">
            <strong className="text-gray-400">CHoCH</strong> (Change of Character) - xarakter dəyişikliyi, smart money-nin yeni istiqamətə keçdiyini göstərir.
          </div>
          <div className="text-[9px] text-gray-500 leading-relaxed mt-0.5">
            <strong className="text-gray-400">FVG</strong> (Fair Value Gap) - qiymət boşluğu, adətən doldurulmağa meyllidir.
          </div>
          <div className="text-[9px] text-gray-500 leading-relaxed mt-0.5">
            <strong className="text-gray-400">OB</strong> (Order Block) - smart money-nin əmr buraxdığı zona.
          </div>
          <div className="text-[9px] text-gray-500 leading-relaxed mt-0.5">
            <strong className="text-gray-400">Likvidite</strong> - stop-loss və marjanın toplandığı hədəf zona.
          </div>
        </div>
      )}
    </div>
  )
}

function ScenarioCard({
  title, scenario, color, icon: Icon, muted,
}: {
  title: string; scenario?: Record<string, unknown>; color: string; icon: React.ElementType; muted?: boolean
}) {
  if (!scenario) return null

  const colorClasses: Record<string, { border: string; bg: string; text: string; badge: string }> = {
    green: { border: "border-green-500/30", bg: "bg-green-500/5", text: "text-green-400", badge: "bg-green-500/20 text-green-400" },
    red: { border: "border-red-500/30", bg: "bg-red-500/5", text: "text-red-400", badge: "bg-red-500/20 text-red-400" },
    yellow: { border: "border-yellow-500/30", bg: "bg-yellow-500/5", text: "text-yellow-400", badge: "bg-yellow-500/20 text-yellow-400" },
  }
  const c = colorClasses[color] || colorClasses.green
  const dir = strVal(scenario.direction)
  const prob = numVal(scenario.probability)
  const dirLabel = dir === "LONG" ? "ALIŞ" : dir === "SHORT" ? "SATIŞ" : dir

  return (
    <div className={cn("rounded border p-2", c.border, c.bg, muted && "opacity-70")}>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1">
          <Icon className={cn("w-3 h-3", c.text)} />
          <span className="text-[11px] font-semibold text-gray-300">{title}</span>
        </div>
        <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-mono", c.badge)}>
          {dirLabel} {prob}%
        </span>
      </div>
      <div className="text-[10px] text-gray-400 space-y-0.5">
        {scenario.activation_trigger != null && strVal(scenario.activation_trigger) && (
          <div className="flex items-start gap-1">
            <Target className="w-2.5 h-2.5 mt-0.5 shrink-0 text-gray-600" />
            <span>Aktivləşmə: {strVal(scenario.activation_trigger)}</span>
          </div>
        )}
        {Array.isArray(scenario.target_zones) && (
          <div className="flex items-center gap-1">
            <span className="text-gray-600">Hədəflər:</span>
            <span className="font-mono text-gray-300">{(scenario.target_zones as string[]).join(" → ")}</span>
          </div>
        )}
        {scenario.invalidation != null && strVal(scenario.invalidation) && (
          <div className="flex items-start gap-1">
            <Shield className="w-2.5 h-2.5 mt-0.5 shrink-0 text-gray-600" />
            <span>Ləğvetmə: {strVal(scenario.invalidation)}</span>
          </div>
        )}
        {Array.isArray(scenario.supporting_reasons) && (
          <div className="flex items-start gap-1">
            <span className="text-gray-600">Səbəblər:</span>
            <span className="text-gray-300">{(scenario.supporting_reasons as string[]).slice(0, 2).join(", ")}</span>
          </div>
        )}
      </div>
    </div>
  )
}
