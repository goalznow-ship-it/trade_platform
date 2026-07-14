"""
Market Coverage Service
- Maintains top 30 futures coins by Binance USDT perpetual volume
- Auto-updates weekly from Binance volume ranking
- Cached symbols with fallback
"""
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from app.core.cache import cache_get, cache_set
from app.core.logging import logger

TOP_30_FALLBACK = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "SUI/USDT", "LINK/USDT", "AVAX/USDT",
    "DOT/USDT", "LTC/USDT", "TRX/USDT", "APT/USDT", "ATOM/USDT",
    "ARB/USDT", "OP/USDT", "NEAR/USDT", "FIL/USDT", "AAVE/USDT",
    "INJ/USDT", "SEI/USDT", "TIA/USDT", "WIF/USDT", "PEPE/USDT",
    "ETC/USDT", "BCH/USDT", "UNI/USDT", "MKR/USDT", "FET/USDT",
]


class MarketCoverageService:
    def __init__(self):
        self._cache_key = "market:top30"
        self._cache_key_timestamp = "market:top30:updated"
        self._update_interval_hours = 168  # 7 days
        self._fallback = TOP_30_FALLBACK
        self._logger = logger

    async def get_top_symbols(self, count: int = 30, force_refresh: bool = False) -> List[str]:
        if force_refresh:
            return await self._fetch_and_cache()

        cached = await cache_get(self._cache_key)
        if cached is not None and isinstance(cached, list) and len(cached) >= count:
            return cached[:count]

        return await self._fetch_and_cache()

    async def _fetch_and_cache(self) -> List[str]:
        try:
            symbols = await self._fetch_top_from_exchange()
            if symbols and len(symbols) >= 20:
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
            import ccxt
            ex = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            markets = ex.load_markets()
            tickers = ex.fetch_tickers()

            usdt_perps = []
            for symbol, ticker in tickers.items():
                if symbol.endswith("/USDT") and symbol in markets:
                    m = markets[symbol]
                    if m.get('future', False) or m.get('linear', False):
                        quote_volume = ticker.get('quoteVolume', 0) or 0
                        usdt_perps.append((symbol, quote_volume))

            usdt_perps.sort(key=lambda x: x[1], reverse=True)
            top = [s[0] for s in usdt_perps[:40]]

            self._logger.info(f"Fetched {len(top)} symbols from Binance volume ranking")
            return top if top else self._fallback
        except Exception as e:
            self._logger.error(f"Exchange fetch failed: {e}")
            return self._fallback

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

        results = []
        for s in symbols[:count]:
            try:
                f = await market_service.get_funding_rate(s)
                if f and f.get('funding_rate') is not None:
                    t = await market_service.get_ticker(s)
                    results.append({
                        'symbol': s,
                        'funding_rate': round(f['funding_rate'], 6),
                        'price': t.get('price') if t else None,
                        'change_percent': t.get('change_percent') if t else None,
                    })
            except Exception:
                continue

        results.sort(key=lambda r: abs(r['funding_rate']), reverse=True)
        return results

    async def get_open_interest_data(self, count: int = 20) -> List[dict]:
        symbols = await self.get_top_symbols(count=30)
        from app.services.market import market_service

        results = []
        for s in symbols[:count]:
            try:
                oi = await market_service.get_open_interest(s)
                if oi and oi.get('open_interest') is not None:
                    t = await market_service.get_ticker(s)
                    oi_value = oi['open_interest']
                    market_price = t.get('price', 0) if t else 0
                    results.append({
                        'symbol': s,
                        'open_interest': round(oi_value, 2),
                        'open_interest_usd': round(oi_value * market_price, 0) if market_price else 0,
                        'price': market_price,
                        'change_percent': t.get('change_percent') if t else None,
                    })
            except Exception:
                continue

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
