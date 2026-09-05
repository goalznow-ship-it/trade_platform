"""Tests for the per-engine circuit breaker.

The breaker has a small state machine — closed → open → half_open →
closed — and the hot path is ``is_open()``. We exercise every
transition plus the cache layer that keeps the SQL load down.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

# The conftest exposes ``db_session_factory`` (the test engine's
# session factory). Patch the breaker to use it instead of the
# live ``async_session_factory`` so tests run against SQLite.
from tests.conftest import db_session_factory as _test_factory

import app.services.circuit_breaker as _cb

# Module-level swap. Restore at the end of each test so a
# failure in one test doesn't leak into the next.
@pytest.fixture(autouse=True)
def _patch_session_factory():
    original = _cb.async_session_factory
    _cb.async_session_factory = _test_factory
    try:
        yield
    finally:
        _cb.async_session_factory = original


# Convenience alias for use in test bodies below. Patched in
# the autouse fixture above.
async_session_factory = _test_factory


from app.models.quality import CircuitBreakerState
from app.services import circuit_breaker

# Re-imported here so the test bodies that reference
# ``settings.CB_FAILURE_THRESHOLD`` resolve without a
# second top-level import.
from app.core.config import settings  # noqa: E402


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _reset(engine: str, scope: str = "default") -> None:
    # Wipe both the in-memory cache and the DB row so each
    # test starts from a known state.
    circuit_breaker._CACHE.clear()
    async with async_session_factory() as db:
        from sqlalchemy import delete
        await db.execute(
            delete(CircuitBreakerState).where(
                CircuitBreakerState.engine == engine,
                CircuitBreakerState.scope == scope,
            )
        )
        await db.commit()


@pytest.mark.asyncio
async def test_starts_closed():
    """A brand-new (engine, scope) row starts in the
    ``closed`` state with zero failures.
    """
    engine = "test_breaker_starts_closed"
    await _reset(engine)

    assert await circuit_breaker.is_open(engine) is False
    state = await circuit_breaker.get_state(engine)
    assert state["state"] == "closed"
    assert state["consecutive_failures"] == 0


@pytest.mark.asyncio
async def test_opens_after_threshold_failures():
    """N consecutive failures (default 5) trip the breaker
    to ``open``. ``is_open`` then returns True.
    """
    engine = "test_breaker_opens"
    await _reset(engine)
    # Default threshold is settings.CB_FAILURE_THRESHOLD.
    for _ in range(settings.CB_FAILURE_THRESHOLD):
        await circuit_breaker.record_failure(engine, reason="unit_test")
    assert await circuit_breaker.is_open(engine) is True
    state = await circuit_breaker.get_state(engine)
    assert state["state"] == "open"
    assert state["opened_at"] is not None
    assert "threshold_reached" in state["last_transition_reason"]


@pytest.mark.asyncio
async def test_success_resets_failure_counter():
    """A success while the breaker is still closed must
    reset the failure counter so a flapping engine doesn't
    accumulate failures across days.
    """
    engine = "test_breaker_resets"
    await _reset(engine)
    # 3 failures (below threshold of 5).
    for _ in range(3):
        await circuit_breaker.record_failure(engine, reason="flap")
    state = await circuit_breaker.get_state(engine)
    assert state["consecutive_failures"] == 3

    # A success resets the counter.
    await circuit_breaker.record_success(engine)
    state = await circuit_breaker.get_state(engine)
    assert state["consecutive_failures"] == 0
    assert state["state"] == "closed"


@pytest.mark.asyncio
async def test_half_open_after_open_duration():
    """Once the open duration elapses, ``is_open`` returns
    False and the state transitions to ``half_open`` so the
    next call can probe.
    """
    engine = "test_breaker_half_open"
    await _reset(engine)

    # Open the breaker.
    for _ in range(settings.CB_FAILURE_THRESHOLD):
        await circuit_breaker.record_failure(engine, reason="unit_test")
    assert await circuit_breaker.is_open(engine) is True

    # Manually rewind the opened_at timestamp so the open
    # window has "elapsed".
    async with async_session_factory() as db:
        row = await circuit_breaker._load_state(engine, "default", db)
        row.opened_at = _utcnow() - timedelta(
            seconds=row.open_duration_seconds + 60
        )
        await db.commit()
    circuit_breaker._CACHE.clear()

    # The next is_open() should transition to half_open and
    # return False (half_open is *not* open).
    assert await circuit_breaker.is_open(engine) is False
    state = await circuit_breaker.get_state(engine)
    assert state["state"] == "half_open"


@pytest.mark.asyncio
async def test_success_after_half_open_closes():
    """A success while the breaker is in ``half_open``
    returns it to ``closed`` and clears the open timestamp.
    """
    engine = "test_breaker_recover"
    await _reset(engine)

    for _ in range(settings.CB_FAILURE_THRESHOLD):
        await circuit_breaker.record_failure(engine, reason="unit_test")
    # Force into half_open.
    async with async_session_factory() as db:
        row = await circuit_breaker._load_state(engine, "default", db)
        row.opened_at = _utcnow() - timedelta(seconds=row.open_duration_seconds + 60)
        await db.commit()
    circuit_breaker._CACHE.clear()
    await circuit_breaker.is_open(engine)  # triggers half_open
    await circuit_breaker.record_success(engine)
    state = await circuit_breaker.get_state(engine)
    assert state["state"] == "closed"
    assert state["opened_at"] is None
    assert state["consecutive_failures"] == 0


@pytest.mark.asyncio
async def test_force_close_overrides():
    """Operator override: ``force_close`` returns the
    breaker to ``closed`` even if the threshold logic
    would keep it open.
    """
    engine = "test_breaker_force_close"
    await _reset(engine)

    for _ in range(settings.CB_FAILURE_THRESHOLD):
        await circuit_breaker.record_failure(engine, reason="unit_test")
    assert await circuit_breaker.is_open(engine) is True

    await circuit_breaker.force_close(engine, reason="unit_test_override")
    assert await circuit_breaker.is_open(engine) is False
    state = await circuit_breaker.get_state(engine)
    assert state["state"] == "closed"
    assert "force_close" in state["last_transition_reason"]


@pytest.mark.asyncio
async def test_independent_scopes():
    """The (engine, scope) tuple is the key — a per-symbol
    scope keeps one symbol's breaker from blocking another.
    """
    engine = "test_breaker_scopes"
    await _reset(engine, scope="default")
    await _reset(engine, scope="BTC/USDT")

    for _ in range(settings.CB_FAILURE_THRESHOLD):
        await circuit_breaker.record_failure(engine, scope="BTC/USDT", reason="x")

    # The default scope is still closed.
    assert await circuit_breaker.is_open(engine, scope="default") is False
    # The symbol scope is open.
    assert await circuit_breaker.is_open(engine, scope="BTC/USDT") is True


@pytest.mark.asyncio
async def test_cache_returns_same_answer(db_session):
    """The hot-path cache means consecutive ``is_open()``
    calls don't hit the DB. We confirm by calling twice and
    checking the cache key is set.
    """
    engine = "test_breaker_cache"
    await _reset(engine)
    # First call seeds the cache.
    await circuit_breaker.is_open(engine)
    assert (engine, "default") in circuit_breaker._CACHE
    # Second call uses the cache.
    cached_value = circuit_breaker._cache_get(engine, "default")
    assert cached_value is False
