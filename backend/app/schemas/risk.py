from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RiskProfileCreate(BaseModel):
    max_daily_loss: float = Field(default=500.0, ge=0)
    max_weekly_loss: float = Field(default=1500.0, ge=0)
    max_monthly_loss: float = Field(default=3000.0, ge=0)
    max_position_size: float = Field(default=1000.0, ge=0)
    max_leverage: int = Field(default=20, ge=1, le=100)
    max_open_positions: int = Field(default=10, ge=1)
    max_correlation: float = Field(default=0.7, ge=0, le=1)
    risk_per_trade: float = Field(default=0.02, ge=0, le=1)
    max_drawdown: float = Field(default=0.25, ge=0, le=1)
    stop_loss_default: float = Field(default=0.02, ge=0, le=1)
    take_profit_default: float = Field(default=0.04, ge=0, le=1)


class RiskProfileResponse(BaseModel):
    id: int
    user_id: int
    max_daily_loss: float
    max_weekly_loss: float
    max_monthly_loss: float
    max_position_size: float
    max_leverage: int
    max_open_positions: int
    max_correlation: float
    risk_per_trade: float
    max_drawdown: float
    stop_loss_default: float
    take_profit_default: float
    risk_score_threshold: float
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RiskSnapshotResponse(BaseModel):
    id: int
    total_exposure: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    max_drawdown: float
    current_drawdown: float
    liquidation_distance: float
    portfolio_risk_score: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    expectancy: float
    kelly_percent: float
    var_95: float
    cvar_95: float
    total_balance: float
    open_position_count: int
    margin_used: float
    margin_free: float
    snapshot_at: datetime

    class Config:
        from_attributes = True


class RiskDashboardResponse(BaseModel):
    profile: RiskProfileResponse
    current: RiskSnapshotResponse
    exposure_by_symbol: List[dict]
    risk_signals: List[str]
    warnings: List[str]
