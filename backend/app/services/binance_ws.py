"""
Binance Futures WebSocket Integration
- Real-time price streams (ticker)
- Kline/candlestick streams
- Depth/orderbook streams

Connects to Binance WebSocket and broadcasts through our ws_manager
"""

import asyncio
import json
from collections import deque
from datetime import UTC, datetime

import aiohttp

from app.core.logging import logger
from app.core.websocket_manager import ws_manager

BINANCE_WS_BASE = "wss://fstream.binance.com"

class BinanceWebSocketService:
    def __init__(self):
        self.tasks: dict[str, asyncio.Task] = {}
        self.running = False
        self._session: aiohttp.ClientSession | None = None
        self._prices: dict[str, float] = {}
        self._subscriptions: set[str] = set()
        self._liquidations: deque[dict] = deque(maxlen=500)

    async def start(self):
        self.running = True
        self._session = aiohttp.ClientSession()
        logger.info("Binance WebSocket Service starting")

    async def stop(self):
        self.running = False
        for _name, task in self.tasks.items():
            task.cancel()
        if self._session:
            await self._session.close()
        logger.info("Binance WebSocket Service stopped")

    async def subscribe_price(self, symbols: list):
        streams = [f"{s.lower().replace('/', '')}@ticker" for s in symbols]
        await self._connect_stream("prices", streams, self._handle_ticker)

    async def subscribe_klines(self, symbols: list, interval: str = "1m"):
        streams = [f"{s.lower().replace('/', '')}@kline_{interval}" for s in symbols]
        await self._connect_stream(f"klines_{interval}", streams, self._handle_kline)

    async def subscribe_depth(self, symbols: list, level: int = 20):
        streams = [f"{s.lower().replace('/', '')}@depth{level}" for s in symbols]
        await self._connect_stream(f"depth_{level}", streams, self._handle_depth)

    async def subscribe_liquidations(self):
        await self._connect_stream("liquidations", ["!forceOrder@arr"], self._handle_liquidation)

    async def _connect_stream(self, name: str, streams: list, handler):
        if name in self.tasks:
            self.tasks[name].cancel()
        self.tasks[name] = asyncio.create_task(self._run_stream(streams, handler))

    async def _run_stream(self, streams: list, handler):
        if len(streams) == 1:
            url = f"{BINANCE_WS_BASE}/ws/{streams[0]}"
        else:
            url = f"{BINANCE_WS_BASE}/stream?streams={'/'.join(streams)}"
        if len(streams) > 200:
            logger.error(f"Too many streams: {len(streams)}")
            return

        # Exponential backoff with jitter. The previous implementation
        # slept a flat 5s on every failure — when Binance had a brief
        # outage, every stream retried at the same cadence, hammering
        # their edge and frequently getting rate-limited into a longer
        # outage. Cap at 60s so a permanently broken stream still
        # recovers within a minute once the upstream is back.
        backoff = 1.0
        while self.running:
            try:
                async with self._session.ws_connect(url, heartbeat=30) as ws:
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            await handler(data.get("data", data))
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
                    # Clean break out of the inner for — reset backoff
                    # because we just had a working connection.
                    backoff = 1.0
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Binance WS stream error: {e}")
                # Jitter ±25% so multiple workers don't reconnect in lockstep.
                jitter = backoff * 0.25 * (2 * (asyncio.get_event_loop().time() % 1) - 1)
                sleep_for = min(60.0, max(1.0, backoff + jitter))
                await asyncio.sleep(sleep_for)
                backoff = min(backoff * 2, 60.0)

    async def _handle_ticker(self, data: dict):
        symbol = data.get("s", "")
        price = float(data.get("c", 0))
        self._prices[symbol] = price
        await ws_manager.broadcast("ticker", "price_update", {
            "symbol": symbol,
            "price": price,
            "change": float(data.get("p", 0)),
            "change_percent": float(data.get("P", 0)),
            "volume": float(data.get("v", 0)),
            "high": float(data.get("h", 0)),
            "low": float(data.get("l", 0)),
            "timestamp": datetime.now(UTC).isoformat(),
        })

    async def _handle_kline(self, data: dict):
        k = data.get("k", {})
        if not k:
            return
        candle = {
            "symbol": data.get("s", ""),
            "time": k["t"] // 1000,
            "open": float(k["o"]),
            "high": float(k["h"]),
            "low": float(k["l"]),
            "close": float(k["c"]),
            "volume": float(k["v"]),
            "is_closed": k["x"],
            "interval": k["i"],
        }
        await ws_manager.broadcast("market", "candle_update", candle)

        if candle["is_closed"]:
            await ws_manager.broadcast("market", "candle_closed", candle)

    async def _handle_depth(self, data: dict):
        symbol = data.get("s", "")
        bids = [[float(b[0]), float(b[1])] for b in data.get("b", [])[:10]]
        asks = [[float(a[0]), float(a[1])] for a in data.get("a", [])[:10]]
        bid_vol = sum(b[1] for b in bids)
        ask_vol = sum(a[1] for a in asks)
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0

        await ws_manager.broadcast("orderbook", "depth_update", {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "imbalance": round(imbalance, 4),
            "timestamp": datetime.now(UTC).isoformat(),
        })

    async def _handle_liquidation(self, data: dict):
        order = data.get("o", {})
        symbol = order.get("s")
        price = float(order.get("ap") or order.get("p") or 0)
        quantity = float(order.get("z") or order.get("q") or 0)
        if not symbol or price <= 0 or quantity <= 0:
            return
        event_time = int(data.get("E") or order.get("T") or 0)
        item = {
            "symbol": symbol,
            "price": price,
            "quantity": quantity,
            "notional": price * quantity,
            "side": "long" if order.get("S") == "SELL" else "short",
            "event_time": event_time,
            "timestamp": (
                datetime.fromtimestamp(event_time / 1000, tz=UTC).isoformat()
                if event_time else datetime.now(UTC).isoformat()
            ),
        }
        self._liquidations.append(item)
        await ws_manager.broadcast("derivatives", "liquidation_update", item)

    def get_price(self, symbol: str) -> float | None:
        return self._prices.get(symbol)

    async def get_all_prices(self) -> dict:
        return dict(self._prices)

    def get_recent_liquidations(self, max_age_seconds: int = 300) -> list[dict]:
        cutoff = int(datetime.now(UTC).timestamp() * 1000) - max_age_seconds * 1000
        return [
            dict(item)
            for item in self._liquidations
            if not item.get("event_time") or item["event_time"] >= cutoff
        ]

binance_ws = BinanceWebSocketService()
