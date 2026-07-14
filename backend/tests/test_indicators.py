import pytest
import math
from app.services.indicators import indicator_service


def _make_candles(count: int, base_price: float = 50000) -> list:
    import random
    random.seed(42)
    candles = []
    price = base_price
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


class TestSMA:
    def test_sma_basic(self):
        data = [{"close": float(i)} for i in range(1, 21)]
        result = indicator_service.sma(data, period=5)
        assert len(result) > 0
        assert all(isinstance(v, float) for v in result)

    def test_sma_insufficient_data(self):
        data = [{"close": 100.0}]
        result = indicator_service.sma(data, period=20)
        assert result == []


class TestRSI:
    def test_rsi_basic(self):
        data = _make_candles(100)
        result = indicator_service.rsi(data)
        assert "current" in result
        assert "values" in result
        assert 0 <= result["current"] <= 100

    def test_rsi_oversold(self):
        candles = _make_candles(100, 50000)
        result = indicator_service.rsi(candles)
        assert "oversold" in result
        assert "overbought" in result


class TestMACD:
    def test_macd_basic(self):
        data = _make_candles(100)
        result = indicator_service.macd(data)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result
        assert "current_macd" in result

    def test_macd_requires_data(self):
        data = _make_candles(10)
        result = indicator_service.macd(data)
        assert isinstance(result["current_macd"], float)


class TestBollinger:
    def test_bollinger_basic(self):
        data = _make_candles(100)
        result = indicator_service.bollinger(data)
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result
        assert len(result["upper"]) > 0

    def test_bollinger_order(self):
        data = _make_candles(100)
        result = indicator_service.bollinger(data)
        assert result["upper"][-1] >= result["middle"][-1] >= result["lower"][-1]


class TestADX:
    def test_adx_basic(self):
        data = _make_candles(100)
        result = indicator_service.adx(data)
        assert "adx" in result
        assert "current_adx" in result
        assert 0 <= result["current_adx"] <= 100


class TestSuperTrend:
    def test_supertrend_basic(self):
        data = _make_candles(100)
        result = indicator_service.supertrend(data)
        assert "supertrend" in result
        assert "current_direction" in result
        assert result["current_direction"] in ("uptrend", "downtrend")
