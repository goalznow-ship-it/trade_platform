from sqlalchemy import Column, Integer, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    max_daily_loss = Column(Float, default=500.0)
    max_weekly_loss = Column(Float, default=1500.0)
    max_monthly_loss = Column(Float, default=3000.0)
    max_position_size = Column(Float, default=1000.0)
    max_leverage = Column(Integer, default=20)
    max_open_positions = Column(Integer, default=10)
    max_correlation = Column(Float, default=0.7)
    risk_per_trade = Column(Float, default=0.02)
    max_drawdown = Column(Float, default=0.25)
    stop_loss_default = Column(Float, default=0.02)
    take_profit_default = Column(Float, default=0.04)
    enable_auto_liquidation_alerts = Column(Boolean, default=True)
    risk_score_threshold = Column(Float, default=0.7)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    total_exposure = Column(Float, default=0.0)
    daily_pnl = Column(Float, default=0.0)
    weekly_pnl = Column(Float, default=0.0)
    monthly_pnl = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    current_drawdown = Column(Float, default=0.0)
    liquidation_distance = Column(Float, default=0.0)
    portfolio_risk_score = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    expectancy = Column(Float, default=0.0)
    kelly_percent = Column(Float, default=0.0)
    var_95 = Column(Float, default=0.0)
    cvar_95 = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    total_balance = Column(Float, default=0.0)
    open_position_count = Column(Integer, default=0)
    margin_used = Column(Float, default=0.0)
    margin_free = Column(Float, default=0.0)
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now())
