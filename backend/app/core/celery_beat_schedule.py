"""Celery beat schedule — exported as ``beat_schedule`` dict.

The schedule is centralised here so:
- ``workers/__init__.py`` can load it on celery_app setup;
- the test suite (``test_celery_beat_schedule.py``) can introspect
  it without booting celery;
- operators can grep one file to see what runs in production.

Cron strings use deterministic offsets (not :00 / :30) so the
fleet's retrain jobs don't pile up at the top of the hour. The
``retrain-ml-models`` task is the most expensive one and runs
overnight in the deploy timezone; everything else is lightweight.
"""
from __future__ import annotations

from celery.schedules import crontab


# Each entry maps to a celery task that workers/__init__.py
# already defines. ``schedule`` is a ``crontab(...)`` (celery's
# aware type) so test_celery_beat_schedule.py can introspect
# the hour / minute / day-of-week fields without parsing the
# raw string.
beat_schedule: dict = {
    # The ML retrain is long (10-30 min on 15 symbols) and
    # produces the live ensemble for the next 24h. 02:13 local
    # — far enough from :00 that the API gateway isn't already
    # busy with traffic spikes, but before the EU open at 09:00.
    "retrain-ml-models": {
        "task": "app.workers.retrain_ml_models",
        "schedule": crontab(hour=2, minute=13),
    },
    # Resolve every active signal that has no outcome yet. Cheap
    # (one candle-walk per signal) so we run it every 5 min.
    # Off-minute so a 5-min cron doesn't pile up at 00/05/10/...
    "resolve-signal-outcomes": {
        "task": "app.workers.resolve_signal_outcomes",
        "schedule": crontab(minute="*/5"),
    },
    # Re-derive the self-learning weights from the SQL trade
    # store every hour. The orchestrator's ``adjust_weights`` is
    # idempotent — if the trade window is unchanged since the
    # last successful run, this writes a skip audit row and
    # returns.
    "adjust-scoring-weights": {
        "task": "app.workers.adjust_scoring_weights",
        "schedule": crontab(minute=7),  # 07 past every hour
    },
    # Daily cleanup of signals whose ``expires_at`` has passed
    # but were never resolved (e.g. their symbol left the
    # market_coverage top-N). 03:37 local, off-minute again.
    "prune-stale-signals": {
        "task": "app.workers.prune_stale_signals",
        "schedule": crontab(hour=3, minute=37),
    },
    # Phase 5: re-evaluate every active engine's hit rate and
    # auto-disable any that fall below the quality threshold.
    # 15-min cadence balances DB load against freshness. The
    # minute is pinned to 11/26/41/56 so it doesn't race the
    # 5-min outcome resolver.
    "evaluate-quality": {
        "task": "app.workers.evaluate_quality",
        "schedule": crontab(minute="11,26,41,56"),
    },
    # Generate live institutional signals for top 30 symbols every 15 min.
    # Off-minute (03/18/33/48) so it doesn't race the 5-min outcome
    # resolver or the 15-min quality evaluator.
    "generate-live-signals": {
        "task": "app.workers.generate_live_signals",
        "schedule": crontab(minute="03,18,33,48"),
    },
}


def load_beat_schedule() -> dict:
    """Return the schedule dict. Indirection so tests can
    monkeypatch the constant without mutating the imported
    module.
    """
    return beat_schedule
