from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.alert import AlertCondition, AlertType


class AlertCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    alert_type: AlertType
    symbol: str = Field(..., min_length=1, max_length=20)
    exchange: str = Field(default="binance")
    timeframe: str | None = None
    condition: AlertCondition
    value: float | None = None
    value_secondary: float | None = None
    comparison_symbol: str | None = None
    channels: list[str] = Field(default=["in_app"])
    cooldown_minutes: int = Field(default=0, ge=0)
    max_triggers: int = Field(default=0, ge=0)
    is_recurring: bool = False
    metadata: dict | None = None


class AlertUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    alert_type: AlertType | None = None
    symbol: str | None = None
    condition: AlertCondition | None = None
    value: float | None = None
    value_secondary: float | None = None
    channels: list[str] | None = None
    cooldown_minutes: int | None = None
    max_triggers: int | None = None
    is_active: bool | None = None
    is_recurring: bool | None = None


class AlertTriggerResponse(BaseModel):
    id: int
    triggered_value: float
    triggered_at_price: float | None
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
    timeframe: str | None
    condition: str
    value: float | None
    value_secondary: float | None
    channels: Any
    cooldown_minutes: int
    max_triggers: int
    is_active: bool
    is_recurring: bool
    trigger_count: int
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    triggers: list[AlertTriggerResponse] = []

    class Config:
        from_attributes = True
