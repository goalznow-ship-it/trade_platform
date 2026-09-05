"""Persistence layer for the self-learning feedback loop.

Replaces the in-memory trade list on ``SelfLearningEngine`` with a
SQL-backed store. The store is what ``record_trade`` writes to and
``adjust_weights`` reads from — so the loop survives process
restarts, which is the whole point of the migration in 012.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.logging import logger
from app.models.persistence import AdjustmentRun, Trade


class SQLAlchemyTradeStore:
    """Async SQL store for closed trades and weight-adjustment runs.

    The store is intentionally a thin wrapper over the model layer so
    the engine doesn't need to know about SQLAlchemy. Callers can
    pass in a session (preferred for the request lifecycle) or let
    the store open one itself for fire-and-forget writes from
    background tasks.
    """

    def __init__(self, session_factory=async_session_factory):
        self._session_factory = session_factory

    async def record_trade(
        self,
        trade: dict[str, Any],
        db: AsyncSession | None = None,
    ) -> int | None:
        """Insert a trade. Returns the new trade id, or None if the
        ``source_trade_id`` was already recorded.

        Idempotency is the same shape as the legacy in-memory engine
        used: a (source_trade_id) collision is a no-op, not an error.
        """
        session, owns = self._session(db)
        try:
            source_id = trade.get("source_trade_id")
            if source_id is not None:
                existing = await session.execute(
                    select(Trade.id).where(Trade.source_trade_id == source_id)
                )
                if existing.scalar_one_or_none() is not None:
                    return None

            record = Trade(
                source_trade_id=trade.get("source_trade_id"),
                signal_id=trade.get("signal_id"),
                symbol=trade.get("symbol", "unknown"),
                timeframe=trade.get("timeframe"),
                direction=trade.get("direction", "long"),
                entry_price=trade.get("entry_price"),
                exit_price=trade.get("exit_price"),
                entry_time=_parse_dt(trade.get("entry_time")),
                exit_time=_parse_dt(trade.get("exit_time")),
                pnl_percent=trade.get("pnl_percent"),
                risk_reward=trade.get("risk_reward"),
                target_rr=trade.get("target_rr"),
                max_drawdown_percent=trade.get("max_drawdown_percent"),
                max_favorable_excursion=trade.get("max_favorable_excursion"),
                duration_hours=trade.get("duration_hours"),
                actual_outcome=trade.get("actual_outcome"),
                scores_at_entry=trade.get("scores_at_entry"),
                notes=trade.get("notes"),
            )
            session.add(record)
            try:
                await session.commit()
            except IntegrityError:
                # Two concurrent inserts with the same source_trade_id
                # — treat the second as a successful no-op.
                await session.rollback()
                logger.debug("trade_insert_duplicate source=%s", source_id)
                return None
            await session.refresh(record)
            return record.id
        finally:
            if owns:
                await session.close()

    async def list_recent_trades(
        self,
        limit: int = 100,
        db: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Return the most recent ``limit`` trades as dicts.

        ``adjust_weights`` reads this list to compute per-category
        accuracy. The order is ``recorded_at DESC`` so the limit
        captures the freshest signal of category performance — older
        trades may reflect a regime that no longer applies.
        """
        session, owns = self._session(db)
        try:
            result = await session.execute(
                select(Trade).order_by(Trade.recorded_at.desc()).limit(limit)
            )
            rows = result.scalars().all()
            return [_trade_to_dict(row) for row in rows]
        finally:
            if owns:
                await session.close()

    async def record_adjustment(
        self,
        *,
        status: str,
        trade_count: int | None = None,
        avg_accuracy: float | None = None,
        previous_weights: dict | None = None,
        new_weights: dict | None = None,
        accuracies: dict | None = None,
        skip_reason: str | None = None,
        notes: str | None = None,
        db: AsyncSession | None = None,
    ) -> int:
        session, owns = self._session(db)
        try:
            record = AdjustmentRun(
                status=status,
                skip_reason=skip_reason,
                trade_count=trade_count,
                avg_accuracy=avg_accuracy,
                previous_weights=previous_weights,
                new_weights=new_weights,
                accuracies=accuracies,
                notes=notes,
                finished_at=datetime.now(UTC),
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record.id
        finally:
            if owns:
                await session.close()

    async def latest_successful_weights(
        self,
        db: AsyncSession | None = None,
    ) -> dict[str, float] | None:
        """Most-recent non-skipped adjustment's new_weights, if any.

        Called from ``weight_orchestrator.hydrate_from_db()`` on
        startup so a process restart picks up where the previous
        one left off instead of resetting to defaults.
        """
        session, owns = self._session(db)
        try:
            result = await session.execute(
                select(AdjustmentRun)
                .where(AdjustmentRun.status == "ok")
                .order_by(AdjustmentRun.started_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row is None or not row.new_weights:
                return None
            return {k: float(v) for k, v in row.new_weights.items()}
        finally:
            if owns:
                await session.close()

    def _session(self, db: AsyncSession | None) -> tuple[AsyncSession, bool]:
        if db is not None:
            return db, False
        return self._session_factory(), True


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _trade_to_dict(row: Trade) -> dict[str, Any]:
    return {
        "id": row.id,
        "source_trade_id": row.source_trade_id,
        "signal_id": row.signal_id,
        "symbol": row.symbol,
        "timeframe": row.timeframe,
        "direction": row.direction,
        "entry_price": row.entry_price,
        "exit_price": row.exit_price,
        "entry_time": row.entry_time.isoformat() if row.entry_time else None,
        "exit_time": row.exit_time.isoformat() if row.exit_time else None,
        "pnl_percent": row.pnl_percent,
        "risk_reward": row.risk_reward,
        "target_rr": row.target_rr,
        "max_drawdown_percent": row.max_drawdown_percent,
        "max_favorable_excursion": row.max_favorable_excursion,
        "duration_hours": row.duration_hours,
        "actual_outcome": row.actual_outcome,
        "scores_at_entry": row.scores_at_entry,
        "notes": row.notes,
        "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
    }


# Default global instance — most callers don't need to construct their own.
trade_store = SQLAlchemyTradeStore()


__all__ = ["SQLAlchemyTradeStore", "trade_store"]
