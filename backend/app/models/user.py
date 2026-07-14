from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    display_name = Column(String(50))
    avatar_url = Column(String(500))
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    theme = Column(String(20), default="dark")

    balance = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)

    subscription_tier = Column(String(20), default="free")
    subscription_expires = Column(DateTime, nullable=True)

    telegram_id = Column(String(50), nullable=True)
    discord_id = Column(String(50), nullable=True)
    notification_settings = Column(JSON, default=dict)

    binance_api_key = Column(String(255), nullable=True)
    binance_secret_key = Column(String(255), nullable=True)
    bybit_api_key = Column(String(255), nullable=True)
    bybit_secret_key = Column(String(255), nullable=True)

    twofa_secret = Column(String(100), nullable=True)
    twofa_enabled = Column(Boolean, default=False)

    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
