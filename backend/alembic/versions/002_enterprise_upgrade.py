"""enterprise upgrade - watchlists, alerts, risk, journal, paper trading, trade history notes

Revision ID: 002
Revises: 001
Create Date: 2026-07-14 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Watchlists
    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_watchlists_id", "watchlists", ["id"])
    op.create_index("ix_watchlists_user_id", "watchlists", ["user_id"])

    op.create_table(
        "watchlist_symbols",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("watchlist_id", sa.Integer(), sa.ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(20), server_default=sa.text("'binance'")),
        sa.Column("is_favorite", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0")),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_watchlist_symbols_id", "watchlist_symbols", ["id"])
    op.create_index("ix_watchlist_symbols_watchlist_id", "watchlist_symbols", ["watchlist_id"])

    # Alerts
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(20), server_default=sa.text("'binance'")),
        sa.Column("timeframe", sa.String(5), nullable=True),
        sa.Column("condition", sa.String(20), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("value_secondary", sa.Float(), nullable=True),
        sa.Column("comparison_symbol", sa.String(20), nullable=True),
        sa.Column("channels", sa.JSON(), nullable=True),
        sa.Column("cooldown_minutes", sa.Integer(), server_default=sa.text("0")),
        sa.Column("max_triggers", sa.Integer(), server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_recurring", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_id", "alerts", ["id"])
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])

    op.create_table(
        "alert_triggers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("triggered_value", sa.Float(), nullable=False),
        sa.Column("triggered_at_price", sa.Float(), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("sent", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("delivered", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_triggers_id", "alert_triggers", ["id"])
    op.create_index("ix_alert_triggers_alert_id", "alert_triggers", ["alert_id"])

    # Risk
    op.create_table(
        "risk_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("max_daily_loss", sa.Float(), server_default=sa.text("500.0")),
        sa.Column("max_weekly_loss", sa.Float(), server_default=sa.text("1500.0")),
        sa.Column("max_monthly_loss", sa.Float(), server_default=sa.text("3000.0")),
        sa.Column("max_position_size", sa.Float(), server_default=sa.text("1000.0")),
        sa.Column("max_leverage", sa.Integer(), server_default=sa.text("20")),
        sa.Column("max_open_positions", sa.Integer(), server_default=sa.text("10")),
        sa.Column("max_correlation", sa.Float(), server_default=sa.text("0.7")),
        sa.Column("risk_per_trade", sa.Float(), server_default=sa.text("0.02")),
        sa.Column("max_drawdown", sa.Float(), server_default=sa.text("0.25")),
        sa.Column("stop_loss_default", sa.Float(), server_default=sa.text("0.02")),
        sa.Column("take_profit_default", sa.Float(), server_default=sa.text("0.04")),
        sa.Column("enable_auto_liquidation_alerts", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("risk_score_threshold", sa.Float(), server_default=sa.text("0.7")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_profiles_id", "risk_profiles", ["id"])
    op.create_index("ix_risk_profiles_user_id", "risk_profiles", ["user_id"])

    op.create_table(
        "risk_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_exposure", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("daily_pnl", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("weekly_pnl", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("monthly_pnl", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("max_drawdown", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("current_drawdown", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("liquidation_distance", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("portfolio_risk_score", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("sharpe_ratio", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("sortino_ratio", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("profit_factor", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("expectancy", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("kelly_percent", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("var_95", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("cvar_95", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("total_balance", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("open_position_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("margin_used", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("margin_free", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_snapshots_id", "risk_snapshots", ["id"])
    op.create_index("ix_risk_snapshots_user_id", "risk_snapshots", ["user_id"])

    # Journal
    op.create_table(
        "trade_journals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_id", sa.Integer(), sa.ForeignKey("trade_history.id", ondelete="SET NULL"), nullable=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("lessons", sa.Text(), nullable=True),
        sa.Column("emotion", sa.String(20), nullable=True),
        sa.Column("mistakes", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("strategy", sa.String(100), nullable=True),
        sa.Column("setup_description", sa.Text(), nullable=True),
        sa.Column("entry_reason", sa.Text(), nullable=True),
        sa.Column("exit_reason", sa.Text(), nullable=True),
        sa.Column("rating", sa.String(10), nullable=True),
        sa.Column("win_loss_reason", sa.Text(), nullable=True),
        sa.Column("screenshot_urls", sa.JSON(), nullable=True),
        sa.Column("executed_plan", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("followed_rules", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("psychological_state", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trade_journals_id", "trade_journals", ["id"])
    op.create_index("ix_trade_journals_user_id", "trade_journals", ["user_id"])
    op.create_index("ix_trade_journals_trade_id", "trade_journals", ["trade_id"])

    # Paper Trading
    op.create_table(
        "paper_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("name", sa.String(100), server_default=sa.text("'Paper Trading'")),
        sa.Column("balance", sa.Float(), server_default=sa.text("100000.0")),
        sa.Column("initial_balance", sa.Float(), server_default=sa.text("100000.0")),
        sa.Column("equity", sa.Float(), server_default=sa.text("100000.0")),
        sa.Column("free_margin", sa.Float(), server_default=sa.text("100000.0")),
        sa.Column("used_margin", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("total_pnl", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("total_trades", sa.Integer(), server_default=sa.text("0")),
        sa.Column("win_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("loss_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("win_rate", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("sharpe_ratio", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("max_drawdown", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("best_trade", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("worst_trade", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("profit_factor", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_accounts_id", "paper_accounts", ["id"])
    op.create_index("ix_paper_accounts_user_id", "paper_accounts", ["user_id"])

    op.create_table(
        "paper_positions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("size", sa.Float(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("mark_price", sa.Float(), nullable=True),
        sa.Column("liquidation_price", sa.Float(), nullable=True),
        sa.Column("leverage", sa.Integer(), server_default=sa.text("1")),
        sa.Column("margin", sa.Float(), nullable=False),
        sa.Column("unrealized_pnl", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("realized_pnl", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("take_profit", sa.Float(), nullable=True),
        sa.Column("is_open", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_positions_id", "paper_positions", ["id"])
    op.create_index("ix_paper_positions_account_id", "paper_positions", ["account_id"])

    op.create_table(
        "paper_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("order_type", sa.String(20), server_default=sa.text("'market'")),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("stop_price", sa.Float(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("filled_quantity", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'")),
        sa.Column("leverage", sa.Integer(), server_default=sa.text("1")),
        sa.Column("reduce_only", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("time_in_force", sa.String(10), server_default=sa.text("'GTC'")),
        sa.Column("executed_price", sa.Float(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_orders_id", "paper_orders", ["id"])
    op.create_index("ix_paper_orders_account_id", "paper_orders", ["account_id"])

    # Exchange Credentials
    op.create_table(
        "exchange_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("api_key", sa.String(255), nullable=False),
        sa.Column("secret_key", sa.String(255), nullable=False),
        sa.Column("passphrase", sa.String(255), nullable=True),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("permissions", sa.JSON(), nullable=True),
        sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_exchange_credentials_id", "exchange_credentials", ["id"])
    op.create_index("ix_exchange_credentials_user_id", "exchange_credentials", ["user_id"])

    # Add notes and tags to trade_history
    op.add_column("trade_history", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("trade_history", sa.Column("tags", sa.JSON(), nullable=True))

    # Add index on trade_history closed_at for analytics
    op.create_index("ix_trade_history_closed_at", "trade_history", ["closed_at"])


def downgrade() -> None:
    op.drop_table("exchange_credentials")
    op.drop_table("paper_orders")
    op.drop_table("paper_positions")
    op.drop_table("paper_accounts")
    op.drop_table("trade_journals")
    op.drop_table("risk_snapshots")
    op.drop_table("risk_profiles")
    op.drop_table("alert_triggers")
    op.drop_table("alerts")
    op.drop_table("watchlist_symbols")
    op.drop_table("watchlists")
    op.drop_index("ix_trade_history_closed_at", table_name="trade_history")
    op.drop_column("trade_history", "tags")
    op.drop_column("trade_history", "notes")
