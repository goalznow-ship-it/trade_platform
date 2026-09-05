from datetime import datetime

from pydantic import BaseModel, Field

from app.models.journal import Emotion, MistakeType, TradeRating


class JournalCreate(BaseModel):
    trade_id: int | None = None
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern="^(long|short)$")
    notes: str | None = None
    lessons: str | None = None
    emotion: Emotion | None = None
    mistakes: list[MistakeType] = []
    tags: list[str] = []
    strategy: str | None = None
    setup_description: str | None = None
    entry_reason: str | None = None
    exit_reason: str | None = None
    rating: TradeRating | None = None
    win_loss_reason: str | None = None
    screenshot_urls: list[str] = []
    executed_plan: bool = False
    followed_rules: bool = False
    psychological_state: str | None = None


class JournalUpdate(BaseModel):
    notes: str | None = None
    lessons: str | None = None
    emotion: Emotion | None = None
    mistakes: list[MistakeType] | None = None
    tags: list[str] | None = None
    strategy: str | None = None
    setup_description: str | None = None
    entry_reason: str | None = None
    exit_reason: str | None = None
    rating: TradeRating | None = None
    win_loss_reason: str | None = None
    screenshot_urls: list[str] | None = None
    executed_plan: bool | None = None
    followed_rules: bool | None = None
    psychological_state: str | None = None


class JournalResponse(BaseModel):
    id: int
    user_id: int
    trade_id: int | None
    symbol: str
    side: str
    notes: str | None
    lessons: str | None
    emotion: str | None
    mistakes: list
    tags: list
    strategy: str | None
    setup_description: str | None
    entry_reason: str | None
    exit_reason: str | None
    rating: str | None
    win_loss_reason: str | None
    screenshot_urls: list
    executed_plan: bool
    followed_rules: bool
    psychological_state: str | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
