import ccxt
from typing import Optional, Dict, Any
from app.core.cache import cache_get, cache_set
from app.core.logging import logger


class ExchangeRegistry:
    def __init__(self):
        self.logger = logger
        self._exchanges: Dict[str, ccxt.Exchange] = {}

    def _get_exchange(self, name: str, api_key: Optional[str] = None,
                       secret: Optional[str] = None, passphrase: Optional[str] = None) -> Optional[ccxt.Exchange]:
        cache_key = f"{name}:{api_key or ''}"
        if cache_key in self._exchanges:
            return self._exchanges[cache_key]

        config = {
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        }
        if api_key:
            config["apiKey"] = api_key
        if secret:
            config["secret"] = secret
        if passphrase:
            config["password"] = passphrase

        factory = {
            "binance": lambda: ccxt.binance(config),
            "bybit": lambda: ccxt.bybit(config),
            "okx": lambda: ccxt.okx(config),
            "bitget": lambda: ccxt.bitget(config),
            "kucoin": lambda: ccxt.kucoin(config),
            "hyperliquid": lambda: ccxt.hyperliquid(config),
        }

        factory_func = factory.get(name)
        if not factory_func:
            self.logger.error(f"Unsupported exchange: {name}")
            return None

        try:
            exchange = factory_func()
            exchange.load_markets()
            self._exchanges[cache_key] = exchange
            return exchange
        except Exception as e:
            self.logger.error(f"Failed to initialize {name}: {e}")
            return None

    async def get_ohlcv(self, exchange: str, symbol: str, timeframe: str = "1h",
                         limit: int = 200, api_key: str = None, secret: str = None,
                         passphrase: str = None) -> list:
        cache_key = f"ohlcv:{exchange}:{symbol}:{timeframe}:{limit}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        ex = self._get_exchange(exchange, api_key, secret, passphrase)
        if not ex:
            return []
        try:
            ohlcv = ex.fetch_ohlcv(symbol, timeframe, limit=limit)
            result = [{"time": o[0] // 1000, "open": o[1], "high": o[2],
                       "low": o[3], "close": o[4], "volume": o[5]} for o in ohlcv]
            await cache_set(cache_key, result, ttl=30)
            return result
        except Exception as e:
            self.logger.error(f"{exchange} OHLCV error {symbol}: {e}")
            return []

    async def get_ticker(self, exchange: str, symbol: str, api_key: str = None,
                          secret: str = None, passphrase: str = None) -> dict:
        ex = self._get_exchange(exchange, api_key, secret, passphrase)
        if not ex:
            return {}
        try:
            t = ex.fetch_ticker(symbol)
            return {
                "symbol": t["symbol"],
                "price": t["last"],
                "bid": t["bid"], "ask": t["ask"],
                "high_24h": t["high"], "low_24h": t["low"],
                "volume_24h": t["baseVolume"],
                "change_percent": t["percentage"],
                "exchange": exchange,
            }
        except Exception:
            return {}

    async def get_orderbook(self, exchange: str, symbol: str, limit: int = 50,
                             api_key: str = None, secret: str = None,
                             passphrase: str = None) -> dict:
        ex = self._get_exchange(exchange, api_key, secret, passphrase)
        if not ex:
            return {}
        try:
            ob = ex.fetch_order_book(symbol, limit)
            return {"bids": ob["bids"][:10], "asks": ob["asks"][:10],
                    "timestamp": ob["timestamp"], "exchange": exchange}
        except Exception:
            return {}

    async def get_funding_rate(self, exchange: str, symbol: str, api_key: str = None,
                                secret: str = None, passphrase: str = None) -> dict:
        ex = self._get_exchange(exchange, api_key, secret, passphrase)
        if not ex:
            return {}
        try:
            funding = ex.fetch_funding_rate(symbol)
            return {
                "symbol": funding["symbol"],
                "funding_rate": funding["fundingRate"],
                "funding_time": funding["fundingTime"],
                "exchange": exchange,
            }
        except Exception:
            return {}

    async def get_open_interest(self, exchange: str, symbol: str, api_key: str = None,
                                 secret: str = None, passphrase: str = None) -> dict:
        ex = self._get_exchange(exchange, api_key, secret, passphrase)
        if not ex:
            return {}
        try:
            oi = ex.fetch_open_interest(symbol)
            return {"symbol": oi["symbol"], "open_interest": oi["openInterest"], "exchange": exchange}
        except Exception:
            return {}

    @property
    def supported_exchanges(self) -> list:
        return ["binance", "bybit", "okx", "bitget", "kucoin", "hyperliquid"]


exchange_registry = ExchangeRegistry()
