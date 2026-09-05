# Production-Readiness Plan — Trade Platform

Seven phases, all pushed to `main`. Each phase is a self-contained
slice of work with its own tests, commit, and a one-paragraph
"what it adds" summary. This document is the long-form
post-mortem of what each phase actually changed, why those
changes were needed, and the seams future phases will use.

| # | Phase | What it adds | Commit | Tests added |
|---|-------|--------------|--------|-------------|
| 1 | Canonical signal path | Single `SignalPipeline.emit` / `persist_composed` entry point. Every emitted signal writes the same provenance columns (`factor_payload`, `weights_used`, `ml_boost`, `pipeline_version`, `model_version`, `source_engine`). | (pre-this-doc) | 6 |
| 2 | Self-learning feedback loop | SQL-backed `trades` store + `adjustment_runs` audit table. `weight_orchestrator` reads trades from SQL, writes an audit row on every run, hydrates from the latest successful run on startup. | (pre-this-doc) | 8 |
| 3 | ML reproducibility | Walk-forward validator + forward-return outcomes. Every resolved signal gets a `signal_outcomes` row (forward_return_pct, mae, mfe, bars_held). | (pre-this-doc) | 12 |
| 4 | Scheduled retrain + MLflow | Celery beat cron for the four heavy jobs, MLflow tracking with deterministic `run_id` and `registry.json` for the active model. `/backtest/ml` endpoint with 1h cache. | `0417a2a` | 21 |
| 5 | Observability + quality gate + circuit breaker | Per-engine rolling hit-rate → auto-disable, per-engine circuit breaker (closed→open→half_open→closed), in-process Counter/Gauge/Histogram, admin surface at `/api/v1/admin/quality` and `/admin/breakers`. | `674c714` | 29 |
| 6 | E2E + latency SLO + coverage + frontend history | Per-request `MetricsMiddleware` records into `trading_api_request_seconds`; SLO test asserts p95 < 1.0s; `pytest-cov` always-on; `/performance` route with Overview/History/Quality Gate tabs. | `6955272` | 11 |
| 7 | Final wiring + Definition of Done | Auth fail-closed → fail-open in non-prod (Redis-not-required in tests); trade schema split (`feedback_trades` separate from the user-journal `trades`); production-readiness doc; smoke test. | this commit | 4 |

## Why seven phases?

The platform shipped with the right *architecture* (multi-timeframe
engine, institutional scoring, ML ensemble, professional risk)
but the *runtime story* was missing. A signal could fire forever
with no quality feedback, no operator override, no latency
tracking, and no tests that exercised the full data flow.

Each phase closes one runtime gap:

1. **Phase 1** — *Reproducibility.* Without a single canonical
   emit path, every "what produced this signal?" question
   required archaeology across three different write paths.
   With `SignalPipeline`, the answer is a column on the row.

2. **Phase 2** — *Persistence.* The self-learning loop used to
   keep an in-memory trade list that evaporated on every
   process restart. Hydration from the SQL audit table on
   startup means the loop continues from where the previous
   process left off.

3. **Phase 3** — *Forward-return truth.* Walking forward
   through real candles to compute the actual return from
   entry to TP/SL/horizon gives the quality gate (Phase 5)
   real data to gate on. The same `signal_outcomes` rows are
   what the calibration drift table on `/performance` shows.

4. **Phase 4** — *Automation.* A retrain that only runs when
   someone remembers to call it is a retrain that doesn't run.
   The beat schedule is the small, boring piece that makes the
   whole pipeline self-driving. MLflow gives the audit trail
   and the `registry.json` makes the model version reproducible
   across processes.

5. **Phase 5** — *Safety.* Three independent mechanisms —
   quality gate, circuit breaker, metrics registry — that
   together turn "emit forever" into "emit while healthy,
   stop when not, and tell the operator why." None of them
   shuts the engine down (the engine stays loaded), they
   just starve it of new signal flow until an operator
   re-enables it.

6. **Phase 6** — *Visibility.* The latency middleware feeds a
   histogram the SLO test asserts against. The coverage
   reporter fails the suite when code is missed. The
   `/performance` page is the read-only surface for "how is
   the platform doing" without needing Grafana.

7. **Phase 7** — *Wiring.* Two long-standing test-only
   problems fixed: auth fails closed when Redis is missing
   (correct in production, wrong in tests) and the
   self-learning `Trade` model was sharing a table with the
   user-journal `Trade` model (the merged schema made
   `record_trade` look like every insert was a duplicate).

## Acceptance criteria checklist

| Item | Status | Where it lives |
|------|--------|----------------|
| Single canonical signal path | ✅ | `services/signal_pipeline.py:SignalPipeline.emit` |
| Every emitted signal persisted with provenance | ✅ | `_persist()` writes `factor_payload`, `weights_used`, `ml_boost`, `pipeline_version`, `model_version`, `source_engine` |
| Self-learning loop persists across restarts | ✅ | `weight_orchestrator.hydrate_from_db()` reads latest `adjustment_runs.new_weights` on startup |
| Walk-forward validation on retrain | ✅ | `services/walk_forward.py` + MLflow tracking |
| Scheduled retrain + OOS backtest | ✅ | `core/celery_beat_schedule.py:retrain-ml-models` (daily 02:13) |
| Per-engine quality gate (hit rate, auto-disable) | ✅ | `services/quality_gate.py` + `cron:evaluate-quality` (15 min) |
| Per-engine circuit breaker (5 failures → 24h block) | ✅ | `services/circuit_breaker.py` with 5s in-memory cache |
| Prometheus-compatible metrics | ✅ | `services/observability.py:registry` + `GET /api/v1/admin/metrics` |
| Per-engine admin endpoint | ✅ | `api/v1/quality.py` + `GET /admin/quality`, `GET /admin/breakers` |
| Structured logging | ✅ | `core/logging.py` — JSON logger |
| E2E signal lifecycle test | ✅ | `tests/test_e2e_signal_lifecycle.py` |
| Latency SLO (p95 < 1.0s) | ✅ | `core/metrics_middleware.py` + `tests/test_latency_slo.py` |
| Coverage report | ✅ | `pytest.ini` always-on `--cov=app` |
| Frontend history/performance page | ✅ | `frontend/src/app/performance/page.tsx` |

## How to run

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head                  # apply all migrations, including 014 (split feedback_trades)
pytest                                # run the full test suite (~170 tests)
pytest --cov=app --cov-report=html    # write the HTML coverage report
uvicorn app.main:app --reload         # dev server
celery -A app.workers worker -l info  # beat-scheduled workers
celery -A app.workers beat -l info    # beat scheduler
```

## Operational notes

- **`SLO_API_P95_SECONDS`** — set this in the env to tighten
  or loosen the p95 budget. The test asserts against it.
- **`QUALITY_MIN_HIT_RATE`** — engines with hit rate below
  this over `QUALITY_WINDOW_HOURS` get auto-disabled.
  Default 0.40, fine for the 100-point institutional scorer.
- **`CB_FAILURE_THRESHOLD`** — N consecutive failures before
  the breaker trips. Default 5.
- **`feedback_trades` migration** — migration 014 splits the
  self-learning `Trade` table out of the user-journal `Trade`
  table. Before applying this on a live DB, copy any rows
  with `source_trade_id IS NOT NULL` to `feedback_trades`
  (the migration does this automatically for PostgreSQL).
