"""Lightweight Prometheus-compatible metrics.

Why
---
Phase 5's quality gate produces audit rows in PostgreSQL, but
operators want live counters and gauges without a SQL query.
This module is a minimal in-process registry that exposes
the same shape Prometheus expects (counters, gauges, histograms)
plus a /metrics text-format exporter.

We intentionally don't depend on the ``prometheus_client``
package — its multiprocess mode requires a shared-memory
backend that's fiddly to wire into a Celery worker. The
in-process registry is good enough for a single-tenant
deployment and trivially testable.

Output format
-------------
``render()`` returns the standard ``# HELP`` / ``# TYPE`` /
``name{label="..."} value`` Prometheus text format. The
admin endpoint returns it as ``text/plain``.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any

# ── Counter ────────────────────────────────────────────────────
class Counter:
    """A monotonically increasing counter with labels.

    The label tuple is hashed and used as the dict key so
    callers don't have to manage it themselves.
    """

    def __init__(self, name: str, help_: str = ""):
        self.name = name
        self.help_ = help_
        self._values: dict[tuple[tuple[str, str], ...], float] = {}
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        key = tuple(sorted(labels.items()))
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def value(self, **labels: str) -> float:
        key = tuple(sorted(labels.items()))
        with self._lock:
            return self._values.get(key, 0.0)

    def render(self) -> list[str]:
        lines = []
        if self.help_:
            lines.append(f"# HELP {self.name} {self.help_}")
        lines.append(f"# TYPE {self.name} counter")
        with self._lock:
            items = list(self._values.items())
        items.sort(key=lambda kv: kv[0])
        for key, val in items:
            if key:
                label_str = ",".join(f'{k}="{v}"' for k, v in key)
                lines.append(f"{self.name}{{{label_str}}} {val}")
            else:
                lines.append(f"{self.name} {val}")
        return lines


# ── Gauge ──────────────────────────────────────────────────────
class Gauge:
    """A value that can go up or down."""

    def __init__(self, name: str, help_: str = ""):
        self.name = name
        self.help_ = help_
        self._values: dict[tuple[tuple[str, str], ...], float] = {}
        self._lock = threading.Lock()

    def set(self, value: float, **labels: str) -> None:
        key = tuple(sorted(labels.items()))
        with self._lock:
            self._values[key] = float(value)

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        key = tuple(sorted(labels.items()))
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def dec(self, amount: float = 1.0, **labels: str) -> None:
        self.inc(-amount, **labels)

    def render(self) -> list[str]:
        lines = []
        if self.help_:
            lines.append(f"# HELP {self.name} {self.help_}")
        lines.append(f"# TYPE {self.name} gauge")
        with self._lock:
            items = list(self._values.items())
        items.sort(key=lambda kv: kv[0])
        for key, val in items:
            if key:
                label_str = ",".join(f'{k}="{v}"' for k, v in key)
                lines.append(f"{self.name}{{{label_str}}} {val}")
            else:
                lines.append(f"{self.name} {val}")
        return lines


# ── Histogram ──────────────────────────────────────────────────
class Histogram:
    """A simple fixed-bucket histogram.

    Default buckets are sized for an HTTP-style latency
    distribution. Callers can override; the +Inf bucket is
    always present.
    """

    DEFAULT_BUCKETS = (
        0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
    )

    def __init__(self, name: str, help_: str = "", buckets: tuple = DEFAULT_BUCKETS):
        self.name = name
        self.help_ = help_
        self.buckets = tuple(sorted(buckets))
        self._counts: dict[tuple[tuple[str, str], ...], list[int]] = {}
        self._sums: dict[tuple[tuple[str, str], ...], float] = {}
        # Raw observations kept per label set so ``quantile()`` can
        # return an exact answer instead of a bucket approximation.
        # Bounded by the number of label combinations times the
        # total observations; for the API-latency histogram that's
        # bounded by the route count * request count, well within
        # the process memory budget for a single-tenant service.
        self._observations: dict[tuple[tuple[str, str], ...], list[float]] = {}
        self._lock = threading.Lock()

    def observe(self, value: float, **labels: str) -> None:
        key = tuple(sorted(labels.items()))
        with self._lock:
            counts = self._counts.setdefault(
                key, [0] * (len(self.buckets) + 1)
            )
            for i, b in enumerate(self.buckets):
                if value <= b:
                    counts[i] += 1
            counts[-1] += 1  # +Inf bucket
            self._sums[key] = self._sums.get(key, 0.0) + float(value)
            obs = self._observations.setdefault(key, [])
            obs.append(float(value))

    def quantile(self, q: float, **labels: str) -> float | None:
        """Return the q-quantile (0 < q < 1) of observations with
        matching labels. ``None`` if no observations match.

        Uses linear interpolation between sorted observations, the
        same way numpy.percentile does. The SLO test relies on this
        to assert that p95 is under budget.
        """
        if not 0 < q < 1:
            raise ValueError("q must be in (0, 1)")
        key = tuple(sorted(labels.items()))
        with self._lock:
            obs = list(self._observations.get(key, []))
        if not obs:
            return None
        obs.sort()
        # Linear interpolation: pick the index ``q * (n - 1)``.
        pos = q * (len(obs) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(obs) - 1)
        frac = pos - lo
        return obs[lo] * (1 - frac) + obs[hi] * frac

    def render(self) -> list[str]:
        lines = []
        if self.help_:
            lines.append(f"# HELP {self.name} {self.help_}")
        lines.append(f"# TYPE {self.name} histogram")
        with self._lock:
            keys = list(self._counts.keys())
        keys.sort()
        for key in keys:
            label_str = (
                ",".join(f'{k}="{v}"' for k, v in key) + "," if key else ""
            )
            counts = self._counts[key]
            cum = 0
            for i, b in enumerate(self.buckets):
                cum = counts[i]
                # le= bucket is cumulative
                bucket_label = f'{label_str}le="{b}"'
                lines.append(f"{self.name}_bucket{{{bucket_label}}} {cum}")
            # +Inf bucket
            inf_label = f'{label_str}le="+Inf"'
            lines.append(f"{self.name}_bucket{{{inf_label}}} {counts[-1]}")
            sum_ = self._sums.get(key, 0.0)
            label_clean = "{" + label_str.rstrip(",") + "}" if label_str else ""
            lines.append(f"{self.name}_sum{label_clean} {sum_}")
            lines.append(f"{self.name}_count{label_clean} {counts[-1]}")
        return lines


# ── Registry ───────────────────────────────────────────────────
class MetricsRegistry:
    """The process-wide metrics container."""

    def __init__(self) -> None:
        # Signal pipeline metrics.
        self.signals_emitted = Counter(
            "trading_signals_emitted_total",
            "Signals emitted by the canonical pipeline, by engine/direction.",
        )
        self.signals_blocked_quality = Counter(
            "trading_signals_blocked_quality_total",
            "Signals blocked by the quality gate (engine auto-disabled).",
        )
        self.signals_blocked_breaker = Counter(
            "trading_signals_blocked_breaker_total",
            "Signals blocked by an open circuit breaker.",
        )
        # Resolution metrics.
        self.signal_resolutions = Counter(
            "trading_signal_resolutions_total",
            "Signals resolved by outcome (tp/sl/expired/etc).",
        )
        self.outcome_forward_return = Histogram(
            "trading_outcome_forward_return_pct",
            "Distribution of forward-return on resolved signals.",
            buckets=(-5, -2, -1, -0.5, 0, 0.5, 1, 2, 5, 10),
        )
        # Self-learning metrics.
        self.weight_adjustments = Counter(
            "trading_weight_adjustments_total",
            "Successful self-learning weight adjustments.",
        )
        self.weight_adjustment_skips = Counter(
            "trading_weight_adjustment_skips_total",
            "Skipped weight adjustments (insufficient data / not enough time).",
        )
        # ML retrain / OOS.
        self.ml_retrain_runs = Counter(
            "trading_ml_retrain_runs_total",
            "ML retrain runs and their outcome (ok / skipped / failed).",
        )
        self.ml_oos_hit_rate = Gauge(
            "trading_ml_oos_hit_rate",
            "Last OOS hit rate observed by the retrain job (0-1).",
        )
        # Quality gate / circuit breaker.
        self.quality_evaluations = Counter(
            "trading_quality_evaluations_total",
            "Quality-gate evaluations by engine and result.",
        )
        self.engines_disabled = Gauge(
            "trading_engines_disabled",
            "Engines currently auto-disabled by the quality gate (1 = disabled).",
        )
        self.breaker_state = Gauge(
            "trading_circuit_breaker_state",
            "Current circuit-breaker state per engine (0=closed, 1=half_open, 2=open).",
        )
        self.breaker_transitions = Counter(
            "trading_circuit_breaker_transitions_total",
            "Circuit-breaker state transitions, by engine and target state.",
        )
        # Pipeline / API latency.
        self.api_latency = Histogram(
            "trading_api_request_seconds",
            "API request latency by route.",
        )
        self.outcome_resolution_duration = Histogram(
            "trading_outcome_resolution_seconds",
            "Time to walk forward through candles and resolve a signal.",
        )

    def render(self) -> str:
        # Iterate every metric and concatenate. The order is
        # fixed for stable test assertions.
        all_metrics: list[Any] = [
            self.signals_emitted, self.signals_blocked_quality,
            self.signals_blocked_breaker,
            self.signal_resolutions, self.outcome_forward_return,
            self.weight_adjustments, self.weight_adjustment_skips,
            self.ml_retrain_runs, self.ml_oos_hit_rate,
            self.quality_evaluations, self.engines_disabled,
            self.breaker_state, self.breaker_transitions,
            self.api_latency, self.outcome_resolution_duration,
        ]
        out: list[str] = []
        for m in all_metrics:
            out.extend(m.render())
        return "\n".join(out) + "\n"

    def reset(self) -> None:
        """Test helper — wipe all counters / gauges so a unit
        test can assert a known starting state.
        """
        for m in (
            self.signals_emitted, self.signals_blocked_quality,
            self.signals_blocked_breaker,
            self.signal_resolutions,
            self.weight_adjustments, self.weight_adjustment_skips,
            self.ml_retrain_runs,
            self.quality_evaluations, self.breaker_transitions,
        ):
            m._values.clear()
        for m in (
            self.ml_oos_hit_rate, self.engines_disabled, self.breaker_state,
        ):
            m._values.clear()
        for m in (self.outcome_forward_return, self.api_latency,
                  self.outcome_resolution_duration):
            m._counts.clear()
            m._sums.clear()
            m._observations.clear()


# Process-wide singleton. ``import metrics`` from anywhere.
registry = MetricsRegistry()


__all__ = ["Counter", "Gauge", "Histogram", "MetricsRegistry", "registry"]
