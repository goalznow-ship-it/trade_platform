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
    def test_position_executes_at_next_candle_open(self, monkeypatch):
        data = _make_candles(130)
        signal_close = data[100]["close"]
        next_open = data[101]["open"]

        def fixed_signal(*args, **kwargs):
            return {
                "action": 1,
                "direction": "long",
                "entry_price": signal_close,
                "stop_loss": min(signal_close, next_open) * 0.5,
                "take_profit_1": max(signal_close, next_open) * 2,
                "take_profit_2": max(signal_close, next_open) * 3,
                "take_profit_3": max(signal_close, next_open) * 4,
                "score": 80,
                "reason": "test",
            }

        monkeypatch.setattr(backtest_service, "_generate_institutional_signal", fixed_signal)
        result = backtest_service._run_backtest_sync(
            "BTC/USDT", data, mode="strict", slippage_bps=0,
        )

        assert result["trades"]
        assert result["trades"][0]["entry_price"] == pytest.approx(next_open)
        assert result["trades"][0]["entry_time"].startswith("1970-01-01 00:01:41")

    def test_invalid_gap_entry_is_skipped(self):
        signal = {
            "direction": "long",
            "stop_loss": 90,
            "take_profit_1": 110,
        }
        assert backtest_service._entry_plan_is_valid(signal, 100)
        assert not backtest_service._entry_plan_is_valid(signal, 111)
        assert not backtest_service._entry_plan_is_valid(signal, 89)

    def test_atr_uses_most_recent_period(self):
        data = [
            {"high": 101, "low": 99, "close": 100},
            {"high": 102, "low": 100, "close": 101},
            {"high": 121, "low": 81, "close": 100},
            {"high": 131, "low": 71, "close": 100},
        ]
        assert backtest_service._calc_atr(data, period=2) == pytest.approx(50)

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
