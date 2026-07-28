import pytest

from app.services.exchange.base import OrderRequest
from app.services.exchange.binance_futures import BinanceFuturesExchange


class FakeCCXT:
    def __init__(self):
        self.calls = []

    def set_leverage(self, *_args):
        return None

    def set_margin_mode(self, *_args):
        return None

    def create_order(self, symbol, order_type, side, amount, price, params=None):
        self.calls.append((symbol, order_type, side, amount, price, params))
        return {
            "id": "protect-1", "symbol": symbol, "side": side,
            "type": order_type, "amount": None, "filled": 0,
            "status": "open",
        }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("order_type", "expected_type"),
    [("stop_market", "STOP_MARKET"), ("take_profit_market", "TAKE_PROFIT_MARKET")],
)
async def test_reduce_only_protection_uses_close_position_without_quantity(
    order_type, expected_type,
):
    exchange = BinanceFuturesExchange()
    exchange._connected = True
    exchange._ccxt = FakeCCXT()

    result = await exchange.create_order(OrderRequest(
        symbol="BTC/USDT",
        side="sell",
        quantity=0.01,
        order_type=order_type,
        stop_price=65000,
        reduce_only=True,
    ))

    call = exchange._ccxt.calls[0]
    assert call[1] == expected_type
    assert call[3] is None
    assert call[5] == {"stopPrice": 65000, "closePosition": True}
    assert result.error is None
    assert result.quantity == 0.01
