/* eslint-disable @typescript-eslint/no-explicit-any */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem("refresh_token")
  if (!refreshToken) return null
  const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!res.ok) return null
  const data = await res.json()
  localStorage.setItem("token", data.access_token)
  localStorage.setItem("refresh_token", data.refresh_token)
  return data.access_token
}

async function request<T>(endpoint: string, options?: RequestInit, retried = false): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`
  if (options?.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json"
  }

  const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers })
  if (res.status === 401 && typeof window !== "undefined" && !retried && endpoint !== "/api/v1/auth/refresh") {
    refreshPromise ??= refreshAccessToken().finally(() => { refreshPromise = null })
    const accessToken = await refreshPromise
    if (accessToken) return request<T>(endpoint, options, true)
  }
  if (res.status === 401 && typeof window !== "undefined") {
    localStorage.removeItem("token")
    localStorage.removeItem("refresh_token")
    if (!window.location.pathname.startsWith("/login")) window.location.assign("/login")
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const detail = err.detail
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item?.msg || "Invalid input").join(", ")
        : res.statusText || "Request failed"
    throw new Error(message)
  }
  return res.json()
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    request<{ access_token: string; refresh_token: string; user: any }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  register: (data: { username: string; email: string; password: string }) =>
    request("/api/v1/auth/register", { method: "POST", body: JSON.stringify(data) }),

  me: () => request<any>("/api/v1/auth/me"),

  logout: (accessToken: string | null, refreshToken: string | null) =>
    request<void>("/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ access_token: accessToken, refresh_token: refreshToken }),
    }),

  // Market
  getOHLCV: (symbol: string, timeframe = "1h", limit = 200) =>
    request<any[]>(`/api/v1/market/ohlcv/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`),

  getTicker: (symbol: string) =>
    request<any>(`/api/v1/market/ticker/${encodeURIComponent(symbol)}`),

  getOverview: () => request<any>("/api/v1/market/overview"),

  getFearGreed: () => request<any>("/api/v1/market/fear-greed"),

  searchSymbols: (q: string) => request<any[]>(`/api/v1/market/search?q=${encodeURIComponent(q)}`),

  getSymbols: () => request<any[]>("/api/v1/market/symbols"),

  // Analysis
  getIndicators: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/analysis/indicators/${symbol}?timeframe=${timeframe}`),

  getAIAnalysis: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/analysis/ai/${symbol}?timeframe=${timeframe}`),

  getPatternAnalysis: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/institutional/ai-analysis/${encodeURIComponent(symbol.replace("/", "-"))}?timeframe=${encodeURIComponent(timeframe)}`),

  getFullAnalysis: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/analysis/full/${symbol}?timeframe=${timeframe}`),

  // Signals
  getSignals: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/signals/${symbol}?timeframe=${timeframe}`),

  scanAll: (minConfidence = 70) =>
    request<any[]>(`/api/v1/scanner/top-signals?min_confidence=${minConfidence}`),

  getScannerFilters: () =>
    Promise.resolve([
      "rsi_oversold", "rsi_overbought", "volume_spike", "breakout",
      "breakdown", "ema_bullish", "ema_bearish",
      "golden_cross", "death_cross", "high_volatility",
      "strong_trend", "liquidity_grab", "macd_bullish", "macd_bearish",
      "supertrend_bullish", "supertrend_bearish",
    ]),

  scanWithFilters: () =>
    api.institutionalScan(0, 30) as Promise<{ signals?: Record<string, unknown>[] }>,

  // Trading
  createOrder: (data: any) =>
    request<any>("/api/v1/trade/order", { method: "POST", body: JSON.stringify(data) }),

  getPositions: () => request<any[]>("/api/v1/trade/positions"),
  reconcileOrders: (exchange = "binance") =>
    request<any>(`/api/v1/trade/orders/reconcile?exchange=${encodeURIComponent(exchange)}`, {
      method: "POST",
    }),

  getBalance: () => request<any>("/api/v1/trade/balance"),

  saveAPIKeys: (data: { exchange: string; api_key: string; secret_key: string }) =>
    request("/api/v1/trade/api-keys", { method: "POST", body: JSON.stringify(data) }),

  getTradeHistory: (params?: { skip?: number; limit?: number; symbol?: string }) => {
    const q = new URLSearchParams()
    if (params?.skip) q.set("offset", String(params.skip))
    if (params?.limit) q.set("limit", String(params.limit))
    if (params?.symbol) q.set("symbol", params.symbol)
    return request<any[]>("/api/v1/trade/history?" + q.toString())
  },

  deleteTrade: (id: number) => request(`/api/v1/trade/history/${id}`, { method: "DELETE" }),

  exportTradeHistory: () => {
    const token = localStorage.getItem("token")
    const url = `${API_URL}/api/v1/trade/history/export/csv`
    return fetch(url, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.blob())
  },

  // Portfolio
  getPortfolio: () => request<any>("/api/v1/portfolio/summary"),

  getPortfolioAnalytics: () => request<any>("/api/v1/portfolio/analytics"),

  getDailyPnL: () => request<any[]>("/api/v1/portfolio/daily-pnl"),

  // Backtest
  runBacktest: (symbol: string, timeframe = "1h", limit = 500, initialBalance = 10000, leverage = 1) =>
    request<any>(
      `/api/v1/backtest/run?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`
      + `&limit=${limit}&initial_balance=${initialBalance}&leverage=${leverage}`,
    ),

  saveBacktest: (data: any) =>
    request("/api/v1/backtest/save", { method: "POST", body: JSON.stringify(data) }),

  getBacktestHistory: () => request<any[]>("/api/v1/backtest/history"),

  deleteBacktest: (id: number) => request(`/api/v1/backtest/history/${id}`, { method: "DELETE" }),

  // News
  getNews: () => request<any[]>("/api/v1/news/latest"),

  getNewsIntelligence: (symbol?: string) => {
    const q = symbol ? `?symbol=${symbol}` : ""
    return request<any>("/api/v1/enterprise/news-intelligence" + q)
  },

  // Watchlist
  getWatchlists: () => request<any[]>("/api/v1/watchlists"),

  createWatchlist: (name: string) =>
    request("/api/v1/watchlists", { method: "POST", body: JSON.stringify({ name }) }),

  deleteWatchlist: (id: number) =>
    request(`/api/v1/watchlists/${id}`, { method: "DELETE" }),

  addWatchlistSymbol: (watchlistId: number, symbol: string) =>
    request(`/api/v1/watchlists/${watchlistId}/symbols`, {
      method: "POST", body: JSON.stringify({ symbol }),
    }),

  removeWatchlistSymbol: (watchlistId: number, symbol: string) =>
    request(`/api/v1/watchlists/${watchlistId}/symbols/${encodeURIComponent(symbol)}`, { method: "DELETE" }),

  reorderWatchlistSymbols: (watchlistId: number, symbols: string[]) =>
    request(`/api/v1/watchlists/${watchlistId}/symbols/reorder`, {
      method: "PUT", body: JSON.stringify({ symbols }),
    }),

  // Alerts
  getAlerts: () => request<any[]>("/api/v1/alerts"),

  createAlert: (data: any) =>
    request("/api/v1/alerts", { method: "POST", body: JSON.stringify(data) }),

  updateAlert: (id: number, data: any) =>
    request(`/api/v1/alerts/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  deleteAlert: (id: number) => request(`/api/v1/alerts/${id}`, { method: "DELETE" }),

  // Risk Management
  getRiskDashboard: () => request<any>("/api/v1/risk/dashboard"),

  getRiskProfile: () => request<any>("/api/v1/risk/profile"),

  updateRiskProfile: (data: any) =>
    request("/api/v1/risk/profile", { method: "PUT", body: JSON.stringify(data) }),

  // Trading Journal
  getJournal: (page = 1, perPage = 20) =>
    request<any>(`/api/v1/journal?page=${page}&per_page=${perPage}`),

  createJournalEntry: (data: any) =>
    request("/api/v1/journal", { method: "POST", body: JSON.stringify(data) }),

  updateJournalEntry: (id: number, data: any) =>
    request(`/api/v1/journal/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  deleteJournalEntry: (id: number) => request(`/api/v1/journal/${id}`, { method: "DELETE" }),

  // Paper Trading
  getPaperAccount: () => request<any>("/api/v1/paper/account"),

  getPaperPositions: () => request<any[]>("/api/v1/paper/positions"),

  getPaperOrders: () => request<any[]>("/api/v1/paper/orders"),

  createPaperOrder: (data: any) =>
    request("/api/v1/paper/orders", { method: "POST", body: JSON.stringify(data) }),

  closePaperPosition: (id: number) =>
    request(`/api/v1/paper/positions/${id}/close`, { method: "POST" }),

  resetPaperAccount: () =>
    request("/api/v1/paper/account/reset", { method: "POST" }),

  getAIExplainability: () =>
    Promise.resolve(null),

  // Notifications
  getNotifications: () => request<any[]>("/api/v1/notifications"),

  markNotificationRead: (id: number) =>
    request(`/api/v1/notifications/${id}/read`, { method: "POST" }),

  markAllNotificationsRead: () =>
    request("/api/v1/notifications/read-all", { method: "POST" }),

  archiveNotification: (id: number) =>
    request(`/api/v1/notifications/${id}`, { method: "DELETE" }),

  // AI Signals v2
  generateSignal: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/signals/generate/${symbol}?timeframe=${timeframe}`),

  scanAllV2: (minConfidence = 50) =>
    request<any>(`/api/v1/signals/scan?min_confidence=${minConfidence}`),

  // Performance
  getPerformanceStats: (days = 30) =>
    request<any>(`/api/v1/performance/stats?days=${days}`),

  getPerformanceAccuracy: (days = 90) =>
    request<any[]>(`/api/v1/performance/accuracy?days=${days}`),

  // Whales
  getRecentWhales: (limit = 10) =>
    request<any[]>(`/api/v1/whales/recent?limit=${limit}`),

  getWhaleAlerts: (hours = 24) =>
    request<any[]>(`/api/v1/whales/alerts?hours=${hours}`),

  // Admin
  getAdminStats: () => request<any>("/api/v1/admin/stats"),
  getAdminHealth: () => request<any>("/api/v1/admin/health"),
  getTradingControl: () => request<any>("/api/v1/admin/trading/control"),
  getProviderHealth: () => request<any>("/api/v1/admin/providers/health"),
  setTradingControl: (halted: boolean, reason: string) =>
    request<any>("/api/v1/admin/trading/control", {
      method: "PUT", body: JSON.stringify({ halted, reason }),
    }),
  getAdminUsers: () => request<any[]>("/api/v1/admin/users"),
  updateUser: (id: number, data: any) =>
    request(`/api/v1/admin/users/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteUser: (id: number) =>
    request(`/api/v1/admin/users/${id}`, { method: "DELETE" }),
  getAdminSymbols: () => request<any[]>("/api/v1/admin/symbols"),
  addSymbol: (data: any) =>
    request("/api/v1/admin/symbols", { method: "POST", body: JSON.stringify(data) }),
  deleteSymbol: (id: number) =>
    request(`/api/v1/admin/symbols/${id}`, { method: "DELETE" }),
  getAdminSignals: () => request<any[]>("/api/v1/admin/signals"),
  deleteSignal: (id: number) =>
    request(`/api/v1/admin/signals/${id}`, { method: "DELETE" }),
  getLogs: () => request<any[]>("/api/v1/admin/logs"),

  // WebSocket Stats
  getWsStats: () => request<any>("/ws/stats"),

  // Admin AI Brain
  getBrainStatus: () => request<any>("/api/v1/admin/brain/status"),
  getBrainEngines: () => request<any>("/api/v1/admin/brain/engines"),
  getBrainAssessment: (symbol = "BTCUSDT") => request<any>(`/api/v1/admin/brain/assessment?symbol=${symbol}`),
  getBrainSelfLearning: () => request<any>("/api/v1/admin/brain/self-learning"),
  getBrainSystem: () => request<any>("/api/v1/admin/brain/system"),

  // Institutional
  getInstitutionalSignal: (symbol: string, timeframe = "1h", capital = 10000, riskPercent = 0.02) =>
    request<any>(`/api/v1/institutional/signal/${encodeURIComponent(symbol.replace("/", "-"))}?timeframe=${encodeURIComponent(timeframe)}&capital=${capital}&risk_percent=${riskPercent}`),

  institutionalScan: (minScore = 70, limit = 10) =>
    request<any>(`/api/v1/institutional/scan?min_score=${minScore}&limit=${limit}`),

  getMultiTimeframe: (symbol: string) =>
    request<any>(`/api/v1/institutional/multi-timeframe/${symbol}`),

  getSMC: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/institutional/smc/${symbol}?timeframe=${timeframe}`),

  getInstitutionalScore: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/institutional/score/${symbol}?timeframe=${timeframe}`),

  calculatePositionSize: (entryPrice: number, stopLoss: number, capital = 10000, riskPercent = 0.02, leverage?: number) => {
    let q = `entry_price=${entryPrice}&stop_loss=${stopLoss}&capital=${capital}&risk_percent=${riskPercent}`
    if (leverage) q += `&leverage=${leverage}`
    return request<any>(`/api/v1/institutional/risk/position-size?${q}`)
  },

  calculateKelly: (winRate: number, avgWin: number, avgLoss: number) =>
    request<any>(`/api/v1/institutional/risk/kelly?win_rate=${winRate}&avg_win=${avgWin}&avg_loss=${avgLoss}`),

  validateTrade: (symbol: string, direction: string, entryPrice: number, stopLoss: number, takeProfit: number, leverage = 1, balance = 10000) =>
    request<any>(`/api/v1/institutional/risk/validate?symbol=${symbol}&direction=${direction}&entry_price=${entryPrice}&stop_loss=${stopLoss}&take_profit=${takeProfit}&leverage=${leverage}&balance=${balance}`),

  getTopMarkets: (count = 30) =>
    request<any>(`/api/v1/institutional/market/top?count=${count}`),

  getMarketGainers: (count = 10) =>
    request<any>(`/api/v1/institutional/market/gainers?count=${count}`),

  getMarketLosers: (count = 10) =>
    request<any>(`/api/v1/institutional/market/losers?count=${count}`),

  getVolumeLeaders: (count = 10) =>
    request<any>(`/api/v1/institutional/market/volume-leaders?count=${count}`),

  getFundingRates: (count = 20) =>
    request<any>(`/api/v1/institutional/market/funding?count=${count}`),

  getOpenInterest: (count = 20) =>
    request<any>(`/api/v1/institutional/market/open-interest?count=${count}`),

  getTrendingCoins: (count = 10) =>
    request<any>(`/api/v1/institutional/market/trending?count=${count}`),

  getMarketMatrix: (count = 30) =>
    request<any>(`/api/v1/institutional/market/matrix?count=${count}`),

}
