from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import trading


class ScalarResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    def __init__(self):
        self.added = []
        self.committed = False

    async def execute(self, _query):
        return ScalarResult()

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.committed = True


class FakeExchange:
    is_connected = True

    def __init__(self, positions):
        self.positions = positions

    async def get_positions(self, _symbol=None):
        return self.positions


@pytest.mark.asyncio
async def test_partial_close_is_opposite_side_reduce_only(monkeypatch):
    position = SimpleNamespace(
        symbol="BTC/USDT:USDT", side="long", size=2.0, leverage=5, isolated=True,
    )
    exchange = FakeExchange([position])
    received = {}

    async def get_exchange(*_args):
        return exchange

    async def create_order(*args):
        received["request"] = args[2]
        return SimpleNamespace(
            order_id="close-1", symbol="BTC/USDT", side="sell", status="closed",
            filled_quantity=0.5, avg_price=65000.0, error=None,
        )

    async def redis_get(_key):
        return None

    monkeypatch.setattr(trading.settings, "TRADING_ENABLED", True)
    monkeypatch.setattr(trading.redis_client, "get", redis_get)
    monkeypatch.setattr(trading.exchange_manager, "get_user_exchange", get_exchange)
    monkeypatch.setattr(trading.exchange_manager, "create_order", create_order)

    response = await trading.close_position(
        trading.ClosePositionRequest(
            symbol="BTC/USDT", percentage=25, client_order_id="close_test_001",
        ),
        user=SimpleNamespace(id=7),
        db=FakeDB(),
    )

    request = received["request"]
    assert request.side == "sell"
    assert request.quantity == 0.5
    assert request.reduce_only is True
    assert response["requested_percentage"] == 25
    assert response["reduce_only"] is True


@pytest.mark.asyncio
async def test_close_rejects_missing_position_without_order(monkeypatch):
    exchange = FakeExchange([])
    called = False

    async def get_exchange(*_args):
        return exchange

    async def create_order(*_args):
        nonlocal called
        called = True

    async def redis_get(_key):
        return None

    monkeypatch.setattr(trading.settings, "TRADING_ENABLED", True)
    monkeypatch.setattr(trading.redis_client, "get", redis_get)
    monkeypatch.setattr(trading.exchange_manager, "get_user_exchange", get_exchange)
    monkeypatch.setattr(trading.exchange_manager, "create_order", create_order)

    with pytest.raises(HTTPException) as exc:
        await trading.close_position(
            trading.ClosePositionRequest(
                symbol="ETH/USDT", percentage=100, client_order_id="close_test_002",
            ),
            user=SimpleNamespace(id=7),
            db=FakeDB(),
        )

    assert exc.value.status_code == 404
    assert called is False


def test_symbol_comparison_handles_ccxt_futures_suffix():
    assert trading._canonical_symbol("BTC/USDT:USDT") == trading._canonical_symbol("BTCUSDT")
