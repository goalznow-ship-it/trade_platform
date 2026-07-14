const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`
  if (options?.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json"
  }

  const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || "Request failed")
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

  // Market
  getOHLCV: (symbol: string, timeframe = "1h", limit = 200) =>
    request<any[]>(`/api/v1/market/ohlcv/${symbol}?timeframe=${timeframe}&limit=${limit}`),

  getTicker: (symbol: string) =>
    request<any>(`/api/v1/market/ticker/${symbol}`),

  getOverview: () => request<any>("/api/v1/market/overview"),

  getFearGreed: () => request<any>("/api/v1/market/fear-greed"),

  searchSymbols: (q: string) => request<any[]>(`/api/v1/market/search?q=${q}`),

  getSymbols: () => request<any[]>("/api/v1/market/symbols"),

  // Analysis
  getIndicators: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/analysis/indicators/${symbol}?timeframe=${timeframe}`),

  getAIAnalysis: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/analysis/ai/${symbol}?timeframe=${timeframe}`),

  getFullAnalysis: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/analysis/full/${symbol}?timeframe=${timeframe}`),

  // Signals
  getSignals: (symbol: string, timeframe = "1h") =>
    request<any>(`/api/v1/signals/${symbol}?timeframe=${timeframe}`),

  scanAll: (timeframe = "1h", minConfidence = 70) =>
    request<any[]>(`/api/v1/scanner/top-signals?min_confidence=${minConfidence}`),

  // Trading
  createOrder: (data: any) =>
    request<any>("/api/v1/trade/order", { method: "POST", body: JSON.stringify(data) }),

  getPositions: () => request<any[]>("/api/v1/trade/positions"),

  getBalance: () => request<any>("/api/v1/trade/balance"),

  saveAPIKeys: (data: { exchange: string; api_key: string; secret_key: string }) =>
    request("/api/v1/trade/api-keys", { method: "POST", body: JSON.stringify(data) }),

  // Portfolio
  getPortfolio: () => request<any>("/api/v1/portfolio/summary"),

  // Backtest
  runBacktest: (symbol: string, timeframe = "1h", limit = 500, initialBalance = 10000) =>
    request<any>(`/api/v1/backtest/run?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}&initial_balance=${initialBalance}`),

  // News
  getNews: () => request<any[]>("/api/v1/news/latest"),

  // Admin
  getAdminStats: () => request<any>("/api/v1/admin/stats"),
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
}
