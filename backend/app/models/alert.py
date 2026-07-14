from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class AlertType(str, enum.Enum):
    PRICE = "price"
    EMA_CROSS = "ema_cross"
    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"
    MACD = "macd"
    RSI = "rsi"
    ADX = "adx"
    ATR = "atr"
    VOLUME_SPIKE = "volume_spike"
    FUNDING_RATE = "funding_rate"
    OPEN_INTEREST = "open_interest"
    FEAR_GREED = "fear_greed"
    WHALE_TRADE = "whale_trade"
    LIQUIDITY_GRAB = "liquidity_grab"
    SMC_EVENT = "smc_event"
    ICT_EVENT = "ict_event"
    TREND_CHANGE = "trend_change"


class AlertChannel(str, enum.Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    IN_APP = "in_app"
    PUSH = "push"


class AlertCondition(str, enum.Enum):
    ABOVE = "above"
    BELOW = "below"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"
    BETWEEN = "between"
    OUTSIDE = "outside"
    CHANGES_BY = "changes_by"
    EQUALS = "equals"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    alert_type = Column(String(50), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(20), default="binance")
    timeframe = Column(String(5), nullable=True)
    condition = Column(String(20), nullable=False)
    value = Column(Float, nullable=True)
    value_secondary = Column(Float, nullable=True)
    comparison_symbol = Column(String(20), nullable=True)
    channels = Column(JSON, default=lambda: ["in_app"])
    cooldown_minutes = Column(Integer, default=0)
    max_triggers = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, server_default="true")
    is_recurring = Column(Boolean, default=False, server_default="false")
    cooldown_until = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    alert_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    triggers = relationship("AlertTrigger", back_populates="alert", cascade="all, delete-orphan",
                            order_by="AlertTrigger.triggered_at.desc()")


class AlertTrigger(Base):
    __tablename__ = "alert_triggers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_value = Column(Float, nullable=False)
    triggered_at_price = Column(Float, nullable=True)
    channel = Column(String(20), nullable=False)
    sent = Column(Boolean, default=True)
    delivered = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())

    alert = relationship("Alert", back_populates="triggers")
