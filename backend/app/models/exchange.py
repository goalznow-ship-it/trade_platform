from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ExchangeName(str, enum.Enum):
    BINANCE = "binance"
    BYBIT = "bybit"
    OKX = "okx"
    BITGET = "bitget"
    KUCOIN = "kucoin"
    HYPERLIQUID = "hyperliquid"


class ExchangeCredentials(Base):
    __tablename__ = "exchange_credentials"
    __table_args__ = (UniqueConstraint("user_id", "exchange", name="uq_exchange_credentials_user_exchange"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exchange = Column(String(20), nullable=False)
    api_key = Column(String(255), nullable=False)
    secret_key = Column(String(255), nullable=False)
    passphrase = Column(String(255), nullable=True)
    label = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, server_default="true")
    permissions = Column(JSON, default=dict)
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
