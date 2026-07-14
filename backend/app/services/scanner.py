import asyncio
from typing import List
from app.services.market import market_service
from app.services.ai_analysis import ai_engine
from app.core.logging import logger

class ScannerService:
    def __init__(self):
        self.logger = logger

    async def scan_market(self, symbols: List[str] = None, timeframe: str = '1h') -> list:
        if symbols is None:
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT',
                       'XRP/USDT', 'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT',
                       'DOT/USDT', 'LINK/USDT', 'MATIC/USDT', 'ATOM/USDT',
                       'UNI/USDT', 'ARB/USDT', 'OP/USDT']

        results = []
        for symbol in symbols:
            try:
                data = await market_service.get_ohlcv(symbol, 'binance', timeframe, 100)
                if data and len(data) >= 50:
                    analysis = await ai_engine.analyze(symbol, data, timeframe)
                    results.append(analysis)
            except Exception:
                continue
            await asyncio.sleep(0.1)

        results.sort(key=lambda r: r.get('confidence', 0), reverse=True)
        return results

    async def scan_top_signals(self, min_confidence: float = 70) -> list:
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
                   'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
                   'MATIC/USDT', 'ATOM/USDT', 'UNI/USDT', 'ARB/USDT', 'OP/USDT',
                   'INJ/USDT', 'TIA/USDT', 'SEI/USDT', 'APT/USDT', 'SUI/USDT']
        results = []

        for symbol in symbols:
            try:
                data = await market_service.get_ohlcv(symbol, 'binance', '1h', 100)
                if data and len(data) >= 50:
                    analysis = await ai_engine.analyze(symbol, data, '1h')
                    if analysis['confidence'] >= min_confidence:
                        results.append(analysis)
            except Exception:
                continue
            await asyncio.sleep(0.1)

        return sorted(results, key=lambda r: r['confidence'], reverse=True)[:20]

scanner_service = ScannerService()
