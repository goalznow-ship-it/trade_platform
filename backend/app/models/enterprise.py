from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, JSON, Text
from sqlalchemy.sql import func
from app.core.database import Base


class MarketEvent(Base):
    __tablename__ = "market_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), default="info")
    title = Column(String(255))
    description = Column(Text)
    price_at_event = Column(Float)
    volume_at_event = Column(Float)
    metadata_json = Column(JSON, default=dict)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expired_at = Column(DateTime(timezone=True), nullable=True)


class PricePrediction(Base):
    __tablename__ = "price_predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    prediction = Column(String(20), nullable=False)
    confidence = Column(Float, default=0)
    bullish_probability = Column(Float, default=50)
    bearish_probability = Column(Float, default=50)
    expected_move_pct = Column(Float, default=0)
    expected_target_price = Column(Float)
    entry_zone_low = Column(Float)
    entry_zone_high = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)
    risk_level = Column(String(20), default="medium")
    risk_reward_ratio = Column(Float)
    factors_used = Column(JSON, default=list)
    model_version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True)
    accuracy_at_resolution = Column(Float, nullable=True)
    resolved_price = Column(Float, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AISignalHistory(Base):
    __tablename__ = "ai_signals_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    direction = Column(String(20), nullable=False)
    confidence = Column(Float, default=0)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)
    take_profit_3 = Column(Float)
    risk_reward = Column(Float)
    signal_type = Column(String(50))
    reasons = Column(JSON, default=list)
    factors = Column(JSON, default=dict)
    market_structure = Column(JSON, default=dict)
    futures_data = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    was_triggered = Column(Boolean, default=False)
    triggered_price = Column(Float, nullable=True)
    pnl_at_resolution = Column(Float, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NewsEvent(Base):
    __tablename__ = "news_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False)
    source = Column(String(100))
    category = Column(String(50), default="general")
    summary = Column(Text)
    content = Column(Text)
    published_at = Column(DateTime(timezone=True))
    sentiment = Column(String(20), default="neutral")
    sentiment_score = Column(Float, default=0)
    impact = Column(String(20), default="low")
    impact_score = Column(Float, default=0)
    affected_assets = Column(JSON, default=list)
    event_type = Column(String(50))
    is_macro = Column(Boolean, default=False)
    is_regulation = Column(Boolean, default=False)
    is_whale = Column(Boolean, default=False)
    is_analyzed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Liquidation(Base):
    __tablename__ = "liquidations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    quantity = Column(Float)
    price = Column(Float)
    value_usd = Column(Float)
    exchange = Column(String(50))
    liquidation_type = Column(String(20), default="long")
    is_whale = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WhaleActivity(Base):
    __tablename__ = "whale_activity"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False)
    direction = Column(String(10))
    quantity = Column(Float)
    value_usd = Column(Float)
    price = Column(Float)
    exchange = Column(String(50))
    wallet_address = Column(String(255), nullable=True)
    confidence = Column(Float, default=0)
    is_analyzed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FuturesMetrics(Base):
    __tablename__ = "futures_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    funding_rate = Column(Float, default=0)
    funding_rate_8h = Column(Float, default=0)
    open_interest = Column(Float, default=0)
    open_interest_change_24h = Column(Float, default=0)
    volume_24h = Column(Float, default=0)
    long_short_ratio = Column(Float, default=0)
    long_accounts_pct = Column(Float, default=50)
    short_accounts_pct = Column(Float, default=50)
    liquidation_clusters = Column(JSON, default=list)
    whale_positions = Column(JSON, default=dict)
    mark_price = Column(Float)
    index_price = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
