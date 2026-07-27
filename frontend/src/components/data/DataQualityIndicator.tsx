"use client"

import { AlertTriangle, CheckCircle2, Clock3, Database, RefreshCw, XCircle } from "lucide-react"
import { cn } from "@/lib/utils"

export interface DataQualityMeta {
  source?: string | null
  provider_status?: string | null
  data_freshness?: string | null
  last_updated?: string | null
  is_stale?: boolean | null
  fallback_used?: boolean | null
  error_reason?: string | null
}

export function DataQualityIndicator({ meta, compact = false, className }: {
  meta?: DataQualityMeta | null
  compact?: boolean
  className?: string
}) {
  const status = qualityStatus(meta)
  const config = {
    live: { label: "CANLI", icon: CheckCircle2, color: "text-green-400", border: "border-green-900/50 bg-green-950/20" },
    fallback: { label: "FALLBACK", icon: RefreshCw, color: "text-yellow-400", border: "border-yellow-900/50 bg-yellow-950/20" },
    stale: { label: "KÖHNƏ", icon: Clock3, color: "text-orange-400", border: "border-orange-900/50 bg-orange-950/20" },
    unavailable: { label: "ƏLÇATMAZ", icon: XCircle, color: "text-red-400", border: "border-red-900/50 bg-red-950/20" },
    unknown: { label: "YOXLANILIR", icon: AlertTriangle, color: "text-gray-400", border: "border-gray-800 bg-gray-900/40" },
  }[status]
  const Icon = config.icon
  const updated = formatUpdated(meta?.last_updated)

  if (compact) {
    return <span className={cn("inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px]", config.border, config.color, className)} title={qualityTitle(meta, updated)}>
      <Icon className="h-2.5 w-2.5" /> {config.label}
    </span>
  }

  return <div className={cn("flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border px-3 py-2 text-[10px]", config.border, className)}>
    <span className={cn("inline-flex items-center gap-1 font-semibold", config.color)}><Icon className="h-3 w-3" /> {config.label}</span>
    <span className="inline-flex items-center gap-1 text-gray-400"><Database className="h-3 w-3" /> {meta?.source || "Mənbə bildirilməyib"}</span>
    <span className="inline-flex items-center gap-1 text-gray-600"><Clock3 className="h-3 w-3" /> {updated}</span>
    {meta?.fallback_used && <span className="text-yellow-500">Son etibarlı real məlumat istifadə olunur</span>}
    {meta?.error_reason && <span className="w-full text-red-400">{meta.error_reason}</span>}
  </div>
}

function qualityStatus(meta?: DataQualityMeta | null): "live" | "fallback" | "stale" | "unavailable" | "unknown" {
  if (!meta) return "unknown"
  if (meta.fallback_used) return meta.is_stale ? "stale" : "fallback"
  if (meta.provider_status === "unavailable" || meta.provider_status === "not_configured" || meta.error_reason) return "unavailable"
  if (meta.is_stale || meta.data_freshness === "stale") return "stale"
  if (meta.provider_status === "available" && meta.data_freshness === "live") return "live"
  return "unknown"
}

function formatUpdated(value?: string | null) {
  if (!value) return "Yenilənmə vaxtı yoxdur"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "Yenilənmə vaxtı bilinmir"
  return `Yeniləndi ${date.toLocaleString("az")}`
}

function qualityTitle(meta: DataQualityMeta | null | undefined, updated: string) {
  return [meta?.source || "Mənbə yoxdur", updated, meta?.error_reason].filter(Boolean).join(" · ")
}
