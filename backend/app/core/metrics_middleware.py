"""Per-request latency tracking for the in-process metrics registry.

Why
---
Phase 5's `trading_api_request_seconds` histogram only matters if
something actually feeds it. Without a middleware, the bucket counts
are 0 forever and the SLO test can't fail loud when p95 drifts past
its budget.

The middleware wraps every HTTP request in a `time.perf_counter()`
and records the elapsed seconds into the histogram with labels
``route`` (the templated path, e.g. ``/api/v1/signals/{id}``) and
``method``. The templated path is what FastAPI stores on
``request.scope["route"].path`` after routing — using the raw URL
would explode the label cardinality and burn Prometheus memory.

Skipping static / docs paths keeps the histogram focused on real
work; ``/health`` is the readiness probe and is intentionally
included because slow health is a real signal.
"""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.observability import registry

# Paths the middleware will *not* record. Static assets and the
# OpenAPI / JSON-schema pages are scraped by ops tools on their own
# cadence and would otherwise drown the histogram.
_SKIP_PREFIXES: tuple[str, ...] = (
    "/static/", "/_next/", "/favicon.ico",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record every request's latency into ``registry.api_latency``.

    Failures (500 / timeout) are still recorded so the histogram
    reflects actual user experience — including the slow tail. A
    label ``status_class`` (``2xx``/``3xx``/``4xx``/``5xx``) keeps
    the success/error split queryable in Grafana.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            # The exception will be re-raised by the framework and
            # turned into a 500; we still want to record the
            # latency so a hung handler is visible in the histogram.
            raise
        finally:
            elapsed = time.perf_counter() - start
            route = _route_template(request, path)
            status_class = f"{status_code // 100}xx"
            registry.api_latency.observe(
                elapsed,
                route=route,
                method=request.method,
                status_class=status_class,
            )


def _route_template(request: Request, fallback: str) -> str:
    """Return the templated path (``/api/v1/signals/{id}``) if
    FastAPI matched a route, else the raw path.

    Falling back to the raw path is fine for unrouted requests
    (404s) — the cardinality is bounded by the number of 404 paths
    a misbehaving client can ask for, which is its own signal.
    """
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return fallback


__all__ = ["MetricsMiddleware"]
