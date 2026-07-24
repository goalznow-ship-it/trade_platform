"use client"

import { useEffect, useState, useMemo, useCallback } from "react"
import { api } from "@/lib/api"
import { cn, formatPrice, formatPercent, getChangeColor } from "@/lib/utils"
import { ArrowUpDown, Search, Eye, EyeOff, Pin, Clock, AlertCircle } from "lucide-react"

interface MatrixRow {
  symbol: string
  exchange: string
  live_price: number | null
  direction: string
  status: string
  confidence: number
  long_score: number
  short_score: number
  pattern?: { name?: string; status?: string; confidence?: number }
  stop_loss?: number
  tp1?: number
  tp2?: number
  tp3?: number
  risk_reward?: number
  support?: number
  resistance?: number
  entry_trigger?: string
  invalidation?: string
  reasons?: string[]
  risks?: string[]
  factor_scores?: Record<string, number>
  funding?: { rate?: number; pressure?: string }
  open_interest?: { value?: number; change?: number }
  volume?: { current?: number; status?: string }
  indicators?: { rsi?: number; macd_histogram?: number; adx?: number }
  multi_timeframe_alignment?: { major_aligned?: boolean; aligned_tfs?: number; aggregate_direction?: string }
  data_freshness?: string
  last_updated?: string
  error?: string
}

type SortField = "symbol" | "confidence" | "direction" | "live_price" | "risk_reward"
type SortDir = "asc" | "desc"

const DIRECTION_COLORS: Record<string, string> = {
  long: "text-green-400 bg-green-900/20 border-green-800/30",
  short: "text-red-400 bg-red-900/20 border-red-800/30",
  neutral: "text-yellow-400 bg-yellow-900/20 border-yellow-800/30",
}

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500/20 text-green-400",
  watchlist: "bg-yellow-500/20 text-yellow-400",
  reject: "bg-red-500/20 text-red-400",
}

const ALL_COLUMNS = [
  { key: "symbol", label: "Symbol", sortable: true, default: true },
  { key: "exchange", label: "Exchange", sortable: true, default: true },
  { key: "live_price", label: "Live Price", sortable: true, default: true },
  { key: "direction", label: "Direction", sortable: true, default: true },
  { key: "confidence", label: "Confidence", sortable: true, default: true },
  { key: "long_score", label: "LONG", sortable: true, default: true },
  { key: "short_score", label: "SHORT", sortable: true, default: true },
  { key: "pattern_name", label: "Pattern", sortable: false, default: true },
  { key: "pattern_status", label: "Pattern Status", sortable: false, default: true },
  { key: "entry_trigger", label: "Entry Trigger", sortable: false, default: false },
  { key: "stop_loss", label: "Invalidation", sortable: true, default: true },
  { key: "tp1", label: "TP1", sortable: true, default: false },
  { key: "tp2", label: "TP2", sortable: true, default: false },
  { key: "tp3", label: "TP3", sortable: true, default: false },
  { key: "risk_reward", label: "R:R", sortable: true, default: true },
  { key: "support", label: "Support", sortable: true, default: false },
  { key: "resistance", label: "Resistance", sortable: true, default: false },
  { key: "funding", label: "Funding", sortable: true, default: false },
  { key: "oi", label: "OI Change", sortable: true, default: false },
  { key: "volume_status", label: "Volume", sortable: false, default: false },
  { key: "rsi", label: "RSI", sortable: true, default: false },
  { key: "reasons", label: "Reasons", sortable: false, default: false },
  { key: "risks", label: "Risks", sortable: false, default: false },
  { key: "status", label: "Signal Status", sortable: true, default: false },
  { key: "exchange_status", label: "Data Freshness", sortable: false, default: false },
]

