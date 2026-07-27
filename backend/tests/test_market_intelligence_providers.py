from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_dominance_uses_coinpaprika_when_coingecko_fails(monkeypatch):
    from app.services.market_intelligence import market_intelligence

    provider = AsyncMock(side_effect=[
        RuntimeError("CoinGecko unavailable"),
        {"bitcoin_dominance_percentage": 57.25},
    ])
    monkeypatch.setattr(market_intelligence, "_json", provider)

    result = await market_intelligence._dominance()

    assert result["value"] == 57.25
    assert result["source"] == "CoinPaprika Global"
    assert provider.await_count == 2


@pytest.mark.asyncio
async def test_liquidation_websocket_events_feed_market_intelligence(monkeypatch):
    from app.core.websocket_manager import ws_manager
    from app.services.binance_ws import binance_ws
    from app.services.market_intelligence import market_intelligence

    binance_ws._liquidations.clear()
    monkeypatch.setattr(ws_manager, "broadcast", AsyncMock())
    await binance_ws._handle_liquidation({
        "E": 9999999999999,
        "o": {
            "s": "BTCUSDT",
            "S": "SELL",
            "ap": "65000",
            "z": "0.5",
        },
    })

    result = await market_intelligence._liquidations_ws()

    assert result["provider_status"] == "available"
    assert result["source"] == "Binance Futures liquidation WebSocket"
    assert result["items"][0]["symbol"] == "BTCUSDT"
    assert result["items"][0]["side"] == "long"
    assert result["items"][0]["notional"] == 32500
