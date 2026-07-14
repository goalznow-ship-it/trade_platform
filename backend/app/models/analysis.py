from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol_id = Column(Integer, index=True, nullable=False)
    timeframe = Column(String(5), nullable=False)
    name = Column(String(50), nullable=False)
    value = Column(JSON)
    timestamp = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol_id = Column(Integer, index=True, nullable=False)
    symbol = Column(String(20))
    timeframe = Column(String(5))
    direction = Column(String(10), nullable=False)
    strength = Column(Float)
    confidence = Column(Float)
    risk_score = Column(Float)
    probability = Column(Float)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)
    take_profit_3 = Column(Float)
    risk_reward = Column(Float)
    leverage = Column(Integer, default=1)
    reason = Column(Text)
    ai_summary = Column(Text)
    signal_type = Column(String(50))
    is_active = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    triggered_price = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime, nullable=True)

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol_id = Column(Integer, index=True)
    symbol = Column(String(20))
    timeframe = Column(String(5))

    trend_score = Column(Float)
    momentum_score = Column(Float)
    volume_score = Column(Float)
    volatility_score = Column(Float)
    liquidity_score = Column(Float)
    market_structure_score = Column(Float)
    smc_score = Column(Float)
    ict_score = Column(Float)
    news_sentiment_score = Column(Float)
    fear_greed_score = Column(Float)
    open_interest_score = Column(Float)
    funding_rate_score = Column(Float)

    overall_score = Column(Float)
    confidence = Column(Float)
    risk_level = Column(String(10))
    prediction = Column(String(10))
    long_probability = Column(Float)
    short_probability = Column(Float)

    summary = Column(Text)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Pattern(Base):
    __tablename__ = "patterns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol_id = Column(Integer, index=True)
    symbol = Column(String(20))
    timeframe = Column(String(5))
    pattern_type = Column(String(50))
    direction = Column(String(10))
    start_price = Column(Float)
    end_price = Column(Float)
    target_price = Column(Float)
    confidence = Column(Float)
    detected_at = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
