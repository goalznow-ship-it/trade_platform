"use client"

import { useEffect, useMemo, useState } from "react"
import { api } from "@/lib/api"
import { useMarketStore } from "@/store/market"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { cn, formatPrice } from "@/lib/utils"
import { AlertTriangle, ArrowDown, ArrowUp, RefreshCw, ShieldCheck, Store, X } from "lucide-react"

type Mode = "paper" | "live"
type Side = "long" | "short"

interface TradingStatus {
  default_mode: Mode
  live_trading_enabled: boolean
  kill_switch_active: boolean
  accepting_live_orders: boolean
  configured_exchanges: string[]
}

interface OrderPreview {
  preview_only: true
  entry_price: number
  quantity: number
  notional: number
  required_margin: number
  estimated_fees: number
  liquidation_price?: number | null
  max_loss_at_stop: number
  potential_profit_at_target: number
  risk_reward?: number | null
  can_submit_live: boolean
  approval: {
    approved: boolean
    risk_score?: number
    risk_label?: string
    rejection_reasons?: string[]
    validation?: { passed_count?: number; check_count?: number }
  }
  estimated_slippage?: { estimated_slippage_pct?: number; liquidity_tier?: string }
}

interface LivePosition {
  exchange: string
  symbol: string
  side: "long" | "short"
  size: number
  entry_price: number
  mark_price: number
  liquidation_price: number
  leverage: number
  unrealized_pnl: number
}

interface LiveOrder {
  order_id: string
  symbol: string
  side: string
  order_type: string
  quantity: number
  filled_quantity: number
  price?: number | null
  status: string
}

const LEVERAGE_OPTIONS = [1, 2, 3, 5, 10, 20, 50]
const fieldClass = "w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 font-mono text-sm text-white outline-none focus:border-blue-500"

