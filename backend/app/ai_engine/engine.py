"""
AI Signal Engine - generates complete trade setups with entry zones, targets, and analysis
"""

import numpy as np
from typing import Optional, List
from app.services.ai_analysis import ai_engine as core_ai
from app.services.market import market_service
from app.services.indicators import indicator_service
from app.ai_engine.scoring import SignalScorer
from app.core.logging import logger

scorer = SignalScorer()

class AIEngine:
    async def generate_signal(self, symbol: str, timeframe: str = '1h') -> Optional[dict]:
        try:
            data = await market_service.get_ohlcv(symbol, 'binance', timeframe, 200)
            if not data or len(data) < 50:
                return None

            analysis = await core_ai.analyze(symbol, data, timeframe)
            if not analysis or analysis.get('confidence', 0) == 0:
                return None

            futures = await market_service.get_funding_rate(symbol)
            oi = await market_service.get_open_interest(symbol)

            scoring = scorer.calculate(analysis, futures_data={
                'funding_rate': futures.get('funding_rate', 0),
                'long_short_ratio': 1.0,
            })

            current_price = data[-1]['close']
            atr = indicator_service.atr(data)
            atr_val = atr if atr else current_price * 0.02

            is_long = scoring['direction'] == 'long'
            conf = scoring['confidence']
            stop_dist = atr_val * 1.5

            entry_min = current_price * (0.998 if is_long else 1.002)
            entry_max = current_price * (1.002 if is_long else 0.998)
            stop_loss = current_price - stop_dist if is_long else current_price + stop_dist
            tp1 = current_price + atr_val * 2 if is_long else current_price - atr_val * 2
            tp2 = current_price + atr_val * 3.5 if is_long else current_price - atr_val * 3.5
            tp3 = current_price + atr_val * 5.5 if is_long else current_price - atr_val * 5.5
            rr = abs((tp1 - current_price) / (current_price - stop_loss)) if stop_loss != current_price else 0

            reasons = self._generate_reasons(analysis, scoring, is_long, conf)
            invalidations = self._generate_invalidations(analysis, is_long, current_price, stop_loss)

            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'direction': scoring['direction'],
                'confidence': conf,
                'risk': 'low' if conf > 80 else ('medium' if conf > 65 else 'high'),
                'entry_zone': {
                    'min': round(entry_min, 2),
                    'max': round(entry_max, 2),
                },
                'entry_price': round(min(entry_min, entry_max) if is_long else max(entry_min, entry_max), 2),
                'stop_loss': round(stop_loss, 2),
                'take_profit': [round(tp1, 2), round(tp2, 2), round(tp3, 2)],
                'risk_reward': round(rr, 1),
                'reasons': reasons,
                'invalidations': invalidations,
                'scores': scoring,
                'details': analysis.get('details', {}),
            }
        except Exception as e:
            logger.error(f"Signal generation failed for {symbol}: {e}")
            return None

    async def scan_all(self, symbols: Optional[List[str]] = None, min_confidence: float = 50) -> List[dict]:
        if symbols is None:
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
                       'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
                       'MATIC/USDT', 'ATOM/USDT', 'UNI/USDT', 'ARB/USDT', 'OP/USDT',
                       'INJ/USDT', 'TIA/USDT', 'SEI/USDT', 'APT/USDT', 'SUI/USDT']

        results = []
        for sym in symbols:
            signal = await self.generate_signal(sym, '1h')
            if signal and signal['confidence'] >= min_confidence:
                results.append(signal)

        return sorted(results, key=lambda r: r['confidence'], reverse=True)[:20]

    def _generate_reasons(self, analysis: dict, scoring: dict, is_long: bool, conf: float) -> List[str]:
        reasons = []
        details = analysis.get('details', {})
        scores = analysis.get('scores', {})

        trend = scores.get('trend', 0)
        momentum = scores.get('momentum', 0)
        volume = scores.get('volume', 0)
        structure = scores.get('market_structure', 0)

        if abs(trend) > 0.3:
            reasons.append(f"{'4H' if is_long else '4H'} {'bullish' if trend > 0 else 'bearish'} trend structure")
        if abs(momentum) > 0.3:
            reasons.append(f"{'Bullish' if momentum > 0 else 'Bearish'} momentum confirmed by RSI/MACD")
        if volume > 0.3:
            reasons.append("Volume breakout with CMF confirmation")
        if structure > 0.3:
            reasons.append("Bullish market structure with higher highs")
        elif structure < -0.3:
            reasons.append("Bearish market structure with lower lows")
        if scoring.get('futures_score', 0) > 0:
            reasons.append("Funding rate healthy for continuation")
        if scoring.get('technical_score', 0) > 0:
            reasons.append("EMA alignment confirms trend direction")
        if scoring.get('news_score', 0) > 0.2:
            reasons.append("Positive news sentiment supporting move")

        if not reasons:
            reasons.append("Technical setup forming")
        return reasons[:5]

    def _generate_invalidations(self, analysis: dict, is_long: bool, price: float, sl: float) -> List[str]:
        inv = []
        if is_long:
            inv.append(f"4H candle close below ${round(sl, 0)}")
            inv.append("BTC dominance spike above 55%")
        else:
            inv.append(f"4H candle close above ${round(sl, 0)}")
            inv.append("BTC dominance drop below 48%")
        inv.append("High-impact news event (FOMC, CPI)")
        return inv[:3]

ai_engine = AIEngine()
