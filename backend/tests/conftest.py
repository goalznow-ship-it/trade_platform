import sys
import types

import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool


# ── optional-deps stubs ────────────────────────────────────────
# Heavyweight ML deps (torch) may not be installed in the test
# environment. We install a minimal stub so ``import`` succeeds;
# tests that actually exercise torch are skipped if the real
# dep is missing.
try:
    import torch  # noqa: F401
    import torch.nn  # noqa: F401
    import torch.utils.data  # noqa: F401
    import torch.optim  # noqa: F401
except Exception:
    _torch = types.ModuleType("torch")
    _nn = types.ModuleType("torch.nn")
    _utils = types.ModuleType("torch.utils")
    _data = types.ModuleType("torch.utils.data")
    _optim = types.ModuleType("torch.optim")
    class _StubModule:
        def __init__(self, *a, **k):
            pass
    for mod in (_nn, _data, _optim):
        mod.DataLoader = _StubModule
        mod.TensorDataset = _StubModule
        mod.Adam = _StubModule
        mod.AdamW = _StubModule
    _nn.Module = _StubModule
    _nn.Linear = _StubModule
    _nn.LayerNorm = _StubModule
    _nn.Dropout = _StubModule
    _nn.GELU = _StubModule
    _nn.ReLU = _StubModule
    _nn.Sequential = _StubModule
    _nn.CrossEntropyLoss = _StubModule
    _utils.data = _data
    _torch.nn = _nn
    _torch.utils = _utils
    _torch.optim = _optim
    _torch.Tensor = type("Tensor", (), {})
    _torch.float = "float32"
    _torch.long = "int64"
    sys.modules.setdefault("torch", _torch)
    sys.modules.setdefault("torch.nn", _nn)
    sys.modules.setdefault("torch.utils", _utils)
    sys.modules.setdefault("torch.utils.data", _data)
    sys.modules.setdefault("torch.optim", _optim)


from app.core.database import Base, get_db
from app.main import app
TEST_DATABASE_URL = "sqlite+aiosqlite://"


# ── test-dialect shims ────────────────────────────────────────
# SQLite (the in-memory engine used by tests) doesn't support
# PostgreSQL's JSONB column type. We patch the JSONB symbol
# before any model imports so ``Column(JSONB, ...)`` calls
# resolve to plain JSON at table-create time. The live app
# never goes through this conftest.
from sqlalchemy import types as _sa_types
try:
    from sqlalchemy.dialects import postgresql as _pg_dialect
    _pg_dialect.JSONB = _sa_types.JSON  # type: ignore[attr-defined]
except Exception:
    pass


# Some models already imported ``JSONB`` as a local reference
# before this conftest ran (notably via ``app.main``). Walk
# the metadata after import and swap any leftover JSONB
# columns to the generic JSON type so SQLite can render them.
from sqlalchemy.types import JSON as _GenericJSON
try:
    from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB  # noqa: F401
except Exception:
    _PG_JSONB = None

if _PG_JSONB is not None:
    from app.core.database import Base as _Base  # noqa: F401
    for _table in _Base.metadata.tables.values():
        for _col in _table.columns:
            if isinstance(_col.type, _PG_JSONB):
                _col.type = _GenericJSON()

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
db_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with db_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    await client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
    })
    resp = await client.post("/api/v1/auth/login", data={
        "username": "testuser",
        "password": "testpass123",
    })
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}
