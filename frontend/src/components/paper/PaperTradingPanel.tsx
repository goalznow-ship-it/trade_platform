"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { cn, formatPrice } from "@/lib/utils"
import { ArrowDown, ArrowUp, Clock, Plus, RotateCcw, Shield, Wallet, X } from "lucide-react"

interface PaperAccount {
  balance: number
  initial_balance: number
  equity: number
  free_margin: number
  used_margin: number
  total_pnl: number
  total_trades: number
  win_rate: number
}

interface PaperPosition {
  id: number
  symbol: string
  side: "long" | "short"
  size: number
  entry_price: number
  mark_price?: number | null
  liquidation_price?: number | null
  leverage: number
  margin: number
  unrealized_pnl: number
  stop_loss?: number | null
  take_profit?: number | null
}

interface PaperOrder {
  id: number
  symbol: string
  side: "buy" | "sell"
  order_type: string
  status: string
  quantity: number
  price?: number | null
  executed_price?: number | null
}

interface ClosedPosition {
  id: number
  symbol: string
  side: string
  pnl: number
  closed_at?: string | null
}

interface OrderResponse {
  error?: string
  validation_failures?: string[]
  risk_score?: number
}

const symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
const fieldClass = "w-full rounded border border-gray-700 bg-gray-800 px-2 py-1.5 font-mono text-xs text-white outline-none focus:border-blue-500"

