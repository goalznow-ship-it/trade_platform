"""Tests for the self-learning weight feedback loop (Phase 2).

Covers:
- ``WeightOrchestrator.apply_to_score`` rescales per-category
  scores using the (active / default) weight ratio.
- ``weight_orchestrator.adjust_weights`` writes a successful
  ``adjustment_runs`` row when there are enough trades, and a
  skipped row when there are fewer than 10.
- Trend-heavy / SMC-light history pushes the trend weight up and
  the SMC weight down on the next run.
"""
import pytest
from sqlalchemy import select

from app.models.persistence import AdjustmentRun, Trade
from app.services.weight_orchestrator import (
    DEFAULT_WEIGHTS,
    WeightOrchestrator,
    weight_orchestrator,
)


# Phase 7: ``trade_store`` constructs its own ``async_session_factory``
# at import time, so without this fixture it would point at the live
# PostgreSQL URL and the integration tests below would try to connect
# to a database that isn't running. We swap the factory for the test
# engine's, then restore it so other test files aren't affected.
@pytest.fixture(autouse=True)
def _patch_trade_store_factory():
    from app.core import persistence
    from tests.conftest import db_session_factory as _test_factory
    original = persistence.trade_store._session_factory
    persistence.trade_store._session_factory = _test_factory
    # Clear any session override the test body may have set so the
    # next test starts from a clean slate.
    persistence.trade_store.clear_session_override()
    try:
        yield
    finally:
        persistence.trade_store._session_factory = original
        persistence.trade_store.clear_session_override()


# ── Unit: apply_to_score scaling ────────────────────────────────
def test_apply_to_score_uses_default_ratio() -> None:
    orch = WeightOrchestrator()
    # With default weights (no adjust runs yet) the orchestrator
    # uses the engine's defaults — scaling should be 1.0 for every
    # category.
    out = orch.apply_to_score({"trend": 20.0, "smc": 20.0})
    assert pytest.approx(out["trend"], rel=1e-3) == 20.0
    assert pytest.approx(out["smc"], rel=1e-3) == 20.0


def test_apply_to_score_scales_active_over_default() -> None:
    orch = WeightOrchestrator()
    # Hand-set the weights to mimic a successful adjust run that
    # moved trend up and smc down.
    orch.engine.current_weights = {
        "trend": 0.30,
        "momentum": 0.15,
        "volume": 0.15,
        "liquidity": 0.15,
        "smc": 0.10,
        "risk": 0.15,
    }
    # Default trend=0.20 → active 0.30 → scale 1.5x
    # Default smc=0.20 → active 0.10 → scale 0.5x
    out = orch.apply_to_score({"trend": 20.0, "smc": 20.0})
    assert pytest.approx(out["trend"], rel=1e-3) == 30.0
    assert pytest.approx(out["smc"], rel=1e-3) == 10.0


def test_apply_to_score_preserves_sign() -> None:
    orch = WeightOrchestrator()
    orch.engine.current_weights = {
        "trend": 0.30,
        "momentum": 0.15,
        "volume": 0.15,
        "liquidity": 0.15,
        "smc": 0.10,
        "risk": 0.15,
    }
    # Negative scores stay negative — direction sign matters.
    out = orch.apply_to_score({"trend": -10.0, "smc": -20.0})
    assert out["trend"] < 0
    assert out["smc"] < 0
    assert pytest.approx(out["trend"], rel=1e-3) == -15.0
    assert pytest.approx(out["smc"], rel=1e-3) == -10.0


def test_weights_used_snapshot_strips_metadata() -> None:
    orch = WeightOrchestrator()
    orch.engine.current_weights = {
        "trend": 0.25,
        "momentum": 0.15,
        "volume": 0.15,
        "liquidity": 0.15,
        "smc": 0.15,
        "risk": 0.15,
        "_hydrated_at": "2026-09-05T00:00:00+00:00",
    }
    snap = orch.weights_used_snapshot()
    assert "_hydrated_at" not in snap
    assert snap["trend"] == 0.25
    assert set(snap.keys()) == set(DEFAULT_WEIGHTS.keys())


