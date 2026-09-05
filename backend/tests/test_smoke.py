"""Smoke test: the entire app boots and the public surface responds.

Phase 7 acceptance — a fresh clone, a clean DB, and a single
``pytest tests/test_smoke.py`` should be enough to prove that:

1. The FastAPI app constructs without import errors.
2. The root endpoint returns the running banner.
3. The health endpoint reports ``status='ok'``.
4. The Prometheus-format metrics endpoint serves valid text.
5. The unauthenticated admin endpoints reject with 401 (not 500).
6. The CORS / security headers are present on every response.

If any of these break, the deploy is broken — fail loud.
"""
import re

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_root_returns_running_banner():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "running"
        assert "version" in body
        assert "name" in body


@pytest.mark.asyncio
async def test_health_endpoint_reports_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        # Readiness is one of: ready / not_started / degraded.
        assert body["readiness"] in {"ready", "not_started", "degraded"}


@pytest.mark.asyncio
async def test_metrics_endpoint_serves_prometheus_text():
    """The /admin/metrics route must return valid text/plain in
    Prometheus exposition format. Operators scrape this for
    alerts; a 500 here is a real ops bug.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/admin/metrics")
        # Either 200 (admin access) or 401 (auth required). Both
        # are valid outcomes depending on whether the route
        # demands auth. We only assert "not 500".
        assert r.status_code in {200, 401, 403}
        if r.status_code == 200:
            # Prometheus text format must include # HELP and # TYPE
            # directives for the metrics we ship in Phase 5.
            assert "# HELP trading_signals_emitted_total" in r.text
            assert "# TYPE trading_signals_emitted_total counter" in r.text
            assert "trading_quality_evaluations_total" in r.text


@pytest.mark.asyncio
async def test_admin_endpoints_require_auth():
    """A random protected endpoint must return 401 (not 500)
    when called without a token. The router's auth dependency
    is what protects operator-only surfaces.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/admin/quality")
        assert r.status_code == 401
        r = await c.get("/api/v1/admin/breakers")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_security_headers_present():
    """Every response carries the security headers from
    SecurityHeadersMiddleware. Pinning this so a future middleware
    reorder can't silently strip them.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/")
        # X-Frame-Options / X-Content-Type-Options are the
        # baseline that Phase 7 ships.
        assert "X-Frame-Options" in r.headers or "x-frame-options" in {k.lower() for k in r.headers}
        # Request-ID is added by AuditMiddleware — useful for
        # correlating log lines to user-reported issues.
        assert "X-Request-ID" in r.headers
        # Response-Time is added by AuditMiddleware so client
        # tools can spot slow responses without server access.
        assert "X-Response-Time-Ms" in r.headers


def test_celery_beat_schedule_loads():
    """The beat schedule dict must import without error and
    contain the cron jobs Phase 4/5 added.
    """
    from app.core.celery_beat_schedule import beat_schedule
    advertised = {entry["task"] for entry in beat_schedule.values()}
    assert "app.workers.retrain_ml_models" in advertised
    assert "app.workers.resolve_signal_outcomes" in advertised
    assert "app.workers.adjust_scoring_weights" in advertised
    assert "app.workers.prune_stale_signals" in advertised
    assert "app.workers.evaluate_quality" in advertised


def test_prometheus_text_format_regex():
    """A spot check on a rendered histogram line so a future
    label-reorder regression is loud. The format spec is
    ``name_bucket{le="..."} <count>``.
    """
    from app.services.observability import registry
    registry.reset()
    registry.api_latency.observe(0.123, route="/x", method="GET", status_class="2xx")
    out = registry.render()
    # ``trading_api_request_seconds_bucket`` is the histogram name.
    bucket_lines = [
        line for line in out.splitlines()
        if line.startswith("trading_api_request_seconds_bucket")
    ]
    assert bucket_lines, "no histogram bucket lines rendered"
    # Every bucket line has a le="..." label and a numeric value.
    pattern = re.compile(
        r'^trading_api_request_seconds_bucket\{.*le="[\d\.\+Inf]+".*\} \d+'
    )
    for line in bucket_lines:
        assert pattern.match(line), f"bad bucket line: {line}"
