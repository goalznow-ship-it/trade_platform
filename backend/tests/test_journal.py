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
        "username": "journaluser", "email": "journal@test.com", "password": "testpass123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "journaluser", "password": "testpass123",
    })
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_journal_entry(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/journal", json={
        "symbol": "BTC/USDT", "side": "long",
        "notes": "Good trade", "rating": "good",
        "emotion": "confident",
    }, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["symbol"] == "BTC/USDT"


@pytest.mark.asyncio
async def test_get_journal_entries(client: AsyncClient, auth_headers: dict):
    await client.post("/api/v1/journal", json={
        "symbol": "ETH/USDT", "side": "short", "notes": "Test",
    }, headers=auth_headers)
    resp = await client.get("/api/v1/journal", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
