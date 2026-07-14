"use client"

import React, { createContext, useContext, useEffect, useRef, useState } from "react"
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

export function WSProvider({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  const { quality, connect, subscribe, unsubscribe, on, isConnected } = useWebSocketV2(token || undefined)
  const [ready, setReady] = useState(false)
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
      setReady(false)
      return
    }
    setLive(true)
    setReady(true)

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
    if (!ready) return

    const unsubs: (() => void)[] = []

    unsubs.push(on("price_update", (msg: any) => {
      if (msg.data?.symbol) updateTicker(msg.data.symbol, msg.data)
    }))

    unsubs.push(on("ticker", (msg: any) => {
      if (msg.data?.symbol) updateTicker(msg.data.symbol, msg.data)
    }))

    unsubs.push(on("orderflow_update", (msg: any) => {
      if (msg.data?.symbol && msg.data?.data) updateOrderFlow(msg.data.symbol, msg.data.data)
    }))

    unsubs.push(on("derivatives_update", (msg: any) => {
      if (msg.data?.symbol && msg.data?.data) updateDerivatives(msg.data.symbol, msg.data.data)
    }))

    unsubs.push(on("news_article", (msg: any) => {
      if (msg.data) addNews(msg.data)
    }))

    unsubs.push(on("sentiment_update", (msg: any) => {
      if (msg.data?.symbol && msg.data?.data) updateSentiment(msg.data.symbol, msg.data.data)
    }))

    unsubs.push(on("onchain_update", (msg: any) => {
      if (msg.data?.symbol && msg.data?.data) updateOnchain(msg.data.symbol, msg.data.data)
    }))

    unsubs.push(on("macro_update", (msg: any) => {
      if (msg.data?.data) updateMacro(msg.data.data)
    }))

    unsubs.push(on("brain_assessment", (msg: any) => {
      if (msg.data?.symbol && msg.data?.data) updateBrain(msg.data.symbol, msg.data.data)
    }))

    unsubs.push(on("fear_greed_update", (msg: any) => {
      if (msg.data?.data) updateFearGreed(msg.data.data)
    }))

    unsubs.push(on("breadth_update", (msg: any) => {
      if (msg.data?.data) updateBreadth(msg.data.data)
    }))

    return () => unsubs.forEach((u) => u())
  }, [
    ready, on, updateTicker, updateOrderFlow, updateDerivatives,
    addNews, updateSentiment, updateOnchain, updateMacro,
    updateBrain, updateFearGreed, updateBreadth,
  ])

  return (
    <WSContext.Provider value={{ quality, subscribe, unsubscribe, on, isConnected }}>
      {children}
    </WSContext.Provider>
  )
}
