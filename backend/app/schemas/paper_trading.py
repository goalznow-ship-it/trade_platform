from datetime import datetime

from pydantic import BaseModel, Field


class PaperOrderCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern="^(buy|sell)$")
    order_type: str = Field(default="market", pattern="^(market|limit|stop|stop_limit)$")
    quantity: float = Field(..., gt=0)
    price: float | None = Field(None, gt=0)
    stop_price: float | None = Field(None, gt=0)
    leverage: int = Field(default=1, ge=1, le=100)
    reduce_only: bool = False
    time_in_force: str = Field(default="GTC", pattern="^(GTC|IOC|FOK)$")


class PaperAccountResponse(BaseModel):
    id: int
    name: str
    balance: float
    initial_balance: float
    equity: float
    free_margin: float
    used_margin: float
    total_pnl: float
    total_trades: int
    win_count: int
    loss_count: int
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class PaperPositionResponse(BaseModel):
    id: int
    symbol: str
    side: str
    size: float
    entry_price: float
    mark_price: float | None
    liquidation_price: float | None
    leverage: int
    margin: float
    unrealized_pnl: float
    stop_loss: float | None
    take_profit: float | None
    is_open: bool
    opened_at: datetime
    closed_at: datetime | None

    class Config:
        from_attributes = True


class PaperOrderResponse(BaseModel):
    id: int
    symbol: str
    side: str
    order_type: str
    price: float | None
    stop_price: float | None
    quantity: float
    filled_quantity: float
    status: str
    leverage: int
    executed_price: float | None
    executed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class PaperResetResponse(BaseModel):
    message: str
    account: PaperAccountResponse
