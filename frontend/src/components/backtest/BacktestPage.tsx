"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  BarChart3, Play, History,
} from "lucide-react"

interface BacktestTrade {
  direction: string
  entry: number
  exit: number
  pnl: number
  risk_reward: number
}

interface BacktestResult {
  win_rate: number
  profit_factor: number
  max_drawdown: number
  total_return: number
  total_trades: number
  sharpe_ratio: number
  avg_risk_reward: number
  final_balance: number
  trades: BacktestTrade[]
}

interface BacktestHistoryItem {
  id: number
  symbol: string
  timeframe: string
  total_trades: number
  win_rate: number
  profit_factor: number
  max_drawdown: number
  total_return: number
}

export function BacktestPage() {
  const [symbol, setSymbol] = useState("BTC/USDT")
  const [timeframe, setTimeframe] = useState("1h")
  const [balance, setBalance] = useState(10000)
  const [leverage, setLeverage] = useState(1)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [history, setHistory] = useState<BacktestHistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<"backtest" | "history">("backtest")

  useEffect(() => {
    api.getBacktestHistory().then(setHistory).catch(() => {})
  }, [])

  async function runBacktest() {
    setLoading(true)
    try {
      const res = await api.runBacktest(symbol, timeframe, 500, balance)
      setResult(res)
    } catch {
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto bg-[#0d1117]">
      <div className="max-w-6xl mx-auto p-4 lg:p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white">Backtesting Engine</h1>
              <p className="text-xs text-gray-500">Test strategies against historical market data</p>
            </div>
          </div>
          <div className="flex gap-1 p-0.5 rounded-lg bg-gray-800 border border-gray-700">
            {(["backtest", "history"] as const).map((tab) => (
              <button key={tab} onClick={() => setActiveTab(tab)}
                className={cn(
                  "px-3 py-1.5 text-xs rounded-md transition-colors",
                  activeTab === tab ? "bg-gray-700 text-white" : "text-gray-400 hover:text-gray-200"
                )}>
                {tab === "backtest" ? "Run Backtest" : "History"}
              </button>
            ))}
          </div>
        </div>

        {activeTab === "backtest" && (
          <>
            {/* Controls */}
            <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                <div>
                  <label className="text-[10px] text-gray-500 uppercase tracking-wider mb-1 block">Symbol</label>
                  <select value={symbol} onChange={(e) => setSymbol(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-blue-500">
                    {["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"].map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-gray-500 uppercase tracking-wider mb-1 block">Timeframe</label>
                  <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-blue-500">
                    {[{ id: "5m", label: "5m" }, { id: "15m", label: "15m" }, { id: "1h", label: "1H" }, { id: "4h", label: "4H" }, { id: "1d", label: "1D" }].map((tf) => (
                      <option key={tf.id} value={tf.id}>{tf.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-gray-500 uppercase tracking-wider mb-1 block">Initial Balance</label>
                  <input type="number" value={balance} onChange={(e) => setBalance(Number(e.target.value))}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="text-[10px] text-gray-500 uppercase tracking-wider mb-1 block">Leverage</label>
                  <select value={leverage} onChange={(e) => setLeverage(Number(e.target.value))}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-blue-500">
                    {[1, 2, 3, 5, 10, 20, 50, 100].map((l) => (
                      <option key={l} value={l}>{l}x</option>
                    ))}
                  </select>
                </div>
                <div className="flex items-end">
                  <button onClick={runBacktest} disabled={loading}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50">
                    <Play className="w-3.5 h-3.5" />
                    {loading ? "Running..." : "Run Backtest"}
                  </button>
                </div>
              </div>
            </div>

            {/* Results */}
            {result && (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
                    <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Win Rate</div>
                    <div className={cn("text-lg font-bold font-mono", (result.win_rate || 0) >= 50 ? "text-green-400" : "text-red-400")}>
                      {(result.win_rate || 0).toFixed(1)}%
                    </div>
                  </div>
                  <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
                    <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Profit Factor</div>
                    <div className={cn("text-lg font-bold font-mono", (result.profit_factor || 0) >= 1.5 ? "text-green-400" : (result.profit_factor || 0) >= 1 ? "text-yellow-400" : "text-red-400")}>
                      {result.profit_factor?.toFixed(2) || "0.00"}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
                    <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Max Drawdown</div>
                    <div className="text-lg font-bold text-red-400 font-mono">
                      {(result.max_drawdown || 0).toFixed(1)}%
                    </div>
                  </div>
                  <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
                    <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Total Return</div>
                    <div className={cn("text-lg font-bold font-mono", (result.total_return || 0) >= 0 ? "text-green-400" : "text-red-400")}>
                      {result.total_return ? `${result.total_return >= 0 ? "+" : ""}${result.total_return.toFixed(2)}%` : "0.00%"}
                    </div>
                  </div>
                </div>

                {/* Detailed Results */}
                <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
                  <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3">Performance Metrics</h2>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    {[
                      { label: "Total Trades", value: result.total_trades || 0 },
                      { label: "Sharpe Ratio", value: result.sharpe_ratio?.toFixed(2) || "0.00" },
                      { label: "Avg Risk/Reward", value: result.avg_risk_reward ? `1:${result.avg_risk_reward.toFixed(1)}` : "--" },
                      { label: "Final Balance", value: result.final_balance ? `$${result.final_balance.toFixed(0)}` : "--" },
                    ].map((m) => (
                      <div key={m.label} className="p-3 rounded-lg bg-gray-800/30">
                        <div className="text-[10px] text-gray-500">{m.label}</div>
                        <div className="text-sm font-bold text-white font-mono mt-0.5">{m.value}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Trades Table */}
                {result.trades && result.trades.length > 0 && (
                  <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
                    <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3">Trades</h2>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-800">
                            <th className="text-left py-2 pr-2">#</th>
                            <th className="text-center py-2 pr-2">Direction</th>
                            <th className="text-right py-2 pr-2">Entry</th>
                            <th className="text-right py-2 pr-2">Exit</th>
                            <th className="text-right py-2 pr-2">PnL</th>
                            <th className="text-right py-2">RR</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.trades.slice(0, 20).map((t: BacktestTrade, i: number) => (
                            <tr key={i} className="border-b border-gray-800/50 text-gray-400">
                              <td className="py-1.5 pr-2 text-gray-600">{i + 1}</td>
                              <td className="py-1.5 pr-2 text-center">
                                <span className={cn("text-[9px] font-bold", t.direction === "long" ? "text-green-400" : "text-red-400")}>
                                  {t.direction?.toUpperCase() || "N/A"}
                                </span>
                              </td>
                              <td className="py-1.5 pr-2 text-right font-mono">${t.entry?.toFixed(2) || 0}</td>
                              <td className="py-1.5 pr-2 text-right font-mono">${t.exit?.toFixed(2) || 0}</td>
                              <td className={cn("py-1.5 pr-2 text-right font-mono", (t.pnl || 0) >= 0 ? "text-green-400" : "text-red-400")}>
                                {t.pnl ? `${t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}%` : "0.00%"}
                              </td>
                              <td className="py-1.5 text-right font-mono">{t.risk_reward?.toFixed(1) || "--"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            )}

            {!result && !loading && (
              <div className="text-center py-16 text-gray-600">
                <BarChart3 className="w-12 h-12 mx-auto mb-3 text-gray-700" />
                <div className="text-sm">Configure parameters and click <span className="text-blue-400">Run Backtest</span></div>
                <p className="text-xs text-gray-600 mt-1">Test your strategy on 500 candles of historical data</p>
              </div>
            )}
          </>
        )}

        {activeTab === "history" && (
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/40">
            <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3">Backtest History</h2>
            {history.length === 0 ? (
              <div className="text-center py-8 text-gray-600">
                <History className="w-8 h-8 mx-auto mb-2" />
                <div className="text-xs">No backtest history yet</div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-800">
                      <th className="text-left py-2 pr-2">Symbol</th>
                      <th className="text-center py-2 pr-2">TF</th>
                      <th className="text-center py-2 pr-2">Trades</th>
                      <th className="text-center py-2 pr-2">Win Rate</th>
                      <th className="text-center py-2 pr-2">Profit Factor</th>
                      <th className="text-center py-2 pr-2">Max DD</th>
                      <th className="text-right py-2">Return</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((h: BacktestHistoryItem) => (
                      <tr key={h.id} className="border-b border-gray-800/50 text-gray-400 hover:bg-gray-800/20">
                        <td className="py-2 pr-2 font-medium text-white font-mono">{h.symbol}</td>
                        <td className="py-2 pr-2 text-center">{h.timeframe}</td>
                        <td className="py-2 pr-2 text-center">{h.total_trades}</td>
                        <td className="py-2 pr-2 text-center font-mono">{(h.win_rate || 0).toFixed(1)}%</td>
                        <td className="py-2 pr-2 text-center font-mono">{h.profit_factor?.toFixed(2) || "0.00"}</td>
                        <td className="py-2 pr-2 text-center font-mono text-red-400">{(h.max_drawdown || 0).toFixed(1)}%</td>
                        <td className={cn("py-2 text-right font-mono", (h.total_return || 0) >= 0 ? "text-green-400" : "text-red-400")}>
                          {h.total_return ? `${h.total_return >= 0 ? "+" : ""}${h.total_return.toFixed(2)}%` : "0.00%"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
