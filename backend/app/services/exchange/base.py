from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OrderRequest:
    symbol: str
    side: str
    quantity: float
    order_type: str = "market"
    price: float | None = None
    stop_price: float | None = None
    leverage: int = 1
    reduce_only: bool = False
    time_in_force: str = "GTC"
    margin_mode: str = "isolated"
    client_order_id: str | None = None


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    filled_quantity: float
    price: float | None
    avg_price: float | None
    status: str
    reduce_only: bool
    leverage: int
    margin_mode: str
    created_at: datetime
    updated_at: datetime
    error: str | None = None


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
        self._api_key: str | None = None
        self._secret_key: str | None = None
        self._connected = False
        self._last_error: str | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self, api_key: str, secret_key: str, passphrase: str | None = None) -> bool:
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
                           price: float | None = None,
                           quantity: float | None = None,
                           stop_price: float | None = None) -> OrderResult:
        ...

    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> OrderResult | None:
        ...

    @abstractmethod
    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        ...

    @abstractmethod
    async def get_positions(self, symbol: str | None = None) -> list[PositionResult]:
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
    async def get_funding_rate(self, symbol: str) -> dict | None:
        ...

    @abstractmethod
    async def get_open_interest(self, symbol: str) -> dict | None:
        ...

    @abstractmethod
    async def get_ticker(self, symbol: str) -> dict | None:
        ...

    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 50) -> dict | None:
        ...

    @abstractmethod
    async def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 200) -> list[dict]:
        ...

    @abstractmethod
    async def get_leverage_brackets(self, symbol: str) -> list[dict] | None:
        ...

    @abstractmethod
    def _normalize_symbol(self, symbol: str) -> str:
        ...

    @abstractmethod
    def _denormalize_symbol(self, symbol: str) -> str:
        ...
