import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import Base, get_db
from tests.conftest import override_get_db

app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    from tests.conftest import test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "testuser", "email": "test@example.com", "password": "testpass123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser", "password": "testpass123",
    })
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_watchlist(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/watchlists", json={"name": "My Watchlist"}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Watchlist"
    assert data["symbol_count"] == 0


@pytest.mark.asyncio
async def test_get_watchlists(client: AsyncClient, auth_headers: dict):
    await client.post("/api/v1/watchlists", json={"name": "Watchlist 1"}, headers=auth_headers)
    resp = await client.get("/api/v1/watchlists", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_add_symbol(client: AsyncClient, auth_headers: dict):
    wl = await client.post("/api/v1/watchlists", json={"name": "Test"}, headers=auth_headers)
    wl_id = wl.json()["id"]
    resp = await client.post(f"/api/v1/watchlists/{wl_id}/symbols",
                              json={"symbol": "BTC/USDT"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["symbol"] == "BTC/USDT"
