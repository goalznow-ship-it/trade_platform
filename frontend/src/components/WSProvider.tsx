"use client"

import React, { createContext, useContext, useEffect, useRef } from "react"
import { useWebSocketV2, type ConnectionQuality, type WSEventHandler } from "@/hooks/useWebSocket"
import { useMarketStore } from "@/store/market"
import { useAuth } from "@/hooks/useAuth"

interface WSContextValue {
  quality: ConnectionQuality
  subscribe: (channel: string, symbols?: string[]) => void
  unsubscribe: (channel: string) => void
  on: (event: string, handler: WSEventHandler) => () => void
  isConnected: boolean
}

const WSContext = createContext<WSContextValue | null>(null)

export function useWS() {
  const ctx = useContext(WSContext)
  if (!ctx) throw new Error("useWS must be used within WSProvider")
  return ctx
}

interface WSMsgData {
  symbol?: string
  data?: unknown
  [key: string]: unknown
}

interface WSMsg {
  data?: WSMsgData
  [key: string]: unknown
}

export function WSProvider({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  const { quality, connect, subscribe, unsubscribe, on, isConnected } = useWebSocketV2(token || undefined)
  const initialized = useRef(false)

  const updateTicker = useMarketStore((s) => s.updateTicker)
  const updateOrderFlow = useMarketStore((s) => s.updateOrderFlow)
  const updateDerivatives = useMarketStore((s) => s.updateDerivatives)
  const addNews = useMarketStore((s) => s.addNews)
  const updateSentiment = useMarketStore((s) => s.updateSentiment)
  const updateOnchain = useMarketStore((s) => s.updateOnchain)
  const updateMacro = useMarketStore((s) => s.updateMacro)
  const updateBrain = useMarketStore((s) => s.updateBrain)
  const updateFearGreed = useMarketStore((s) => s.updateFearGreed)
  const updateBreadth = useMarketStore((s) => s.updateBreadth)
  const setLive = useMarketStore((s) => s.setLive)

  useEffect(() => {
    if (!initialized.current && token) {
      initialized.current = true
      connect()
    }
  }, [token, connect])

  useEffect(() => {
    if (!isConnected) {
      setLive(false)
      return
    }
    setLive(true)

    subscribe("ticker")
    subscribe("orderflow")
    subscribe("derivatives")
    subscribe("news")
    subscribe("sentiment")
    subscribe("onchain")
    subscribe("macro")
    subscribe("brain")
    subscribe("signals")
    subscribe("fear_greed")
    subscribe("breadth")
  }, [isConnected, subscribe, setLive])

  useEffect(() => {
    if (!isConnected) return

    const unsubs: (() => void)[] = []

    unsubs.push(on("price_update", (msg: WSMsg) => {
      const d = msg.data
      if (d?.symbol) updateTicker(d.symbol, d as never)
    }))

    unsubs.push(on("ticker", (msg: WSMsg) => {
      const d = msg.data
      if (d?.symbol) updateTicker(d.symbol, d as never)
    }))

    unsubs.push(on("orderflow_update", (msg: WSMsg) => {
      const d = msg.data
      if (d?.symbol && d?.data) updateOrderFlow(d.symbol, d.data as never)
    }))

    unsubs.push(on("derivatives_update", (msg: WSMsg) => {
      const d = msg.data
      if (d?.symbol && d?.data) updateDerivatives(d.symbol, d.data as never)
    }))

    unsubs.push(on("news_article", (msg: WSMsg) => {
      if (msg.data) addNews(msg.data as never)
    }))

    unsubs.push(on("sentiment_update", (msg: WSMsg) => {
      const d = msg.data
      if (d?.symbol && d?.data) updateSentiment(d.symbol, d.data as never)
    }))

    unsubs.push(on("onchain_update", (msg: WSMsg) => {
      const d = msg.data
      if (d?.symbol && d?.data) updateOnchain(d.symbol, d.data as never)
    }))

    unsubs.push(on("macro_update", (msg: WSMsg) => {
      if (msg.data?.data) updateMacro(msg.data.data as never)
    }))

    unsubs.push(on("brain_assessment", (msg: WSMsg) => {
      const d = msg.data
      if (d?.symbol && d?.data) updateBrain(d.symbol, d.data as never)
    }))

    unsubs.push(on("fear_greed_update", (msg: WSMsg) => {
      if (msg.data?.data) updateFearGreed(msg.data.data as never)
    }))

    unsubs.push(on("breadth_update", (msg: WSMsg) => {
      if (msg.data?.data) updateBreadth(msg.data.data as never)
    }))

    return () => unsubs.forEach((u) => u())
  }, [
    isConnected, on, updateTicker, updateOrderFlow, updateDerivatives,
    addNews, updateSentiment, updateOnchain, updateMacro,
    updateBrain, updateFearGreed, updateBreadth,
  ])

  return (
    <WSContext.Provider value={{ quality, subscribe, unsubscribe, on, isConnected }}>
      {children}
    </WSContext.Provider>
  )
}