export function PaperTradingPanel() {
  const [account, setAccount] = useState<PaperAccount | null>(null)
  const [positions, setPositions] = useState<PaperPosition[]>([])
  const [orders, setOrders] = useState<PaperOrder[]>([])
  const [closed, setClosed] = useState<ClosedPosition[]>([])
  const [showOrder, setShowOrder] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [riskDraft, setRiskDraft] = useState<Record<number, { sl: string; tp: string }>>({})
  const [form, setForm] = useState({
    symbol: "BTC/USDT", side: "buy", order_type: "market",
    quantity: 0.01, price: 0, leverage: 1,
  })

  const load = useCallback(async () => {
    try {
      const [accountData, positionData, orderData, closedData] = await Promise.all([
        api.getPaperAccount(),
        api.getPaperPositions(),
        api.getPaperOrders(),
        api.getClosedPaperPositions(),
      ])
      setAccount(accountData as PaperAccount)
      setPositions(Array.isArray(positionData) ? positionData as PaperPosition[] : [])
      setOrders(Array.isArray(orderData) ? orderData as PaperOrder[] : [])
      setClosed(Array.isArray(closedData) ? closedData as ClosedPosition[] : [])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Paper hesab məlumatı alınmadı")
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 15000)
    return () => clearInterval(interval)
  }, [load])

  const pendingOrders = useMemo(
    () => orders.filter((order) => order.status === "pending" || order.status === "open"),
    [orders],
  )

  async function runAction(action: () => Promise<unknown>, success: string) {
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const response = await action() as OrderResponse | undefined
      if (response?.error) {
        const failures = response.validation_failures?.join(" · ")
        throw new Error(`${response.error}${failures ? `: ${failures}` : ""}`)
      }
      setNotice(success)
      await load()
      return true
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Əməliyyat tamamlanmadı")
      return false
    } finally {
      setBusy(false)
    }
  }

  async function handlePlaceOrder() {
    if (!form.symbol || form.quantity <= 0 || (form.order_type === "limit" && form.price <= 0)) {
      setError("Symbol, miqdar və limit order üçün qiymət düzgün daxil edilməlidir")
      return
    }
    const payload = {
      ...form,
      symbol: form.symbol.trim().toUpperCase(),
      price: form.order_type === "limit" ? form.price : undefined,
    }
    const completed = await runAction(
      () => api.createPaperOrder(payload),
      form.order_type === "market" ? "Market order icra edildi" : "Limit order yaradıldı",
    )
    if (completed) setShowOrder(false)
  }

  async function updateRisk(position: PaperPosition) {
    const draft = riskDraft[position.id]
    const stopLoss = draft?.sl ? Number(draft.sl) : position.stop_loss ?? undefined
    const takeProfit = draft?.tp ? Number(draft.tp) : position.take_profit ?? undefined
    await runAction(
      () => api.updatePaperPositionRisk(position.id, stopLoss, takeProfit),
      "SL/TP yeniləndi",
    )
  }

  async function handleReset() {
    if (!window.confirm("Paper hesabı, bütün order və mövqelərlə birlikdə sıfırlansın?")) return
    await runAction(() => api.resetPaperAccount(), "Paper hesab sıfırlandı")
  }

  const pnl = account?.total_pnl ?? ((account?.equity ?? 0) - (account?.initial_balance ?? 0))
  const pnlPct = account?.initial_balance ? pnl / account.initial_balance * 100 : 0

  return (
    <div className="flex h-full flex-col">
      <div className="space-y-3 border-b border-gray-800 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Wallet className="h-4 w-4 text-blue-400" />
            <span className="text-sm font-medium text-gray-200">Paper Trading</span>
            <Badge variant="info">Real qiymət · virtual kapital</Badge>
          </div>
          <div className="flex gap-1">
            <Button size="sm" onClick={() => setShowOrder(!showOrder)} disabled={busy}>
              <Plus className="mr-1 h-3 w-3" /> Order
            </Button>
            <Button variant="ghost" size="sm" onClick={handleReset} disabled={busy} title="Hesabı sıfırla">
              <RotateCcw className="h-3 w-3" />
            </Button>
          </div>
        </div>

        {error && <div className="rounded border border-red-900/60 bg-red-950/30 p-2 text-[10px] text-red-300">{error}</div>}
        {notice && <div className="rounded border border-green-900/60 bg-green-950/30 p-2 text-[10px] text-green-300">{notice}</div>}

        <div className="grid grid-cols-2 gap-2 lg:grid-cols-5">
          <Metric label="Equity" value={formatPrice(account?.equity ?? 0)} />
          <Metric label="Free margin" value={formatPrice(account?.free_margin ?? 0)} />
          <Metric label="Used margin" value={formatPrice(account?.used_margin ?? 0)} />
          <Metric label="PnL" value={`${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)} (${pnlPct.toFixed(2)}%)`} positive={pnl >= 0} />
          <Metric label="Win rate" value={account?.total_trades ? `${account.win_rate.toFixed(1)}% · ${account.total_trades}` : "Məlumat yoxdur"} />
        </div>
      </div>

      {showOrder && (
        <div className="space-y-2 border-b border-gray-800 bg-gray-900/50 p-3">
          <div className="grid grid-cols-2 gap-2">
            <SideButton side="buy" active={form.side === "buy"} onClick={() => setForm({ ...form, side: "buy" })} />
            <SideButton side="sell" active={form.side === "sell"} onClick={() => setForm({ ...form, side: "sell" })} />
          </div>
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
            <select value={form.symbol} onChange={(event) => setForm({ ...form, symbol: event.target.value })} className={fieldClass}>
              {symbols.map((symbol) => <option key={symbol}>{symbol}</option>)}
            </select>
            <select value={form.order_type} onChange={(event) => setForm({ ...form, order_type: event.target.value })} className={fieldClass}>
              <option value="market">Market</option>
              <option value="limit">Limit</option>
            </select>
            <input type="number" min="0" step="any" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: Number(event.target.value) })} className={fieldClass} aria-label="Miqdar" />
            <select value={form.leverage} onChange={(event) => setForm({ ...form, leverage: Number(event.target.value) })} className={fieldClass}>
              {[1, 2, 3, 5, 10, 20].map((leverage) => <option key={leverage} value={leverage}>{leverage}x</option>)}
            </select>
          </div>
          {form.order_type === "limit" && (
            <input type="number" min="0" step="any" placeholder="Limit qiyməti" value={form.price || ""} onChange={(event) => setForm({ ...form, price: Number(event.target.value) })} className={fieldClass} />
          )}
          <Button size="sm" onClick={handlePlaceOrder} disabled={busy} className="w-full">
            {busy ? "Yoxlanılır..." : `${form.side === "buy" ? "LONG" : "SHORT"} order göndər`}
          </Button>
          <div className="flex items-center gap-1 text-[9px] text-gray-600">
            <Shield className="h-3 w-3" /> Order execution gate və margin yoxlamasından keçir.
          </div>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        <Section title={`Açıq mövqelər (${positions.length})`}>
          {positions.map((position) => (
            <div key={position.id} className="space-y-2 border-b border-gray-800 px-3 py-2">
              <div className="flex items-center gap-2">
                <div className={cn("h-8 w-1 rounded-full", position.side === "long" ? "bg-green-500" : "bg-red-500")} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1">
                    <span className="font-mono text-xs font-medium text-gray-200">{position.symbol}</span>
                    <Badge variant={position.side === "long" ? "success" : "danger"} className="text-[9px]">{position.side.toUpperCase()}</Badge>
                  </div>
                  <div className="text-[10px] text-gray-500">
                    {position.size} @ {formatPrice(position.entry_price)} · mark {formatPrice(position.mark_price ?? 0)} · {position.leverage}x
                  </div>
                </div>
                <div className="text-right">
                  <div className={cn("font-mono text-xs font-medium", position.unrealized_pnl >= 0 ? "text-green-400" : "text-red-400")}>
                    {position.unrealized_pnl >= 0 ? "+" : ""}{position.unrealized_pnl.toFixed(2)}
                  </div>
                  <Button variant="ghost" size="sm" disabled={busy} onClick={() => runAction(() => api.closePaperPosition(position.id), "Mövqe bağlandı")}>
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-[1fr_1fr_auto] gap-2">
                <input className={fieldClass} placeholder={`SL ${position.stop_loss ?? "—"}`} value={riskDraft[position.id]?.sl ?? ""} onChange={(event) => setRiskDraft({ ...riskDraft, [position.id]: { sl: event.target.value, tp: riskDraft[position.id]?.tp ?? "" } })} />
                <input className={fieldClass} placeholder={`TP ${position.take_profit ?? "—"}`} value={riskDraft[position.id]?.tp ?? ""} onChange={(event) => setRiskDraft({ ...riskDraft, [position.id]: { sl: riskDraft[position.id]?.sl ?? "", tp: event.target.value } })} />
                <Button variant="ghost" size="sm" disabled={busy} onClick={() => updateRisk(position)}>SL/TP</Button>
              </div>
            </div>
          ))}
          {positions.length === 0 && <Empty text="Açıq paper mövqe yoxdur" />}
        </Section>

        <Section title={`Gözləyən orderlər (${pendingOrders.length})`}>
          {pendingOrders.map((order) => (
            <div key={order.id} className="flex items-center gap-2 border-b border-gray-800 px-3 py-2">
              <Clock className="h-3 w-3 text-yellow-500" />
              <span className="font-mono text-xs text-gray-200">{order.symbol}</span>
              <Badge variant="warning" className="text-[9px]">{order.side.toUpperCase()} · {order.order_type}</Badge>
              <span className="flex-1 text-[10px] text-gray-500">{order.quantity} @ {order.price ? formatPrice(order.price) : "market"}</span>
              <Button variant="ghost" size="sm" disabled={busy} onClick={() => runAction(() => api.cancelPaperOrder(order.id), "Order ləğv edildi")}><X className="h-3 w-3" /></Button>
            </div>
          ))}
          {pendingOrders.length === 0 && <Empty text="Gözləyən order yoxdur" />}
        </Section>

        <Section title="Son bağlanan mövqelər">
          {closed.slice(0, 10).map((position) => (
            <div key={position.id} className="flex items-center gap-2 border-b border-gray-800 px-3 py-2 text-xs">
              <span className="flex-1 font-mono text-gray-300">{position.symbol} · {position.side.toUpperCase()}</span>
              <span className={position.pnl >= 0 ? "text-green-400" : "text-red-400"}>{position.pnl >= 0 ? "+" : ""}{position.pnl.toFixed(2)}</span>
            </div>
          ))}
          {closed.length === 0 && <Empty text="Bağlanmış mövqe yoxdur" />}
        </Section>
      </div>
    </div>
  )
}

function Metric({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return <div className="rounded-lg bg-gray-800/50 p-2">
    <div className="text-[9px] uppercase text-gray-500">{label}</div>
    <div className={cn("mt-0.5 font-mono text-xs font-bold text-white", positive != null && (positive ? "text-green-400" : "text-red-400"))}>{value}</div>
  </div>
}

function SideButton({ side, active, onClick }: { side: "buy" | "sell"; active: boolean; onClick: () => void }) {
  const buy = side === "buy"
  return <button onClick={onClick} className={cn("rounded py-1.5 text-xs font-medium", active ? (buy ? "bg-green-600 text-white" : "bg-red-600 text-white") : "bg-gray-800 text-gray-400")}>
    {buy ? <ArrowUp className="mr-1 inline h-3 w-3" /> : <ArrowDown className="mr-1 inline h-3 w-3" />}
    {buy ? "LONG" : "SHORT"}
  </button>
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section><div className="bg-gray-900/50 px-3 py-1.5 text-[10px] font-medium uppercase text-gray-500">{title}</div>{children}</section>
}

function Empty({ text }: { text: string }) {
  return <div className="p-4 text-center text-xs text-gray-600">{text}</div>
}
