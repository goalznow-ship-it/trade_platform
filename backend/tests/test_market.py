import pytest
from httpx import AsyncClient


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
