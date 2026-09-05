"""self_learning persistence: trades + adjustment_runs

Replaces the in-memory trade history that
``SelfLearningEngine.trade_history`` previously kept (lost on every
process restart) with durable SQL tables. The self-learning loop
needs history across restarts for two reasons:

1. ``weight_orchestrator.hydrate_from_db()`` reads the most recent
   ``adjustment_runs.new_weights`` row on startup so the running
   engine starts with the same weights the previous process ended
   on — no regression after deploys.
2. The trade store is queryable for downstream analytics (per-symbol
   win rate, per-factor hit rate, MAE / MFE distribution) that the
   quality gate in Phase 5 reads from.

Also adds the ``adjustment_runs`` audit table so every weight
adjustment is reproducible. The negative test in Phase 2 — fewer
than 10 trades → skip with audit row — relies on this table.

Revision ID: 012_self_learning_persistence
Revises: 011_signal_pipeline_provenance
Create Date: 2026-09-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision = "012_self_learning_persistence"
down_revision = "011_signal_pipeline_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_trade_id", sa.String(80), nullable=True, index=True),
        sa.Column(
            "signal_id",
            sa.Integer,
            sa.ForeignKey("signals.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("timeframe", sa.String(5), nullable=True, index=True),
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
        sa.Column("actual_outcome", sa.String(10), nullable=True, index=True),
        sa.Column("scores_at_entry", JSONB, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "ix_trades_symbol_recorded",
        "trades",
        ["symbol", "recorded_at"],
        unique=False,
    )
    op.create_index(
        "ix_trades_outcome_recorded",
        "trades",
        ["actual_outcome", "recorded_at"],
        unique=False,
    )

    op.create_table(
        "adjustment_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("skip_reason", sa.String(120), nullable=True),
        sa.Column("trade_count", sa.Integer, nullable=True),
        sa.Column("avg_accuracy", sa.Float, nullable=True),
        sa.Column("previous_weights", JSONB, nullable=True),
        sa.Column("new_weights", JSONB, nullable=True),
        sa.Column("accuracies", JSONB, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_adjustment_runs_status_started",
        "adjustment_runs",
        ["status", "started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_adjustment_runs_status_started", table_name="adjustment_runs")
    op.drop_table("adjustment_runs")

    op.drop_index("ix_trades_outcome_recorded", table_name="trades")
    op.drop_index("ix_trades_symbol_recorded", table_name="trades")
    op.drop_table("trades")
