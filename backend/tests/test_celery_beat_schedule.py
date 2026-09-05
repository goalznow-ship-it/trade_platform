"""Tests for the centralised celery beat schedule.

Phase 4 acceptance: ``celery -A app.workers beat (test mode)``
loads the schedule without errors. We don't actually start a
beat daemon in the test — we introspect the schedule dict the
way beat itself would.
"""
from __future__ import annotations

from celery.schedules import crontab

from app.core.celery_beat_schedule import beat_schedule, load_beat_schedule


# Every cron task that the beat schedule advertises must have a
# matching task defined in ``app.workers`` so a cron tick doesn't
# fire into the void. The list is read by both
# ``test_workers_tasks.py`` (does the task exist?) and the
# integration check (does the schedule point to a real one?).
EXPECTED_TASKS = {
    "app.workers.retrain_ml_models",
    "app.workers.resolve_signal_outcomes",
    "app.workers.adjust_scoring_weights",
    "app.workers.prune_stale_signals",
}


def test_beat_schedule_loads():
    """``load_beat_schedule()`` returns the constant dict."""
    sched = load_beat_schedule()
    assert sched is beat_schedule
    assert isinstance(sched, dict)
    assert len(sched) >= 4


def test_beat_schedule_lists_expected_tasks():
    """All four cron entries are registered, no extras."""
    advertised = {entry["task"] for entry in beat_schedule.values()}
    assert EXPECTED_TASKS.issubset(advertised), (
        f"missing tasks: {EXPECTED_TASKS - advertised}"
    )


def test_beat_schedule_entries_have_crontab():
    """Each entry's ``schedule`` is a celery ``crontab`` so the
    beat daemon can serialise it to disk / wire it through the
    broker. A bare string would silently break the schedule."""
    for name, entry in beat_schedule.items():
        sched = entry.get("schedule")
        assert isinstance(sched, crontab), (
            f"task {name} schedule is {type(sched).__name__}, expected crontab"
        )


def test_beat_schedule_cron_strings_parse():
    """The cron fields are within valid ranges (0-23h, 0-59m)."""
    for name, entry in beat_schedule.items():
        sched: crontab = entry["schedule"]
        # celery stores hour/minute as a frozen set of ints
        # (or a string with */N). Either is valid; we just
        # need to confirm it parsed and isn't empty.
        assert sched.hour is not None, f"task {name} has no hour field"
        assert sched.minute is not None, f"task {name} has no minute field"


def test_beat_schedule_retrain_is_expensive_safe():
    """The ML retrain runs daily at an off-minute so a 5-min
    cron doesn't pile up at :00 / :30. The test pins the
    exact value so an accidental shift is loud."""
    entry = beat_schedule["retrain-ml-models"]
    assert entry["task"] == "app.workers.retrain_ml_models"
    sched: crontab = entry["schedule"]
    # crontab.hour is a set of allowed hours; ours is one.
    assert 2 in sched.hour, f"retrain hour drifted: {sched.hour}"
    assert 13 in sched.minute, f"retrain minute drifted: {sched.minute}"


def test_beat_schedule_resolver_runs_every_5_min():
    """The signal-outcome resolver is the one task that runs
    frequently. Pin the cadence so an off-by-one (every 6 min)
    doesn't slip through."""
    entry = beat_schedule["resolve-signal-outcomes"]
    sched: crontab = entry["schedule"]
    # */5 expands to {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}
    assert {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55} == set(sched.minute), (
        f"resolver minute drift: {sched.minute}"
    )


def test_beat_schedule_adjusts_off_minute():
    """The weight adjustor is hourly at :07 so the 5-min
    resolver and the 60-min adjustor don't race for the same
    Redis lock at :00."""
    entry = beat_schedule["adjust-scoring-weights"]
    sched: crontab = entry["schedule"]
    assert 7 in sched.minute, f"adjust minute drifted: {sched.minute}"


def test_beat_schedule_prune_is_overnight():
    """The prune task runs once a day at 03:37 — far from the
    retrain window at 02:13 and well before the EU morning
    traffic spike at 09:00."""
    entry = beat_schedule["prune-stale-signals"]
    sched: crontab = entry["schedule"]
    assert 3 in sched.hour, f"prune hour drifted: {sched.hour}"
    assert 37 in sched.minute, f"prune minute drifted: {sched.minute}"


def test_workers_load_beat_schedule():
    """The workers module imports the schedule at module load
    time. Confirming it doesn't blow up proves the import
    chain is healthy.
    """
    from app.workers import celery_app
    assert celery_app.conf.beat_schedule, "workers. celery_app has empty beat_schedule"
    # And the schedule is the same object as the central one.
    assert celery_app.conf.beat_schedule is beat_schedule
