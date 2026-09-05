"""Persistence models for the self-learning feedback loop.

These tables back the SQLAlchemy trade store and the weight-adjustment
audit trail. The store replaces the in-memory list that
``SelfLearningEngine`` previously used, so that:

- a process restart does not lose history,
- the weight orchestrator can hydrate ``current_weights`` from the
  most recent successful ``adjustment_runs`` row on startup,
- the resolver's closed trades are queryable for downstream analytics
  (per-symbol win rate, per-factor hit rate, etc.).
"""
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base


class Trade(Base):
    """One row per closed trade observed by the resolver.

    The store is the source of truth that ``adjust_weights`` reads
    from. Schema mirrors the keys the in-memory engine used to keep
    (``scores_at_entry``, ``actual_outcome``, ``pnl_percent``) so the
    existing accuracy math keeps working without re-derivation.
    """

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_trade_id = Column(String(80), nullable=True, index=True)
    signal_id = Column(
        Integer,
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(5), nullable=True, index=True)
    direction = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    entry_time = Column(DateTime(timezone=True), nullable=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    pnl_percent = Column(Float, nullable=True)
    risk_reward = Column(Float, nullable=True)
    target_rr = Column(Float, nullable=True)
    max_drawdown_percent = Column(Float, nullable=True)
    max_favorable_excursion = Column(Float, nullable=True)
    duration_hours = Column(Float, nullable=True)
    actual_outcome = Column(String(10), nullable=True, index=True)
    scores_at_entry = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    recorded_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class AdjustmentRun(Base):
    """Audit row written every time ``adjust_weights`` runs.

    Stores the *previous* and *new* weight dicts plus per-category
    accuracies so the self-learning loop is reproducible: any
    ``current_weights`` value on the running engine can be traced
    back to a specific adjustment run. Rows with ``status='skipped'``
    capture the reason (e.g. <10 trades), satisfying the negative
    test in Phase 2's acceptance.
    """

    __tablename__ = "adjustment_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, index=True)  # ok | skipped | failed
    skip_reason = Column(String(120), nullable=True)
    trade_count = Column(Integer, nullable=True)
    avg_accuracy = Column(Float, nullable=True)
    previous_weights = Column(JSON, nullable=True)
    new_weights = Column(JSON, nullable=True)
    accuracies = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
