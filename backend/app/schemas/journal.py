from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.journal import TradeRating, Emotion, MistakeType


class JournalCreate(BaseModel):
    trade_id: Optional[int] = None
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern="^(long|short)$")
    notes: Optional[str] = None
    lessons: Optional[str] = None
    emotion: Optional[Emotion] = None
    mistakes: List[MistakeType] = []
    tags: List[str] = []
    strategy: Optional[str] = None
    setup_description: Optional[str] = None
    entry_reason: Optional[str] = None
    exit_reason: Optional[str] = None
    rating: Optional[TradeRating] = None
    win_loss_reason: Optional[str] = None
    screenshot_urls: List[str] = []
    executed_plan: bool = False
    followed_rules: bool = False
    psychological_state: Optional[str] = None


class JournalUpdate(BaseModel):
    notes: Optional[str] = None
    lessons: Optional[str] = None
    emotion: Optional[Emotion] = None
    mistakes: Optional[List[MistakeType]] = None
    tags: Optional[List[str]] = None
    strategy: Optional[str] = None
    setup_description: Optional[str] = None
    entry_reason: Optional[str] = None
    exit_reason: Optional[str] = None
    rating: Optional[TradeRating] = None
    win_loss_reason: Optional[str] = None
    screenshot_urls: Optional[List[str]] = None
    executed_plan: Optional[bool] = None
    followed_rules: Optional[bool] = None
    psychological_state: Optional[str] = None


class JournalResponse(BaseModel):
    id: int
    user_id: int
    trade_id: Optional[int]
    symbol: str
    side: str
    notes: Optional[str]
    lessons: Optional[str]
    emotion: Optional[str]
    mistakes: List
    tags: List
    strategy: Optional[str]
    setup_description: Optional[str]
    entry_reason: Optional[str]
    exit_reason: Optional[str]
    rating: Optional[str]
    win_loss_reason: Optional[str]
    screenshot_urls: List
    executed_plan: bool
    followed_rules: bool
    psychological_state: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
