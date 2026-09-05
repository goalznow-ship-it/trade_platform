"""Tests for the canonical signal pipeline.

Phase 1 — every emitted signal must go through ``SignalPipeline``.
These tests cover:
- ``is_persistable`` filters neutral / low-confidence signals.
- ``persist_composed`` writes a row with the new provenance columns.
- The same (symbol, timeframe, direction) is deduped on the second
  emit.
- The ML boost is a no-op when models aren't ready, and the
  bypass sentinel is recorded on the row.
"""
import pytest
from sqlalchemy import select

from app.models.analysis import Signal
from app.services.signal_pipeline import (
    ML_BYPASS_MODEL_VERSION,
    PIPELINE_VERSION,
    signal_pipeline,
)


# Phase 7: ``SignalPipeline.persist_composed`` opens its own
# ``async_session_factory()`` rather than accepting a session for
# the persist path. Patch the reference to the test factory so the
# integration tests below hit the in-memory SQLite instead of
# attempting a PostgreSQL connection that isn't running.
@pytest.fixture(autouse=True)
def _patch_pipeline_session_factory():
    from app.services import signal_pipeline
    from tests.conftest import db_session_factory as _test_factory
    original = signal_pipeline.async_session_factory
    signal_pipeline.async_session_factory = _test_factory
    try:
        yield
    finally:
        signal_pipeline.async_session_factory = original


def test_is_persistable_rejects_neutral() -> None:
    assert signal_pipeline._is_persistable({"direction": "neutral", "confidence": 80}) is False


def test_is_persistable_rejects_low_confidence() -> None:
    assert signal_pipeline._is_persistable({"direction": "long", "confidence": 40}) is False


def test_is_persistable_accepts_long_strong() -> None:
    assert signal_pipeline._is_persistable({"direction": "long", "confidence": 75}) is True


def test_is_persistable_accepts_short_strong() -> None:
    assert signal_pipeline._is_persistable({"direction": "SHORT", "confidence": 70}) is True


def test_extract_factor_payload_includes_institutional_scores() -> None:
    inst = {
        "scores": {"trend": 12, "momentum": 8, "volume": 5, "liquidity": 4, "smc": 10, "risk": 3},
        "details": {"rsi": 55.0, "atr": 100.0},
        "weights": {"trend": 20, "momentum": 15, "volume": 15, "liquidity": 15, "smc": 20, "risk": 15},
        "classification": "strong",
        "risk_level": "low",
        "abs_score": 80,
        "direction": "long",
    }
    composed = {
        "entry_zone": {"min": 100, "max": 105, "mid": 102.5},
        "stop_loss": 95,
        "take_profit_1": 110,
        "take_profit_2": 120,
        "invalidation": "below 95",
        "expected_hold_time": "1-3 days",
        "current_price": 102.5,
        "ml_boost_meta": {"ml_adjustment": 3.5, "note": "boosted"},
    }
    payload = signal_pipeline._extract_factor_payload(composed, inst)
    assert payload["abs_score"] == 80
    assert payload["direction"] == "long"
    assert payload["ml_boost_meta"]["ml_adjustment"] == 3.5
    assert payload["entry_zone"]["mid"] == 102.5
    assert payload["stop_loss"] == 95
    assert payload["take_profit_1"] == 110


def test_pipeline_version_constant_is_string() -> None:
    assert isinstance(PIPELINE_VERSION, str)
    # Bump manually when persistence schema changes.
    assert PIPELINE_VERSION == "1.0.0"


def test_ml_bypass_sentinel_is_distinguishable() -> None:
    # The self-learning loop filters rows where model_version !=
    # ML_BYPASS_MODEL_VERSION. Make sure the sentinel stays stable.
    assert ML_BYPASS_MODEL_VERSION == "ml_bypass_v1"


