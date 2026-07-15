from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OrderRequest:
    symbol: str
    side: str
    quantity: float
    order_type: str = "market"
    price: Optional[float] = None
    stop_price: Optional[float] = None
    leverage: int = 1
    reduce_only: bool = False
    time_in_force: str = "GTC"
    margin_mode: str = "isolated"
    client_order_id: Optional[str] = None


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    filled_quantity: float
    price: Optional[float]
    avg_price: Optional[float]
    status: str
    reduce_only: bool
    leverage: int
    margin_mode: str
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None


@dataclass
class PositionResult:
    symbol: str
    side: str
    size: float
    entry_price: float
    mark_price: float
    liquidation_price: float
    leverage: int
    margin: float
    unrealized_pnl: float
    realized_pnl: float
    isolated: bool


@dataclass
class BalanceResult:
    total: float
    free: float
    used: float
    unrealized_pnl: float


@dataclass
class ExchangeInfo:
    name: str
    futures_available: bool
    rate_limit: int
    timezone: str


class BaseExchange(ABC):
    def __init__(self, name: str):
        self.name = name
        self._api_key: Optional[str] = None
        self._secret_key: Optional[str] = None
        self._connected = False
        self._last_error: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self, api_key: str, secret_key: str, passphrase: Optional[str] = None) -> bool:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def reconnect(self) -> bool:
        ...

    @abstractmethod
    async def get_exchange_info(self) -> ExchangeInfo:
        ...

    @abstractmethod
    async def create_order(self, request: OrderRequest) -> OrderResult:
        ...

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        ...

    @abstractmethod
    async def modify_order(self, symbol: str, order_id: str,
                           price: Optional[float] = None,
                           quantity: Optional[float] = None,
                           stop_price: Optional[float] = None) -> OrderResult:
        ...

    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> Optional[OrderResult]:
        ...

    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResult]:
        ...

    @abstractmethod
    async def get_positions(self, symbol: Optional[str] = None) -> List[PositionResult]:
        ...

    @abstractmethod
    async def get_balance(self) -> BalanceResult:
        ...

    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        ...

    @abstractmethod
    async def set_margin_mode(self, symbol: str, mode: str) -> bool:
        ...

    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        ...

    @abstractmethod
    async def get_open_interest(self, symbol: str) -> Optional[Dict]:
        ...

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        ...

    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 50) -> Optional[Dict]:
        ...

    @abstractmethod
    async def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 200) -> List[Dict]:
        ...

    @abstractmethod
    async def get_leverage_brackets(self, symbol: str) -> Optional[List[Dict]]:
        ...

    @abstractmethod
    def _normalize_symbol(self, symbol: str) -> str:
        ...

    @abstractmethod
    def _denormalize_symbol(self, symbol: str) -> str:
        ...