export function TradingPanel() {
  const { selectedSymbol, tickers } = useMarketStore()
  const [mode, setMode] = useState<Mode>("paper")
  const [side, setSide] = useState<Side>("long")
  const [orderType, setOrderType] = useState<"market" | "limit">("market")
  const [leverage, setLeverage] = useState(3)
  const [capital, setCapital] = useState("100")
  const [limitPrice, setLimitPrice] = useState("")
  const [stopLoss, setStopLoss] = useState("")
  const [takeProfit, setTakeProfit] = useState("")
  const [status, setStatus] = useState<TradingStatus | null>(null)
  const [balance, setBalance] = useState<number | null>(null)
  const [positions, setPositions] = useState<LivePosition[]>([])
  const [openOrders, setOpenOrders] = useState<LiveOrder[]>([])
  const [restPrice, setRestPrice] = useState(0)
  const [preview, setPreview] = useState<OrderPreview | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [closeDraft, setCloseDraft] = useState<{ position: LivePosition; percentage: number } | null>(null)

  const ticker = tickers[selectedSymbol] || tickers[selectedSymbol.replace("/", "")] || tickers[selectedSymbol.replace("/", "-")]
  const marketPrice = Number(ticker?.price || restPrice || 0)
  const entryPrice = orderType === "limit" ? Number(limitPrice) : marketPrice
  const capitalValue = Number(capital)
  const quantity = entryPrice > 0 && capitalValue > 0 ? capitalValue / entryPrice : 0
  const symbol = selectedSymbol.includes("/") ? selectedSymbol : selectedSymbol.replace(/USDT$/, "/USDT")
  const liveUnavailable = !status?.accepting_live_orders

  async function loadAccount() {
    try {
      const [statusData, balanceData, positionData, orderData] = await Promise.all([
        api.getTradingStatus(),
        api.getBalance().catch(() => ({})),
        api.getPositions().catch(() => []),
        api.getOpenOrders("binance").catch(() => []),
      ])
      setStatus(statusData)
      setBalance(balanceData?.binance?.free ?? null)
      setPositions(Array.isArray(positionData) ? positionData as LivePosition[] : [])
      setOpenOrders(Array.isArray(orderData) ? orderData as LiveOrder[] : [])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Trading statusu alınmadı")
    }
  }

  useEffect(() => {
    loadAccount()
    const interval = setInterval(loadAccount, 20000)
    return () => clearInterval(interval)
  }, [selectedSymbol])

  useEffect(() => {
    let active = true
    const loadPrice = async () => {
      const data = await api.getTicker(selectedSymbol).catch(() => null)
      if (active && data) setRestPrice(Number(data.price || data.last || 0))
    }
    setRestPrice(0)
    loadPrice()
    const retries = [setTimeout(loadPrice, 2000), setTimeout(loadPrice, 5000)]
    const interval = setInterval(loadPrice, 15000)
    return () => {
      active = false
      retries.forEach(clearTimeout)
      clearInterval(interval)
    }
  }, [selectedSymbol])

  useEffect(() => {
    setPreview(null)
    setConfirming(false)
    setError(null)
  }, [selectedSymbol, side, orderType, leverage, capital, limitPrice, stopLoss, takeProfit, mode])

  const payload = useMemo(() => ({
    exchange: "binance",
    symbol,
    side: side === "long" ? "buy" : "sell",
    amount: quantity,
    order_type: orderType,
    price: orderType === "limit" ? Number(limitPrice) : undefined,
    stop_loss: Number(stopLoss),
    take_profit: Number(takeProfit),
    leverage,
    margin_mode: "isolated",
  }), [symbol, side, quantity, orderType, limitPrice, stopLoss, takeProfit, leverage])

  function validate() {
    if (!entryPrice || !capitalValue || quantity <= 0) return "Real qiymət və kapital düzgün olmalıdır"
    if (!Number(stopLoss) || !Number(takeProfit)) return "Açılış order-i üçün Stop Loss və Take Profit məcburidir"
    if (side === "long" && !(Number(stopLoss) < entryPrice && Number(takeProfit) > entryPrice)) return "LONG üçün SL girişdən aşağı, TP girişdən yuxarı olmalıdır"
    if (side === "short" && !(Number(stopLoss) > entryPrice && Number(takeProfit) < entryPrice)) return "SHORT üçün SL girişdən yuxarı, TP girişdən aşağı olmalıdır"
    return null
  }

  async function handlePreview() {
    const validationError = validate()
    if (validationError) return setError(validationError)
    setBusy(true); setError(null); setNotice(null)
    try {
      setPreview(await api.previewOrder(payload))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Order preview hazırlanmadı")
    } finally {
      setBusy(false)
    }
  }

  async function handlePaperOrder() {
    const validationError = validate()
    if (validationError) return setError(validationError)
    if (!window.confirm(`PAPER ${side.toUpperCase()} order açılsın?\n${capitalValue.toFixed(2)} USDT · ${leverage}x`)) return
    setBusy(true); setError(null)
    try {
      const result = await api.createPaperOrder({
        symbol, side: payload.side, order_type: orderType,
        quantity, price: payload.price, leverage,
        stop_loss: payload.stop_loss, take_profit: payload.take_profit,
      }) as { error?: string; validation_failures?: string[] }
      if (result?.error) throw new Error(result.validation_failures?.join(" · ") || result.error)
      setNotice("Paper order execution gate-dən keçərək yaradıldı")
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Paper order yaradılmadı")
    } finally {
      setBusy(false)
    }
  }

  async function handleLiveOrder() {
    if (!preview?.can_submit_live || !preview.approval.approved) return
    setBusy(true); setError(null); setConfirming(false)
    try {
      const clientOrderId = `ta_${crypto.randomUUID().replaceAll("-", "")}`
      const result = await api.createOrder({ ...payload, client_order_id: clientOrderId })
      setNotice(`Live order qəbul edildi: ${result.order_id || result.status}`)
      setPreview(null)
      await loadAccount()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Live order göndərilmədi")
    } finally {
      setBusy(false)
    }
  }

  async function handleClosePosition() {
    if (!closeDraft || liveUnavailable) return
    setBusy(true); setError(null)
    try {
      const clientOrderId = `close_${crypto.randomUUID().replaceAll("-", "")}`
      const result = await api.closePosition({
        exchange: closeDraft.position.exchange,
        symbol: closeDraft.position.symbol,
        percentage: closeDraft.percentage,
        client_order_id: clientOrderId,
      })
      setNotice(`${closeDraft.percentage}% reduce-only close qəbul edildi: ${result.order_id || result.status}`)
      setCloseDraft(null)
      await loadAccount()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Mövqe bağlanmadı")
    } finally {
      setBusy(false)
    }
  }

  async function handleCancelOrder(order: LiveOrder) {
    if (!window.confirm(`${order.symbol} ${order.order_type} order-i ləğv edilsin?`)) return
    setBusy(true); setError(null)
    try {
      const result = await api.cancelOrder({ exchange: "binance", symbol: order.symbol, order_id: order.order_id })
      if (!result.success) throw new Error("Exchange order-i ləğv etmədi")
      setNotice("Açıq order ləğv edildi")
      await loadAccount()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Order ləğv edilmədi")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="space-y-3 border-b border-gray-800 p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Store className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-200">{selectedSymbol}</span>
            <Badge variant="info">Isolated</Badge>
          </div>
          <button onClick={loadAccount} className="text-gray-500 hover:text-gray-300" title="Yenilə"><RefreshCw className="h-4 w-4" /></button>
        </div>

        <div className="grid grid-cols-2 rounded-lg bg-gray-900 p-1">
          {(["paper", "live"] as Mode[]).map((item) => (
            <button key={item} disabled={item === "live" && liveUnavailable} onClick={() => setMode(item)}
              className={cn("rounded py-1.5 text-xs font-semibold uppercase", mode === item ? "bg-blue-600 text-white" : "text-gray-500", item === "live" && liveUnavailable && "cursor-not-allowed opacity-40")}>
              {item}
            </button>
          ))}
        </div>
        {mode === "paper" ? (
          <div className="rounded border border-blue-500/20 bg-blue-500/5 p-2 text-[11px] text-blue-300">Real bazar qiyməti · virtual kapital · execution gate aktiv</div>
        ) : null}
        {liveUnavailable && (
          <div className="flex gap-2 rounded border border-amber-500/30 bg-amber-500/5 p-2 text-[11px] text-amber-300">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {!status?.configured_exchanges?.length ? "Live üçün Exchange API bağlantısı tələb olunur." : status?.kill_switch_active ? "Emergency kill-switch aktivdir." : "Serverdə live trading bağlıdır."}
          </div>
        )}

        <div className="grid grid-cols-2 gap-2">
          {(["long", "short"] as Side[]).map((item) => (
            <button key={item} onClick={() => setSide(item)} className={cn("rounded-lg py-2 text-sm font-medium", side === item ? item === "long" ? "bg-green-600 text-white" : "bg-red-600 text-white" : "bg-gray-800 text-gray-400")}>
              {item === "long" ? <ArrowUp className="mr-1 inline h-4 w-4" /> : <ArrowDown className="mr-1 inline h-4 w-4" />}{item.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-1">
          {(["market", "limit"] as const).map((type) => <button key={type} onClick={() => setOrderType(type)} className={cn("rounded py-1.5 text-xs font-medium capitalize", orderType === type ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400")}>{type}</button>)}
        </div>

        <div className="space-y-2">
          <label className="block text-xs text-gray-500">Kapital (USDT) <span className="float-right">Live balans: {balance == null ? "—" : formatPrice(balance)}</span>
            <input type="number" min="0" value={capital} onChange={(e) => setCapital(e.target.value)} className={cn(fieldClass, "mt-1")} />
          </label>
          {orderType === "limit" && <label className="block text-xs text-gray-500">Limit qiyməti<input type="number" min="0" value={limitPrice} onChange={(e) => setLimitPrice(e.target.value)} className={cn(fieldClass, "mt-1")} /></label>}
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs text-gray-500">Stop Loss<input type="number" min="0" value={stopLoss} onChange={(e) => setStopLoss(e.target.value)} className={cn(fieldClass, "mt-1 text-red-400")} /></label>
            <label className="text-xs text-gray-500">Take Profit<input type="number" min="0" value={takeProfit} onChange={(e) => setTakeProfit(e.target.value)} className={cn(fieldClass, "mt-1 text-green-400")} /></label>
          </div>
          <div className="flex flex-wrap gap-1">
            {LEVERAGE_OPTIONS.map((value) => <button key={value} onClick={() => setLeverage(value)} className={cn("rounded px-2 py-1 text-xs", leverage === value ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400")}>{value}x</button>)}
          </div>
          <div className="rounded bg-gray-900 p-2 text-[11px] text-gray-400">
            Real qiymət: <b className="text-white">{entryPrice ? formatPrice(entryPrice) : "gözlənilir"}</b> · Miqdar: <b className="text-white">{quantity ? quantity.toFixed(6) : "—"}</b>
          </div>
        </div>

        {error && <div className="rounded border border-red-500/30 bg-red-500/5 p-2 text-xs text-red-300">{error}</div>}
        {notice && <div className="rounded border border-green-500/30 bg-green-500/5 p-2 text-xs text-green-300">{notice}</div>}

        {mode === "paper" ? (
          <Button variant={side === "long" ? "success" : "danger"} className="w-full" disabled={busy} onClick={handlePaperOrder}>{busy ? "Yoxlanılır..." : `Paper ${side.toUpperCase()} aç`}</Button>
        ) : (
          <Button className="w-full" disabled={busy || liveUnavailable} onClick={handlePreview}>{busy ? "10 yoxlama aparılır..." : "Order preview hazırla"}</Button>
        )}

        {preview && (
          <div className={cn("space-y-2 rounded-lg border p-3 text-xs", preview.approval.approved ? "border-green-500/30 bg-green-500/5" : "border-red-500/30 bg-red-500/5")}>
            <div className="flex items-center justify-between font-semibold"><span className="flex items-center gap-1"><ShieldCheck className="h-4 w-4" /> Execution Gate</span><Badge variant={preview.approval.approved ? "success" : "danger"}>{preview.approval.approved ? "APPROVED" : "REJECTED"}</Badge></div>
            <div className="grid grid-cols-2 gap-1 text-gray-400">
              <span>Giriş <b className="float-right text-white">{formatPrice(preview.entry_price)}</b></span>
              <span>Notional <b className="float-right text-white">{formatPrice(preview.notional)}</b></span>
              <span>Margin <b className="float-right text-white">{formatPrice(preview.required_margin)}</b></span>
              <span>Fee (təx.) <b className="float-right text-white">{formatPrice(preview.estimated_fees)}</b></span>
              <span>Likvidasiya <b className="float-right text-red-300">{preview.liquidation_price ? formatPrice(preview.liquidation_price) : "—"}</b></span>
              <span>Slippage <b className="float-right text-white">{preview.estimated_slippage?.estimated_slippage_pct ?? "—"}%</b></span>
              <span>Maks. risk <b className="float-right text-red-300">{formatPrice(preview.max_loss_at_stop)}</b></span>
              <span>Potensial gəlir <b className="float-right text-green-300">{formatPrice(preview.potential_profit_at_target)}</b></span>
              <span>Risk/Gəlir <b className="float-right text-white">{preview.risk_reward ?? "—"}</b></span>
              <span>Risk score <b className="float-right text-white">{preview.approval.risk_score ?? "—"}</b></span>
            </div>
            {!!preview.approval.rejection_reasons?.length && <ul className="space-y-1 text-red-300">{preview.approval.rejection_reasons.map((reason) => <li key={reason}>• {reason}</li>)}</ul>}
            {!confirming ? (
              <Button variant="danger" className="w-full" disabled={!preview.can_submit_live || busy} onClick={() => setConfirming(true)}>Live order mərhələsinə keç</Button>
            ) : (
              <div className="space-y-2 rounded border border-red-500/40 bg-red-950/30 p-2">
                <p className="font-semibold text-red-200">Bu REAL order-dir və real kapital istifadə edəcək.</p>
                <div className="grid grid-cols-2 gap-2"><Button variant="ghost" onClick={() => setConfirming(false)}>Ləğv et</Button><Button variant="danger" disabled={busy} onClick={handleLiveOrder}>{busy ? "Göndərilir..." : "REAL ORDER-I TƏSDİQLƏ"}</Button></div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="p-3">
        <div className="mb-2 text-xs font-medium text-gray-400">Live mövqelər ({positions.length})</div>
        {!positions.length ? <div className="py-3 text-center text-xs text-gray-600">Açıq live mövqe yoxdur</div> : positions.slice(0, 4).map((position) => (
          <div key={`${position.exchange}-${position.symbol}-${position.side}`} className="mb-2 space-y-2 rounded border border-gray-800 bg-gray-900 p-2 text-xs text-gray-400">
            <div><span className="font-semibold text-white">{position.symbol}</span> · <span className={position.side === "long" ? "text-green-400" : "text-red-400"}>{position.side.toUpperCase()}</span> · {position.leverage}x <span className={cn("float-right", position.unrealized_pnl >= 0 ? "text-green-400" : "text-red-400")}>{formatPrice(position.unrealized_pnl)}</span></div>
            <div className="grid grid-cols-2 gap-1 text-[11px]">
              <span>Ölçü <b className="float-right text-white">{position.size}</b></span>
              <span>Giriş <b className="float-right text-white">{formatPrice(position.entry_price)}</b></span>
              <span>Mark <b className="float-right text-white">{formatPrice(position.mark_price)}</b></span>
              <span>Likvidasiya <b className="float-right text-red-300">{position.liquidation_price ? formatPrice(position.liquidation_price) : "—"}</b></span>
            </div>
            <div className="grid grid-cols-3 gap-1">
              {[25, 50, 100].map((percentage) => <button key={percentage} disabled={busy || liveUnavailable} onClick={() => setCloseDraft({ position, percentage })} className="rounded bg-red-950/40 py-1 text-[11px] text-red-300 hover:bg-red-900/50 disabled:opacity-40">{percentage}% bağla</button>)}
            </div>
          </div>
        ))}

        {closeDraft && (
          <div className="mb-3 space-y-2 rounded border border-red-500/40 bg-red-950/30 p-2 text-xs">
            <div className="flex items-center justify-between"><b className="text-red-200">REAL MÖVQE BAĞLAMA</b><button onClick={() => setCloseDraft(null)}><X className="h-3.5 w-3.5" /></button></div>
            <p className="text-gray-300">{closeDraft.position.symbol} mövqeyinin <b>{closeDraft.percentage}%</b> hissəsi reduce-only market order ilə bağlanacaq.</p>
            <div className="grid grid-cols-2 gap-2"><Button variant="ghost" disabled={busy} onClick={() => setCloseDraft(null)}>Ləğv et</Button><Button variant="danger" disabled={busy || liveUnavailable} onClick={handleClosePosition}>{busy ? "Göndərilir..." : "BAĞLANMANI TƏSDİQLƏ"}</Button></div>
          </div>
        )}

        <div className="mb-2 mt-3 text-xs font-medium text-gray-400">Açıq order-lər ({openOrders.length})</div>
        {!openOrders.length ? <div className="py-2 text-center text-xs text-gray-600">Açıq live order yoxdur</div> : openOrders.slice(0, 6).map((order) => (
          <div key={order.order_id} className="mb-1 flex items-center justify-between rounded bg-gray-900 p-2 text-xs">
            <div><b className="text-white">{order.symbol}</b><div className="text-[10px] text-gray-500">{order.side.toUpperCase()} · {order.order_type} · {order.quantity} @ {order.price ? formatPrice(order.price) : "market"}</div></div>
            <button disabled={busy || liveUnavailable} onClick={() => handleCancelOrder(order)} className="rounded p-1 text-red-400 hover:bg-red-950/50 disabled:opacity-40" title="Order-i ləğv et"><X className="h-4 w-4" /></button>
          </div>
        ))}
      </div>
    </div>
  )
}
