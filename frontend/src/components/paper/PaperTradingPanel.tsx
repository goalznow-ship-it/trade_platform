"use client"

import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { cn, formatPrice } from "@/lib/utils"
import {
  Wallet, Plus, RotateCcw, X,
  ArrowUp, ArrowDown, Clock,
} from "lucide-react"

interface PaperAccount {
  balance: number;
}
interface PaperPosition {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  leverage: number;
  pnl: number;
}
interface PaperOrder {
  id: number;
  symbol: string;
  side: string;
  status: string;
  quantity: number;
  price: number;
}

export function PaperTradingPanel() {
  const [account, setAccount] = useState<PaperAccount | null>(null)
  const [positions, setPositions] = useState<PaperPosition[]>([])
  const [orders, setOrders] = useState<PaperOrder[]>([])
  const [showOrder, setShowOrder] = useState(false)
  const [form, setForm] = useState({
    symbol: "BTC/USDT", side: "buy", order_type: "market",
    quantity: 0.01, price: 50000, leverage: 1,
  })

  const load = useCallback(async () => {
    try {
      const [a, p, o] = await Promise.all([
        api.getPaperAccount(), api.getPaperPositions(), api.getPaperOrders(),
      ])
      setAccount(a as PaperAccount)
      setPositions((p || []) as PaperPosition[])
      setOrders((o || []) as PaperOrder[])
    } catch {}
  }, [])

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load() }, [load])

  async function handlePlaceOrder() {
    await api.createPaperOrder(form)
    setShowOrder(false)
    load()
  }

  async function handleClosePosition(id: number) {
    await api.closePaperPosition(id)
    load()
  }

  async function handleReset() {
    await api.resetPaperAccount()
    load()
  }

  const pnl = account ? (account.balance ?? 0) - 100000 : 0
  const pnlPct = (((account?.balance ?? 0) || 100000) / 100000 - 1) * 100

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wallet className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-gray-200">Paper Trading</span>
            <Badge variant="info">Demo</Badge>
          </div>
          <div className="flex gap-1">
            <Button size="sm" onClick={() => setShowOrder(!showOrder)}>
              <Plus className="w-3 h-3 mr-1" /> Order
            </Button>
            <Button variant="ghost" size="sm" onClick={handleReset}>
              <RotateCcw className="w-3 h-3" />
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="p-2 rounded-lg bg-gray-800/50">
            <div className="text-[10px] text-gray-500">Balance</div>
            <div className="text-sm font-bold text-white font-mono">{formatPrice(account?.balance || 0)}</div>
          </div>
          <div className="p-2 rounded-lg bg-gray-800/50">
            <div className="text-[10px] text-gray-500">PnL</div>
            <div className={cn("text-sm font-bold font-mono", pnl >= 0 ? "text-green-400" : "text-red-400")}>
              {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)} ({pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(2)}%)
            </div>
          </div>
        </div>
      </div>

      {showOrder && (
        <div className="p-3 border-b border-gray-800 space-y-2 bg-gray-900/50">
          <div className="flex gap-2">
            <button
              onClick={() => setForm({ ...form, side: "buy" })}
              className={cn("flex-1 py-1.5 text-xs rounded font-medium", form.side === "buy" ? "bg-green-600 text-white" : "bg-gray-800 text-gray-400")}
            >
              <ArrowUp className="w-3 h-3 inline mr-1" /> Buy
            </button>
            <button
              onClick={() => setForm({ ...form, side: "sell" })}
              className={cn("flex-1 py-1.5 text-xs rounded font-medium", form.side === "sell" ? "bg-red-600 text-white" : "bg-gray-800 text-gray-400")}
            >
              <ArrowDown className="w-3 h-3 inline mr-1" /> Sell
            </button>
          </div>
          <div className="flex gap-2">
            <input type="text" placeholder="BTC/USDT" value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value })}
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white font-mono" />
            <input type="number" placeholder="Qty" value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: parseFloat(e.target.value) || 0 })}
              className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white font-mono" />
          </div>
          <div className="flex gap-2">
            <input type="number" placeholder="Price" value={form.price}
              onChange={(e) => setForm({ ...form, price: parseFloat(e.target.value) || 0 })}
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white font-mono" />
            <select value={form.leverage}
              onChange={(e) => setForm({ ...form, leverage: parseInt(e.target.value) })}
              className="w-16 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white">
              {[1, 2, 3, 5, 10, 20].map((l) => (
                <option key={l} value={l}>{l}x</option>
              ))}
            </select>
          </div>
          <Button size="sm" onClick={handlePlaceOrder} className="w-full">
            Place {form.side === "buy" ? "Buy" : "Sell"} Order
          </Button>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        {positions.length > 0 && (
          <>
            <div className="px-3 py-1.5 text-[10px] font-medium text-gray-500 bg-gray-900/50">Open Positions</div>
            {positions.map((p) => (
              <div key={p.id} className="flex items-center gap-2 px-3 py-2 border-b border-gray-800 hover:bg-gray-800/50">
                <div className={cn("w-1 h-8 rounded-full", p.side === "long" ? "bg-green-500" : "bg-red-500")} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1">
                    <span className="text-xs font-medium text-gray-200 font-mono">{p.symbol}</span>
                    <Badge variant={p.side === "long" ? "success" : "danger"} className="text-[9px]">
                      {p.side?.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="text-[10px] text-gray-500">
                    {p.quantity} @ {formatPrice(p.entry_price)} · {p.leverage}x
                  </div>
                </div>
                <div className="text-right">
                  <div className={cn("text-xs font-mono font-medium", p.pnl >= 0 ? "text-green-400" : "text-red-400")}>
                    {p.pnl >= 0 ? "+" : ""}{p.pnl?.toFixed(2)}
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => handleClosePosition(p.id)}>
                    <X className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            ))}
          </>
        )}

        {orders.filter((o: PaperOrder) => o.status === "pending" || o.status === "open").length > 0 && (
          <>
            <div className="px-3 py-1.5 text-[10px] font-medium text-gray-500 bg-gray-900/50">Open Orders</div>
            {orders.filter((o: PaperOrder) => o.status === "pending" || o.status === "open").map((o) => (
              <div key={o.id} className="flex items-center gap-2 px-3 py-2 border-b border-gray-800">
                <Clock className="w-3 h-3 text-yellow-500" />
                <span className="text-xs text-gray-200 font-mono">{o.symbol}</span>
                <Badge variant="warning" className="text-[9px]">{o.side}</Badge>
                <span className="text-[10px] text-gray-500">{o.quantity} @ {formatPrice(o.price)}</span>
              </div>
            ))}
          </>
        )}

        {positions.length === 0 && orders.length === 0 && (
          <div className="p-4 text-center text-gray-600 text-xs">
            No positions or orders. Start paper trading!
          </div>
        )}
      </div>
    </div>
  )
}
