"""Tests for the Phase 5 quality gate.

The quality gate has three concerns:

1. **Aggregation** — given a set of signals and outcomes,
   compute a hit rate, MAE, and MFE for the window.
2. **Auto-disable** — when the hit rate is below the
   threshold, the engine's row is marked ``is_disabled``.
3. **Hot path** — the pipeline reads the latest row to
   decide whether to emit; the helper ``is_engine_disabled``
   returns the right answer.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.analysis import Signal, SignalOutcome
from app.models.quality import EnginePerformance
from app.services import quality_gate


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _make_signal(
    session, *, engine: str, ts: datetime, source_engine: str | None = None,
) -> int:
    sig = Signal(
        symbol="BTC/USDT", symbol_id=0, timeframe="1h",
        direction="long", confidence=70.0, entry_price=100.0,
        stop_loss=99.0, take_profit_1=101.0, take_profit_2=102.0,
        is_active=False, created_at=ts, result="tp1_hit",
        source_engine=source_engine or engine,
    )
    session.add(sig)
    await session.flush()
    return sig.id


async def _make_outcome(
    session, *, signal_id: int, forward_return: float, mae: float = 0.5, mfe: float = 1.2,
    ts: datetime | None = None,
) -> None:
    row = SignalOutcome(
        signal_id=signal_id,
        forward_return_pct=forward_return,
        mae=mae, mfe=mfe,
        resolution_method="tp_sl",
        resolved_at=ts or _utcnow(),
    )
    session.add(row)
    await session.flush()


@pytest.mark.asyncio
async def test_quality_classify_threshold():
    """The classifier is the public surface the cron job
    relies on. Pin its decisions to the settings so a config
    drift fails loud.
    """
    # 12 resolved signals at 30% hit rate should be
    # ``disabled`` (below 0.40).
    assert quality_gate._classify(0.30, 12) == "disabled"
    # 12 resolved at 45% is between the disable threshold
    # (0.40) and degraded (0.50) — call it ``degraded``.
    assert quality_gate._classify(0.45, 12) == "degraded"
    # 12 resolved at 60% is healthy.
    assert quality_gate._classify(0.60, 12) == "ok"
    # 5 resolved is below the min sample size — call it ``ok``
    # so a cold-start engine isn't auto-disabled.
    assert quality_gate._classify(0.10, 5) == "ok"


@pytest.mark.asyncio
async def test_evaluate_engine_writes_row(db_session):
    """A populated window yields a row with the right shape.
    """
    engine = "test_engine_basic"
    # Clean up from previous runs.
    await db_session.execute(
        delete(EnginePerformance).where(EnginePerformance.engine == engine)
    )
    await db_session.execute(
        delete(SignalOutcome).where(SignalOutcome.signal_id.in_(
            select(Signal.id).where(Signal.source_engine == engine)
        ))
    )
    await db_session.execute(
        delete(Signal).where(Signal.source_engine == engine)
    )
    await db_session.commit()

    now = _utcnow()
    for i in range(10):
        sig_id = await _make_signal(
            db_session, engine=engine,
            ts=now - timedelta(hours=2, minutes=i),
        )
        # 6 wins, 4 losses — hit rate 0.6.
        fwd = 1.2 if i < 6 else -0.6
        await _make_outcome(
            db_session, signal_id=sig_id, forward_return=fwd,
            mae=0.4 if i < 6 else 0.8, mfe=1.4 if i < 6 else 0.9,
        )
    await db_session.commit()

    res = await quality_gate.evaluate_engine(engine, db=db_session)
    assert res.n_signals == 10
    assert res.n_resolved == 10
    assert res.n_wins == 6
    assert res.hit_rate == pytest.approx(0.6)
    assert res.status == "ok"
    assert res.is_disabled is False


@pytest.mark.asyncio
async def test_evaluate_engine_disables_on_low_hit_rate(db_session):
    """An engine with a 30% hit rate over 12 resolved signals
    is auto-disabled.
    """
    engine = "test_engine_disabled"
    await db_session.execute(
        delete(EnginePerformance).where(EnginePerformance.engine == engine)
    )
    await db_session.execute(
        delete(SignalOutcome).where(SignalOutcome.signal_id.in_(
            select(Signal.id).where(Signal.source_engine == engine)
        ))
    )
    await db_session.execute(
        delete(Signal).where(Signal.source_engine == engine)
    )
    await db_session.commit()

    now = _utcnow()
    for i in range(12):
        sig_id = await _make_signal(
            db_session, engine=engine, ts=now - timedelta(minutes=30 + i),
        )
        # 4 wins, 8 losses = 33% (close to but above 0.30).
        fwd = 1.0 if i < 4 else -0.5
        await _make_outcome(db_session, signal_id=sig_id, forward_return=fwd)
    await db_session.commit()

    res = await quality_gate.evaluate_engine(engine, db=db_session)
    assert res.hit_rate == pytest.approx(4 / 12, abs=0.01)
    assert res.status == "disabled"
    assert res.is_disabled is True
    assert res.disabled_reason is not None
    assert "below threshold" in res.disabled_reason


@pytest.mark.asyncio
async def test_is_engine_disabled_reads_latest_row(db_session):
    """The pipeline calls ``is_engine_disabled`` on every
    emit. Confirming it reads the *latest* row is what makes
    the auto-disable effective immediately.
    """
    engine = "test_engine_hot_path"
    await db_session.execute(
        delete(EnginePerformance).where(EnginePerformance.engine == engine)
    )
    await db_session.commit()

    # No row yet → not disabled (cold start).
    # Note: this reads via the live async_session_factory; we
    # need to override it for the test session.
    quality_gate._test_session_factory_override = None
    # Instead, use the test session via list_active_engines /
    # an explicit db= arg pattern. We test the read path by
    # inserting rows into the test session, then calling
    # ``evaluate_engine`` which already accepts ``db=``.
    assert await quality_gate.is_engine_disabled(engine, db=db_session) is False

    # Insert an older disabled row + a newer enabled row.
    now = _utcnow()
    db_session.add(EnginePerformance(
        engine=engine, window_start=now - timedelta(hours=2),
        window_end=now - timedelta(hours=1),
        n_signals=5, n_resolved=5, n_wins=1,
        hit_rate=0.2, status="disabled", is_disabled=True,
        disabled_at=now - timedelta(hours=2),
        recorded_at=now - timedelta(hours=2),
    ))
    db_session.add(EnginePerformance(
        engine=engine, window_start=now - timedelta(hours=1),
        window_end=now,
        n_signals=5, n_resolved=5, n_wins=4,
        hit_rate=0.8, status="ok", is_disabled=False,
        recorded_at=now - timedelta(seconds=30),
    ))
    await db_session.commit()

    # The newer row is enabled → engine is not disabled.
    assert await quality_gate.is_engine_disabled(engine, db=db_session) is False

    # Add a third, even newer, disabled row → engine is disabled.
    db_session.add(EnginePerformance(
        engine=engine, window_start=now,
        window_end=now,
        n_signals=2, n_resolved=2, n_wins=0,
        hit_rate=0.0, status="disabled", is_disabled=True,
        disabled_at=now,
        recorded_at=now,
    ))
    await db_session.commit()
    assert await quality_gate.is_engine_disabled(engine, db=db_session) is True


@pytest.mark.asyncio
async def test_re_enable_flips_rows(db_session):
    """An operator re-enable flips the recent disabled rows
    off. The audit trail is preserved (rows aren't deleted).
    """
    engine = "test_engine_reenable"
    now = _utcnow()
    await db_session.execute(
        delete(EnginePerformance).where(EnginePerformance.engine == engine)
    )
    await db_session.commit()

    db_session.add(EnginePerformance(
        engine=engine, window_start=now - timedelta(hours=1),
        window_end=now, n_signals=5, n_resolved=5, n_wins=1,
        hit_rate=0.2, status="disabled", is_disabled=True,
        disabled_at=now, recorded_at=now,
    ))
    await db_session.commit()

    ok = await quality_gate.re_enable_engine(engine, reason="unit_test", db=db_session)
    assert ok is True
    assert await quality_gate.is_engine_disabled(engine, db=db_session) is False
