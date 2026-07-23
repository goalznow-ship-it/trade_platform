"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { useMarketStore } from "@/store/market"
import {
  Star, Plus, Trash2, GripVertical, List,
} from "lucide-react"
import type { Watchlist, WatchlistSymbol } from "@/types"

export function WatchlistPanel() {
  const { setSymbol } = useMarketStore()
  const [watchlists, setWatchlists] = useState<Watchlist[]>([])
  const [activeId, setActiveId] = useState<number | null>(null)
  const [newName, setNewName] = useState("")
  const [newSymbol, setNewSymbol] = useState("")

  async function loadWatchlists() {
    try {
      const data = await api.getWatchlists()
      setWatchlists(data)
      if (data.length > 0 && !activeId) setActiveId(data[0].id)
    } catch {}
  }

  useEffect(() => {
    const initialLoad = async () => {
      try {
        const data = await api.getWatchlists()
        setWatchlists(data)
        if (data.length > 0) setActiveId(data[0].id)
      } catch {}
    }
    initialLoad()
  }, [])

  async function handleCreate() {
    if (!newName) return
    await api.createWatchlist(newName)
    setNewName("")
    loadWatchlists()
  }

  async function handleDelete(id: number) {
    await api.deleteWatchlist(id)
    if (activeId === id) setActiveId(null)
    loadWatchlists()
  }

  async function handleAddSymbol() {
    if (!activeId || !newSymbol) return
    await api.addWatchlistSymbol(activeId, newSymbol.toUpperCase())
    setNewSymbol("")
    loadWatchlists()
  }

  async function handleRemoveSymbol(symbol: string) {
    if (!activeId) return
    await api.removeWatchlistSymbol(activeId, symbol)
    loadWatchlists()
  }

  const active = watchlists.find((w) => w.id === activeId)

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center gap-2 mb-3">
          <List className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-medium text-gray-200">Watchlists</span>
        </div>
        <div className="flex gap-2 mb-2 overflow-x-auto">
          {watchlists.map((wl) => (
            <button
              key={wl.id}
              onClick={() => setActiveId(wl.id)}
              className={`px-3 py-1.5 text-xs rounded-lg whitespace-nowrap ${
                activeId === wl.id
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {wl.name} ({wl.symbol_count || 0})
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="New watchlist..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs text-white"
          />
          <Button size="sm" onClick={handleCreate}>
            <Plus className="w-3 h-3" />
          </Button>
        </div>
      </div>

      {active && (
        <div className="p-3 border-b border-gray-800">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Add symbol (e.g. BTC/USDT)..."
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs text-white font-mono"
            />
            <Button size="sm" onClick={handleAddSymbol}>
              <Plus className="w-3 h-3" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => handleDelete(active.id)}>
              <Trash2 className="w-3 h-3 text-red-400" />
            </Button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        {active?.symbols?.length === 0 && (
          <div className="p-4 text-center text-gray-600 text-xs">No symbols yet</div>
        )}
        {active?.symbols?.map((s: WatchlistSymbol) => (
          <div
            key={s.id}
            className="flex items-center gap-2 px-3 py-2 border-b border-gray-800 hover:bg-gray-800/50 group cursor-pointer"
            onClick={() => setSymbol(s.symbol)}
          >
            <GripVertical className="w-3 h-3 text-gray-700" />
            <Star className="w-3 h-3 text-yellow-500" />
            <span className="text-sm text-gray-200 font-mono flex-1">{s.symbol}</span>
            <Badge variant="info" className="text-[9px]">{s.exchange || "BINANCE"}</Badge>
            <button
              onClick={(e) => { e.stopPropagation(); handleRemoveSymbol(s.symbol) }}
              className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
