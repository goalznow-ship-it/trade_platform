import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import Base, get_db
from tests.conftest import test_async_session_factory, override_get_db

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
        "username": "alertuser", "email": "alert@test.com", "password": "testpass123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "alertuser", "password": "testpass123",
    })
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_price_alert(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/alerts", json={
        "name": "BTC above 100k",
        "alert_type": "price",
        "symbol": "BTC/USDT",
        "condition": "above",
        "value": 100000,
        "channels": ["in_app"],
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "BTC above 100k"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_alerts(client: AsyncClient, auth_headers: dict):
    await client.post("/api/v1/alerts", json={
        "name": "Test Alert", "alert_type": "price",
        "symbol": "ETH/USDT", "condition": "below", "value": 2000,
    }, headers=auth_headers)
    resp = await client.get("/api/v1/alerts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
