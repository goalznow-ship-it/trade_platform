export interface User {
  id: number
  username: string
  email: string
  is_admin: boolean
  is_active?: boolean
  balance?: number
  total_pnl?: number
  win_rate?: number
  created_at?: string
}

export interface Watchlist {
  id: number
  name: string
  user_id: number
  symbol_count: number
  symbols: WatchlistSymbol[]
  created_at: string
}

export interface WatchlistSymbol {
  id: number
  symbol: string
  exchange?: string
  order_index: number
}

export interface Alert {
  id: number
  name: string
  alert_type: string
  symbol: string
  condition: string
  value: number
  is_active: boolean
  channels: string[]
  created_at: string
}

export interface RiskProfile {
  max_daily_loss: number
  max_leverage: number
  max_open_positions: number
  risk_per_trade: number
  max_drawdown: number
  max_position_size: number
}

export interface RiskDashboard {
  profile: RiskProfile
  current: {
    sharpe_ratio: number
    sortino_ratio: number
    profit_factor: number
    kelly_percentage: number
    value_at_risk: number
    win_rate: number
    current_daily_loss: number
    current_drawdown: number
    open_positions: number
    current_exposure: number
  }
}

export interface JournalEntry {
  id: number
  symbol: string
  side: string
  notes?: string
  emotion?: string
  rating?: string
  mistakes?: string
  lessons?: string
  created_at: string
}

export interface PaperAccount {
  id: number
  balance: number
  initial_balance: number
  total_pnl: number
  win_rate: number
  total_trades: number
}

export interface PaperPosition {
  id: number
  symbol: string
  side: string
  quantity: number
  entry_price: number
  leverage: number
  pnl: number
  created_at: string
}

export interface Notification {
  id: number
  title: string
  message?: string
  type: string
  is_read: boolean
  created_at: string
}

export interface PortfolioAnalytics {
  win_rate: number
  profit_factor: number
  total_trades: number
  best_trade: number
  worst_trade: number
  winning_trades: number
  losing_trades: number
  avg_holding_time: string
  monthly_breakdown: Array<{ month: string; pnl: number }>
}

export interface BacktestResult {
  id: number
  symbol: string
  timeframe: string
  total_return: number
  final_balance: number
  total_trades: number
  win_rate: number
  sharpe_ratio: number
  created_at: string
}

export interface OHLCV {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}
