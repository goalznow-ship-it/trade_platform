import pytest
from app.services.signals import signal_service


def _make_candles(count: int) -> list:
    import random
    random.seed(42)
    candles = []
    price = 50000
    for i in range(count):
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
async def test_generate_signals():
    data = _make_candles(100)
    result = await signal_service.generate_signals("BTC/USDT", data, "1h")
    assert result["symbol"] == "BTC/USDT"
    assert "signals" in result
    assert "confidence" in result
    assert "ai_analysis" in result


@pytest.mark.asyncio
async def test_generate_signals_insufficient_data():
    data = _make_candles(10)
    result = await signal_service.generate_signals("BTC/USDT", data, "1h")
    assert result["confidence"]["overall"] == 0
    assert result["confidence"]["recommendation"] == "neutral"


@pytest.mark.asyncio
async def test_signal_contains_required_fields():
    data = _make_candles(100)
    result = await signal_service.generate_signals("BTC/USDT", data, "1h")
    if result["signals"]:
        signal = result["signals"][0]
        assert "symbol" in signal
        assert "direction" in signal
        assert "entry_price" in signal
        assert "stop_loss" in signal
        assert "take_profit_1" in signal
        assert "risk_reward" in signal
        assert "confidence" in signal
