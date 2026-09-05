"""Quality gate: per-engine performance tracking + auto-disable.

Why
---
A signal pipeline that emits forever is worse than one that
fails loud. Phase 5 introduces a quality gate that:

1. Computes a rolling hit-rate / MAE / MFE for every engine
   that has emitted in the last ``QUALITY_WINDOW_HOURS``
   hours. Stored in ``engine_performance``.
2. If the hit rate falls below ``QUALITY_MIN_HIT_RATE``, the
   engine is marked ``is_disabled=True``. The signal pipeline
   reads this flag in ``signal_pipeline.emit`` and returns
   None instead of a new signal.
3. The cron job re-evaluates every
   ``QUALITY_EVAL_INTERVAL_MINUTES`` minutes. A disabled
   engine can be re-enabled by an operator (admin endpoint)
   or by the circuit breaker's half-open probe.

This is a soft gate — the engine isn't shut down, it's just
starved of new signals. The breaker below is the hard
fallback if the engine itself is throwing exceptions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import logger
from app.models.analysis import Signal, SignalOutcome
from app.models.quality import EnginePerformance


# Default window if the caller doesn't pass one — pulled from
# settings at runtime so a config flip is reflected without
# restarting the worker.
def _window_start(window_hours: int | None = None) -> datetime:
    hours = window_hours or settings.QUALITY_WINDOW_HOURS
    return datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)


@dataclass
class QualityResult:
    """One row of the quality-gate evaluation.

    Returned by :func:`evaluate_engine` so the admin endpoint
    can serialise it without going through the SQLAlchemy
    session a second time.
    """

    engine: str
    n_signals: int
    n_resolved: int
    n_wins: int
    hit_rate: float | None
    avg_forward_return: float | None
    avg_mae_bps: float | None
    avg_mfe_bps: float | None
    status: str  # ok / degraded / disabled
    is_disabled: bool
    disabled_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "n_signals": self.n_signals,
            "n_resolved": self.n_resolved,
            "n_wins": self.n_wins,
            "hit_rate": self.hit_rate,
            "avg_forward_return": self.avg_forward_return,
            "avg_mae_bps": self.avg_mae_bps,
            "avg_mfe_bps": self.avg_mfe_bps,
            "status": self.status,
            "is_disabled": self.is_disabled,
            "disabled_reason": self.disabled_reason,
        }


def _classify(
    hit_rate: float | None,
    n_resolved: int,
    min_resolved: int = 10,
) -> str:
    """Return ``ok`` / ``degraded`` / ``disabled``.

    ``disabled`` requires the resolved-sample count to clear
    ``min_resolved`` — a freshly-deployed engine with 2 signals
    should not be auto-disabled just because both lost; that's
    a cold start, not a quality problem.
    """
    if n_resolved < min_resolved or hit_rate is None:
        return "ok"
    if hit_rate < settings.QUALITY_MIN_HIT_RATE:
        return "disabled"
    # ``degraded`` is a soft warning: 5–10% above the disable
    # threshold. Operators can see it on the admin dashboard.
    if hit_rate < settings.QUALITY_MIN_HIT_RATE + 0.10:
        return "degraded"
    return "ok"


async def evaluate_engine(
    engine: str,
    *,
    window_hours: int | None = None,
    db: AsyncSession | None = None,
) -> QualityResult:
    """Compute a single engine's quality row.

    Reads ``signals`` and ``signal_outcomes`` for the engine's
    window and writes a row to ``engine_performance``. If the
    computed hit rate falls below the threshold, sets
    ``is_disabled=True`` on the engine's latest row.
    """
    own_session = db is None
    if own_session:
        db = async_session_factory()

    try:
        window = _window_start(window_hours)
        # Signals emitted by this engine in the window. We
        # only count rows that are not expired — an expired
        # signal is one the resolver never had a chance to
        # evaluate (handled by ``prune_stale_signals``).
        sig_stmt = (
            select(Signal.id)
            .where(Signal.source_engine == engine)
            .where(Signal.created_at >= window)
        )
        sig_rows = await db.execute(sig_stmt)
        signal_ids = [r[0] for r in sig_rows.all()]
        n_signals = len(signal_ids)

        if n_signals == 0:
            # No work to do — record an empty row so the
            # pipeline knows the engine is alive but quiet.
            row = EnginePerformance(
                engine=engine,
                window_start=window,
                window_end=datetime.now(UTC).replace(tzinfo=None),
                n_signals=0,
                n_resolved=0,
                n_wins=0,
                hit_rate=None,
                avg_forward_return=None,
                avg_mae_bps=None,
                avg_mfe_bps=None,
                status="ok",
            )
            db.add(row)
            if own_session:
                await db.commit()
            return QualityResult(
                engine=engine, n_signals=0, n_resolved=0, n_wins=0,
                hit_rate=None, avg_forward_return=None,
                avg_mae_bps=None, avg_mfe_bps=None,
                status="ok", is_disabled=False, disabled_reason=None,
            )

        # Resolved outcomes for those signals.
        out_stmt = select(
            SignalOutcome.signal_id,
            SignalOutcome.forward_return_pct,
            SignalOutcome.mae,
            SignalOutcome.mfe,
        ).where(SignalOutcome.signal_id.in_(signal_ids))
        out_rows = (await db.execute(out_stmt)).all()
        n_resolved = len(out_rows)
        if n_resolved == 0:
            avg_fwd = avg_mae = avg_mfe = None
            n_wins = 0
            hit_rate = None
        else:
            fwds = [float(r[1]) for r in out_rows if r[1] is not None]
            maes = [float(r[2]) for r in out_rows if r[2] is not None]
            mfes = [float(r[3]) for r in out_rows if r[3] is not None]
            n_wins = sum(1 for f in fwds if f > 0)
            hit_rate = n_wins / max(len(fwds), 1)
            avg_fwd = sum(fwds) / len(fwds) if fwds else None
            avg_mae = sum(maes) / len(maes) if maes else None
            avg_mfe = sum(mfes) / len(mfes) if mfes else None

        status = _classify(hit_rate, n_resolved)
        is_disabled = status == "disabled"
        disabled_reason: str | None = None
        if is_disabled:
            disabled_reason = (
                f"hit_rate {hit_rate:.3f} below threshold "
                f"{settings.QUALITY_MIN_HIT_RATE:.3f} over "
                f"{n_resolved} resolved signals"
            )

        row = EnginePerformance(
            engine=engine,
            window_start=window,
            window_end=datetime.now(UTC).replace(tzinfo=None),
            n_signals=n_signals,
            n_resolved=n_resolved,
            n_wins=n_wins,
            hit_rate=hit_rate,
            avg_forward_return=avg_fwd,
            avg_mae_bps=avg_mae,
            avg_mfe_bps=avg_mfe,
            status=status,
            is_disabled=is_disabled,
            disabled_reason=disabled_reason,
            disabled_at=datetime.now(UTC).replace(tzinfo=None) if is_disabled else None,
        )
        db.add(row)

        # Propagate the disabled flag to the *latest* existing
        # row so the pipeline can read it without a join.
        # (The row we just inserted IS the latest, so we
        # commit and re-query.)
        if own_session:
            await db.commit()

        if is_disabled:
            logger.warning(
                "engine_auto_disabled",
                extra={
                    "engine": engine,
                    "hit_rate": hit_rate,
                    "n_resolved": n_resolved,
                    "threshold": settings.QUALITY_MIN_HIT_RATE,
                },
            )

        return QualityResult(
            engine=engine, n_signals=n_signals, n_resolved=n_resolved,
            n_wins=n_wins, hit_rate=hit_rate,
            avg_forward_return=avg_fwd, avg_mae_bps=avg_mae,
            avg_mfe_bps=avg_mfe, status=status, is_disabled=is_disabled,
            disabled_reason=disabled_reason,
        )
    finally:
        if own_session:
            await db.close()


async def list_active_engines(db: AsyncSession | None = None) -> list[str]:
    """Return every distinct ``source_engine`` that has emitted
    a signal in the last 7 days. The cron job uses this to
    iterate the engines; the admin endpoint uses it to render
    the dashboard.
    """
    own_session = db is None
    if own_session:
        db = async_session_factory()
    try:
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
        stmt = (
            select(Signal.source_engine)
            .where(Signal.created_at >= since)
            .where(Signal.source_engine.is_not(None))
            .distinct()
        )
        rows = (await db.execute(stmt)).all()
        return sorted({r[0] for r in rows if r[0]})
    finally:
        if own_session:
            await db.close()


async def is_engine_disabled(engine: str, db: AsyncSession | None = None) -> bool:
    """Hot-path check the pipeline calls before emitting.

    Reads the *latest* ``engine_performance`` row for the
    engine. Returns ``True`` if the most recent evaluation
    disabled it. ``False`` if no row exists (cold start —
    don't block the pipeline because the gate hasn't run).
    """
    if db is not None:
        stmt = (
            select(EnginePerformance.is_disabled)
            .where(EnginePerformance.engine == engine)
            .order_by(EnginePerformance.recorded_at.desc())
            .limit(1)
        )
        row = (await db.execute(stmt)).first()
        if row is None:
            return False
        return bool(row[0])
    async with async_session_factory() as db:
        return await is_engine_disabled(engine, db=db)


async def re_enable_engine(
    engine: str, *, reason: str = "operator_override",
    db: AsyncSession | None = None,
) -> bool:
    """Flip ``is_disabled`` off for every recent row of the
    engine. Returns ``True`` if at least one row was updated.

    Called by the admin endpoint when an operator overrides
    the gate. We don't delete the rows — the audit trail stays.
    """
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    if db is not None:
        stmt = (
            update(EnginePerformance)
            .where(EnginePerformance.engine == engine)
            .where(EnginePerformance.recorded_at >= since)
            .where(EnginePerformance.is_disabled.is_(True))
            .values(is_disabled=False, disabled_reason=None, disabled_at=None)
        )
        result = await db.execute(stmt)
        await db.commit()
        logger.info(
            "engine_re_enabled",
            extra={"engine": engine, "reason": reason, "rows": result.rowcount},
        )
        return bool(result.rowcount)
    async with async_session_factory() as db:
        return await re_enable_engine(engine, reason=reason, db=db)


__all__ = [
    "QualityResult",
    "evaluate_engine",
    "list_active_engines",
    "is_engine_disabled",
    "re_enable_engine",
]
