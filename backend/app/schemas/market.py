
from pydantic import BaseModel


class CandleSchema(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

class TickerSchema(BaseModel):
    symbol: str
    price: float | None = None
    bid: float | None = None
    ask: float | None = None
    high_24h: float | None = None
    low_24h: float | None = None
    volume_24h: float | None = None
    change_percent: float | None = None

class MarketOverviewSchema(BaseModel):
    btc_price: float | None = None
    btc_change: float | None = None
    eth_price: float | None = None
    total_market_cap: float | None = None
    total_volume_24h: float | None = None
    btc_dominance: float | None = None
