"use client"

import { useEffect, useRef, useState, useCallback } from "react"

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"
const PING_INTERVAL = 15_000
const MAX_BACKOFF = 30_000
const INITIAL_BACKOFF = 1_000

export type WSEventHandler = (data: any) => void

export interface ConnectionQuality {
  latency: number
  uptime: number
  connectedAt: number | null
  status: "connecting" | "connected" | "disconnected" | "reconnecting"
  lastMessageAt: number | null
  reconnects: number
}

interface PendingMessage {
  channel: string
  payload: any
  priority: number
  timestamp: number
}

export function useWebSocketV2(token?: string) {
  const wsRef = useRef<WebSocket | null>(null)
  const handlersRef = useRef<Map<string, WSEventHandler[]>>(new Map())
  const pendingRef = useRef<PendingMessage[]>([])
  const subscribedRef = useRef<Set<string>>(new Set())
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const latencyRef = useRef<number[]>([])
  const connectedAtRef = useRef<number | null>(null)
  const reconnectCountRef = useRef(0)
  const backoffRef = useRef(INITIAL_BACKOFF)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastMessageRef = useRef<number | null>(null)
  const seqRef = useRef<Record<string, number>>({})

  const [quality, setQuality] = useState<ConnectionQuality>({
    latency: 0,
    uptime: 0,
    connectedAt: null,
    status: "disconnected",
    lastMessageAt: null,
    reconnects: 0,
  })

  const updateQuality = useCallback((partial: Partial<ConnectionQuality>) => {
    setQuality((prev) => ({ ...prev, ...partial }))
  }, [])

  const flushQueue = useCallback(() => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    const sorted = pendingRef.current.sort((a, b) => b.priority - a.priority)
    pendingRef.current = []
    for (const msg of sorted) {
      ws.send(JSON.stringify(msg.payload))
    }
  }, [])

  const cleanup = useCallback(() => {
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current)
      pingTimerRef.current = null
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }, [])

  const doReconnect = useCallback(() => {
    cleanup()
    const backoff = Math.min(backoffRef.current, MAX_BACKOFF)
    backoffRef.current = Math.min(backoff * 2, MAX_BACKOFF)
    reconnectCountRef.current += 1
    updateQuality({ status: "reconnecting", reconnects: reconnectCountRef.current })
    reconnectTimerRef.current = setTimeout(() => connect(), backoff)
  }, [cleanup, updateQuality])

  const connect = useCallback(() => {
    cleanup()
    const url = token ? `${WS_URL}/ws/v2?token=${token}` : `${WS_URL}/ws/v2`
    const ws = new WebSocket(url)
    wsRef.current = ws
    updateQuality({ status: "connecting" })

    ws.onopen = () => {
      connectedAtRef.current = Date.now()
      backoffRef.current = INITIAL_BACKOFF
      updateQuality({
        status: "connected",
        connectedAt: connectedAtRef.current,
        reconnects: reconnectCountRef.current,
      })
      flushQueue()
      for (const ch of subscribedRef.current) {
        ws.send(JSON.stringify({ type: "subscribe", data: { channel: ch } }))
      }
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          const t0 = performance.now()
          ws.send(JSON.stringify({ type: "ping", data: { t: t0 } }))
        }
      }, PING_INTERVAL)
    }

    ws.onclose = () => {
      updateQuality({ status: "disconnected" })
      doReconnect()
    }

    ws.onerror = () => {
      ws.close()
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        lastMessageRef.current = Date.now()
        updateQuality({ lastMessageAt: lastMessageRef.current })

        if (msg.event === "pong" && msg.data?.t) {
          const latency = performance.now() - msg.data.t
          latencyRef.current.push(latency)
          if (latencyRef.current.length > 10) latencyRef.current.shift()
          const avg = latencyRef.current.reduce((a, b) => a + b, 0) / latencyRef.current.length
          const uptime = connectedAtRef.current ? (Date.now() - connectedAtRef.current) / 1000 : 0
          updateQuality({ latency: Math.round(avg), uptime: Math.round(uptime) })
        }

        if (msg.event === "delta" && msg.data?.channel) {
          const channel = msg.data.channel
          const seq = msg.data.seq ?? 0
          const prev = seqRef.current[channel] ?? -1
          if (seq > prev) {
            seqRef.current[channel] = seq
            const handlers = handlersRef.current.get(channel) || []
            handlers.forEach((h) => h(msg.data))
            const wildcard = handlersRef.current.get("*") || []
            wildcard.forEach((h) => h(msg.data))
          }
          return
        }

        const channel = msg.channel || msg.event
        const handlers = handlersRef.current.get(channel) || []
        handlers.forEach((h) => h(msg))

        const wildcard = handlersRef.current.get("*") || []
        wildcard.forEach((h) => h(msg))
      } catch {}
    }
  }, [token, cleanup, flushQueue, updateQuality, doReconnect])

  const send = useCallback((message: any, priority = 0) => {
    const ws = wsRef.current
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
    } else {
      pendingRef.current.push({ channel: "", payload: message, priority, timestamp: Date.now() })
    }
  }, [])

  const subscribe = useCallback(
    (channel: string, symbols?: string[]) => {
      subscribedRef.current.add(channel)
      send({ type: "subscribe", data: { channel, symbols } })
    },
    [send],
  )

  const unsubscribe = useCallback((channel: string) => {
    subscribedRef.current.delete(channel)
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
    cleanup()
    subscribedRef.current.clear()
    pendingRef.current = []
    connectedAtRef.current = null
    latencyRef.current = []
    seqRef.current = {}
    wsRef.current?.close()
    wsRef.current = null
    updateQuality({
      status: "disconnected",
      connectedAt: null,
      lastMessageAt: null,
      latency: 0,
      uptime: 0,
    })
  }, [cleanup, updateQuality])

  return {
    quality,
    connect,
    send,
    subscribe,
    unsubscribe,
    on,
    disconnect,
    isConnected: quality.status === "connected",
  }
}

export function useWebSocket(symbol: string) {
  const [data, setData] = useState<any>(null)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const backoffRef = useRef(1000)

  useEffect(() => {
    if (!symbol) return

    const connect = () => {
      const ws = new WebSocket(`${WS_URL}/ws/v2/ticker/${symbol.replace("/", "-")}`)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        backoffRef.current = 1000
      }
      ws.onclose = () => {
        setIsConnected(false)
        const delay = backoffRef.current
        backoffRef.current = Math.min(delay * 2, 30000)
        reconnectTimerRef.current = setTimeout(connect, delay)
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data)
          if (parsed.event === "price_update") {
            setData(parsed.data)
          } else {
            setData(parsed)
          }
        } catch {}
      }
    }

    connect()
    return () => {
      wsRef.current?.close()
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
    }
  }, [symbol])

  return { data, isConnected }
}
