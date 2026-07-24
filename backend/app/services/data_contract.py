"""Shared response metadata for every real-data module."""

from datetime import datetime, timezone
from typing import Any, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def data_meta(
    source: str,
    *,
    last_updated: Optional[str] = None,
    max_age_seconds: int = 60,
    error_reason: Optional[str] = None,
    fallback_used: bool = False,
    configured: bool = True,
) -> dict[str, Any]:
    updated = last_updated or (None if error_reason else utc_now())
    freshness = "unavailable"
    stale = True
    if updated:
        try:
            age = max(
                0,
                (datetime.now(timezone.utc) - datetime.fromisoformat(updated.replace("Z", "+00:00"))).total_seconds(),
            )
            stale = age > max_age_seconds
            freshness = "stale" if stale else "live"
        except (TypeError, ValueError):
            freshness = "unknown"
    status = (
        "not_configured" if not configured
        else "unavailable" if error_reason
        else "degraded" if fallback_used
        else "available"
    )
    return {
        "provider_status": status,
        "source": source,
        "last_updated": updated,
        "data_freshness": freshness,
        "error_reason": error_reason,
        "is_stale": stale,
        "fallback_used": fallback_used,
    }


def unavailable(source: str, reason: str, *, configured: bool = True) -> dict[str, Any]:
    return {
        "value": None,
        **data_meta(source, error_reason=reason, configured=configured),
    }
