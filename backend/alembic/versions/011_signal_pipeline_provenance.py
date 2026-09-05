"""signal pipeline provenance + signal_outcomes table

Adds columns to the signals table so every emitted signal carries the
full factor payload, the weights that were used at scoring time, the
ML boost if any, and the pipeline / model versions. Without these,
downstream phases (self-learning feedback, walk-forward gating, and
the quality auto-disable) have nothing to read from.

Also creates the signal_outcomes table that the resolver will write
forward-return, MAE, MFE, and resolution_method into. The resolver
previously only wrote the categorical `result` column on `signals`
(tp_hit / sl_hit / expired), which is not enough to evaluate signal
quality — a signal can be a TP winner with deep drawdown, and that
information must be retained to support the per-(factor, symbol,
timeframe) quality gate in Phase 5.

Revision ID: 011_signal_pipeline_provenance
Revises: 010_query_hot_path_indexes
Create Date: 2026-09-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision = "011_signal_pipeline_provenance"
down_revision = "010_query_hot_path_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Extend signals with provenance columns.
    op.add_column(
        "signals",
        sa.Column("factor_payload", JSONB, nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("weights_used", JSONB, nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("ml_boost", sa.Float, nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("pipeline_version", sa.String(20), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("model_version", sa.String(50), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("source_engine", sa.String(50), nullable=True),
    )

    # 2. signal_outcomes — one row per resolved signal. Linked by
    # signal_id (unique) so we can join cleanly when computing
    # forward-return distribution per factor / symbol / timeframe.
    op.create_table(
        "signal_outcomes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("signal_id", sa.Integer, sa.ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("horizon_bars", sa.Integer, nullable=True),
        sa.Column("forward_return_pct", sa.Float, nullable=True),
        sa.Column("mae", sa.Float, nullable=True),
        sa.Column("mfe", sa.Float, nullable=True),
        sa.Column("resolved_price", sa.Float, nullable=True),
        sa.Column("bars_held", sa.Integer, nullable=True),
        sa.Column(
            "resolution_method",
            sa.String(20),
            nullable=False,
        ),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_signal_outcomes_signal_id",
        "signal_outcomes",
        ["signal_id"],
        unique=True,
    )
    op.create_index(
        "ix_signal_outcomes_resolved_at",
        "signal_outcomes",
        ["resolved_at"],
        unique=False,
    )
    op.create_index(
        "ix_signal_outcomes_method",
        "signal_outcomes",
        ["resolution_method"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_signal_outcomes_method", table_name="signal_outcomes")
    op.drop_index("ix_signal_outcomes_resolved_at", table_name="signal_outcomes")
    op.drop_index("ix_signal_outcomes_signal_id", table_name="signal_outcomes")
    op.drop_table("signal_outcomes")

    op.drop_column("signals", "source_engine")
    op.drop_column("signals", "model_version")
    op.drop_column("signals", "pipeline_version")
    op.drop_column("signals", "ml_boost")
    op.drop_column("signals", "weights_used")
    op.drop_column("signals", "factor_payload")
