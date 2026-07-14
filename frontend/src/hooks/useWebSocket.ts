"use client"

import { useEffect, useRef, useState, useCallback } from "react"

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"

type WSEventHandler = (data: any) => void

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

export function useWebSocketV2() {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const handlersRef = useRef<Map<string, WSEventHandler[]>>(new Map())
  const messageQueue = useRef<any[]>([])

  const connect = useCallback((token?: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const url = token ? `${WS_URL}/ws/v2?token=${token}` : `${WS_URL}/ws/v2`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      for (const msg of messageQueue.current) {
        ws.send(JSON.stringify(msg))
      }
      messageQueue.current = []
    }

    ws.onclose = () => {
      setIsConnected(false)
      setTimeout(() => connect(token), 5000)
    }

    ws.onerror = () => ws.close()

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        const channel = msg.channel || msg.event
        const handlers = handlersRef.current.get(channel) || []
        handlers.forEach((h) => h(msg))

        const wildcard = handlersRef.current.get("*") || []
        wildcard.forEach((h) => h(msg))
      } catch {}
    }
  }, [])

  const send = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      messageQueue.current.push(message)
    }
  }, [])

  const subscribe = useCallback((channel: string, symbols?: string[]) => {
    send({ type: "subscribe", data: { channel, symbols } })
  }, [send])

  const unsubscribe = useCallback((channel: string) => {
    send({ type: "unsubscribe", data: { channel } })
  }, [send])

  const on = useCallback((event: string, handler: WSEventHandler) => {
    const existing = handlersRef.current.get(event) || []
    existing.push(handler)
    handlersRef.current.set(event, existing)
    return () => {
      const h = handlersRef.current.get(event) || []
      handlersRef.current.set(event, h.filter((h) => h !== handler))
    }
  }, [])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setIsConnected(false)
  }, [])

  return { isConnected, connect, send, subscribe, unsubscribe, on, disconnect }
}
