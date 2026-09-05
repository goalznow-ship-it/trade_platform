"""Tests for the in-process metrics registry.

We don't need a real Prometheus server — the registry is
self-contained. The tests cover the increment / observe /
render surface and pin the Prometheus text-format output
so a silent change (e.g. label reordering) fails loud.
"""
from __future__ import annotations

from app.services.observability import Counter, Gauge, Histogram, registry


def test_counter_increments_and_renders():
    """A counter starts at 0, increments with labels, and
    renders as ``# TYPE name counter`` plus the values.
    """
    c = Counter("test_counter", "help text")
    c.inc(3.0, route="/a")
    c.inc(2.0, route="/a")
    c.inc(1.0, route="/b")
    rendered = c.render()
    # The metric name, the help line, and three value lines.
    assert any(line.startswith("# HELP test_counter") for line in rendered)
    assert any(line.startswith("# TYPE test_counter counter") for line in rendered)
    # Per-label value lines exist.
    body = "\n".join(rendered)
    assert 'test_counter{route="/a"} 5' in body
    assert 'test_counter{route="/b"} 1' in body


def test_gauge_set_and_render():
    """A gauge holds a settable value per label set."""
    g = Gauge("test_gauge", "g")
    g.set(42, engine="ml")
    g.set(7, engine="xgb")
    body = "\n".join(g.render())
    assert 'test_gauge{engine="ml"} 42' in body
    assert 'test_gauge{engine="xgb"} 7' in body
    # ``inc`` and ``dec`` move the value.
    g.inc(3, engine="ml")
    g.dec(2, engine="xgb")
    body = "\n".join(g.render())
    assert 'test_gauge{engine="ml"} 45' in body
    assert 'test_gauge{engine="xgb"} 5' in body


def test_histogram_buckets_cumulative():
    """Buckets are cumulative — every observation that fell
    into bucket B also fell into every bucket > B.
    """
    h = Histogram("test_hist", "h", buckets=(0.1, 0.5, 1.0))
    h.observe(0.05)   # bucket le=0.1
    h.observe(0.30)   # bucket le=0.5
    h.observe(2.0)    # only +Inf
    body = "\n".join(h.render())
    # ``le="0.1"`` is cumulative: just the first observation.
    assert 'test_hist_bucket{le="0.1"} 1' in body
    # ``le="0.5"`` is cumulative: 2 (first + second).
    assert 'test_hist_bucket{le="0.5"} 2' in body
    # ``le="1.0"`` is cumulative: still 2 (third was 2.0).
    assert 'test_hist_bucket{le="1.0"} 2' in body
    # ``+Inf`` is the total: 3.
    assert 'test_hist_bucket{le="+Inf"} 3' in body
    # ``_sum`` is the running total.
    assert "test_hist_sum 2.35" in body
    assert "test_hist_count 3" in body


def test_registry_includes_quality_and_breaker_metrics():
    """The process-wide registry ships with the metrics
    Phase 5 relies on. Missing one would mean a regression
    in the public monitoring surface.
    """
    expected = {
        "trading_signals_emitted_total",
        "trading_signals_blocked_quality_total",
        "trading_signals_blocked_breaker_total",
        "trading_signal_resolutions_total",
        "trading_outcome_forward_return_pct",
        "trading_weight_adjustments_total",
        "trading_ml_retrain_runs_total",
        "trading_ml_oos_hit_rate",
        "trading_quality_evaluations_total",
        "trading_engines_disabled",
        "trading_circuit_breaker_state",
        "trading_circuit_breaker_transitions_total",
        "trading_api_request_seconds",
    }
    rendered = registry.render()
    for name in expected:
        assert name in rendered, f"missing metric: {name}"


def test_registry_render_format():
    """The output is valid Prometheus text format. Pin
    a small slice so a label-ordering regression is loud.
    """
    registry.reset()
    registry.signals_emitted.inc(1, engine="ml", direction="long")
    registry.engines_disabled.set(1.0, engine="ml")
    out = registry.render()
    # Counter section.
    assert "# TYPE trading_signals_emitted_total counter" in out
    # Gauge section.
    assert "# TYPE trading_engines_disabled gauge" in out
    # Label ordering is sorted alphabetically so a swap
    # between engines is visible.
    assert 'trading_signals_emitted_total{direction="long",engine="ml"} 1' in out


def test_reset_clears_all_state():
    """``reset()`` returns the registry to a known state
    so a unit test can start from zero. Without it, a
    counter increment in one test would leak into the next.
    """
    registry.signals_emitted.inc(99)
    registry.reset()
    body = registry.render()
    # After reset, no body lines for this counter.
    for line in body.splitlines():
        assert not line.startswith("trading_signals_emitted_total{")
