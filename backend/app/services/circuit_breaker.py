"""Per-engine circuit breaker.

Why
---
A quality-gate auto-disable is a soft signal — the engine is
under-performing but it isn't broken. A circuit breaker is
the hard fallback: when an engine *crashes* N times in a row,
we stop calling it for ``open_duration_seconds`` so a
sustained outage doesn't melt the rest of the platform.

State machine
-------------
::

    closed ──[N consecutive failures]──▶ open
       ▲                                  │
       │                            [open_duration elapsed]
       │                                  ▼
       └──[probe success]── half_open ──[probe failure]──▶ open

The breaker is keyed by ``(engine, scope)`` so a per-symbol
breaker is just ``scope=symbol_name``. The default scope is
``"default"``.

The state is persisted in ``circuit_breaker_state`` so a
process restart doesn't drop the open-circuit information.
Reads in the hot path (``is_open()``) cache the row in
memory for ``CACHE_TTL_SECONDS`` to keep the SQL load down.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import logger
from app.models.quality import CircuitBreakerState


# In-memory cache for the hot path. The pipeline calls
# ``is_open()`` for every emit; we don't want a roundtrip to
# the DB for each one. Keyed by (engine, scope).
_CACHE: dict[tuple[str, str], tuple[float, bool]] = {}
CACHE_TTL_SECONDS = 5.0


def _cache_get(engine: str, scope: str) -> bool | None:
    import time
    entry = _CACHE.get((engine, scope))
    if not entry:
        return None
    expires_at, value = entry
    if expires_at < time.time():
        _CACHE.pop((engine, scope), None)
        return None
    return value


def _cache_set(engine: str, scope: str, value: bool) -> None:
    import time
    _CACHE[(engine, scope)] = (time.time() + CACHE_TTL_SECONDS, value)


def _cache_clear(engine: str, scope: str) -> None:
    _CACHE.pop((engine, scope), None)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _load_state(
    engine: str, scope: str, db: AsyncSession
) -> CircuitBreakerState | None:
    stmt = (
        select(CircuitBreakerState)
        .where(CircuitBreakerState.engine == engine)
        .where(CircuitBreakerState.scope == scope)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _ensure_state(
    engine: str, scope: str, db: AsyncSession
) -> CircuitBreakerState:
    """Return the breaker row, creating one with the platform
    defaults if this is the first call for the (engine, scope)
    pair. The ``scope='default'`` row is what the pipeline
    uses by default; per-symbol/per-timeframe callers can pass
    their own scope and get an independent row.
    """
    row = await _load_state(engine, scope, db)
    if row is not None:
        return row
    row = CircuitBreakerState(
        engine=engine, scope=scope, state="closed",
        consecutive_failures=0,
        failure_threshold=settings.CB_FAILURE_THRESHOLD,
        open_duration_seconds=settings.CB_OPEN_SECONDS,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def is_open(engine: str, scope: str = "default") -> bool:
    """Hot-path check: ``True`` iff the breaker is currently
    open (blocking) for this (engine, scope).

    Auto-transitions ``open`` → ``half_open`` once
    ``open_duration_seconds`` has elapsed. ``half_open`` is
    treated as *not open* so the next call can probe.
    """
    cached = _cache_get(engine, scope)
    if cached is not None:
        return cached

    async with async_session_factory() as db:
        row = await _ensure_state(engine, scope, db)
        if row.state == "open":
            if row.opened_at is None:
                # Defensive: an open breaker without an
                # opened_at is malformed. Close it so we can
                # make progress.
                row.state = "closed"
                row.consecutive_failures = 0
                row.opened_at = None
                await db.commit()
                _cache_set(engine, scope, False)
                return False
            elapsed = (_now() - row.opened_at).total_seconds()
            if elapsed >= row.open_duration_seconds:
                row.state = "half_open"
                row.half_open_at = _now()
                row.last_transition_reason = "open_duration_elapsed"
                await db.commit()
                _cache_set(engine, scope, False)
                logger.info(
                    "circuit_breaker_half_open",
                    extra={"engine": engine, "scope": scope, "elapsed_s": elapsed},
                )
                return False
            _cache_set(engine, scope, True)
            return True
        _cache_set(engine, scope, False)
        return False


async def record_success(engine: str, scope: str = "default") -> None:
    """Reset the failure counter and close the breaker if it
    was half-open. The pipeline calls this on every successful
    call to the engine.
    """
    async with async_session_factory() as db:
        row = await _ensure_state(engine, scope, db)
        changed = False
        if row.state != "closed":
            row.state = "closed"
            row.consecutive_failures = 0
            row.opened_at = None
            row.half_open_at = None
            row.last_transition_reason = "success_after_half_open"
            changed = True
        else:
            row.consecutive_failures = 0
        row.last_success_at = _now()
        await db.commit()
        if changed:
            logger.info(
                "circuit_breaker_closed",
                extra={"engine": engine, "scope": scope},
            )
    _cache_clear(engine, scope)


async def record_failure(
    engine: str, scope: str = "default", *, reason: str = ""
) -> None:
    """Increment the failure counter and trip the breaker
    when it crosses ``failure_threshold``. Idempotent across
    multiple processes — a Redis lock isn't required because
    the worst case is a single extra failure counted.
    """
    async with async_session_factory() as db:
        row = await _ensure_state(engine, scope, db)
        row.consecutive_failures = (row.consecutive_failures or 0) + 1
        row.last_failure_at = _now()
        if (
            row.state != "open"
            and row.consecutive_failures >= row.failure_threshold
        ):
            row.state = "open"
            row.opened_at = _now()
            row.half_open_at = None
            row.last_transition_reason = (
                f"threshold_reached:{row.consecutive_failures} "
                f">= {row.failure_threshold}; reason={reason[:120]}"
            )
            logger.error(
                "circuit_breaker_opened",
                extra={
                    "engine": engine,
                    "scope": scope,
                    "consecutive_failures": row.consecutive_failures,
                    "threshold": row.failure_threshold,
                    "reason": reason[:120],
                },
            )
        await db.commit()
    _cache_clear(engine, scope)


async def force_close(engine: str, scope: str = "default", *, reason: str = "operator") -> None:
    """Operator override: close the breaker regardless of
    failure state. Used by the admin endpoint.
    """
    async with async_session_factory() as db:
        row = await _ensure_state(engine, scope, db)
        row.state = "closed"
        row.consecutive_failures = 0
        row.opened_at = None
        row.half_open_at = None
        row.last_transition_reason = f"force_close:{reason}"
        row.updated_at = _now()
        await db.commit()
        logger.warning(
            "circuit_breaker_force_closed",
            extra={"engine": engine, "scope": scope, "reason": reason},
        )
    _cache_clear(engine, scope)


async def get_state(
    engine: str, scope: str = "default"
) -> dict[str, Any]:
    """Return the current breaker state for the admin
    endpoint. Reads from the DB directly (bypasses the cache)
    so the operator always sees the truth.
    """
    async with async_session_factory() as db:
        row = await _ensure_state(engine, scope, db)
        return {
            "engine": row.engine,
            "scope": row.scope,
            "state": row.state,
            "consecutive_failures": row.consecutive_failures,
            "failure_threshold": row.failure_threshold,
            "open_duration_seconds": row.open_duration_seconds,
            "last_failure_at": (
                row.last_failure_at.isoformat() if row.last_failure_at else None
            ),
            "last_success_at": (
                row.last_success_at.isoformat() if row.last_success_at else None
            ),
            "opened_at": row.opened_at.isoformat() if row.opened_at else None,
            "half_open_at": row.half_open_at.isoformat() if row.half_open_at else None,
            "last_transition_reason": row.last_transition_reason,
        }


async def list_all_states() -> list[dict[str, Any]]:
    """List every breaker row. Used by the admin dashboard.
    """
    async with async_session_factory() as db:
        stmt = select(CircuitBreakerState).order_by(
            CircuitBreakerState.engine, CircuitBreakerState.scope
        )
        rows = (await db.execute(stmt)).scalars().all()
        return [
            {
                "engine": r.engine,
                "scope": r.scope,
                "state": r.state,
                "consecutive_failures": r.consecutive_failures,
                "failure_threshold": r.failure_threshold,
                "opened_at": r.opened_at.isoformat() if r.opened_at else None,
                "last_failure_at": (
                    r.last_failure_at.isoformat() if r.last_failure_at else None
                ),
                "last_transition_reason": r.last_transition_reason,
            }
            for r in rows
        ]


__all__ = [
    "is_open",
    "record_success",
    "record_failure",
    "force_close",
    "get_state",
    "list_all_states",
]
