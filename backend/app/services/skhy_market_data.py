import ccxt
import asyncio
import aiohttp
import time
from datetime import datetime, timezone
from typing import Optional
from app.core.cache import cache_get, cache_set
from app.core.logging import logger

BINANCE_SYMBOL = "SKHY/USDT:USDT"
BINANCE_RAW_SYMBOL = "SKHYUSDT"
BINANCE_BASE = "https://fapi.binance.com"

class SkhyMarketData:
    def __init__(self):
        self.logger = logger
        self._exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(3)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _call_ccxt(self, method, *args, **kwargs):
        async with self._semaphore:
            return await asyncio.wait_for(
                asyncio.to_thread(method, *args, **kwargs),
                timeout=15,
            )

    async def _call_rest(self, path: str, params: dict = None) -> dict:
        session = await self._get_session()
        url = f"{BINANCE_BASE}{path}"
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
                self.logger.error(f"Binance REST error {resp.status} for {path}: {await resp.text()}")
                return {}
        except Exception as e:
            self.logger.error(f"Binance REST exception {path}: {e}")
            return {}

    async def get_snapshot(self) -> dict:
        cache_key = "skhy:snapshot"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        ticker, funding, oi, ls_ratio, trades, ob = await asyncio.gather(
            self.get_ticker(), self.get_funding(), self.get_open_interest(),
            self.get_long_short_ratio(), self.get_recent_trades(), self.get_orderbook(),
            return_exceptions=True,
        )
        result = {
            "ticker": ticker if not isinstance(ticker, Exception) else {},
            "funding": funding if not isinstance(funding, Exception) else {},
            "open_interest": oi if not isinstance(oi, Exception) else {},
            "long_short_ratio": ls_ratio if not isinstance(ls_ratio, Exception) else {},
            "trades": (trades if not isinstance(trades, Exception) else [])[:50],
            "orderbook": ob if not isinstance(ob, Exception) else {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_freshness": "live" if not any(isinstance(e, Exception) for e in [ticker, funding, oi, ls_ratio, trades, ob]) else "partial",
        }
        await cache_set(cache_key, result, ttl=3)
        return result

    async def get_ticker(self) -> dict:
        try:
            t = await self._call_ccxt(self._exchange.fetch_ticker, BINANCE_SYMBOL)
            return {
                "symbol": "SKHYUSDT",
                "price": t.get("last"),
                "bid": t.get("bid"),
                "ask": t.get("ask"),
                "mark_price": t.get("markPrice") or t.get("last"),
                "index_price": t.get("indexPrice"),
                "high_24h": t.get("high"),
                "low_24h": t.get("low"),
                "volume_24h": t.get("baseVolume"),
                "change_24h": t.get("change"),
                "change_percent": t.get("percentage"),
                "timestamp": t.get("timestamp"),
            }
        except Exception as e:
            self.logger.error(f"SKHY ticker failed: {e}")
            return {}

    async def get_ohlcv(self, timeframe: str = "1h", limit: int = 200) -> list:
        cache_key = f"skhy:ohlcv:{timeframe}:{limit}"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        try:
            ohlcv = await self._call_ccxt(
                self._exchange.fetch_ohlcv, BINANCE_SYMBOL, timeframe, limit=limit
            )
            result = [
                {"time": o[0] // 1000, "open": o[1], "high": o[2], "low": o[3], "close": o[4], "volume": o[5]}
                for o in ohlcv
            ]
            ttl = {"1m": 20, "5m": 30, "15m": 45, "30m": 60, "1h": 60, "4h": 120, "1d": 300}.get(timeframe, 60)
            await cache_set(cache_key, result, ttl=ttl)
            return result
        except Exception as e:
            self.logger.error(f"SKHY OHLCV failed: {e}")
            return []

    async def get_funding(self) -> dict:
        try:
            f = await self._call_ccxt(self._exchange.fetch_funding_rate, BINANCE_SYMBOL)
            return {
                "funding_rate": f.get("fundingRate"),
                "funding_time": f.get("fundingTimestamp") or f.get("nextFundingTimestamp"),
                "next_funding_time": f.get("nextFundingTimestamp"),
                "symbol": "SKHYUSDT",
            }
        except Exception as e:
            self.logger.error(f"SKHY funding failed: {e}")
            return {}

    async def get_funding_history(self, limit: int = 50) -> list:
        cache_key = f"skhy:funding_history:{limit}"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        data = await self._call_rest("/fapi/v1/fundingRate", {"symbol": BINANCE_RAW_SYMBOL, "limit": limit})
        if isinstance(data, list):
            result = [
                {"funding_rate": float(d["fundingRate"]), "funding_time": int(d["fundingTime"])}
                for d in data if "fundingRate" in d
            ]
            await cache_set(cache_key, result, ttl=120)
            return result
        return []

    async def get_open_interest(self) -> dict:
        try:
            oi = await self._call_ccxt(self._exchange.fetch_open_interest, BINANCE_SYMBOL)
            amount = oi.get("openInterestAmount") or oi.get("baseVolume")
            value = oi.get("openInterestValue")
            return {
                "open_interest": float(amount) if amount else None,
                "open_interest_value": float(value) if value else None,
                "symbol": "SKHYUSDT",
                "timestamp": oi.get("timestamp"),
            }
        except Exception as e:
            self.logger.error(f"SKHY OI failed: {e}")
            return {}

    async def get_oi_history(self, period: str = "5m", limit: int = 50) -> list:
        cache_key = f"skhy:oi_history:{period}:{limit}"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        data = await self._call_rest("/futures/data/openInterestHist", {
            "symbol": BINANCE_RAW_SYMBOL, "period": period, "limit": limit
        })
        if isinstance(data, list):
            result = [
                {"timestamp": int(d["timestamp"]), "sum_open_interest": float(d["sumOpenInterest"]),
                 "sum_open_interest_value": float(d["sumOpenInterestValue"])}
                for d in data
            ]
            await cache_set(cache_key, result, ttl=120)
            return result
        return []

    async def get_long_short_ratio(self) -> dict:
        data = await self._call_rest("/futures/data/globalLongShortAccountRatio", {
            "symbol": BINANCE_RAW_SYMBOL, "period": "5m", "limit": 1
        })
        if isinstance(data, list) and data:
            d = data[0]
            return {
                "long_account": float(d.get("longAccount", 0)),
                "short_account": float(d.get("shortAccount", 0)),
                "long_short_ratio": float(d.get("longShortRatio", 0)),
                "timestamp": int(d.get("timestamp", 0)),
            }
        return {}

    async def get_top_trader_ls_ratio(self) -> dict:
        data = await self._call_rest("/futures/data/topLongShortAccountRatio", {
            "symbol": BINANCE_RAW_SYMBOL, "period": "5m", "limit": 1
        })
        if isinstance(data, list) and data:
            d = data[0]
            return {
                "long_account": float(d.get("longAccount", 0)),
                "short_account": float(d.get("shortAccount", 0)),
                "long_short_ratio": float(d.get("longShortRatio", 0)),
            }
        return {}

    async def get_taker_buy_sell_ratio(self) -> dict:
        cache_key = "skhy:taker_ratio"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        data = await self._call_rest("/futures/data/takerlongshortRatio", {
            "symbol": BINANCE_RAW_SYMBOL, "period": "5m", "limit": 1
        })
        if isinstance(data, list) and data:
            d = data[0]
            result = {
                "buy_sell_ratio": float(d.get("buySellRatio", 0)),
                "buy_volume": float(d.get("buyVol", 0)),
                "sell_volume": float(d.get("sellVol", 0)),
                "timestamp": int(d.get("timestamp", 0)),
            }
            await cache_set(cache_key, result, ttl=30)
            return result
        return {}

    async def get_recent_trades(self, limit: int = 100) -> list:
        try:
            trades = await self._call_ccxt(self._exchange.fetch_trades, BINANCE_SYMBOL, limit=limit)
            return [
                {
                    "price": t.get("price"), "amount": t.get("amount"),
                    "side": t.get("side"), "timestamp": t.get("timestamp"),
                    "aggressive": t.get("takerOrMaker") == "taker",
                }
                for t in trades if t.get("price")
            ]
        except Exception as e:
            self.logger.error(f"SKHY trades failed: {e}")
            return []

    async def get_orderbook(self, limit: int = 50) -> dict:
        try:
            ob = await self._call_ccxt(self._exchange.fetch_order_book, BINANCE_SYMBOL, limit)
            return {
                "bids": ob.get("bids", [])[:15],
                "asks": ob.get("asks", [])[:15],
                "timestamp": ob.get("timestamp"),
                "bid_ask_spread": (ob["asks"][0][0] - ob["bids"][0][0]) if ob.get("asks") and ob.get("bids") else None,
            }
        except Exception as e:
            self.logger.error(f"SKHY orderbook failed: {e}")
            return {}

    async def get_liquidations(self, limit: int = 50) -> list:
        cache_key = f"skhy:liquidations:{limit}"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        data = await self._call_rest("/fapi/v1/allLiquidation", {"symbol": BINANCE_RAW_SYMBOL, "limit": limit})
        if isinstance(data, list):
            result = [
                {
                    "price": float(d.get("price", 0)), "quantity": float(d.get("origQty", 0)),
                    "side": d.get("side"), "time": int(d.get("time", 0)),
                    "type": d.get("type"),
                }
                for d in data
            ]
            await cache_set(cache_key, result, ttl=30)
            return result
        return []

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

skhy_market_data = SkhyMarketData()
