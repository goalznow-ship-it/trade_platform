import numpy as np
from typing import Optional, List
from app.services.indicators import indicator_service
from app.services.market import market_service
from app.core.logging import logger

class AIAnalysisEngine:
    def __init__(self):
        self.logger = logger
        self.indicator_weights = {
            'trend': 0.20,
            'momentum': 0.20,
            'volume': 0.15,
            'volatility': 0.10,
            'market_structure': 0.15,
            'smc': 0.10,
            'news_sentiment': 0.05,
            'fear_greed': 0.05,
        }

    async def analyze(self, symbol: str, data: list, timeframe: str = '1h') -> dict:
        if len(data) < 50:
            return self._empty_result(symbol, timeframe)

        rsi = indicator_service.rsi(data)
        macd = indicator_service.macd(data)
        bb = indicator_service.bollinger(data)
        adx_data = indicator_service.adx(data)
        supertrend_data = indicator_service.supertrend(data)
        stoch_rsi = indicator_service.stochastic_rsi(data)
        pivot = indicator_service.pivot_points(data)

        trend_score = self._analyze_trend(data, macd, adx_data, supertrend_data)
        momentum_score = self._analyze_momentum(rsi, stoch_rsi, macd)
        volume_score = self._analyze_volume(data)
        volatility_score = self._analyze_volatility(bb, adx_data)
        structure_score = self._analyze_market_structure(data, pivot)
        smc_score = self._analyze_smc(data, pivot)

        scores = {
            'trend': trend_score,
            'momentum': momentum_score,
            'volume': volume_score,
            'volatility': volatility_score,
            'market_structure': structure_score,
            'smc': smc_score,
            'news_sentiment': 0.0,
            'fear_greed': 0.0,
        }

        overall = sum(scores[k] * self.indicator_weights[k] for k in scores)
        confidence = min(abs(overall) * 100, 100)
        long_prob = max(0, min(100, 50 + overall * 50))
        short_prob = 100 - long_prob

        prediction = 'long' if overall > 0.1 else ('short' if overall < -0.1 else 'neutral')
        risk_level = self._calculate_risk_level(volatility_score, volume_score)

        summary_parts = []
        if abs(trend_score) > 0.3:
            summary_parts.append(f"Trend {'bullish' if trend_score > 0 else 'bearish'} ({abs(trend_score)*100:.0f}%)")
        if abs(momentum_score) > 0.3:
            summary_parts.append(f"Momentum {'strong' if momentum_score > 0 else 'weak'} ({abs(momentum_score)*100:.0f}%)")
        if structure_score > 0.3:
            summary_parts.append("Bullish market structure")
        elif structure_score < -0.3:
            summary_parts.append("Bearish market structure")
        if smc_score > 0.3:
            summary_parts.append("SMC bullish liquidity grab")
        elif smc_score < -0.3:
            summary_parts.append("SMC bearish liquidity grab")
        if rsi.get('overbought'):
            summary_parts.append("RSI overbought - caution")
        if rsi.get('oversold'):
            summary_parts.append("RSI oversold - potential bounce")

        details = {
            'rsi': rsi['current'],
            'macd': macd['current_histogram'],
            'adx': adx_data['current_adx'],
            'supertrend': supertrend_data['current_direction'],
            'support': pivot['recent_low'],
            'resistance': pivot['recent_high'],
        }

        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'scores': scores,
            'overall_score': overall,
            'confidence': round(confidence, 1),
            'risk_level': risk_level,
            'prediction': prediction,
            'long_probability': round(long_prob, 1),
            'short_probability': round(short_prob, 1),
            'summary': '. '.join(summary_parts) if summary_parts else 'Market is neutral',
            'details': details,
        }

    def _analyze_trend(self, data: list, macd: dict, adx: dict, supertrend: dict) -> float:
        score = 0.0
        if adx.get('current_adx', 0) > 25:
            score += 0.2 if adx.get('plus_di', [0])[-1:] > adx.get('minus_di', [0])[-1:] else -0.2
        if macd.get('current_histogram', 0) > 0:
            score += 0.15
        else:
            score -= 0.15
        if supertrend.get('current_direction') == 'uptrend':
            score += 0.2
        else:
            score -= 0.2
        sma20 = indicator_service.sma(data, 20)
        sma50 = indicator_service.sma(data, 50)
        if sma20 and sma50 and len(sma20) > 0 and len(sma50) > 0:
            if sma20[-1] > sma50[-1]:
                score += 0.15
            else:
                score -= 0.15
        return max(-1, min(1, score))

    def _analyze_momentum(self, rsi: dict, stoch_rsi: dict, macd: dict) -> float:
        score = 0.0
        if rsi.get('current', 50) > 50:
            score += 0.2
        else:
            score -= 0.2
        if rsi.get('oversold'):
            score += 0.2
        elif rsi.get('overbought'):
            score -= 0.2
        if stoch_rsi.get('k') and stoch_rsi.get('d'):
            k = stoch_rsi['k'][-1] if stoch_rsi['k'] else 50
            d = stoch_rsi['d'][-1] if stoch_rsi['d'] else 50
            if k > d and k < 20:
                score += 0.2
            elif k < d and k > 80:
                score -= 0.2
        return max(-1, min(1, score))

    def _analyze_volume(self, data: list) -> float:
        if len(data) < 20:
            return 0.0
        volumes = [d['volume'] for d in data]
        avg_vol = np.mean(volumes[-20:])
        current_vol = volumes[-1] if volumes else 0
        cmf = indicator_service.cmf(data)
        score = 0.0
        if current_vol > avg_vol * 1.5:
            score += 0.3
        if cmf and cmf[-1] > 0.05:
            score += 0.2
        elif cmf and cmf[-1] < -0.05:
            score -= 0.2
        return max(-1, min(1, score))

    def _analyze_volatility(self, bb: dict, adx: dict) -> float:
        score = 0.0
        if bb.get('upper') and bb.get('lower') and len(bb['upper']) > 0:
            band_width = (bb['upper'][-1] - bb['lower'][-1]) / bb['middle'][-1] if bb['middle'] else 0
            if band_width > 0.05:
                score -= 0.2
            else:
                score += 0.1
        if adx.get('current_adx', 0) > 30:
            score += 0.2
        elif adx.get('current_adx', 0) < 20:
            score -= 0.1
        return max(-1, min(1, score))

    def _analyze_market_structure(self, data: list, pivot: dict) -> float:
        if len(data) < 10:
            return 0.0
        score = 0.0
        closes = [d['close'] for d in data]
        highs = [d['high'] for d in data]
        lows = [d['low'] for d in data]
        if closes[-1] > pivot.get('recent_high', 0):
            score += 0.3
        elif closes[-1] < pivot.get('recent_low', float('inf')):
            score -= 0.3
        if closes[-1] > np.mean(closes[-10:]):
            score += 0.15
        else:
            score -= 0.15
        if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
            score += 0.2
        elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
            score -= 0.2
        return max(-1, min(1, score))

    def _analyze_smc(self, data: list, pivot: dict) -> float:
        score = 0.0
        if len(data) < 10:
            return 0.0
        highs = [d['high'] for d in data]
        lows = [d['low'] for d in data]
        closes = [d['close'] for d in data]
        opens = [d['open'] for d in data]

        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])
        current = closes[-1]

        if current > pivot.get('recent_high', 0):
            score += 0.3
            if current > recent_high:
                score += 0.2
        elif current < pivot.get('recent_low', float('inf')):
            score -= 0.3
            if current < recent_low:
                score -= 0.2

        fvg_detected = False
        for i in range(-5, -1):
            if lows[i] > highs[i+1]:
                fvg_detected = True
                if current > lows[i]:
                    score += 0.2
                break
            if highs[i] < lows[i+1]:
                fvg_detected = True
                if current < highs[i]:
                    score -= 0.2
                break

        if not fvg_detected:
            order_block = False
            for i in range(-5, -1):
                if closes[i] > opens[i] and lows[i] < lows[i+1] and closes[i+1] < closes[i]:
                    order_block = True
                    score += 0.1
                    break

        return max(-1, min(1, score))

    def _calculate_risk_level(self, volatility: float, volume: float) -> str:
        risk = abs(volatility) * 0.5 + abs(volume) * 0.5
        if risk > 0.5:
            return 'high'
        elif risk > 0.2:
            return 'medium'
        return 'low'

    def _empty_result(self, symbol: str, timeframe: str) -> dict:
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'scores': {},
            'overall_score': 0,
            'confidence': 0,
            'risk_level': 'unknown',
            'prediction': 'neutral',
            'long_probability': 50,
            'short_probability': 50,
            'summary': 'Insufficient data for analysis',
            'details': {},
        }

ai_engine = AIAnalysisEngine()
