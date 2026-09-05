"""Split feedback-loop trades into their own table.

Phase 2 introduced the ``trades`` table that the self-learning
weight orchestrator reads from, but ``app.models.trade.Trade``
also declared ``__tablename__ = "trades"`` for the user-facing
trade journal. The two declarations collided at SQLAlchemy
registration time, so the earlier fix in commit 674c714 added
``extend_existing=True`` to merge them into a single table.
That merge produced a Frankenstein schema: the feedback loop's
``record_trade`` saw existing rows that didn't have its
``source_trade_id`` column populated, and treated every insert
as a duplicate, returning ``None`` — so ``adjust_weights`` ran
on zero trades.

This migration:

1. Creates a new ``feedback_trades`` table with the full
   self-learning schema (including the unique index on
   ``source_trade_id`` for idempotency).
2. Copies the data from ``trades`` into ``feedback_trades`` for
   any row whose columns align with the feedback schema
   (``source_trade_id`` IS NOT NULL). The user-journal rows
   stay in ``trades`` untouched.
3. Leaves the original ``trades`` columns in place — the
   weight orchestrator and the journal no longer share a
   table, and the journal still owns its data.

Revision ID: 014_split_feedback_trades
Revises: 013_engine_quality
Create Date: 2026-09-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "014_split_feedback_trades"
down_revision = "013_engine_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "feedback_trades" in inspector.get_table_names():
        # Re-running the migration on a partially-applied DB.
        return

    op.create_table(
        "feedback_trades",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_trade_id", sa.String(80), nullable=True),
        sa.Column(
            "signal_id",
            sa.Integer,
            sa.ForeignKey("signals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(5), nullable=True),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("entry_price", sa.Float, nullable=True),
        sa.Column("exit_price", sa.Float, nullable=True),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pnl_percent", sa.Float, nullable=True),
        sa.Column("risk_reward", sa.Float, nullable=True),
        sa.Column("target_rr", sa.Float, nullable=True),
        sa.Column("max_drawdown_percent", sa.Float, nullable=True),
        sa.Column("max_favorable_excursion", sa.Float, nullable=True),
        sa.Column("duration_hours", sa.Float, nullable=True),
        sa.Column("actual_outcome", sa.String(10), nullable=True),
        sa.Column("scores_at_entry", sa.JSON, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_feedback_trades_source_id",
        "feedback_trades",
        ["source_trade_id"],
        unique=True,
    )
    op.create_index(
        "ix_feedback_trades_symbol_recorded",
        "feedback_trades",
        ["symbol", "recorded_at"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_trades_outcome_recorded",
        "feedback_trades",
        ["actual_outcome", "recorded_at"],
        unique=False,
    )

    # Backfill: copy rows that look like feedback-loop entries
    # (i.e. they have a source_trade_id) from the shared table
    # into the new one. Rows without source_trade_id belong to
    # the user-journal side and stay in ``trades``.
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            INSERT INTO feedback_trades (
                id, source_trade_id, signal_id, symbol, timeframe,
                direction, entry_price, exit_price, entry_time,
                exit_time, pnl_percent, risk_reward, target_rr,
                max_drawdown_percent, max_favorable_excursion,
                duration_hours, actual_outcome, scores_at_entry,
                notes, recorded_at
            )
            SELECT
                id, source_trade_id, signal_id, symbol, timeframe,
                direction, entry_price, exit_price, entry_time,
                exit_time, pnl_percent, risk_reward, target_rr,
                max_drawdown_percent, max_favorable_excursion,
                duration_hours, actual_outcome, scores_at_entry,
                notes, recorded_at
            FROM trades
            WHERE source_trade_id IS NOT NULL
            ON CONFLICT (source_trade_id) DO NOTHING
            """
        )


def downgrade() -> None:
    op.drop_index("ix_feedback_trades_outcome_recorded", "feedback_trades")
    op.drop_index("ix_feedback_trades_symbol_recorded", "feedback_trades")
    op.drop_index("ix_feedback_trades_source_id", "feedback_trades")
    op.drop_table("feedback_trades")
