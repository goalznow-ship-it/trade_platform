"use client"

import { useState } from "react"
import { useMarketStore } from "@/store/market"
import { useAuth } from "@/hooks/useAuth"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { cn, formatPrice } from "@/lib/utils"
import { ArrowUp, ArrowDown, Settings2, Store } from "lucide-react"

const ORDER_TYPES = ["Market", "Limit", "Stop", "Stop Limit"]
const LEVERAGE_OPTIONS = [1, 2, 3, 5, 10, 20, 50, 100]

export function TradingPanel() {
  const { selectedSymbol } = useMarketStore()
  const { user } = useAuth()
  const [side, setSide] = useState<"long" | "short">("long")
  const [orderType, setOrderType] = useState("Market")
  const [leverage, setLeverage] = useState(3)
  const [amount, setAmount] = useState("100")
  const [stopLoss, setStopLoss] = useState("")
  const [takeProfit, setTakeProfit] = useState("")
  const [showLeverage, setShowLeverage] = useState(false)

  const isLong = side === "long"

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Store className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-200">{selectedSymbol}</span>
            <Badge variant="info">Isolated</Badge>
          </div>
          <button className="text-gray-500 hover:text-gray-300">
            <Settings2 className="w-4 h-4" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-3">
          <button
            onClick={() => setSide("long")}
            className={cn(
              "py-2 rounded-lg font-medium text-sm transition-all",
              isLong
                ? "bg-green-600 text-white shadow-lg shadow-green-600/20"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            )}
          >
            <ArrowUp className="w-4 h-4 inline mr-1" />
            Long
          </button>
          <button
            onClick={() => setSide("short")}
            className={cn(
              "py-2 rounded-lg font-medium text-sm transition-all",
              !isLong
                ? "bg-red-600 text-white shadow-lg shadow-red-600/20"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            )}
          >
            <ArrowDown className="w-4 h-4 inline mr-1" />
            Short
          </button>
        </div>

        <div className="flex gap-1 mb-3">
          {ORDER_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => setOrderType(type)}
              className={cn(
                "flex-1 py-1.5 text-xs rounded font-medium transition-colors",
                orderType === type
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              )}
            >
              {type}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Leverage</span>
              <button
                onClick={() => setShowLeverage(!showLeverage)}
                className="text-blue-400 hover:text-blue-300"
              >
                {leverage}x
              </button>
            </div>
            {showLeverage && (
              <div className="flex flex-wrap gap-1 mb-2">
                {LEVERAGE_OPTIONS.map((lev) => (
                  <button
                    key={lev}
                    onClick={() => { setLeverage(lev); setShowLeverage(false) }}
                    className={cn(
                      "px-2 py-1 text-xs rounded",
                      leverage === lev
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                    )}
                  >
                    {lev}x
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Amount (USDT)</span>
              <span className="text-gray-600">Balance: {user?.balance ? formatPrice(user.balance, 0) : "---"}</span>
            </div>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <div className="text-xs text-gray-500 mb-1">Stop Loss</div>
              <input
                type="number"
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
                placeholder="--"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-red-400 font-mono focus:outline-none focus:border-red-500"
              />
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">Take Profit</div>
              <input
                type="number"
                value={takeProfit}
                onChange={(e) => setTakeProfit(e.target.value)}
                placeholder="--"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-green-400 font-mono focus:outline-none focus:border-green-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-1">
            {["25%", "50%", "75%", "100%"].map((pct) => (
              <button
                key={pct}
                className="px-2 py-1 text-xs bg-gray-800 text-gray-400 rounded hover:bg-gray-700"
              >
                {pct}
              </button>
            ))}
          </div>

          <Button
            variant={isLong ? "success" : "danger"}
            className="w-full py-3"
          >
            {isLong ? "Buy / Long" : "Sell / Short"} {selectedSymbol}
          </Button>

          <div className="text-xs text-gray-500 space-y-1">
            <div className="flex justify-between">
              <span>Entry Price</span>
              <span className="text-gray-300 font-mono">--</span>
            </div>
            <div className="flex justify-between">
              <span>Liquidation</span>
              <span className="text-red-400 font-mono">--</span>
            </div>
            <div className="flex justify-between">
              <span>Margin</span>
              <span className="text-gray-300 font-mono">{amount ? formatPrice(parseFloat(amount) / leverage, 0) : "--"}</span>
            </div>
            <div className="flex justify-between">
              <span>Fee</span>
              <span className="text-gray-300 font-mono">{amount ? formatPrice(parseFloat(amount) * 0.0004, 0) : "--"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Open Positions Summary */}
      <div className="p-3 border-t border-gray-800">
        <div className="text-xs font-medium text-gray-400 mb-2">Open Positions</div>
        <div className="text-center py-4 text-gray-600 text-xs">No open positions</div>
      </div>
    </div>
  )
}
