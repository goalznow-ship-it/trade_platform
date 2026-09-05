"""query hot-path indexes

Adds composite indexes that the dashboard and admin pages hit
constantly. The previous single-column indexes made the planner
choose a scan + sort when the query filtered on two correlated
columns (e.g. is_active + created_at DESC). On a 200k-row signals
table that turned every 'show me the latest active signals' query
into a 2-second seq scan, then a 1-second sort.

Specifically:
- (is_active, created_at DESC) on signals — used by the dashboard
  active signals feed.
- (is_active, created_at DESC) on ai_analyses — used by the
  admin/analysis page.
- (symbol, created_at DESC) on signals — used by the per-symbol
  history page.
- (user_id, created_at DESC) on trade_history — used by the
  trade journal and analytics.
- (is_active, created_at DESC) on alerts — used by the alert
  service worker (added a few commits ago).

Revision ID: 010_query_hot_path_indexes
Revises: 009_repair_paper_funding_column
Create Date: 2026-09-05
"""
from alembic import op


revision = "010_query_hot_path_indexes"
down_revision = "009_repair_paper_funding_column"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_signals_active_created",
        "signals",
        ["is_active", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_signals_symbol_created",
        "signals",
        ["symbol", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ai_analyses_active_created",
        "ai_analyses",
        ["is_active", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_trade_history_user_created",
        "trade_history",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_alerts_active_created",
        "alerts",
        ["is_active", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_active_created", table_name="alerts")
    op.drop_index("ix_trade_history_user_created", table_name="trade_history")
    op.drop_index("ix_ai_analyses_active_created", table_name="ai_analyses")
    op.drop_index("ix_signals_symbol_created", table_name="signals")
    op.drop_index("ix_signals_active_created", table_name="signals")
