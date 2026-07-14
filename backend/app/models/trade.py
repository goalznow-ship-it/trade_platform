from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    type = Column(String(20), default="market")
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    stop_price = Column(Float, nullable=True)
    leverage = Column(Integer, default=1)
    margin_mode = Column(String(10), default="isolated")
    status = Column(String(20), default="open")
    pnl = Column(Float, default=0.0)
    pnl_percent = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    exchange = Column(String(20), default="binance")
    exchange_order_id = Column(String(100), nullable=True)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime, nullable=True)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    trade_id = Column(Integer, nullable=True)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    type = Column(String(20), nullable=False)
    price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    filled_quantity = Column(Float, default=0.0)
    status = Column(String(20), default="pending")
    exchange_order_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    mark_price = Column(Float, nullable=False)
    liquidation_price = Column(Float, nullable=True)
    leverage = Column(Integer, default=1)
    margin = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    exchange = Column(String(20), default="binance")
    is_open = Column(Boolean, default=True)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TradeHistory(Base):
    __tablename__ = "trade_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    symbol = Column(String(20))
    side = Column(String(10))
    type = Column(String(20))
    quantity = Column(Float)
    entry_price = Column(Float)
    exit_price = Column(Float)
    pnl = Column(Float)
    pnl_percent = Column(Float)
    roi = Column(Float)
    leverage = Column(Integer)
    duration_minutes = Column(Integer)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    risk_reward = Column(Float)
    reason = Column(Text)
    exchange = Column(String(20))
    closed_at = Column(DateTime(timezone=True), server_default=func.now())
