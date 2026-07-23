from app.services.indicators import indicator_service
from app.services.ai_analysis import ai_engine
from app.core.logging import logger

class SignalService:
    def __init__(self):
        self.logger = logger

    async def generate_signals(self, symbol: str, data: list, timeframe: str = '1h') -> dict:
        if len(data) < 50:
            return {'symbol': symbol, 'signals': [], 'confidence': {'overall': 0, 'recommendation': 'neutral'}}

        ai_result = await ai_engine.analyze(symbol, data, timeframe)
        signals = []

        rsi = indicator_service.rsi(data)
        macd = indicator_service.macd(data)
        bb = indicator_service.bollinger(data)
        supertrend_data = indicator_service.supertrend(data)
        pivot = indicator_service.pivot_points(data)

        current_price = data[-1]['close']

        if ai_result['prediction'] == 'long' and ai_result['confidence'] > 60:
            sig = self._create_signal(symbol, timeframe, 'long', current_price, ai_result)
            signals.append(sig)

        if ai_result['prediction'] == 'short' and ai_result['confidence'] > 60:
            sig = self._create_signal(symbol, timeframe, 'short', current_price, ai_result)
            signals.append(sig)

        if rsi.get('oversold') and macd.get('current_histogram', 0) > 0:
            signals.append(self._create_indicator_signal(
                symbol, 'rsi_macd', 'long', current_price, ai_result,
                f"RSI oversold ({rsi['current']:.0f}) + MACD bullish"
            ))

        if rsi.get('overbought') and macd.get('current_histogram', 0) < 0:
            signals.append(self._create_indicator_signal(
                symbol, 'rsi_macd', 'short', current_price, ai_result,
                f"RSI overbought ({rsi['current']:.0f}) + MACD bearish"
            ))

        if supertrend_data.get('current_direction') == 'uptrend' and rsi['current'] < 70:
            signals.append(self._create_indicator_signal(
                symbol, 'supertrend', 'long', current_price, ai_result,
                "Supertrend uptrend"
            ))
        elif supertrend_data.get('current_direction') == 'downtrend' and rsi['current'] > 30:
            signals.append(self._create_indicator_signal(
                symbol, 'supertrend', 'short', current_price, ai_result,
                "Supertrend downtrend"
            ))

        signals = sorted(signals, key=lambda s: s['confidence'], reverse=True)[:5]

        buy_conf = sum(s['confidence'] for s in signals if s['direction'] == 'long') / 100
        sell_conf = sum(s['confidence'] for s in signals if s['direction'] == 'short') / 100

        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'current_price': current_price,
            'signals': signals,
            'ai_analysis': ai_result,
            'confidence': {
                'buy': min(round(buy_conf, 1), 100),
                'sell': min(round(sell_conf, 1), 100),
                'overall': ai_result['confidence'],
                'recommendation': 'long' if buy_conf > sell_conf + 10 else ('short' if sell_conf > buy_conf + 10 else 'neutral'),
            },
        }

    def _create_signal(self, symbol: str, timeframe: str, direction: str, price: float, ai: dict) -> dict:
        stop_percent = 0.02 if ai['risk_level'] == 'low' else 0.03 if ai['risk_level'] == 'medium' else 0.05
        rr = 2.0 if ai['risk_level'] == 'low' else 1.5 if ai['risk_level'] == 'medium' else 1.0

        if direction == 'long':
            sl = round(price * (1 - stop_percent), 4)
            tp1 = round(price * (1 + stop_percent * rr), 4)
            tp2 = round(price * (1 + stop_percent * rr * 1.5), 4)
            tp3 = round(price * (1 + stop_percent * rr * 2), 4)
        else:
            sl = round(price * (1 + stop_percent), 4)
            tp1 = round(price * (1 - stop_percent * rr), 4)
            tp2 = round(price * (1 - stop_percent * rr * 1.5), 4)
            tp3 = round(price * (1 - stop_percent * rr * 2), 4)

        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'direction': direction,
            'confidence': ai['confidence'],
            'risk_score': ai['confidence'] * 0.3 if ai['risk_level'] == 'high' else ai['confidence'] * 0.2,
            'probability': ai['long_probability'] if direction == 'long' else ai['short_probability'],
            'entry_price': price,
            'stop_loss': sl,
            'take_profit_1': tp1,
            'take_profit_2': tp2,
            'take_profit_3': tp3,
            'risk_reward': round(rr, 2),
            'leverage': 3 if ai['risk_level'] == 'low' else 2 if ai['risk_level'] == 'medium' else 1,
            'reason': ai['summary'],
            'ai_summary': f"AI Confidence: {ai['confidence']}% | Risk: {ai['risk_level'].upper()} | "
                          f"Trend: {ai['scores'].get('trend', 0)*100:.0f}% | "
                          f"Momentum: {ai['scores'].get('momentum', 0)*100:.0f}%",
            'signal_type': 'ai_multi',
        }

    def _create_indicator_signal(self, symbol: str, sig_type: str, direction: str, price: float, ai: dict, reason: str) -> dict:
        return {
            'symbol': symbol,
            'timeframe': '1h',
            'direction': direction,
            'confidence': ai['confidence'] * 0.8,
            'risk_score': ai['confidence'] * 0.15,
            'probability': ai['long_probability'] if direction == 'long' else ai['short_probability'],
            'entry_price': price,
            'stop_loss': round(price * 0.98, 4),
            'take_profit_1': round(price * 1.03, 4),
            'take_profit_2': round(price * 1.05, 4),
            'take_profit_3': round(price * 1.08, 4),
            'risk_reward': 2.0,
            'leverage': 2,
            'reason': reason,
            'ai_summary': f"AI Score: {ai['confidence']}%",
            'signal_type': sig_type,
        }

signal_service = SignalService()
