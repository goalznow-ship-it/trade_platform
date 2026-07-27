from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.api.v1.signals import _persist_signal
from app.models.analysis import Signal
from app.services.signal_outcome import SignalOutcomeResolver


def signal(direction="long", triggered=False):
    return SimpleNamespace(
        direction=direction,
        entry_price=100.0,
        stop_loss=95.0 if direction == "long" else 105.0,
        take_profit_1=110.0 if direction == "long" else 90.0,
        is_triggered=triggered,
        triggered_price=None,
    )


def test_signal_waits_until_entry_is_touched():
    item = signal()

    result = SignalOutcomeResolver._candle_result(
        item,
        {"high": 120, "low": 111},
    )

    assert result is None
    assert item.is_triggered is False


def test_long_signal_resolves_take_profit_after_entry():
    item = signal(triggered=True)

    result = SignalOutcomeResolver._candle_result(
        item,
        {"high": 111, "low": 99},
    )

    assert result == "tp_hit"


def test_short_signal_resolves_take_profit_after_entry():
    item = signal(direction="short", triggered=True)

    result = SignalOutcomeResolver._candle_result(
        item,
        {"high": 101, "low": 89},
    )

    assert result == "tp_hit"


def test_same_candle_tp_and_sl_is_resolved_conservatively():
    item = signal(triggered=True)

    result = SignalOutcomeResolver._candle_result(
        item,
        {"high": 111, "low": 94},
    )

    assert result == "sl_hit"


@pytest.mark.asyncio
async def test_delivered_signal_is_persisted_for_verified_symbol(db_session, monkeypatch):
    from app.services.market_coverage import market_coverage

    monkeypatch.setattr(
        market_coverage,
        "get_top_symbols",
        AsyncMock(return_value=["BTC/USDT"]),
    )
    await _persist_signal({
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "direction": "long",
        "confidence": 75,
        "entry_price": 100,
        "stop_loss": 95,
        "take_profit": [110, 115, 120],
        "risk_reward": 2,
        "reasons": ["Real test setup"],
    }, db_session)

    saved = (await db_session.execute(select(Signal))).scalar_one()

    assert saved.symbol == "BTC/USDT"
    assert saved.result == "new"
    assert saved.is_active is True
    assert saved.expires_at is not None
