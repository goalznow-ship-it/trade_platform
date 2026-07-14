"""initial migration

Revision ID: 001
Revises:
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("display_name", sa.String(length=50), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=True, server_default=sa.text("'UTC'")),
        sa.Column("language", sa.String(length=10), nullable=True, server_default=sa.text("'en'")),
        sa.Column("theme", sa.String(length=20), nullable=True, server_default=sa.text("'dark'")),
        sa.Column("balance", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("total_pnl", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("win_rate", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("total_trades", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("subscription_tier", sa.String(length=20), nullable=True, server_default=sa.text("'free'")),
        sa.Column("subscription_expires", sa.DateTime(), nullable=True),
        sa.Column("telegram_id", sa.String(length=50), nullable=True),
        sa.Column("discord_id", sa.String(length=50), nullable=True),
        sa.Column("notification_settings", sa.JSON(), nullable=True),
        sa.Column("binance_api_key", sa.String(length=255), nullable=True),
        sa.Column("binance_secret_key", sa.String(length=255), nullable=True),
        sa.Column("bybit_api_key", sa.String(length=255), nullable=True),
        sa.Column("bybit_secret_key", sa.String(length=255), nullable=True),
        sa.Column("twofa_secret", sa.String(length=100), nullable=True),
        sa.Column("twofa_enabled", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "symbols",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.Column("base_asset", sa.String(length=10), nullable=True),
        sa.Column("quote_asset", sa.String(length=10), nullable=True, server_default=sa.text("'USDT'")),
        sa.Column("exchange", sa.String(length=20), nullable=True, server_default=sa.text("'binance'")),
        sa.Column("asset_type", sa.String(length=10), nullable=True, server_default=sa.text("'crypto'")),
        sa.Column("price_precision", sa.Integer(), nullable=True, server_default=sa.text("2")),
        sa.Column("quantity_precision", sa.Integer(), nullable=True, server_default=sa.text("4")),
        sa.Column("min_notional", sa.Float(), nullable=True, server_default=sa.text("10.0")),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("is_futures", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_symbols_id", "symbols", ["id"])
    op.create_index("ix_symbols_name", "symbols", ["name"], unique=True)

    op.create_table(
        "candles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=5), nullable=False),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("trades", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_candles_id", "candles", ["id"])
    op.create_index("ix_candles_symbol_id", "candles", ["symbol_id"])

    op.create_table(
        "tickers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("price_change_24h", sa.Float(), nullable=True),
        sa.Column("price_change_percent_24h", sa.Float(), nullable=True),
        sa.Column("high_24h", sa.Float(), nullable=True),
        sa.Column("low_24h", sa.Float(), nullable=True),
        sa.Column("volume_24h", sa.Float(), nullable=True),
        sa.Column("market_cap", sa.Float(), nullable=True, server_default=sa.text("0")),
        sa.Column("dominance", sa.Float(), nullable=True, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tickers_id", "tickers", ["id"])
    op.create_index("ix_tickers_symbol_id", "tickers", ["symbol_id"])

    op.create_table(
        "indicators",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=5), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_indicators_id", "indicators", ["id"])
    op.create_index("ix_indicators_symbol_id", "indicators", ["symbol_id"])

    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("timeframe", sa.String(length=5), nullable=True),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("strength", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("entry_price", sa.Float(), nullable=True),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("take_profit_1", sa.Float(), nullable=True),
        sa.Column("take_profit_2", sa.Float(), nullable=True),
        sa.Column("take_profit_3", sa.Float(), nullable=True),
        sa.Column("risk_reward", sa.Float(), nullable=True),
        sa.Column("leverage", sa.Integer(), nullable=True, server_default=sa.text("1")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("signal_type", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("is_triggered", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("triggered_price", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signals_id", "signals", ["id"])
    op.create_index("ix_signals_symbol_id", "signals", ["symbol_id"])

    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("timeframe", sa.String(length=5), nullable=True),
        sa.Column("trend_score", sa.Float(), nullable=True),
        sa.Column("momentum_score", sa.Float(), nullable=True),
        sa.Column("volume_score", sa.Float(), nullable=True),
        sa.Column("volatility_score", sa.Float(), nullable=True),
        sa.Column("liquidity_score", sa.Float(), nullable=True),
        sa.Column("market_structure_score", sa.Float(), nullable=True),
        sa.Column("smc_score", sa.Float(), nullable=True),
        sa.Column("ict_score", sa.Float(), nullable=True),
        sa.Column("news_sentiment_score", sa.Float(), nullable=True),
        sa.Column("fear_greed_score", sa.Float(), nullable=True),
        sa.Column("open_interest_score", sa.Float(), nullable=True),
        sa.Column("funding_rate_score", sa.Float(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(length=10), nullable=True),
        sa.Column("prediction", sa.String(length=10), nullable=True),
        sa.Column("long_probability", sa.Float(), nullable=True),
        sa.Column("short_probability", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_analyses_id", "ai_analyses", ["id"])
    op.create_index("ix_ai_analyses_symbol_id", "ai_analyses", ["symbol_id"])

    op.create_table(
        "patterns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("timeframe", sa.String(length=5), nullable=True),
        sa.Column("pattern_type", sa.String(length=50), nullable=True),
        sa.Column("direction", sa.String(length=10), nullable=True),
        sa.Column("start_price", sa.Float(), nullable=True),
        sa.Column("end_price", sa.Float(), nullable=True),
        sa.Column("target_price", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("detected_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patterns_id", "patterns", ["id"])
    op.create_index("ix_patterns_symbol_id", "patterns", ["symbol_id"])

    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=True, server_default=sa.text("'market'")),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("stop_price", sa.Float(), nullable=True),
        sa.Column("leverage", sa.Integer(), nullable=True, server_default=sa.text("1")),
        sa.Column("margin_mode", sa.String(length=10), nullable=True, server_default=sa.text("'isolated'")),
        sa.Column("status", sa.String(length=20), nullable=True, server_default=sa.text("'open'")),
        sa.Column("pnl", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("pnl_percent", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("commission", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("exchange", sa.String(length=20), nullable=True, server_default=sa.text("'binance'")),
        sa.Column("exchange_order_id", sa.String(length=100), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trades_id", "trades", ["id"])
    op.create_index("ix_trades_user_id", "trades", ["user_id"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("trade_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("stop_price", sa.Float(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("filled_quantity", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("status", sa.String(length=20), nullable=True, server_default=sa.text("'pending'")),
        sa.Column("exchange_order_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_id", "orders", ["id"])
    op.create_index("ix_orders_user_id", "orders", ["user_id"])

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("size", sa.Float(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("mark_price", sa.Float(), nullable=False),
        sa.Column("liquidation_price", sa.Float(), nullable=True),
        sa.Column("leverage", sa.Integer(), nullable=True, server_default=sa.text("1")),
        sa.Column("margin", sa.Float(), nullable=False),
        sa.Column("unrealized_pnl", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("realized_pnl", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("take_profit", sa.Float(), nullable=True),
        sa.Column("exchange", sa.String(length=20), nullable=True, server_default=sa.text("'binance'")),
        sa.Column("is_open", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_positions_id", "positions", ["id"])
    op.create_index("ix_positions_user_id", "positions", ["user_id"])

    op.create_table(
        "trade_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("side", sa.String(length=10), nullable=True),
        sa.Column("type", sa.String(length=20), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("entry_price", sa.Float(), nullable=True),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("pnl", sa.Float(), nullable=True),
        sa.Column("pnl_percent", sa.Float(), nullable=True),
        sa.Column("roi", sa.Float(), nullable=True),
        sa.Column("leverage", sa.Integer(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("take_profit", sa.Float(), nullable=True),
        sa.Column("risk_reward", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("exchange", sa.String(length=20), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trade_history_id", "trade_history", ["id"])
    op.create_index("ix_trade_history_user_id", "trade_history", ["user_id"])

    op.create_table(
        "news",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True, server_default=sa.text("'crypto'")),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=100), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True, server_default=sa.text("'en'")),
        sa.Column("image_url", sa.String(length=1000), nullable=True),
        sa.Column("is_analyzed", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index("ix_news_id", "news", ["id"])

    op.create_table(
        "news_analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("news_id", sa.Integer(), nullable=False),
        sa.Column("sentiment", sa.String(length=20), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("impact_score", sa.Float(), nullable=True),
        sa.Column("relevant_symbols", sa.JSON(), nullable=True),
        sa.Column("market_impact", sa.String(length=20), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_news_analyses_id", "news_analyses", ["id"])
    op.create_index("ix_news_analyses_news_id", "news_analyses", ["news_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.String(length=50), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("exchange", sa.String(length=20), nullable=False),
        sa.Column("api_key", sa.String(length=255), nullable=False),
        sa.Column("secret_key", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("permissions", sa.JSON(), nullable=True),
        sa.Column("last_used", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_id", "api_keys", ["id"])
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=True, server_default=sa.text("'in_app'")),
        sa.Column("is_read", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("is_sent", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("related_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=True, server_default=sa.text("'free'")),
        sa.Column("price", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("signals_per_day", sa.Integer(), nullable=True, server_default=sa.text("10")),
        sa.Column("max_watchlist", sa.Integer(), nullable=True, server_default=sa.text("10")),
        sa.Column("has_backtest", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("has_api_access", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("start_date", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_subscriptions_id", "subscriptions", ["id"])
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("total_balance", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("total_pnl", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("total_pnl_percent", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("daily_pnl", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("monthly_pnl", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("total_trades", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("win_rate", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("avg_risk_reward", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("best_trade", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("worst_trade", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_portfolios_id", "portfolios", ["id"])
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])

    op.create_table(
        "portfolio_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("avg_entry", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("current_price", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("value", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("pnl", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("pnl_percent", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("allocation_percent", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portfolio_assets_id", "portfolio_assets", ["id"])
    op.create_index("ix_portfolio_assets_portfolio_id", "portfolio_assets", ["portfolio_id"])

    op.create_table(
        "backtest_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("timeframe", sa.String(length=5), nullable=True),
        sa.Column("strategy_name", sa.String(length=100), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("win_rate", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("profit_factor", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("sharpe_ratio", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("max_drawdown", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("total_return", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("avg_risk_reward", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("monthly_results", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backtest_results_id", "backtest_results", ["id"])
    op.create_index("ix_backtest_results_user_id", "backtest_results", ["user_id"])


def downgrade() -> None:
    op.drop_table("backtest_results")
    op.drop_table("portfolio_assets")
    op.drop_table("portfolios")
    op.drop_table("subscriptions")
    op.drop_table("notifications")
    op.drop_table("api_keys")
    op.drop_table("audit_logs")
    op.drop_table("news_analyses")
    op.drop_table("news")
    op.drop_table("trade_history")
    op.drop_table("positions")
    op.drop_table("orders")
    op.drop_table("trades")
    op.drop_table("patterns")
    op.drop_table("ai_analyses")
    op.drop_table("signals")
    op.drop_table("indicators")
    op.drop_table("tickers")
    op.drop_table("candles")
    op.drop_table("symbols")
    op.drop_table("users")
