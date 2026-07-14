import { create } from "zustand"

export interface TickerData {
  price: number
  change: number
  high_24h?: number
  low_24h?: number
  volume_24h?: number
}

export interface OrderFlowSnapshot {
  imbalance: number
  bid_pressure: number
  ask_pressure: number
  cumulative_volume_delta: number
  large_orders: number
  liquidity_vacuum: boolean
  spoofing_detected: boolean
  iceberg_detected: boolean
  spread: number
  market_mood: string
}

export interface DerivativesSnapshot {
  funding_rate: number
  funding_trend: string
  funding_pressure: string
  open_interest: number
  oi_change_24h: number
  oi_trend: string
  long_short_ratio: number
  long_ratio: number
  short_ratio: number
  liquidation_risk: string
  basis: number
  basis_annualized: number | null
  contango: boolean
  large_liquidation_zones: number
}

export interface NewsArticle {
  id: string
  title: string
  source: string
  url: string
  sentiment: "bullish" | "bearish" | "neutral"
  impact_score: number
  confidence: number
  affected_coins: string[]
  category: string
  published_at: string
}

export interface SentimentSnapshot {
  overall_score: number
  classification: string
  twitter_score: number
  reddit_score: number
  telegram_score: number
  github_score: number
  fear_level: number
  fomo_level: number
  panic_level: number
  trending_narratives: string[]
}

export interface OnChainSnapshot {
  exchange_inflow: number
  exchange_outflow: number
  net_flow: number
  whale_transfers_24h: number
  whale_accumulation: string
  stablecoin_reserves: number
  exchange_reserves: number
  dormant_supply_1y: number
  miner_selling_pressure: string
  large_transfers_24h: number
}

export interface MacroSnapshot {
  dxy: number
  nasdaq: number
  sp500: number
  gold: number
  oil: number
  us10y: number
  vix: number
  market_env: string
  crypto_impact: string
  crypto_impact_score: number
  next_fomc_days: number | null
}

export interface BrainAssessment {
  overall_market_score: number
  bull_probability: number
  bear_probability: number
  crash_probability: number
  short_squeeze_probability: number
  long_squeeze_probability: number
  alt_season_probability: number
  confidence: number
  regime: string
  contributing_factors: string[]
  timestamp: string
}

export interface MarketState {
  selectedSymbol: string
  selectedTimeframe: string
  tickers: Record<string, TickerData>
  orderFlow: Record<string, OrderFlowSnapshot>
  derivatives: Record<string, DerivativesSnapshot>
  news: NewsArticle[]
  sentiment: Record<string, SentimentSnapshot>
  onchain: Record<string, OnChainSnapshot>
  macro: MacroSnapshot | null
  brain: Record<string, BrainAssessment>
  fearGreed: { value: number; classification: string } | null
  breadth: { advancing: number; declining: number; unchanged: number; breadth_ratio: number; total_symbols: number } | null
  lastUpdate: number | null
  isLive: boolean
  lastPerChannel: Record<string, number>
  setSymbol: (symbol: string) => void
  setTimeframe: (timeframe: string) => void
  updateTicker: (symbol: string, data: Partial<TickerData>) => void
  updateOrderFlow: (symbol: string, data: OrderFlowSnapshot) => void
  updateDerivatives: (symbol: string, data: DerivativesSnapshot) => void
  addNews: (article: NewsArticle) => void
  updateSentiment: (symbol: string, data: SentimentSnapshot) => void
  updateOnchain: (symbol: string, data: OnChainSnapshot) => void
  updateMacro: (data: MacroSnapshot) => void
  updateBrain: (symbol: string, data: BrainAssessment) => void
  updateFearGreed: (data: { value: number; classification: string }) => void
  updateBreadth: (data: { advancing: number; declining: number; unchanged: number; breadth_ratio: number; total_symbols: number }) => void
  setLive: (live: boolean) => void
  touchChannel: (channel: string) => void
}

const MAX_NEWS = 100

export const useMarketStore = create<MarketState>((set) => ({
  selectedSymbol: "BTC/USDT",
  selectedTimeframe: "1h",
  tickers: {},
  orderFlow: {},
  derivatives: {},
  news: [],
  sentiment: {},
  onchain: {},
  macro: null,
  brain: {},
  fearGreed: null,
  breadth: null,
  lastUpdate: null,
  isLive: false,
  lastPerChannel: {},
  setSymbol: (symbol) => set({ selectedSymbol: symbol }),
  setTimeframe: (timeframe) => set({ selectedTimeframe: timeframe }),
  updateTicker: (symbol, data) =>
    set((state) => ({
      tickers: { ...state.tickers, [symbol]: { ...state.tickers[symbol], ...data as TickerData } },
      lastUpdate: Date.now(),
      lastPerChannel: { ...state.lastPerChannel, ticker: Date.now() },
    })),
  updateOrderFlow: (symbol, data) =>
    set((state) => ({
      orderFlow: { ...state.orderFlow, [symbol]: data },
      lastUpdate: Date.now(),
      lastPerChannel: { ...state.lastPerChannel, orderflow: Date.now() },
    })),
  updateDerivatives: (symbol, data) =>
    set((state) => ({
      derivatives: { ...state.derivatives, [symbol]: data },
      lastUpdate: Date.now(),
      lastPerChannel: { ...state.lastPerChannel, derivatives: Date.now() },
    })),
  addNews: (article) =>
    set((state) => ({
      news: [article, ...state.news].slice(0, MAX_NEWS),
      lastUpdate: Date.now(),
      lastPerChannel: { ...state.lastPerChannel, news: Date.now() },
    })),
  updateSentiment: (symbol, data) =>
    set((state) => ({
      sentiment: { ...state.sentiment, [symbol]: data },
      lastUpdate: Date.now(),
      lastPerChannel: { ...state.lastPerChannel, sentiment: Date.now() },
    })),
  updateOnchain: (symbol, data) =>
    set((state) => ({
      onchain: { ...state.onchain, [symbol]: data },
      lastUpdate: Date.now(),
      lastPerChannel: { ...state.lastPerChannel, onchain: Date.now() },
    })),
  updateMacro: (data) =>
    set(() => ({
      macro: data,
      lastUpdate: Date.now(),
      lastPerChannel: { ["macro"]: Date.now() },
    })),
  updateBrain: (symbol, data) =>
    set((state) => ({
      brain: { ...state.brain, [symbol]: data },
      lastUpdate: Date.now(),
      lastPerChannel: { ...state.lastPerChannel, brain: Date.now() },
    })),
  updateFearGreed: (data) =>
    set(() => ({
      fearGreed: data,
      lastUpdate: Date.now(),
      lastPerChannel: { ["fear_greed"]: Date.now() },
    })),
  updateBreadth: (data) =>
    set(() => ({
      breadth: data,
      lastUpdate: Date.now(),
      lastPerChannel: { ["breadth"]: Date.now() },
    })),
  setLive: (live) => set({ isLive: live }),
  touchChannel: (channel) =>
    set((state) => ({
      lastPerChannel: { ...state.lastPerChannel, [channel]: Date.now() },
      lastUpdate: Date.now(),
    })),
}))
