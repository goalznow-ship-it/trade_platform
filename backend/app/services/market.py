import ccxt
import yfinance as yf
import pandas as pd
from typing import Optional, List
from datetime import datetime, timezone
import asyncio
from app.core.cache import cache_get, cache_set
from app.core.logging import logger

class MarketService:
    def __init__(self):
        self.logger = logger
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

    async def get_ohlcv(self, symbol: str, exchange: str = 'binance', timeframe: str = '1h', limit: int = 200) -> list:
        cache_key = f"ohlcv:{exchange}:{symbol}:{timeframe}:{limit}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            ex = self.exchanges.get(exchange, self.exchanges['binance'])
            ohlcv = ex.fetch_ohlcv(symbol, timeframe, limit=limit)
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

    async def get_ticker(self, symbol: str, exchange: str = 'binance') -> dict:
        try:
            ex = self.exchanges.get(exchange, self.exchanges['binance'])
            t = ex.fetch_ticker(symbol)
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
            }
        except Exception as e:
            return {}

    async def get_orderbook(self, symbol: str, exchange: str = 'binance', limit: int = 50) -> dict:
        try:
            ex = self.exchanges.get(exchange, self.exchanges['binance'])
            ob = ex.fetch_order_book(symbol, limit)
            return {
                'bids': ob['bids'][:10],
                'asks': ob['asks'][:10],
                'timestamp': ob['timestamp'],
            }
        except Exception:
            return {}

    async def get_funding_rate(self, symbol: str, exchange: str = 'binance') -> dict:
        try:
            ex = self.exchanges.get(exchange, self.exchanges['binance'])
            funding = ex.fetch_funding_rate(symbol)
            return {
                'symbol': funding['symbol'],
                'funding_rate': funding['fundingRate'],
                'funding_time': funding['fundingTime'],
            }
        except Exception:
            return {}

    async def get_open_interest(self, symbol: str, exchange: str = 'binance') -> dict:
        try:
            ex = self.exchanges.get(exchange, self.exchanges['binance'])
            oi = ex.fetch_open_interest(symbol)
            return {
                'symbol': oi['symbol'],
                'open_interest': oi['openInterest'],
            }
        except Exception:
            return {}

    async def get_market_overview(self) -> dict:
        cache_key = "market:overview"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
        tickers = await asyncio.gather(*[self.get_ticker(s) for s in symbols])
        btc = tickers[0] if tickers else {}

        overview = {
            'btc_price': btc.get('price'),
            'btc_change': btc.get('change_percent'),
            'eth_price': tickers[1].get('price') if len(tickers) > 1 else None,
            'total_market_cap': None,
            'total_volume_24h': None,
            'btc_dominance': None,
            'tickers': {s: t for s, t in zip(symbols, tickers)},
        }
        await cache_set(cache_key, overview, ttl=15)
        return overview

    async def search_symbols(self, query: str) -> list:
        cache_key = f"search:{query}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        results = []
        try:
            markets = self.exchanges['binance'].load_markets()
            for s in markets:
                if query.upper() in s and '/USDT' in s:
                    results.append({
                        'symbol': s,
                        'exchange': 'binance',
                        'type': 'crypto'
                    })
                    if len(results) >= 20:
                        break
        except Exception:
            pass

        await cache_set(cache_key, results, ttl=300)
        return results


market_service = MarketService()

