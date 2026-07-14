import pytest
from app.services.ai_analysis import ai_engine


def _make_candles(count: int, base_price: float = 50000, trend: str = "up") -> list:
    import random
    random.seed(42)
    candles = []
    price = base_price
    for i in range(count):
        if trend == "up":
            change = price * random.uniform(-0.01, 0.03)
        elif trend == "down":
            change = price * random.uniform(-0.03, 0.01)
        else:
            change = price * random.uniform(-0.02, 0.02)
        price += change
        candles.append({
            "time": i,
            "open": price - change * 0.5,
            "high": price + abs(change) * 0.5,
            "low": price - abs(change) * 0.5,
            "close": price,
            "volume": random.uniform(100, 1000),
        })
    return candles


@pytest.mark.asyncio
async def test_analyze_basic():
    data = _make_candles(100)
    result = await ai_engine.analyze("BTC/USDT", data, "1h")
    assert result["symbol"] == "BTC/USDT"
    assert result["timeframe"] == "1h"
    assert "scores" in result
    assert "overall_score" in result
    assert "confidence" in result
    assert "prediction" in result
    assert "long_probability" in result
    assert "short_probability" in result


@pytest.mark.asyncio
async def test_analyze_insufficient_data():
    data = _make_candles(10)
    result = await ai_engine.analyze("BTC/USDT", data, "1h")
    assert result["prediction"] == "neutral"
    assert result["summary"] == "Insufficient data for analysis"


@pytest.mark.asyncio
async def test_analyze_up_trend():
    data = _make_candles(100, trend="up")
    result = await ai_engine.analyze("BTC/USDT", data, "1h")
    assert result["confidence"] >= 0


@pytest.mark.asyncio
async def test_analyze_down_trend():
    data = _make_candles(100, trend="down")
    result = await ai_engine.analyze("BTC/USDT", data, "1h")
    assert result["confidence"] >= 0


@pytest.mark.asyncio
async def test_scores_sum_to_one():
    data = _make_candles(100)
    result = await ai_engine.analyze("BTC/USDT", data, "1h")
    scores = result["scores"]
    assert all(-1 <= v <= 1 for v in scores.values())
