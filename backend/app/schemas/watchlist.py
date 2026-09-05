from datetime import datetime

from pydantic import BaseModel, Field


class WatchlistSymbolCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    exchange: str = Field(default="binance", max_length=20)
    notes: str | None = None


class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class WatchlistUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    is_default: bool | None = None
    sort_order: int | None = None


class WatchlistSymbolReorder(BaseModel):
    symbols: list[str]


class WatchlistSymbolResponse(BaseModel):
    id: int
    symbol: str
    exchange: str
    is_favorite: bool
    notes: str | None
    sort_order: int
    added_at: datetime

    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_default: bool
    sort_order: int
    symbol_count: int
    symbols: list[WatchlistSymbolResponse]
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
