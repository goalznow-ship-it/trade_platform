from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WatchlistSymbolCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    exchange: str = Field(default="binance", max_length=20)
    notes: Optional[str] = None


class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class WatchlistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_default: Optional[bool] = None
    sort_order: Optional[int] = None


class WatchlistSymbolReorder(BaseModel):
    symbols: List[str]


class WatchlistSymbolResponse(BaseModel):
    id: int
    symbol: str
    exchange: str
    is_favorite: bool
    notes: Optional[str]
    sort_order: int
    added_at: datetime

    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_default: bool
    sort_order: int
    symbol_count: int
    symbols: List[WatchlistSymbolResponse]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
