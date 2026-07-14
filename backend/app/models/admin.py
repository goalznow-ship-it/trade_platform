from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100))
    resource_id = Column(String(50))
    details = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    exchange = Column(String(20), nullable=False)
    api_key = Column(String(255), nullable=False)
    secret_key = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    permissions = Column(JSON, default=dict)
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text)
    channel = Column(String(20), default="in_app")
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    related_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, unique=True)
    tier = Column(String(20), default="free")
    price = Column(Float, default=0.0)
    signals_per_day = Column(Integer, default=10)
    max_watchlist = Column(Integer, default=10)
    has_backtest = Column(Boolean, default=False)
    has_api_access = Column(Boolean, default=False)
    start_date = Column(DateTime, server_default=func.now())
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
