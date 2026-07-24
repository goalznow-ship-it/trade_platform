"""
Market Coverage Service
- Maintains top 30 futures coins by Binance USDT perpetual volume
- Auto-updates weekly from Binance volume ranking
- Cached symbols with fallback
"""
from datetime import datetime, timezone
from typing import List
import asyncio
from app.core.cache import cache_get, cache_set
from app.core.logging import logger

TOP_30_FALLBACK = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "LINK/USDT", "DOT/USDT",
    "TRX/USDT", "LTC/USDT", "ATOM/USDT", "NEAR/USDT", "APT/USDT",
    "FIL/USDT", "ARB/USDT", "OP/USDT", "SUI/USDT", "INJ/USDT",
    "UNI/USDT", "ETC/USDT", "FET/USDT", "TIA/USDT", "WIF/USDT",
    "1000PEPE/USDT", "SKY/USDT", "SKH/USDT", "AAVE/USDT", "SEI/USDT",
]

# Symbols that require Bybit (not on Binance futures)
SYMBOL_EXCHANGE_OVERRIDE = {
    "SKH": "bybit",
    "SKHY": "bybit",
}


class MarketCoverageService:
    def __init__(self):
        self._cache_key = "market:top30"
        self._cache_key_timestamp = "market:top30:updated"
        self._update_interval_hours = 168  # 7 days
        self._fallback = TOP_30_FALLBACK
        self._symbol_exchange_override = SYMBOL_EXCHANGE_OVERRIDE
        self._logger = logger

    @staticmethod
    def _normalize_symbols(symbols: List[str]) -> List[str]:
        # Repair symbols cached by older releases that used spot asset names
        # for Binance perpetual contracts.
        aliases = {"PEPE/USDT": "1000PEPE/USDT"}
        return list(dict.fromkeys(aliases.get(symbol, symbol) for symbol in symbols))

    def get_symbol_exchange(self, symbol: str) -> str:
        """Get the exchange for a symbol. Bybit for SKH/SKHY, Binance otherwise."""
        base = symbol.split("/")[0] if "/" in symbol else symbol
        return self._symbol_exchange_override.get(base, "binance")

    async def get_top_symbols(self, count: int = 30, force_refresh: bool = False) -> List[str]:
        if force_refresh:
            return await self._fetch_and_cache()

        cached = await cache_get(self._cache_key)
        if cached is not None and isinstance(cached, list) and len(cached) >= count:
            normalized = self._normalize_symbols(cached)
            if normalized != cached:
                await cache_set(
                    self._cache_key,
                    normalized,
                    ttl=self._update_interval_hours * 3600,
                )
            # Always ensure Bybit-only symbols are in the list
            forced_symbols = ["SKH/USDT", "SKHY/USDT"]
            symbols = normalized[:count]
            for fs in forced_symbols:
                if fs not in symbols:
                    symbols.append(fs)
                    if len(symbols) > count + len(forced_symbols):
                        break
            return symbols

        return await self._fetch_and_cache()

    async def _fetch_and_cache(self) -> List[str]:
        try:
            symbols = self._normalize_symbols(await self._fetch_top_from_exchange())
            if symbols and len(symbols) >= 20:
                # Always ensure Bybit-only symbols like SKH are in the list
                forced_symbols = ["SKH/USDT", "SKHY/USDT"]
                for fs in forced_symbols:
                    if fs not in symbols:
                        symbols.append(fs)
                await cache_set(self._cache_key, symbols, ttl=self._update_interval_hours * 3600)
                await cache_set(self._cache_key_timestamp, datetime.now(timezone.utc).isoformat(),
                                ttl=self._update_interval_hours * 3600)
                self._logger.info(f"Market coverage updated: {len(symbols)} symbols")
                return symbols
        except Exception as e:
            self._logger.warning(f"Failed to fetch top symbols: {e}")

        await cache_set(self._cache_key, self._fallback, ttl=3600)
        return self._fallback

    async def _fetch_top_from_exchange(self) -> List[str]:
        try:
            import asyncio
            import ccxt
            ex = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            markets = await asyncio.to_thread(ex.load_markets)
            tickers = await asyncio.to_thread(ex.fetch_tickers)

            usdt_perps = []
            for symbol, market in markets.items():
                if (
                    market.get("active", True)
                    and market.get("swap")
                    and market.get("linear")
                    and market.get("settle") == "USDT"
                ):
                    ticker = tickers.get(symbol, {})
                    quote_volume = ticker.get("quoteVolume", 0) or 0
                    api_symbol = f"{market.get('base')}/USDT"
                    usdt_perps.append((api_symbol, quote_volume))

            usdt_perps.sort(key=lambda x: x[1], reverse=True)
            top = [s[0] for s in usdt_perps[:40]]

            self._logger.info(f"Fetched {len(top)} symbols from Binance volume ranking")
            return top if top else self._fallback
        except Exception as e:
            self._logger.error(f"Exchange fetch failed: {e}")
            return self._fallback

    async def get_bybit_ticker(self, symbol: str) -> dict:
        """Fetch ticker from Bybit (for symbols not on Binance like SKH/SKHY)."""
        from app.services.market import market_service
        bybit_ex = market_service.exchanges.get("bybit")
        if not bybit_ex:
            return {}
        try:
            t = await market_service._call_exchange(bybit_ex.fetch_ticker, symbol)
            if t:
                return {
                    'symbol': t['symbol'],
                    'price': t['last'],
                    'bid': t['bid'],
                    'ask': t['ask'],
                    'high_24h': t['high'],
                    'low_24h': t['low'],
                    'volume_24h': t['baseVolume'],
                    'change_24h': t['change'],
                    'change_percent': t['percentage'],
                    'timestamp': t['timestamp'],
                    'exchange': 'bybit',
                }
        except Exception:
            pass
        return {}

    async def get_market_gainers(self, count: int = 10) -> List[dict]:
        symbols = await self.get_top_symbols(count=30)
        from app.services.market import market_service

        results = []
        for s in symbols[:20]:
            try:
                t = await market_service.get_ticker(s)
                if t and t.get('change_percent') is not None:
                    results.append({
                        'symbol': s,
                        'price': t['price'],
                        'change_percent': t['change_percent'],
                        'volume_24h': t.get('volume_24h', 0),
                    })
            except Exception:
                continue

        results.sort(key=lambda r: r['change_percent'], reverse=True)
        return results[:count]

    async def get_market_losers(self, count: int = 10) -> List[dict]:
        symbols = await self.get_top_symbols(count=30)
        from app.services.market import market_service

        results = []
        for s in symbols[:20]:
            try:
                t = await market_service.get_ticker(s)
                if t and t.get('change_percent') is not None:
                    results.append({
                        'symbol': s,
                        'price': t['price'],
                        'change_percent': t['change_percent'],
                        'volume_24h': t.get('volume_24h', 0),
                    })
            except Exception:
                continue

        results.sort(key=lambda r: r['change_percent'])
        return results[:count]

    async def get_volume_leaders(self, count: int = 10) -> List[dict]:
        symbols = await self.get_top_symbols(count=30)
        from app.services.market import market_service

        results = []
        for s in symbols[:25]:
            try:
                t = await market_service.get_ticker(s)
                if t and t.get('volume_24h'):
                    results.append({
                        'symbol': s,
                        'price': t['price'],
                        'change_percent': t['change_percent'],
                        'volume_24h': t['volume_24h'],
                    })
            except Exception:
                continue

        results.sort(key=lambda r: r['volume_24h'], reverse=True)
        return results[:count]

    async def get_funding_rates(self, count: int = 20) -> List[dict]:
        symbols = await self.get_top_symbols(count=30)
        from app.services.market import market_service

        async def load_symbol(s: str):
            try:
                f, t = await asyncio.gather(
                    market_service.get_funding_rate(s),
                    market_service.get_ticker(s),
                )
                if f and f.get('funding_rate') is not None:
                    return {
                        'symbol': s,
                        'funding_rate': round(f['funding_rate'], 6),
                        'price': t.get('price') if t else None,
                        'change_percent': t.get('change_percent') if t else None,
                    }
            except Exception:
                pass
            return None

        loaded = await asyncio.gather(*(load_symbol(s) for s in symbols[:count]))
        results = [item for item in loaded if item is not None]
        results.sort(key=lambda r: abs(r['funding_rate']), reverse=True)
        return results

    async def get_open_interest_data(self, count: int = 20) -> List[dict]:
        symbols = await self.get_top_symbols(count=30)
        from app.services.market import market_service

        async def load_symbol(s: str):
            try:
                oi, t = await asyncio.gather(
                    market_service.get_open_interest(s),
                    market_service.get_ticker(s),
                )
                if oi and oi.get('open_interest') is not None:
                    oi_value = oi['open_interest']
                    market_price = t.get('price', 0) if t else 0
                    oi_usd = oi.get('open_interest_value')
                    if oi_usd is None and market_price:
                        oi_usd = oi_value * market_price
                    return {
                        'symbol': s,
                        'open_interest': round(oi_value, 2),
                        'open_interest_usd': round(oi_usd, 0) if oi_usd is not None else None,
                        'price': market_price,
                        'change_percent': t.get('change_percent') if t else None,
                    }
            except Exception:
                pass
            return None

        loaded = await asyncio.gather(*(load_symbol(s) for s in symbols[:count]))
        results = [item for item in loaded if item is not None]
        results.sort(key=lambda r: r['open_interest_usd'], reverse=True)
        return results

    async def get_trending_coins(self, count: int = 10) -> List[dict]:
        gainers = await self.get_market_gainers(count * 2)
        volumes = await self.get_volume_leaders(count * 2)

        trending_map = {}
        for g in gainers:
            trending_map[g['symbol']] = {'score': g['change_percent'] * 0.6, 'price': g['price'], 'change': g['change_percent']}
        for v in volumes:
            if v['symbol'] in trending_map:
                trending_map[v['symbol']]['score'] += v['volume_24h'] * 0.4
            else:
                trending_map[v['symbol']] = {'score': v['volume_24h'] * 0.4, 'price': v['price'], 'change': v.get('change_percent')}

        trending = [{'symbol': s, **d} for s, d in trending_map.items()]
        trending.sort(key=lambda r: r['score'], reverse=True)
        return [{k: v for k, v in t.items() if k != 'score'} for t in trending[:count]]


market_coverage = MarketCoverageService()
