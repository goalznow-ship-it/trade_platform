import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_get_symbols(client: AsyncClient):
    response = await client.get("/api/v1/market/symbols")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["symbol"] == "BTC/USDT"


@pytest.mark.asyncio
async def test_get_overview(client: AsyncClient):
    response = await client.get("/api/v1/market/overview")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_overview_resolves_btc_and_eth_by_symbol(monkeypatch):
    from app.services.market import market_service
    from app.services.market_coverage import market_coverage
    import app.services.market as market_module

    monkeypatch.setattr(market_module, "cache_get", AsyncMock(return_value=None))
    monkeypatch.setattr(market_module, "cache_set", AsyncMock())
    monkeypatch.setattr(
        market_coverage,
        "get_top_symbols",
        AsyncMock(return_value=["ETH/USDT", "BTC/USDT", "SOL/USDT"]),
    )

    prices = {
        "BTC/USDT": {"price": 65000, "change_percent": 1.2, "volume_24h": 10},
        "ETH/USDT": {"price": 1900, "change_percent": 2.3, "volume_24h": 20},
        "SOL/USDT": {"price": 75, "change_percent": 3.4, "volume_24h": 30},
    }
    monkeypatch.setattr(
        market_service,
        "get_ticker",
        AsyncMock(side_effect=lambda symbol: prices[symbol]),
    )

    overview = await market_service.get_market_overview()

    assert overview["btc_price"] == 65000
    assert overview["eth_price"] == 1900
    assert overview["tickers"]["BTC/USDT"]["price"] == 65000
    assert overview["tickers"]["ETH/USDT"]["price"] == 1900


def test_required_market_symbols_only_include_verified_contracts():
    from app.services.market_coverage import market_coverage

    symbols = market_coverage._with_required_symbols(
        ["BTC/USDT", "ETH/USDT", "SKH/USDT"],
        3,
    )

    assert "SKHY/USDT" in symbols
    assert "SKH/USDT" not in symbols
    assert "SKH/USDT" not in market_coverage._normalize_symbols(["BTC/USDT", "SKH/USDT"])


@pytest.mark.asyncio
async def test_search_symbols(client: AsyncClient):
    response = await client.get("/api/v1/market/search", params={"q": "BTC"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_fear_greed(client: AsyncClient):
    response = await client.get("/api/v1/market/fear-greed")
    assert response.status_code == 200
    data = response.json()
    assert "value" in data
