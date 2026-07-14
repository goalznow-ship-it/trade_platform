from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, unique=True)
    total_balance = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    total_pnl_percent = Column(Float, default=0.0)
    daily_pnl = Column(Float, default=0.0)
    monthly_pnl = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    avg_risk_reward = Column(Float, default=0.0)
    best_trade = Column(Float, default=0.0)
    worst_trade = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class PortfolioAsset(Base):
    __tablename__ = "portfolio_assets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id = Column(Integer, index=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, default=0.0)
    avg_entry = Column(Float, default=0.0)
    current_price = Column(Float, default=0.0)
    value = Column(Float, default=0.0)
    pnl = Column(Float, default=0.0)
    pnl_percent = Column(Float, default=0.0)
    allocation_percent = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    symbol = Column(String(20))
    timeframe = Column(String(5))
    strategy_name = Column(String(100))
    parameters = Column(JSON)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    total_return = Column(Float, default=0.0)
    avg_risk_reward = Column(Float, default=0.0)
    monthly_results = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
