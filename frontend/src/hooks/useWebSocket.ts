"use client"

import { useEffect, useRef, useState, useCallback } from "react"

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"

export function useWebSocket(symbol: string) {
  const [data, setData] = useState<any>(null)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!symbol) return

    const connect = () => {
      const ws = new WebSocket(`${WS_URL}/ws/${symbol}`)
      wsRef.current = ws

      ws.onopen = () => setIsConnected(true)
      ws.onclose = () => {
        setIsConnected(false)
        setTimeout(connect, 5000)
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (event) => {
        try {
          setData(JSON.parse(event.data))
        } catch {}
      }
    }

    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [symbol])

  return { data, isConnected }
}
