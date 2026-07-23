import pytest
from app.services.backtest import backtest_service


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


class TestBacktest:
    @pytest.mark.asyncio
    async def test_run_backtest_basic(self):
        data = _make_candles(200)
        result = await backtest_service.run_backtest("BTC/USDT", data)
        assert "total_trades" in result
        assert "win_rate" in result
        assert "total_return" in result
        assert "final_balance" in result

    @pytest.mark.asyncio
    async def test_run_backtest_insufficient_data(self):
        data = _make_candles(10)
        result = await backtest_service.run_backtest("BTC/USDT", data)
        assert "error" in result
        assert result["error"] == "Insufficient data"

    @pytest.mark.asyncio
    async def test_backtest_with_custom_params(self):
        data = _make_candles(200)
        result = await backtest_service.run_backtest(
            "BTC/USDT", data, initial_balance=50000, leverage=2, risk_per_trade=0.03
        )
        assert result["total_trades"] >= 0
        assert result["final_balance"] > 0

    @pytest.mark.asyncio
    async def test_backtest_metrics_valid(self):
        data = _make_candles(200)
        result = await backtest_service.run_backtest("BTC/USDT", data)
        if "error" not in result:
            assert 0 <= result["win_rate"] <= 100
            assert result["profit_factor"] >= 0
            assert result["sharpe_ratio"] is not None

    @pytest.mark.asyncio
    async def test_backtest_equity_curve(self):
        data = _make_candles(200)
        result = await backtest_service.run_backtest("BTC/USDT", data)
        if "error" not in result:
            assert len(result["equity_curve"]) > 0
            assert result["equity_curve"][0] > 0
