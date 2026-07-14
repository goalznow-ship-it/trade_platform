"""
Binance Futures WebSocket Integration
- Real-time price streams (ticker)
- Kline/candlestick streams
- Depth/orderbook streams

Connects to Binance WebSocket and broadcasts through our ws_manager
"""

import asyncio
import json
import time
from typing import Dict, Set, Optional
from datetime import datetime, timezone
import aiohttp
from app.core.websocket_manager import ws_manager
from app.core.cache import cache_get, cache_set
from app.core.logging import logger

BINANCE_WS_BASE = "wss://fstream.binance.com/ws"

class BinanceWebSocketService:
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        self._session: Optional[aiohttp.ClientSession] = None
        self._prices: Dict[str, float] = {}
        self._subscriptions: Set[str] = set()

    async def start(self):
        self.running = True
        self._session = aiohttp.ClientSession()
        logger.info("Binance WebSocket Service starting")

    async def stop(self):
        self.running = False
        for name, task in self.tasks.items():
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

    async def _connect_stream(self, name: str, streams: list, handler):
        if name in self.tasks:
            self.tasks[name].cancel()
        self.tasks[name] = asyncio.create_task(self._run_stream(streams, handler))

    async def _run_stream(self, streams: list, handler):
        url = f"{BINANCE_WS_BASE}/{'/'.join(streams)}"
        if len(streams) > 1:
            url = f"{BINANCE_WS_BASE}/{'/'.join(streams)}"
        if len(streams) > 200:
            logger.error(f"Too many streams: {len(streams)}")
            return

        while self.running:
            try:
                async with self._session.ws_connect(url, heartbeat=30) as ws:
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            await handler(data)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Binance WS stream error: {e}")
                await asyncio.sleep(5)

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_price(self, symbol: str) -> Optional[float]:
        return self._prices.get(symbol)

    async def get_all_prices(self) -> dict:
        return dict(self._prices)

binance_ws = BinanceWebSocketService()
