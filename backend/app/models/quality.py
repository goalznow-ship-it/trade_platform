"""Phase 5: engine quality / observability models.

Two tables back the quality gate and circuit breaker:

* ``EnginePerformance`` — rolling-window aggregates (hit rate,
  MAE, MFE, signal count) per engine. The ``evaluate_quality``
  cron job inserts a fresh row every window. The signal
  pipeline reads the latest row to decide whether the engine
  is allowed to emit.

* ``CircuitBreakerState`` — one row per (engine, scope). The
  state machine is owned by
  ``app.services.circuit_breaker.CircuitBreaker``. The model
  just stores the persistent half of the state so a process
  restart doesn't drop the open-circuit information.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
)
from sqlalchemy.sql import func

from app.core.database import Base


class EnginePerformance(Base):
    __tablename__ = "engine_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engine = Column(String(50), nullable=False, index=True)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    n_signals = Column(Integer, nullable=False, default=0)
    n_resolved = Column(Integer, nullable=False, default=0)
    n_wins = Column(Integer, nullable=False, default=0)
    hit_rate = Column(Float, nullable=True)
    avg_forward_return = Column(Float, nullable=True)
    avg_mae_bps = Column(Float, nullable=True)
    avg_mfe_bps = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="ok")
    # ``is_disabled=True`` means the quality gate has flagged
    # this engine. The pipeline checks this before emitting.
    is_disabled = Column(Boolean, nullable=False, default=False)
    disabled_reason = Column(String(200), nullable=True)
    disabled_at = Column(DateTime(timezone=True), nullable=True)
    recorded_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class CircuitBreakerState(Base):
    __tablename__ = "circuit_breaker_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engine = Column(String(50), nullable=False, index=True)
    scope = Column(String(80), nullable=False, default="default")
    state = Column(String(20), nullable=False, default="closed")
    consecutive_failures = Column(Integer, nullable=False, default=0)
    failure_threshold = Column(Integer, nullable=False, default=5)
    open_duration_seconds = Column(Integer, nullable=False, default=86_400)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    half_open_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_transition_reason = Column(String(200), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


__all__ = ["EnginePerformance", "CircuitBreakerState"]