# ── Integration: trade_store + adjust_weights ────────────────────
@pytest.mark.asyncio
async def test_adjust_weights_skips_with_fewer_than_10_trades(db_session) -> None:
    from app.core.persistence import trade_store

    # No prior runs, no trades — should skip with audit row.
    result = await weight_orchestrator.adjust_weights()
    assert result["status"] == "skipped"
    assert result["trade_count"] == 0
    assert result["audit_id"] is not None

    rows = (await db_session.execute(
        select(AdjustmentRun).order_by(AdjustmentRun.id.desc()).limit(1)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "skipped"
    assert rows[0].skip_reason == "insufficient_trades_lt_10"


@pytest.mark.asyncio
async def test_adjust_weights_promotes_trend_over_smc(db_session) -> None:
    """Feed 20 closed trades where trend was right on every win
    and SMC was right on every loss. After adjust_weights runs,
    trend's weight should rise above smc's — proving the loop is
    actually feeding back into scoring.
    """
    from app.core.persistence import trade_store

    # Wipe any runs and trades left from earlier tests so the
    # assertion is clean. ``source_trade_id`` collisions are
    # silently treated as a no-op in ``record_trade`` so without
    # this the inserts would be skipped and the orchestrator
    # would see 0 trades.
    from app.models.persistence import Trade
    (await db_session.execute(Trade.__table__.delete()))
    (await db_session.execute(AdjustmentRun.__table__.delete()))
    await db_session.commit()

    for i in range(20):
        await trade_store.record_trade(
            {
                "source_trade_id": f"weight-test-{i}",
                "symbol": "BTC/USDT",
                "timeframe": "1h",
                "direction": "long",
                "entry_price": 30000.0,
                "exit_price": 30100.0,
                "pnl_percent": 0.33,
                "actual_outcome": "win",
                # Trend predicted long correctly, SMC was wrong
                # (signed 0 — the per-category accuracy math treats
                # zero scores as "not predicted", so we hand-craft
                # scores with both sign-correct and sign-incorrect
                # outcomes for trend and smc).
                "scores_at_entry": {
                    "trend": 12.0,   # long + positive — sign agrees with win
                    "momentum": 5.0,
                    "volume": 3.0,
                    "liquidity": 2.0,
                    "smc": -10.0,    # short sign on a long winner — wrong
                    "risk": 1.0,
                },
            },
            db=db_session,
        )
    # Phase 7: pin the trade_store's internal session opens to the
    # test session so the orchestrator's downstream
    # ``list_recent_trades(limit=100)`` reads the rows we just wrote
    # (SQLite + StaticPool would otherwise hand out a fresh
    # connection that can't see uncommitted rows from another
    # session).
    trade_store.bind_session_for_test(db_session)

    # Force hydration of trade_history on the engine so adjust_weights
    # can read the freshly written rows.
    weight_orchestrator.engine.trade_history = (
        await trade_store.list_recent_trades(limit=100, db=db_session)
    )
    weight_orchestrator.engine._hydrated_from_store = True

    result = await weight_orchestrator.adjust_weights()
    assert result["status"] == "ok"
    assert result["trade_count"] >= 10

    new = result["new_weights"]
    # Trend did the right thing more often than SMC — the new
    # weights should reflect that.
    assert new["trend"] > new["smc"]

    # And an audit row was written.
    rows = (await db_session.execute(
        select(AdjustmentRun)
        .where(AdjustmentRun.status == "ok")
        .order_by(AdjustmentRun.id.desc())
        .limit(1)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].trade_count == 20
    assert rows[0].new_weights["trend"] > rows[0].new_weights["smc"]


@pytest.mark.asyncio
async def test_hydrate_from_db_picks_up_latest_weights(db_session) -> None:
    """The orchestrator's hydrate_from_db must read the most recent
    successful adjustment_runs.new_weights, not reset to defaults.
    """
    from app.core.persistence import trade_store

    custom_weights = {
        "trend": 0.30, "momentum": 0.10, "volume": 0.10,
        "liquidity": 0.10, "smc": 0.30, "risk": 0.10,
    }
    await trade_store.record_adjustment(
        status="ok",
        previous_weights=dict(DEFAULT_WEIGHTS),
        new_weights=custom_weights,
        trade_count=20,
        avg_accuracy=0.55,
        db=db_session,
    )
    # Same Session-pinning as the trade-write tests above so the
    # orchestrator's downstream ``latest_successful_weights()`` can
    # see the row.
    trade_store.bind_session_for_test(db_session)

    # Reset engine state to defaults so we can prove hydrate moves it.
    weight_orchestrator.engine.current_weights = dict(DEFAULT_WEIGHTS)
    hydrated = await weight_orchestrator.hydrate_from_db()
    assert hydrated["trend"] == pytest.approx(0.30, rel=1e-3)
    assert hydrated["smc"] == pytest.approx(0.30, rel=1e-3)
    assert hydrated["momentum"] == pytest.approx(0.10, rel=1e-3)


@pytest.mark.asyncio
async def test_hydrate_from_db_returns_defaults_when_no_runs(db_session) -> None:
    """Fresh DB → hydrate returns defaults rather than crashing."""
    (await db_session.execute(AdjustmentRun.__table__.delete()))
    weight_orchestrator.engine.current_weights = {"trend": 0.99, "_stale": True}
    hydrated = await weight_orchestrator.hydrate_from_db()
    assert pytest.approx(hydrated["trend"], rel=1e-3) == DEFAULT_WEIGHTS["trend"]
    assert "_stale" not in hydrated
    assert "_hydrated_at" in weight_orchestrator.engine.current_weights
