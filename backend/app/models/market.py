from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, BigInteger
from sqlalchemy.sql import func
from app.core.database import Base

class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), unique=True, index=True, nullable=False)
    base_asset = Column(String(10))
    quote_asset = Column(String(10), default="USDT")
    exchange = Column(String(20), default="binance")
    asset_type = Column(String(10), default="crypto")
    price_precision = Column(Integer, default=2)
    quantity_precision = Column(Integer, default=4)
    min_notional = Column(Float, default=10.0)
    is_active = Column(Boolean, default=True)
    is_futures = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Candle(Base):
    __tablename__ = "candles"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    symbol_id = Column(Integer, index=True, nullable=False)
    timeframe = Column(String(5), nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    trades = Column(Integer, default=0)

class Ticker(Base):
    __tablename__ = "tickers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol_id = Column(Integer, index=True)
    symbol = Column(String(20))
    price = Column(Float)
    price_change_24h = Column(Float)
    price_change_percent_24h = Column(Float)
    high_24h = Column(Float)
    low_24h = Column(Float)
    volume_24h = Column(Float)
    market_cap = Column(Float, default=0)
    dominance = Column(Float, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
