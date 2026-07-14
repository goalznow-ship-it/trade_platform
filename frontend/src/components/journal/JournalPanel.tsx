"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { cn } from "@/lib/utils"
import {
  BookOpen, Plus, Trash2, TrendingUp, TrendingDown,
  Smile, Frown, Meh, Star, Edit3,
} from "lucide-react"

const SIDES = ["long", "short"]
const RATINGS = ["excellent", "good", "average", "poor", "terrible"]
const EMOTIONS = ["confident", "anxious", "neutral", "excited", "fearful", "greedy", "regretful"]

export function JournalPanel() {
  const [entries, setEntries] = useState<any[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    symbol: "", side: "long", notes: "", emotion: "neutral",
    rating: "good", mistakes: "", lessons: "",
  })

  async function load() {
    try {
      const res = await api.getJournal(page, 20)
      setEntries(res.items || res.data || res || [])
      setTotal(res.total || 0)
    } catch {}
  }

  useEffect(() => { load() }, [page])

  async function handleCreate() {
    await api.createJournalEntry(form)
    setShowForm(false)
    setForm({ symbol: "", side: "long", notes: "", emotion: "neutral", rating: "good", mistakes: "", lessons: "" })
    load()
  }

  async function handleDelete(id: number) {
    await api.deleteJournalEntry(id)
    load()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-gray-200">Trading Journal</span>
            <Badge variant="info">{total}</Badge>
          </div>
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            <Plus className="w-3 h-3 mr-1" /> Entry
          </Button>
        </div>
      </div>

      {showForm && (
        <div className="p-3 border-b border-gray-800 space-y-2 bg-gray-900/50">
          <div className="flex gap-2">
            <input
              type="text" placeholder="Symbol (e.g. BTC/USDT)" value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value })}
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white font-mono"
            />
            <div className="flex gap-1">
              {SIDES.map((s) => (
                <button
                  key={s}
                  onClick={() => setForm({ ...form, side: s })}
                  className={cn("px-2 py-1 text-xs rounded", {
                    "bg-green-600 text-white": form.side === "long" && s === "long",
                    "bg-red-600 text-white": form.side === "short" && s === "short",
                    "bg-gray-800 text-gray-400": form.side !== s,
                  })}
                >
                  {s === "long" ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                </button>
              ))}
            </div>
          </div>
          <textarea
            placeholder="Trade notes..."
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white h-16 resize-none"
          />
          <div className="flex gap-2">
            <select
              value={form.emotion}
              onChange={(e) => setForm({ ...form, emotion: e.target.value })}
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
            >
              {EMOTIONS.map((e) => (
                <option key={e} value={e}>{e}</option>
              ))}
            </select>
            <select
              value={form.rating}
              onChange={(e) => setForm({ ...form, rating: e.target.value })}
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
            >
              {RATINGS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <input
            type="text" placeholder="Mistakes made..." value={form.mistakes}
            onChange={(e) => setForm({ ...form, mistakes: e.target.value })}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
          />
          <input
            type="text" placeholder="Lessons learned..." value={form.lessons}
            onChange={(e) => setForm({ ...form, lessons: e.target.value })}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
          />
          <Button size="sm" onClick={handleCreate} className="w-full">Save Entry</Button>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        {(entries.length === 0) && (
          <div className="p-4 text-center text-gray-600 text-xs">No journal entries yet</div>
        )}
        {Array.isArray(entries) && entries.map((e) => (
          <div key={e.id} className="px-3 py-2.5 border-b border-gray-800 hover:bg-gray-800/50 group">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium text-gray-200 font-mono">{e.symbol}</span>
              <Badge variant={e.side === "long" ? "success" : "danger"} className="text-[9px]">
                {e.side?.toUpperCase()}
              </Badge>
              <div className="flex gap-0.5">
                {["excellent", "good", "average", "poor", "terrible"].indexOf(e.rating) <= 2 ? (
                  <Star className="w-3 h-3 text-yellow-500" />
                ) : (
                  <Star className="w-3 h-3 text-gray-600" />
                )}
              </div>
              <span className="text-[10px] text-gray-500 capitalize">{e.emotion}</span>
              <div className="flex-1" />
              <button onClick={() => handleDelete(e.id)} className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100">
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
            {e.notes && <div className="text-[10px] text-gray-400 line-clamp-2">{e.notes}</div>}
            <div className="text-[9px] text-gray-600 mt-1">
              {e.created_at ? new Date(e.created_at).toLocaleDateString() : ""}
              {e.mistakes && ` · Mistakes: ${e.mistakes}`}
            </div>
          </div>
        ))}
      </div>

      {total > 20 && (
        <div className="flex items-center justify-between px-3 py-2 border-t border-gray-800">
          <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </Button>
          <span className="text-[10px] text-gray-500">Page {page}</span>
          <Button variant="ghost" size="sm" disabled={page * 20 >= total} onClick={() => setPage(page + 1)}>
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
