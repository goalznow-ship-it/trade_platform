"""Add enterprise tables: market_events, predictions, signal_history, news_events, liquidations, whale_activity, futures_metrics

Revision ID: 003
Revises: 002
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "market_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), server_default="info"),
        sa.Column("title", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("price_at_event", sa.Float()),
        sa.Column("volume_at_event", sa.Float()),
        sa.Column("metadata_json", JSON(), server_default="{}"),
        sa.Column("is_processed", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expired_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_events_symbol", "market_events", ["symbol"])
    op.create_index("ix_market_events_event_type", "market_events", ["event_type"])

    op.create_table(
        "price_predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("prediction", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0"),
        sa.Column("bullish_probability", sa.Float(), server_default="50"),
        sa.Column("bearish_probability", sa.Float(), server_default="50"),
        sa.Column("expected_move_pct", sa.Float(), server_default="0"),
        sa.Column("expected_target_price", sa.Float()),
        sa.Column("entry_zone_low", sa.Float()),
        sa.Column("entry_zone_high", sa.Float()),
        sa.Column("stop_loss", sa.Float()),
        sa.Column("take_profit_1", sa.Float()),
        sa.Column("take_profit_2", sa.Float()),
        sa.Column("risk_level", sa.String(20), server_default="medium"),
        sa.Column("risk_reward_ratio", sa.Float()),
        sa.Column("factors_used", JSON(), server_default="[]"),
        sa.Column("model_version", sa.String(20), server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("accuracy_at_resolution", sa.Float()),
        sa.Column("resolved_price", sa.Float()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_predictions_symbol", "price_predictions", ["symbol"])

    op.create_table(
        "ai_signals_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0"),
        sa.Column("entry_price", sa.Float()),
        sa.Column("stop_loss", sa.Float()),
        sa.Column("take_profit_1", sa.Float()),
        sa.Column("take_profit_2", sa.Float()),
        sa.Column("take_profit_3", sa.Float()),
        sa.Column("risk_reward", sa.Float()),
        sa.Column("signal_type", sa.String(50)),
        sa.Column("reasons", JSON(), server_default="[]"),
        sa.Column("factors", JSON(), server_default="{}"),
        sa.Column("market_structure", JSON(), server_default="{}"),
        sa.Column("futures_data", JSON(), server_default="{}"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("was_triggered", sa.Boolean(), server_default="false"),
        sa.Column("triggered_price", sa.Float()),
        sa.Column("pnl_at_resolution", sa.Float()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_signals_history_symbol", "ai_signals_history", ["symbol"])

    op.create_table(
        "news_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("source", sa.String(100)),
        sa.Column("category", sa.String(50), server_default="general"),
        sa.Column("summary", sa.Text()),
        sa.Column("content", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("sentiment", sa.String(20), server_default="neutral"),
        sa.Column("sentiment_score", sa.Float(), server_default="0"),
        sa.Column("impact", sa.String(20), server_default="low"),
        sa.Column("impact_score", sa.Float(), server_default="0"),
        sa.Column("affected_assets", JSON(), server_default="[]"),
        sa.Column("event_type", sa.String(50)),
        sa.Column("is_macro", sa.Boolean(), server_default="false"),
        sa.Column("is_regulation", sa.Boolean(), server_default="false"),
        sa.Column("is_whale", sa.Boolean(), server_default="false"),
        sa.Column("is_analyzed", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )

    op.create_table(
        "liquidations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Float()),
        sa.Column("price", sa.Float()),
        sa.Column("value_usd", sa.Float()),
        sa.Column("exchange", sa.String(50)),
        sa.Column("liquidation_type", sa.String(20), server_default="long"),
        sa.Column("is_whale", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_liquidations_symbol", "liquidations", ["symbol"])

    op.create_table(
        "whale_activity",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("activity_type", sa.String(50), nullable=False),
        sa.Column("direction", sa.String(10)),
        sa.Column("quantity", sa.Float()),
        sa.Column("value_usd", sa.Float()),
        sa.Column("price", sa.Float()),
        sa.Column("exchange", sa.String(50)),
        sa.Column("wallet_address", sa.String(255)),
        sa.Column("confidence", sa.Float(), server_default="0"),
        sa.Column("is_analyzed", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_whale_activity_symbol", "whale_activity", ["symbol"])

    op.create_table(
        "futures_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("funding_rate", sa.Float(), server_default="0"),
        sa.Column("funding_rate_8h", sa.Float(), server_default="0"),
        sa.Column("open_interest", sa.Float(), server_default="0"),
        sa.Column("open_interest_change_24h", sa.Float(), server_default="0"),
        sa.Column("volume_24h", sa.Float(), server_default="0"),
        sa.Column("long_short_ratio", sa.Float(), server_default="0"),
        sa.Column("long_accounts_pct", sa.Float(), server_default="50"),
        sa.Column("short_accounts_pct", sa.Float(), server_default="50"),
        sa.Column("liquidation_clusters", JSON(), server_default="[]"),
        sa.Column("whale_positions", JSON(), server_default="{}"),
        sa.Column("mark_price", sa.Float()),
        sa.Column("index_price", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_futures_metrics_symbol", "futures_metrics", ["symbol"])


def downgrade():
    op.drop_table("futures_metrics")
    op.drop_table("whale_activity")
    op.drop_table("liquidations")
    op.drop_table("news_events")
    op.drop_table("ai_signals_history")
    op.drop_table("price_predictions")
    op.drop_table("market_events")
