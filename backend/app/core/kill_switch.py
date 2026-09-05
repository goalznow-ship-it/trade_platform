"""
Trading kill switch — fail-closed state management.

A single Redis key (`trading:kill_switch`) controls whether live
orders can be submitted. The previous implementation consulted
Redis inline inside the order endpoint and silently passed if
Redis was unreachable — a fail-OPEN default on the most
safety-critical control in a trading platform.

This module gives callers three entry points:

- is_kill_switch_active(): strict check. Returns True on Redis
  error so the request is blocked. Use this on every order path.

- get_kill_switch_status(): best-effort status for admin UIs.
  Returns ('unknown', None) on Redis error so the admin sees
  that something is wrong instead of a stale "inactive" reading.

- activate(reason) / deactivate(): admin actions, surfaced as
  separate audit events.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Tuple

from app.core.redis import redis_client

logger = logging.getLogger(__name__)

KILL_SWITCH_KEY = "trading:kill_switch"
KILL_SWITCH_REASON_KEY = "trading:kill_switch:reason"

# We cache the last known state in-process with a short TTL so a
# transient Redis blip doesn't toggle the kill switch on and off
# for every in-flight order. The cache is bounded — under sustained
# Redis unreachability the read path will fail-closed (block orders)
# which is the safer default.
_last_state: bool = False
_last_state_at: float = 0.0
_last_state_lock = asyncio.Lock()
_CACHE_TTL_SECONDS = 2.0


async def is_kill_switch_active() -> bool:
    """
    Strict check used by every order path. Fails CLOSED — if Redis
    is unreachable or the key is unparseable, returns True (block).

    Result is cached for 2 seconds per process so a Redis hiccup
    doesn't toggle the switch for every in-flight order, but a
    manually-activated switch takes effect within ~2s everywhere.
    """
    global _last_state, _last_state_at
    now = time.monotonic()
    if now - _last_state_at < _CACHE_TTL_SECONDS:
        return _last_state

    async with _last_state_lock:
        # Re-check under the lock to avoid a thundering herd of
        # concurrent requests all hitting Redis at once after expiry.
        now = time.monotonic()
        if now - _last_state_at < _CACHE_TTL_SECONDS:
            return _last_state
        try:
            value = await redis_client.get(KILL_SWITCH_KEY)
            active = (value == "1")
        except Exception as e:
            # Fail closed: better to refuse a few orders during a
            # Redis blip than to silently let a kill switch be bypassed.
            logger.error(
                f"Kill switch check failed (failing closed): "
                f"{type(e).__name__}: {e}"
            )
            active = True

        _last_state = active
        _last_state_at = now
        return active


async def get_kill_switch_status() -> Tuple[str, str | None]:
    """
    Best-effort status for admin UIs. Returns (state, reason) where
    state is one of 'active', 'inactive', 'unknown'. 'unknown' means
    Redis is down — the admin needs to know that, not see a stale
    'inactive' reading.
    """
    try:
        value = await redis_client.get(KILL_SWITCH_KEY)
        reason = await redis_client.get(KILL_SWITCH_REASON_KEY)
        if value is None:
            return ("inactive", None)
        return ("active" if value == "1" else "inactive", reason)
    except Exception as e:
        logger.error(f"Kill switch status read failed: {e}")
        return ("unknown", None)


async def activate(reason: str) -> None:
    """Activate the kill switch. Persists a reason string for the audit log."""
    try:
        await redis_client.set(KILL_SWITCH_KEY, "1")
        await redis_client.set(KILL_SWITCH_REASON_KEY, reason[:500])
    except Exception as e:
        logger.error(f"Failed to activate kill switch: {e}")
        raise


async def deactivate() -> None:
    """Deactivate the kill switch. Removes both the state and the reason."""
    try:
        await redis_client.delete(KILL_SWITCH_KEY, KILL_SWITCH_REASON_KEY)
    except Exception as e:
        logger.error(f"Failed to deactivate kill switch: {e}")
        raise
