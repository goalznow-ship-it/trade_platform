"""Tests for the signal outcome resolver (Phase 3).

Covers the walk-forward math and the DB write of both
``signals.result`` and ``signal_outcomes``. The resolver is the
only writer of ``signal_outcomes``; the per-(factor, symbol,
timeframe) quality gate in Phase 5 reads from that table.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.api.v1.signals import _persist_signal
from app.models.analysis import Signal, SignalOutcome
from app.services.signal_outcome import SignalOutcomeResolver


def _resolver_signal(direction="long", entry=100.0):
    """Build a Signal-shaped object the resolver can score."""
    return SimpleNamespace(
        id=1,
        symbol="BTC/USDT",
        timeframe="1h",
        direction=direction,
        entry_price=entry,
        stop_loss=95.0 if direction == "long" else 105.0,
        take_profit_1=110.0 if direction == "long" else 90.0,
        is_triggered=False,
    )


# ── Walk-forward unit tests ─────────────────────────────────────
def test_long_signal_tp_hit_in_walk_forward() -> None:
    resolver = SignalOutcomeResolver()
    sig = _resolver_signal("long")
    # First bar moves up past TP1 → resolution is tp_hit.
    candles = [
        {"high": 100.0, "low": 100.0, "close": 100.0},  # entry
        {"high": 111.0, "low": 100.0, "close": 110.0},  # TP1 hit
    ]
    out = resolver._walk_forward(candles, 100.0, "long", sig, horizon_bars=24)
    assert out["resolution_method"] == "tp_hit"
    assert out["resolved_price"] == 110.0
    assert out["forward_return_pct"] > 0
    assert out["bars_held"] == 1


def test_long_signal_sl_hit_in_walk_forward() -> None:
    resolver = SignalOutcomeResolver()
    sig = _resolver_signal("long")
    candles = [
        {"high": 100.0, "low": 100.0, "close": 100.0},
        {"high": 100.0, "low": 94.0, "close": 95.0},  # SL hit
    ]
    out = resolver._walk_forward(candles, 100.0, "long", sig, horizon_bars=24)
    assert out["resolution_method"] == "sl_hit"
    assert out["resolved_price"] == 95.0
    assert out["forward_return_pct"] < 0
    # MFE is positive (the 100 high beats entry by 0), MAE is the
    # depth of the drawdown.
    assert out["mae"] > 0


def test_short_signal_tp_hit_in_walk_forward() -> None:
    resolver = SignalOutcomeResolver()
    sig = _resolver_signal("short", entry=100.0)
    candles = [
        {"high": 100.0, "low": 100.0, "close": 100.0},
        {"high": 92.0, "low": 89.0, "close": 90.0},  # TP1 (90) hit
    ]
    out = resolver._walk_forward(candles, 100.0, "short", sig, horizon_bars=24)
    assert out["resolution_method"] == "tp_hit"
    # Short wins when price falls — forward_return is positive.
    assert out["forward_return_pct"] > 0


def test_signal_expires_when_horizon_reached() -> None:
    resolver = SignalOutcomeResolver()
    sig = _resolver_signal("long")
    # 5 bars that drift up but never reach TP1. Horizon is 3 so
    # the resolver marks the trade expired at the last close.
    candles = [
        {"high": 100.0, "low": 100.0, "close": 100.0},
        {"high": 101.0, "low": 100.0, "close": 100.5},
        {"high": 102.0, "low": 100.5, "close": 101.5},
        {"high": 103.0, "low": 101.0, "close": 102.5},
    ]
    out = resolver._walk_forward(candles, 100.0, "long", sig, horizon_bars=3)
    assert out["resolution_method"] == "forward_horizon"
    assert out["bars_held"] == 3
    assert out["forward_return_pct"] > 0  # price drifted up


def test_signal_with_too_few_candles_is_expired() -> None:
    resolver = SignalOutcomeResolver()
    sig = _resolver_signal("long")
    candles = [{"high": 100.0, "low": 100.0, "close": 100.0}]
    out = resolver._walk_forward(candles, 100.0, "long", sig, horizon_bars=24)
    assert out["resolution_method"] == "expired"
    # No path walked → bars_held stays at 0.
    assert out["bars_held"] == 0


def test_mae_mfe_are_within_reasonable_bounds() -> None:
    """MAE / MFE are always non-negative percentages."""
    resolver = SignalOutcomeResolver()
    sig = _resolver_signal("long")
    # 10% drawdown then a recovery.
    candles = [
        {"high": 100.0, "low": 100.0, "close": 100.0},
        {"high": 101.0, "low": 90.0, "close": 91.0},   # 9% drawdown
        {"high": 105.0, "low": 92.0, "close": 104.0},  # recovered
        {"high": 110.0, "low": 104.0, "close": 109.0},  # MFE 10%
        {"high": 112.0, "low": 109.0, "close": 111.5},  # TP1 hit
    ]
    out = resolver._walk_forward(candles, 100.0, "long", sig, horizon_bars=24)
    assert out["mae"] >= 0
    assert out["mfe"] >= 0
    assert out["mae"] < 20  # sane cap — no NaN / runaway values
    assert out["mfe"] < 20


# ── DB write integration ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_resolver_writes_both_signals_result_and_signal_outcomes(
    db_session, monkeypatch
) -> None:
    """A successful resolve_all() writes to both tables.

    The signal was a long; we mock market_service to return
    candles that immediately hit TP1, so the resolution is
    ``tp_hit`` and ``signals.result`` flips to ``tp_hit`` too.
    """
    from app.services import market as market_module

    candles = [
        {"high": 100.0, "low": 100.0, "close": 100.0},
        {"high": 111.0, "low": 100.0, "close": 110.0},  # TP hit
    ]
    monkeypatch.setattr(
        market_module.market_service,
        "get_ohlcv",
        AsyncMock(return_value=candles),
    )

    # Seed a candidate signal in the active state.
    sig = Signal(
        symbol_id=1,  # not enforced; resolver doesn't read it
        symbol="BTC/USDT",
        timeframe="1h",
        direction="long",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit_1=110.0,
        is_active=True,
        result="new",
    )
    db_session.add(sig)
    await db_session.commit()
    await db_session.refresh(sig)

    resolver = SignalOutcomeResolver()
    summary = await resolver.resolve_all(db=db_session, horizon_bars=24)
    await db_session.commit()

    assert summary["resolved"] == 1
    assert summary["skipped"] == 0

    # Both rows were written.
    outcome_rows = (await db_session.execute(
        select(SignalOutcome)
    )).scalars().all()
    assert len(outcome_rows) == 1
    outcome = outcome_rows[0]
    assert outcome.signal_id == sig.id
    assert outcome.resolution_method == "tp_hit"
    assert outcome.forward_return_pct > 0
    assert outcome.mae >= 0
    assert outcome.mfe >= 0
    assert outcome.bars_held == 1

    # The signal's categorical result and is_active flag flip too.
    refreshed = (await db_session.execute(
        select(Signal).where(Signal.id == sig.id)
    )).scalar_one()
    assert refreshed.result == "tp_hit"
    assert refreshed.is_active is False


@pytest.mark.asyncio
async def test_resolver_is_idempotent(db_session, monkeypatch) -> None:
    """A second pass on the same signal writes no new outcome row.
    The unique constraint on ``signal_outcomes.signal_id`` is the
    safety net, but the candidate query should already skip
    signals with an outcome row.
    """
    from app.services import market as market_module

    candles = [
        {"high": 100.0, "low": 100.0, "close": 100.0},
        {"high": 111.0, "low": 100.0, "close": 110.0},
    ]
    monkeypatch.setattr(
        market_module.market_service,
        "get_ohlcv",
        AsyncMock(return_value=candles),
    )

    sig = Signal(
        symbol_id=1, symbol="BTC/USDT", timeframe="1h",
        direction="long", entry_price=100.0, stop_loss=95.0,
        take_profit_1=110.0, is_active=True, result="new",
    )
    db_session.add(sig)
    await db_session.commit()
    await db_session.refresh(sig)

    resolver = SignalOutcomeResolver()
    first = await resolver.resolve_all(db=db_session, horizon_bars=24)
    second = await resolver.resolve_all(db=db_session, horizon_bars=24)
    await db_session.commit()

    assert first["resolved"] == 1
    # The candidate query filters by ``is_active=True`` so the
    # already-resolved signal doesn't show up again.
    assert second["resolved"] == 0
    rows = (await db_session.execute(select(SignalOutcome))).scalars().all()
    assert len(rows) == 1


# ── Persist (legacy) sanity ──────────────────────────────────────
@pytest.mark.asyncio
async def test_delivered_signal_is_persisted_for_verified_symbol(
    db_session, monkeypatch
) -> None:
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
