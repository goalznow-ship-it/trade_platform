import ccxt
import asyncio
from app.core.cache import cache_get, cache_set
from app.core.logging import logger

class MarketService:
    def __init__(self):
        self.logger = logger
        self._exchange_semaphore = asyncio.Semaphore(2)
        self.exchanges = {
            'binance': ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            }),
            'bybit': ccxt.bybit({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            }),
            'coinbase': ccxt.coinbase(),
        }

    async def _call_exchange(self, method, *args, **kwargs):
        async with self._exchange_semaphore:
            return await asyncio.wait_for(
                asyncio.to_thread(method, *args, **kwargs),
                timeout=12,
            )

    def _resolve_exchange(self, symbol: str) -> str:
        """Auto-detect exchange for a symbol. SKH/SKHY -> bybit, rest -> binance."""
        base = symbol.split("/")[0] if "/" in symbol else symbol
        bybit_symbols = {"SKH", "SKHY"}
        return "bybit" if base in bybit_symbols else "binance"

    async def get_ohlcv(self, symbol: str, exchange: str = None, timeframe: str = '1h', limit: int = 200) -> list:
        exchange = exchange or self._resolve_exchange(symbol)
        cache_key = f"ohlcv:{exchange}:{symbol}:{timeframe}:{limit}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            ex = self.exchanges.get(exchange, self.exchanges['binance'])
            ohlcv = await self._call_exchange(
                ex.fetch_ohlcv, symbol, timeframe, limit=limit,
            )
            result = [
                {
                    'time': o[0] // 1000,
                    'open': o[1],
                    'high': o[2],
                    'low': o[3],
                    'close': o[4],
                    'volume': o[5]
                }
                for o in ohlcv
            ]
            await cache_set(cache_key, result, ttl=30)
            return result
        except Exception as e:
            self.logger.error(f"OHLCV fetch failed for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str, exchange: str = None) -> dict:
        exchange = exchange or self._resolve_exchange(symbol)
        cache_key = f"ticker:{exchange}:{symbol}"
        cached = await cache_get(cache_key)
        if isinstance(cached, dict):
            return cached
        try:
            ex = self.exchanges.get(exchange, self.exchanges['binance'])
            t = await self._call_exchange(ex.fetch_ticker, symbol)
            result = {
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
            }
            await cache_set(cache_key, result, ttl=3)
            return result
        except Exception:
            return {}

    async def get_orderbook(self, symbol: str, exchange: str = None, limit: int = 50) -> dict:
        exchange = exchange or self._resolve_exchange(symbol)
        cache_key = f"orderbook:{exchange}:{symbol}:{limit}"
        cached = await cache_get(cache_key)
        if isinstance(cached, dict):
            return cached
        try:
            ex = self.exchanges.get(exchange, self.exchanges['binance'])
            ob = await self._call_exchange(ex.fetch_order_book, symbol, limit)
            result = {
                'bids': ob['bids'][:10],
                'asks': ob['asks'][:10],
                'timestamp': ob['timestamp'],
            }
            await cache_set(cache_key, result, ttl=1)
            return result
        except Exception:
            return {}

    async def get_trades(self, symbol: str, exchange: str = 'binance', limit: int = 100) -> list:
        cache_key = f"trades:{exchange}:{symbol}:{limit}"
        cached = await cache_get(cache_key)
        if isinstance(cached, list):
            return cached
        try:
            ex = self.exchanges.get(exchange, self.exchanges['binance'])
            trades = await self._call_exchange(ex.fetch_trades, symbol, limit=limit)
            result = [
                {
                    'price': trade.get('price'),
                    'amount': trade.get('amount'),
                    'side': trade.get('side'),
                    'timestamp': trade.get('timestamp'),
                    'aggressive': trade.get('takerOrMaker') == 'taker',
                }
                for trade in trades
                if trade.get('price') is not None and trade.get('amount') is not None
            ]
            await cache_set(cache_key, result, ttl=1)
            return result
        except Exception:
            return []

    async def get_funding_rate(self, symbol: str, exchange: str = None) -> dict:
        exchange = exchange or self._resolve_exchange(symbol)
        cache_key = f"funding:{exchange}:{symbol}"
        cached = await cache_get(cache_key)
        if isinstance(cached, dict):
            return cached
        try:
            ex = self.exchanges.get(exchange, self.exchanges['binance'])
            funding = await self._call_exchange(ex.fetch_funding_rate, symbol)
            result = {
                'symbol': funding['symbol'],
                'funding_rate': funding['fundingRate'],
                'funding_time': (
                    funding.get('fundingTimestamp')
                    or funding.get('nextFundingTimestamp')
                    or funding.get('timestamp')
                ),
            }
            await cache_set(cache_key, result, ttl=15)
            return result
        except Exception:
            return {}

    async def get_open_interest(self, symbol: str, exchange: str = None) -> dict:
        exchange = exchange or self._resolve_exchange(symbol)
        cache_key = f"open-interest:{exchange}:{symbol}"
        cached = await cache_get(cache_key)
        if isinstance(cached, dict):
            return cached
        try:
            ex = self.exchanges.get(exchange, self.exchanges['binance'])
            oi = await self._call_exchange(ex.fetch_open_interest, symbol)
            result = {
                'symbol': oi['symbol'],
                'open_interest': (
                    oi.get('openInterestAmount')
                    or oi.get('baseVolume')
                    or oi.get('openInterest')
                ),
                'open_interest_value': oi.get('openInterestValue'),
            }
            await cache_set(cache_key, result, ttl=10)
            return result
        except Exception:
            return {}

    async def get_market_overview(self) -> dict:
        cache_key = "market:overview"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            from app.services.market_coverage import market_coverage
            symbols = await market_coverage.get_top_symbols(10)
        except Exception:
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']

        tickers = await asyncio.gather(*[self.get_ticker(s) for s in symbols])
        btc = tickers[0] if tickers else {}

        total_volume = sum(t.get('volume_24h', 0) or 0 for t in tickers if t)

        overview = {
            'btc_price': btc.get('price'),
            'btc_change': btc.get('change_percent'),
            'eth_price': tickers[1].get('price') if len(tickers) > 1 else None,
            'total_market_cap': None,
            'total_volume_24h': total_volume if total_volume > 0 else None,
            'btc_dominance': None,
            'tickers': {s: t for s, t in zip(symbols, tickers)},
            'symbols_count': len(symbols),
        }
        await cache_set(cache_key, overview, ttl=15)
        return overview

    async def search_symbols(self, query: str) -> list:
        cache_key = f"search:{query}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        results = []
        for exchange_name in ['binance', 'bybit']:
            try:
                ex = self.exchanges[exchange_name]
                markets = await self._call_exchange(ex.load_markets)
                for s in markets:
                    if query.upper() in s and '/USDT' in s:
                        results.append({
                            'symbol': s,
                            'exchange': exchange_name,
                            'type': 'crypto'
                        })
                        if len(results) >= 20:
                            break
            except Exception:
                continue
            if len(results) >= 20:
                break

        await cache_set(cache_key, results, ttl=300)
        return results


market_service = MarketService()
