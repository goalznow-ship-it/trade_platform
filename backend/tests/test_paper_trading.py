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
        "username": "paperuser", "email": "paper@test.com", "password": "testpass123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "paperuser", "password": "testpass123",
    })
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_paper_account(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/paper/account", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["balance"] == 100000.0


@pytest.mark.asyncio
async def test_reset_account(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/paper/account/reset", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["account"]["balance"] == 100000.0


@pytest.mark.asyncio
async def test_create_paper_order(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/paper/orders", json={
        "symbol": "BTC/USDT", "side": "buy", "order_type": "market",
        "quantity": 0.01, "price": 50000, "leverage": 1,
    }, headers=auth_headers)
    assert resp.status_code == 201
