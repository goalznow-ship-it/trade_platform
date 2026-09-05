"""Tests for the API latency SLO.

The SLO is simple: p95 of ``trading_api_request_seconds`` must stay
under ``settings.SLO_API_P95_SECONDS``. The latency middleware feeds
the histogram; this test verifies both the feeder and the budget
check.

Why we exercise the middleware in-process
-----------------------------------------
Spinning up the FastAPI app under TestClient + threading captures
real middleware execution without the complexity of uvicorn.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.metrics_middleware import MetricsMiddleware
from app.services.observability import registry


@pytest.fixture(autouse=True)
def _reset_latency():
    """Wipe the latency histogram between tests so a slow
    observation in one test doesn't bleed into the SLO budget
    of the next.
    """
    registry.api_latency._counts.clear()
    registry.api_latency._sums.clear()
    registry.api_latency._observations.clear()
    yield
    registry.api_latency._counts.clear()
    registry.api_latency._sums.clear()
    registry.api_latency._observations.clear()


def _build_app() -> FastAPI:
    """Minimal FastAPI app for middleware testing. The handler
    sleeps a configurable amount to simulate a slow endpoint."""
    import asyncio

    from fastapi import Query

    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/fast")
    async def fast():
        return {"ok": True}

    @app.get("/slow")
    async def slow(ms: int = Query(0, ge=0, le=2000)):
        await asyncio.sleep(ms / 1000.0)
        return {"ok": True}

    @app.get("/static/file.txt")
    async def static_file():
        return {"ok": True}

    return app


def test_middleware_records_latency_on_routed_request():
    """A normal API call lands in the histogram with the templated
    path (so cardinality stays bounded).
    """
    app = _build_app()
    client = TestClient(app)
    r = client.get("/fast")
    assert r.status_code == 200
    p50 = registry.api_latency.quantile(
        0.50, route="/fast", method="GET", status_class="2xx"
    )
    assert p50 is not None
    # A no-op handler is sub-millisecond, but allow some slack.
    assert p50 < 0.5


def test_middleware_uses_templated_path_not_raw_url():
    """Cardinality matters: a single API endpoint with a path
    parameter (``/items/42``, ``/items/99``) must be recorded
    once, not twice.
    """
    from fastapi import Path

    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/items/{item_id}")
    async def get_item(item_id: int = Path(...)):
        return {"id": item_id}

    client = TestClient(app)
    client.get("/items/1")
    client.get("/items/2")
    client.get("/items/3")

    # One label set, three observations.
    p50 = registry.api_latency.quantile(
        0.50, route="/items/{item_id}", method="GET", status_class="2xx"
    )
    assert p50 is not None
    # Count the observations for that label set.
    key = tuple(sorted({
        "route": "/items/{item_id}", "method": "GET", "status_class": "2xx",
    }.items()))
    assert len(registry.api_latency._observations[key]) == 3


def test_middleware_skips_static_assets():
    """Static asset paths are not recorded — they would otherwise
    inflate the histogram with observations we don't care about.
    """
    app = _build_app()
    client = TestClient(app)
    client.get("/static/file.txt")
    # No histogram entries for the static path.
    p50 = registry.api_latency.quantile(
        0.50, route="/static/file.txt", method="GET", status_class="2xx"
    )
    assert p50 is None


def test_middleware_records_status_class():
    """A 4xx response still feeds the histogram with a status_class
    label so the slow tail is split by success / error in Grafana.
    """
    from fastapi import HTTPException

    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/missing")
    async def missing():
        raise HTTPException(status_code=404, detail="nope")

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/missing")
    assert r.status_code == 404
    p50 = registry.api_latency.quantile(
        0.50, route="/missing", method="GET", status_class="4xx"
    )
    assert p50 is not None


def test_slo_p95_under_budget_for_fast_endpoint():
    """A handler that responds in <5ms keeps p95 well under the
    1.0s SLO budget. This is the "happy path" SLO assertion.
    """
    app = _build_app()
    client = TestClient(app)
    for _ in range(20):
        client.get("/fast")
    p95 = registry.api_latency.quantile(
        0.95, route="/fast", method="GET", status_class="2xx"
    )
    assert p95 is not None
    assert p95 < settings.SLO_API_P95_SECONDS, (
        f"p95 {p95:.3f}s exceeded SLO budget "
        f"{settings.SLO_API_P95_SECONDS}s"
    )


def test_slo_p95_quantile_is_linear_interpolation():
    """The quantile helper uses numpy-style linear interpolation,
    not a bucket approximation. Confirm with a known distribution.
    """
    h = registry.api_latency
    key = tuple(sorted({"route": "/test", "method": "GET",
                        "status_class": "2xx"}.items()))
    # 10 observations: 1, 2, 3, ..., 10.
    for v in range(1, 11):
        h.observe(float(v), route="/test", method="GET", status_class="2xx")
    # p50 of [1..10] = 5.5
    p50 = h.quantile(0.50, route="/test", method="GET", status_class="2xx")
    assert p50 == pytest.approx(5.5)
    # p95 = 9.55
    p95 = h.quantile(0.95, route="/test", method="GET", status_class="2xx")
    assert p95 == pytest.approx(9.55)


def test_slo_budget_is_a_setting():
    """The SLO budget is settings-driven so a config drift is
    loud — operators can change the budget via env var without
    a code change.
    """
    assert hasattr(settings, "SLO_API_P95_SECONDS")
    assert settings.SLO_API_P95_SECONDS > 0
    assert settings.SLO_API_P95_SECONDS < 10  # sanity check