export function MarketMatrix() {
  const [rows, setRows] = useState<MatrixRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortField, setSortField] = useState<SortField>("confidence")
  const [sortDir, setSortDir] = useState<SortDir>("desc")
  const [search, setSearch] = useState("")
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(new Set())
  const [pinnedCols, setPinnedCols] = useState<Set<string>>(new Set(["symbol", "live_price", "direction", "confidence"]))

  const load = useCallback(async () => {
    try {
      const data = await api.getMarketMatrix(30)
      if (data?.symbols && Array.isArray(data.symbols)) {
        const matrix: MatrixRow[] = data.symbols.map((sym: Record<string, unknown>) => ({
          symbol: sym.symbol as string || "",
          exchange: sym.exchange as string || "N/A",
          live_price: sym.live_price as number || null,
          direction: sym.direction as string || "neutral",
          status: sym.status as string || "reject",
          confidence: sym.confidence as number || 0,
          long_score: sym.long_score as number || 50,
          short_score: sym.short_score as number || 50,
          pattern: sym.pattern as MatrixRow["pattern"],
          stop_loss: sym.stop_loss as number,
          tp1: sym.tp1 as number,
          tp2: sym.tp2 as number,
          tp3: sym.tp3 as number,
          risk_reward: sym.risk_reward as number,
          support: sym.support as number,
          resistance: sym.resistance as number,
          entry_trigger: sym.entry_trigger as string,
          invalidation: (sym as Record<string, unknown>).invalidation as string,
          reasons: sym.reasons as string[] || [],
          risks: sym.risks as string[] || [],
          funding: sym.funding as MatrixRow["funding"],
          open_interest: sym.open_interest as MatrixRow["open_interest"],
          volume: sym.volume as MatrixRow["volume"],
          indicators: sym.indicators as MatrixRow["indicators"],
          data_freshness: sym.data_freshness as string,
          last_updated: sym.last_updated as string,
          error: sym.error as string,
        }))
        setRows(matrix)
        setError(null)
      } else {
        setRows([])
        setError("No matrix data")
      }
    } catch (e) {
      setError("Market data unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const sorted = useMemo(() => {
    const filtered = rows.filter(r =>
      !search || r.symbol.toLowerCase().includes(search.toLowerCase())
    )
    return [...filtered].sort((a, b) => {
      let cmp = 0
      switch (sortField) {
        case "symbol": cmp = a.symbol.localeCompare(b.symbol); break
        case "confidence": cmp = a.confidence - b.confidence; break
        case "direction": cmp = a.direction.localeCompare(b.direction); break
        case "live_price": cmp = (a.live_price || 0) - (b.live_price || 0); break
        case "risk_reward": cmp = (a.risk_reward || 0) - (b.risk_reward || 0); break
      }
      return sortDir === "desc" ? -cmp : cmp
    })
  }, [rows, search, sortField, sortDir])

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(d => d === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortDir("desc")
    }
  }

  const toggleCol = (key: string) => {
    setHiddenCols(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key); else next.add(key)
      return next
    })
  }

  const visibleCols = ALL_COLUMNS.filter(c => !hiddenCols.has(c.key))

  const cell = (row: MatrixRow, col: typeof ALL_COLUMNS[0]) => {
    const val = col.key
    const classes = "px-2 py-1.5 text-[11px] whitespace-nowrap"

    switch (val) {
      case "symbol":
        return (
          <td key={val} className={cn(classes, "font-bold text-white font-mono sticky left-0 bg-[#0d1117] z-10")}>
            {row.symbol}
          </td>
        )
      case "exchange":
        return <td key={val} className={classes}>{row.exchange}</td>
      case "live_price":
        return (
          <td key={val} className={cn(classes, "font-mono")}>
            {row.live_price ? `$${formatPrice(row.live_price)}` : "N/A"}
          </td>
        )
      case "direction":
        return (
          <td key={val} className={classes}>
            <span className={cn("px-1.5 py-0.5 rounded text-[10px] font-bold border", DIRECTION_COLORS[row.direction] || "")}>
              {row.direction === "long" ? "LONG" : row.direction === "short" ? "SHORT" : "WAIT"}
            </span>
          </td>
        )
      case "confidence":
        return (
          <td key={val} className={classes}>
            <div className="flex items-center gap-1">
              <div className="w-12 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div className={cn("h-full rounded-full", row.confidence >= 80 ? "bg-green-500" : row.confidence >= 60 ? "bg-yellow-500" : "bg-red-500")}
                  style={{ width: `${row.confidence}%` }} />
              </div>
              <span className="font-mono text-[10px]">{row.confidence.toFixed(0)}%</span>
            </div>
          </td>
        )
      case "long_score":
        return (
          <td key={val} className={cn(classes, "font-mono", row.long_score > 60 ? "text-green-400" : "text-gray-500")}>
            {row.long_score.toFixed(0)}%
          </td>
        )
      case "short_score":
        return (
          <td key={val} className={cn(classes, "font-mono", row.short_score > 60 ? "text-red-400" : "text-gray-500")}>
            {row.short_score.toFixed(0)}%
          </td>
        )
      case "pattern_name":
        return <td key={val} className={classes}>{row.pattern?.name || "--"}</td>
      case "pattern_status":
        return (
          <td key={val} className={classes}>
            {row.pattern?.status ? (
              <span className={cn("text-[9px] px-1 rounded", row.pattern.status === "confirmed" ? "text-green-400 bg-green-900/20" : "text-yellow-400 bg-yellow-900/20")}>
                {row.pattern.status === "confirmed" ? "Təsdiq" : "Formalaşır"}
              </span>
            ) : "--"}
          </td>
        )
      case "entry_trigger":
        return <td key={val} className={cn(classes, "max-w-[120px] truncate")}>{row.entry_trigger || "--"}</td>
      case "stop_loss":
        return <td key={val} className={cn(classes, "font-mono text-red-400")}>{row.stop_loss ? `$${row.stop_loss.toFixed(2)}` : "--"}</td>
      case "tp1":
        return <td key={val} className={cn(classes, "font-mono text-green-400")}>{row.tp1 ? `$${row.tp1.toFixed(2)}` : "--"}</td>
      case "tp2":
        return <td key={val} className={cn(classes, "font-mono text-green-400/80")}>{row.tp2 ? `$${row.tp2.toFixed(2)}` : "--"}</td>
      case "tp3":
        return <td key={val} className={cn(classes, "font-mono text-green-400/60")}>{row.tp3 ? `$${row.tp3.toFixed(2)}` : "--"}</td>
      case "risk_reward":
        return <td key={val} className={cn(classes, "font-mono")}>{row.risk_reward ? `1:${row.risk_reward.toFixed(1)}` : "--"}</td>
      case "support":
        return <td key={val} className={cn(classes, "font-mono text-green-500")}>{row.support ? `$${row.support.toFixed(2)}` : "--"}</td>
      case "resistance":
        return <td key={val} className={cn(classes, "font-mono text-red-500")}>{row.resistance ? `$${row.resistance.toFixed(2)}` : "--"}</td>
      case "funding":
        return (
          <td key={val} className={cn(classes, "font-mono")}>
            {row.funding?.rate !== undefined ? `${(row.funding.rate * 100).toFixed(4)}%` : "--"}
          </td>
        )
      case "oi":
        return (
          <td key={val} className={cn(classes, "font-mono", (row.open_interest?.change || 0) > 0 ? "text-green-400" : "text-red-400")}>
            {row.open_interest?.change ? `${(row.open_interest.change > 0 ? "+" : "")}${row.open_interest.change.toFixed(1)}%` : "--"}
          </td>
        )
      case "volume_status":
        return (
          <td key={val} className={classes}>
            {row.volume?.status === "high" ? <span className="text-green-400">Yüksək</span> :
             row.volume?.status === "low" ? <span className="text-red-400">Aşağı</span> :
             row.volume?.status === "normal" ? <span className="text-gray-400">Normal</span> : "--"}
          </td>
        )
      case "rsi":
        return (
          <td key={val} className={cn(classes, "font-mono", (row.indicators?.rsi || 0) > 70 ? "text-red-400" : (row.indicators?.rsi || 0) < 30 ? "text-green-400" : "")}>
            {row.indicators?.rsi?.toFixed(0) || "--"}
          </td>
        )
      case "reasons":
        return <td key={val} className={cn(classes, "max-w-[150px]")}>
          <span className="text-gray-500 truncate block">{row.reasons?.slice(0, 2).join("; ") || "--"}</span>
        </td>
      case "risks":
        return <td key={val} className={cn(classes, "max-w-[120px]")}>
          <span className="text-red-400/70 truncate block">{row.risks?.slice(0, 1).join("; ") || "--"}</span>
        </td>
      case "status":
        return (
          <td key={val} className={classes}>
            <span className={cn("text-[9px] px-1.5 py-0.5 rounded font-medium", STATUS_COLORS[row.status] || "")}>
              {row.status === "active" ? "AKTİV" : row.status === "watchlist" ? "İZLƏMƏ" : "RƏDD"}
            </span>
          </td>
        )
      case "exchange_status":
        return (
          <td key={val} className={classes}>
            <span className="text-[9px] text-gray-500">
              {row.data_freshness === "live" ? "Canlı" : row.data_freshness || "--"}
            </span>
          </td>
        )
      default:
        return <td key={val} className={classes}>--</td>
    }
  }

  if (loading) {
    return (
      <div className="p-6 animate-pulse space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-8 bg-gray-800 rounded" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 flex items-center gap-2 text-yellow-400">
        <AlertCircle className="w-4 h-4" />
        {error}
      </div>
    )
  }

  return (
    <div className="p-4 space-y-3">
      {/* Controls */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">30 Aktiv Monitoru</h2>
          <span className="text-[10px] text-gray-500">{rows.length} aktiv</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-500" />
            <input
              type="text" placeholder="Search..."
              value={search} onChange={e => setSearch(e.target.value)}
              className="pl-6 pr-2 py-1 text-[11px] bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:border-blue-500 w-32"
            />
          </div>
          {/* Column visibility */}
          <div className="relative group">
            <button className="p-1.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-400">
              <Eye className="w-3 h-3" />
            </button>
            <div className="absolute right-0 top-full mt-1 bg-gray-900 border border-gray-700 rounded-lg p-2 shadow-xl z-50 hidden group-hover:block min-w-[160px]">
              {ALL_COLUMNS.map(col => (
                <label key={col.key} className="flex items-center gap-1.5 py-0.5 cursor-pointer hover:bg-gray-800 rounded px-1">
                  <input
                    type="checkbox"
                    checked={!hiddenCols.has(col.key)}
                    onChange={() => toggleCol(col.key)}
                    className="w-2.5 h-2.5"
                  />
                  <span className="text-[10px] text-gray-300">{col.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-900/80 text-[10px] text-gray-500 uppercase tracking-wider border-b border-gray-800">
              {visibleCols.map(col => (
                <th key={col.key} className={cn(
                  "px-2 py-2 font-medium",
                  col.sortable ? "cursor-pointer hover:text-gray-300" : "",
                  col.key === "symbol" ? "sticky left-0 bg-gray-900/80 z-10" : "",
                )}
                  onClick={() => col.sortable && toggleSort(col.key as SortField)}>
                  <div className="flex items-center gap-1">
                    {col.label}
                    {col.sortable && sortField === col.key && (
                      <ArrowUpDown className={cn("w-2.5 h-2.5", sortDir === "asc" ? "rotate-180" : "")} />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr key={row.symbol}
                className={cn(
                  "border-b border-gray-800/50 hover:bg-gray-800/20 transition-colors",
                  i % 2 === 0 ? "bg-gray-900/20" : "",
                  row.error ? "opacity-50" : "",
                )}>
                {visibleCols.map(col => cell(row, col))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-[9px] text-gray-600">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-green-500" /> LONG</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-red-500" /> SHORT</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-yellow-500" /> WAIT</span>
        <span className="flex items-center gap-1"><Clock className="w-2.5 h-2.5" /> Canlı məlumat</span>
      </div>
    </div>
  )
}
