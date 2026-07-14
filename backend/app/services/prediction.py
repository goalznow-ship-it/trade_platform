import random
import math
from datetime import datetime, timedelta
from typing import Optional
from app.services.ai_analysis import ai_engine
from app.services.market import market_service


class PricePredictionEngine:
    async def predict(self, symbol: str, timeframe: str = "4h", exchange: str = "binance") -> dict:
        data = await market_service.get_ohlcv(symbol, exchange, timeframe, 200)
        if not data or len(data) < 50:
            return self._empty_prediction(symbol, timeframe)

        current_price = data[-1]["close"]
        analysis = await ai_engine.analyze(symbol, data, timeframe)

        conf = analysis.get("confidence", 50)
        long_prob = analysis.get("long_probability", 50)
        short_prob = analysis.get("short_probability", 50)

        scores = analysis.get("scores", {})
        overall = analysis.get("overall_score", 0)

        if overall > 0.15:
            prediction = "bullish"
            bullish_prob = long_prob
            bearish_prob = short_prob
        elif overall < -0.15:
            prediction = "bearish"
            bullish_prob = short_prob
            bearish_prob = long_prob
        else:
            prediction = "neutral"
            bullish_prob = 50
            bearish_prob = 50

        # Expected move based on ATR-like volatility estimation
        closes = [d["close"] for d in data[-20:]]
        avg_range = sum(abs(data[i]["high"] - data[i]["low"]) for i in range(-20, 0)) / 20
        expected_move_pct = (avg_range / current_price) * 100 * (0.5 + abs(overall) * 0.5)

        if conf < 50:
            expected_move_pct *= 0.5

        risk_level = analysis.get("risk_level", "medium")
        target_price = current_price * (1 + expected_move_pct / 100 * (1 if prediction == "bullish" else -1 if prediction == "bearish" else 0))

        entry_low = current_price * 0.995
        entry_high = current_price * 1.005
        sl = current_price * (0.97 if prediction == "bullish" else 1.03)
        tp1 = current_price * (1.03 if prediction == "bullish" else 0.97)
        tp2 = current_price * (1.06 if prediction == "bullish" else 0.94)
        rr = abs((tp1 - current_price) / (current_price - sl)) if sl != current_price else 1.0

        factors = []
        for key, val in scores.items():
            if abs(val) > 0.1:
                factors.append({"factor": key.replace("_", " ").title(), "score": round(val, 2), "direction": "bullish" if val > 0 else "bearish"})

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": round(current_price, 2),
            "prediction": prediction,
            "confidence": round(conf, 1),
            "bullish_probability": round(bullish_prob, 1),
            "bearish_probability": round(bearish_prob, 1),
            "expected_move_pct": round(expected_move_pct, 2),
            "expected_target_price": round(target_price, 2),
            "entry_zone": {"low": round(entry_low, 2), "high": round(entry_high, 2)},
            "stop_loss": round(sl, 2),
            "take_profit_1": round(tp1, 2),
            "take_profit_2": round(tp2, 2),
            "risk_level": risk_level,
            "risk_reward_ratio": round(rr, 2),
            "factors": factors[:6],
            "summary": (
                f"{'Bullish' if prediction == 'bullish' else 'Bearish' if prediction == 'bearish' else 'Neutral'} "
                f"bias with {conf}% confidence. "
                f"Expected {'move' if prediction != 'neutral' else 'range'}: "
                f"{'+' if expected_move_pct > 0 else ''}{expected_move_pct:.1f}%. "
                f"Risk level: {risk_level.upper()}."
            ),
        }

    def _empty_prediction(self, symbol: str, timeframe: str) -> dict:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": 0,
            "prediction": "neutral",
            "confidence": 0,
            "bullish_probability": 50,
            "bearish_probability": 50,
            "expected_move_pct": 0,
            "expected_target_price": 0,
            "entry_zone": {"low": 0, "high": 0},
            "stop_loss": 0,
            "take_profit_1": 0,
            "take_profit_2": 0,
            "risk_level": "unknown",
            "risk_reward_ratio": 0,
            "factors": [],
            "summary": "Insufficient data for prediction",
        }


prediction_engine = PricePredictionEngine()
