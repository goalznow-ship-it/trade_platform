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
        "username": "riskuser", "email": "risk@test.com", "password": "testpass123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "riskuser", "password": "testpass123",
    })
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_risk_profile(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/risk/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "max_daily_loss" in data
    assert data["max_leverage"] == 20


@pytest.mark.asyncio
async def test_update_risk_profile(client: AsyncClient, auth_headers: dict):
    resp = await client.put("/api/v1/risk/profile", json={
        "max_daily_loss": 1000, "max_leverage": 10,
        "max_open_positions": 5, "risk_per_trade": 0.01,
        "max_drawdown": 0.2, "max_position_size": 5000,
        "max_weekly_loss": 3000, "max_monthly_loss": 6000,
        "max_correlation": 0.5, "stop_loss_default": 0.01,
        "take_profit_default": 0.03,
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["max_leverage"] == 10


@pytest.mark.asyncio
async def test_risk_dashboard(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/risk/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "profile" in data
    assert "current" in data
