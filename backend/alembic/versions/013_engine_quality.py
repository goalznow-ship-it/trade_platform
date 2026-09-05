"""engine_performance + circuit_breaker_state for the quality gate

Phase 5 observability + auto-disable.

Two new tables back the quality gate:

1. ``engine_performance`` — a per-engine rolling window of
   hit-rate, MAE, MFE, and signal count. The
   ``evaluate_quality`` cron job (every 15 min) computes a fresh
   row from the ``signals`` and ``signal_outcomes`` tables.
   The signal-pipeline reads the latest row when deciding
   whether to emit a new signal from a given engine — if the
   engine is ``disabled``, emit returns None.

2. ``circuit_breaker_state`` — one row per (engine, scope) pair.
   The breaker is tripped when N consecutive failures are
   observed (default 5). When tripped, the engine is blocked
   for ``open_duration_seconds`` (default 24h) before the
   ``half_open`` transition allows one probe. ``scope`` lets
   us separate breakers per symbol / per timeframe later.

Both tables are append-only from the cron job's perspective
but mutable by the operator (``/api/v1/admin/quality`` POST
endpoints).

Revision ID: 013_engine_quality
Revises: 012_self_learning_persistence
Create Date: 2026-09-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision = "013_engine_quality"
down_revision = "012_self_learning_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engine_performance",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("engine", sa.String(50), nullable=False, index=True),
        # Window start/end define what the row aggregates. The
        # cron job writes one row per window (default 24h).
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("n_signals", sa.Integer, nullable=False, server_default="0"),
        sa.Column("n_resolved", sa.Integer, nullable=False, server_default="0"),
        sa.Column("n_wins", sa.Integer, nullable=False, server_default="0"),
        sa.Column("hit_rate", sa.Float, nullable=True),
        sa.Column("avg_forward_return", sa.Float, nullable=True),
        sa.Column("avg_mae_bps", sa.Float, nullable=True),
        sa.Column("avg_mfe_bps", sa.Float, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ok"),
        # Disabled engines don't emit. Set by quality_gate when
        # the rolling hit rate falls below ``MIN_HIT_RATE``.
        sa.Column("is_disabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("disabled_reason", sa.String(200), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "ix_engine_perf_engine_recorded",
        "engine_performance",
        ["engine", "recorded_at"],
        unique=False,
    )
    op.create_index(
        "ix_engine_perf_engine_window",
        "engine_performance",
        ["engine", "window_start", "window_end"],
        unique=False,
    )

    op.create_table(
        "circuit_breaker_state",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("engine", sa.String(50), nullable=False, index=True),
        sa.Column("scope", sa.String(80), nullable=False, server_default="default"),
        # ``closed`` (normal), ``open`` (blocking), ``half_open``
        # (probe pending). The state machine is owned by
        # ``app.services.circuit_breaker``.
        sa.Column("state", sa.String(20), nullable=False, server_default="closed"),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failure_threshold", sa.Integer, nullable=False, server_default="5"),
        sa.Column("open_duration_seconds", sa.Integer, nullable=False, server_default="86400"),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("half_open_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_transition_reason", sa.String(200), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_circuit_breaker_engine_scope",
        "circuit_breaker_state",
        ["engine", "scope"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_circuit_breaker_engine_scope", table_name="circuit_breaker_state")
    op.drop_table("circuit_breaker_state")
    op.drop_index("ix_engine_perf_engine_window", table_name="engine_performance")
    op.drop_index("ix_engine_perf_engine_recorded", table_name="engine_performance")
    op.drop_table("engine_performance")
