import { create } from "zustand"

interface TickerData {
  price: number
  change: number
  high_24h?: number
  low_24h?: number
  volume_24h?: number
}

interface MarketState {
  selectedSymbol: string
  selectedTimeframe: string
  tickers: Record<string, TickerData>
  lastUpdate: number | null
  isLive: boolean
  setSymbol: (symbol: string) => void
  setTimeframe: (timeframe: string) => void
  updateTicker: (symbol: string, data: Partial<TickerData>) => void
  setLive: (live: boolean) => void
}

export const useMarketStore = create<MarketState>((set) => ({
  selectedSymbol: "BTC/USDT",
  selectedTimeframe: "1h",
  tickers: {},
  lastUpdate: null,
  isLive: false,
  setSymbol: (symbol) => set({ selectedSymbol: symbol }),
  setTimeframe: (timeframe) => set({ selectedTimeframe: timeframe }),
  updateTicker: (symbol, data) =>
    set((state) => ({
      tickers: { ...state.tickers, [symbol]: { ...state.tickers[symbol], ...data } },
      lastUpdate: Date.now(),
    })),
  setLive: (live) => set({ isLive: live }),
}))
