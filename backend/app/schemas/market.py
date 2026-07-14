from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CandleSchema(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

class TickerSchema(BaseModel):
    symbol: str
    price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    change_percent: Optional[float] = None

class MarketOverviewSchema(BaseModel):
    btc_price: Optional[float] = None
    btc_change: Optional[float] = None
    eth_price: Optional[float] = None
    total_market_cap: Optional[float] = None
    total_volume_24h: Optional[float] = None
    btc_dominance: Optional[float] = None