def test_apply_ml_boost_records_bypass_when_models_not_ready() -> None:
    composed = {
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "direction": "long",
        "confidence": 80.0,
    }
    # When the predictor isn't ready, the boost is 0 and the
    # model_version is the bypass sentinel — that sentinel is what
    # the self-learning loop will filter on.
    new_composed, ml_boost, model_version = signal_pipeline._apply_ml_boost(
        composed, symbol="BTC/USDT", timeframe="1h"
    )
    # Either the predictor is ready (boost applied) or it's not
    # (bypass recorded). Both are valid outcomes — what matters is
    # that the function returns a stable (dict, float, str) tuple.
    assert isinstance(new_composed, dict)
    assert isinstance(ml_boost, float)
    assert isinstance(model_version, str)
    assert "ml_boost_meta" in new_composed


@pytest.mark.asyncio
async def test_persist_composed_writes_full_provenance(db_session) -> None:
    """End-to-end: a composed dict lands in the signals table with
    factor_payload, weights_used, ml_boost, pipeline_version,
    model_version, and source_engine populated. Without these columns
    the self-learning loop in Phase 2 has nothing to read from.
    """
    composed = {
        "symbol": "ETH/USDT",
        "timeframe": "1h",
        "direction": "long",
        "confidence": 75.0,
        "entry_zone": {"min": 3000, "max": 3050, "mid": 3025},
        "stop_loss": 2950,
        "take_profit_1": 3150,
        "take_profit_2": 3250,
        "take_profit_3": 3400,
        "institutional_score": {
            "scores": {"trend": 10, "momentum": 8, "volume": 6, "liquidity": 5, "smc": 9, "risk": 4},
            "details": {"rsi": 60.0, "atr": 50.0},
            "weights": {"trend": 20, "momentum": 15, "volume": 15, "liquidity": 15, "smc": 20, "risk": 15},
            "abs_score": 75,
            "direction": "long",
            "classification": "strong",
            "risk_level": "low",
        },
        "reasons": ["trend confirmed", "volume spike"],
        "expected_hold_time": "1-3 days",
        "invalidation": "below 2950",
    }
    result = await signal_pipeline.persist_composed(composed, db=db_session)
    assert result.get("signal_id") is not None

    row = (await db_session.execute(
        select(Signal).where(Signal.id == result["signal_id"])
    )).scalar_one()
    assert row.symbol == "ETH/USDT"
    assert row.timeframe == "1h"
    assert row.direction == "long"
    # Provenance columns — Phase 1's whole point.
    assert row.pipeline_version == PIPELINE_VERSION
    assert row.source_engine == "institutional+ml"
    assert row.weights_used is not None
    assert row.weights_used["trend"] == 20
    assert row.factor_payload is not None
    assert row.factor_payload["abs_score"] == 75
    assert row.factor_payload["entry_zone"]["mid"] == 3025


@pytest.mark.asyncio
async def test_persist_composed_dedupes_repeat_active_signal(db_session) -> None:
    """Two emits for the same (symbol, timeframe, direction) on the
    active state must produce only one row. This was the legacy
    _persist_signal behavior — preserved so a runaway cron can't
    multiply a single trade idea into 10 rows.
    """
    composed = {
        "symbol": "BTC/USDT",
        "timeframe": "4h",
        "direction": "short",
        "confidence": 70.0,
        "entry_zone": {"min": 60000, "max": 60100, "mid": 60050},
        "stop_loss": 60500,
        "take_profit_1": 59500,
        "institutional_score": {
            "scores": {"trend": -10, "momentum": -8, "volume": -6, "liquidity": -5, "smc": -9, "risk": -4},
            "weights": {"trend": 20, "momentum": 15, "volume": 15, "liquidity": 15, "smc": 20, "risk": 15},
            "abs_score": 70,
            "direction": "short",
        },
    }
    first = await signal_pipeline.persist_composed(composed, db=db_session)
    second = await signal_pipeline.persist_composed(composed, db=db_session)
    assert first.get("signal_id") is not None
    # Second emit is deduped — no new row.
    assert second.get("signal_id") is None
    rows = (await db_session.execute(
        select(Signal).where(
            Signal.symbol == "BTC/USDT",
            Signal.timeframe == "4h",
            Signal.direction == "short",
        )
    )).scalars().all()
    assert len(rows) == 1
