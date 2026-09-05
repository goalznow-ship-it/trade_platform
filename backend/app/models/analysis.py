from sqlalchemy import JSON, BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
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
    result = Column(String(20), nullable=True)  # new, active, tp1_hit, tp2_hit, tp3_hit, sl_hit
    expires_at = Column(DateTime, nullable=True)

    # Phase 1 — pipeline provenance. Populated by signal_pipeline.emit so
    # downstream phases (self-learning, walk-forward gating, quality
    # auto-disable) can read the exact factors and weights that produced
    # the score at emit time.
    factor_payload = Column(JSONB, nullable=True)
    weights_used = Column(JSONB, nullable=True)
    ml_boost = Column(Float, nullable=True)
    pipeline_version = Column(String(20), nullable=True)
    model_version = Column(String(50), nullable=True)
    source_engine = Column(String(50), nullable=True)

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


class SignalOutcome(Base):
    """Resolved-signal telemetry written by the outcome resolver.

    The resolver walks the live candle stream forward from each emitted
    signal's entry timestamp and records:
      - forward_return_pct — signed return from entry to first TP / SL
        / horizon, depending on resolution_method.
      - mae / mfe — worst adverse and best favorable excursion in
        percent, computed against the M1 candles between entry and
        resolution. Captured so the quality gate can penalize signals
        that print winners only after a deep drawdown.
      - bars_held — how many candles the trade was live.
      - resolution_method — tp_hit / sl_hit / expired / manual.

    One row per signal (signal_id is unique). The self-learning loop
    joins on this table to compute per-(factor, symbol, timeframe)
    forward-return distributions and adjust scoring weights.
    """

    __tablename__ = "signal_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(
        Integer,
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    resolved_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    horizon_bars = Column(Integer, nullable=True)
    forward_return_pct = Column(Float, nullable=True)
    mae = Column(Float, nullable=True)
    mfe = Column(Float, nullable=True)
    resolved_price = Column(Float, nullable=True)
    bars_held = Column(Integer, nullable=True)
    resolution_method = Column(String(20), nullable=False, index=True)
    notes = Column(Text, nullable=True)
