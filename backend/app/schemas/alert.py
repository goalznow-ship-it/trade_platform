from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from app.models.alert import AlertType, AlertChannel, AlertCondition


class AlertCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    alert_type: AlertType
    symbol: str = Field(..., min_length=1, max_length=20)
    exchange: str = Field(default="binance")
    timeframe: Optional[str] = None
    condition: AlertCondition
    value: Optional[float] = None
    value_secondary: Optional[float] = None
    comparison_symbol: Optional[str] = None
    channels: List[str] = Field(default=["in_app"])
    cooldown_minutes: int = Field(default=0, ge=0)
    max_triggers: int = Field(default=0, ge=0)
    is_recurring: bool = False
    metadata: Optional[dict] = None


class AlertUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    alert_type: Optional[AlertType] = None
    symbol: Optional[str] = None
    condition: Optional[AlertCondition] = None
    value: Optional[float] = None
    value_secondary: Optional[float] = None
    channels: Optional[List[str]] = None
    cooldown_minutes: Optional[int] = None
    max_triggers: Optional[int] = None
    is_active: Optional[bool] = None
    is_recurring: Optional[bool] = None


class AlertTriggerResponse(BaseModel):
    id: int
    triggered_value: float
    triggered_at_price: Optional[float]
    channel: str
    delivered: bool
    triggered_at: datetime

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    user_id: int
    name: str
    alert_type: str
    symbol: str
    exchange: str
    timeframe: Optional[str]
    condition: str
    value: Optional[float]
    value_secondary: Optional[float]
    channels: Any
    cooldown_minutes: int
    max_triggers: int
    is_active: bool
    is_recurring: bool
    trigger_count: int
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    triggers: List[AlertTriggerResponse] = []

    class Config:
        from_attributes = True
