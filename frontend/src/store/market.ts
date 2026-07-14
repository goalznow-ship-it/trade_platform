import { create } from "zustand"

interface MarketState {
  selectedSymbol: string
  selectedTimeframe: string
  setSymbol: (symbol: string) => void
  setTimeframe: (timeframe: string) => void
}

export const useMarketStore = create<MarketState>((set) => ({
  selectedSymbol: "BTC/USDT",
  selectedTimeframe: "1h",
  setSymbol: (symbol) => set({ selectedSymbol: symbol }),
  setTimeframe: (timeframe) => set({ selectedTimeframe: timeframe }),
}))
