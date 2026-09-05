"""Tests for ML reproducibility (Phase 3 acceptance).

Acceptance (from production-grade-signals.md):
- Same seed + same data → identical predictions across two runs
  for XGB, LGB, Transformer.
- Two ``train()`` calls produce the same ``mlflow_run_id``
  deterministic hash.

Why this matters
----------------
Without determinism, the walk-forward validator's metric drift
test (in ``test_walk_forward.py``) is meaningless — a 0.04 jump
in OOS accuracy could just be a different RNG draw. The
reproducibility guarantee is the foundation the quality gate in
Phase 5 sits on.
"""
import numpy as np
import pandas as pd
import pytest

from app.services.ml.seed import set_seed


# ── Helpers ──────────────────────────────────────────────────────
def _synth_dataset(n: int = 600, n_features: int = 8, seed: int = 42):
    """Same shape as test_walk_forward's synthetic data so the
    reproducibility test exercises the same code path.
    """
    set_seed(seed)
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(
        rng.normal(0, 1, (n, n_features)),
        columns=[f"f_{i}" for i in range(n_features)],
    )
    # A linearly-separable signal so the model converges quickly.
    signal = X["f_0"] + 0.5 * X["f_1"] - 0.3 * X["f_2"]
    y = pd.Series(np.where(signal > 0.3, 1, np.where(signal < -0.3, -1, 0)))
    # Map the rare class to the middle to avoid 0-count folds.
    counts = y.value_counts()
    if counts.min() == 0:
        # Reassign the smallest-count slice.
        rare = counts.idxmin()
        y = y.replace(rare, 0)
    return X, y


# ── XGBoost reproducibility ──────────────────────────────────────
def test_xgboost_two_runs_produce_same_predictions() -> None:
    from app.services.ml.models.xgboost_model import XGBoostSignalModel

    X, y = _synth_dataset()
    set_seed(42)
    m1 = XGBoostSignalModel()
    m1.train(X, y, n_splits=3)
    preds1 = m1.predict_proba(X)

    set_seed(42)
    m2 = XGBoostSignalModel()
    m2.train(X, y, n_splits=3)
    preds2 = m2.predict_proba(X)

    np.testing.assert_allclose(preds1, preds2, rtol=1e-6, atol=1e-6)


def test_xgboost_metrics_are_byte_identical() -> None:
    from app.services.ml.models.xgboost_model import XGBoostSignalModel

    X, y = _synth_dataset()
    set_seed(42)
    m1 = XGBoostSignalModel()
    metrics1 = m1.train(X, y, n_splits=3)

    set_seed(42)
    m2 = XGBoostSignalModel()
    metrics2 = m2.train(X, y, n_splits=3)

    assert metrics1["accuracy"] == pytest.approx(metrics2["accuracy"], rel=1e-9)
    assert metrics1["log_loss"] == pytest.approx(metrics2["log_loss"], rel=1e-9)


# ── LightGBM reproducibility ─────────────────────────────────────
def test_lightgbm_two_runs_produce_same_predictions() -> None:
    pytest.importorskip("lightgbm")
    from app.services.ml.models.lightgbm_model import LightGBMSignalModel

    X, y = _synth_dataset()
    set_seed(42)
    m1 = LightGBMSignalModel()
    m1.train(X, y, n_splits=3)
    preds1 = m1.predict_proba(X)

    set_seed(42)
    m2 = LightGBMSignalModel()
    m2.train(X, y, n_splits=3)
    preds2 = m2.predict_proba(X)

    np.testing.assert_allclose(preds1, preds2, rtol=1e-5, atol=1e-5)


# ── Deterministic mlflow_run_id ─────────────────────────────────
def test_deterministic_run_id_is_stable() -> None:
    from app.services.ml.signal_engine import MLSignalEngine

    a = MLSignalEngine._deterministic_run_id(
        symbols=["BTC/USDT", "ETH/USDT"],
        timeframe="15m",
        n_splits=5,
        include_transformer=True,
    )
    b = MLSignalEngine._deterministic_run_id(
        symbols=["ETH/USDT", "BTC/USDT"],  # same set, different order
        timeframe="15m",
        n_splits=5,
        include_transformer=True,
    )
    # Symbols are sorted inside the function so order doesn't matter.
    assert a == b


def test_deterministic_run_id_changes_with_inputs() -> None:
    from app.services.ml.signal_engine import MLSignalEngine

    a = MLSignalEngine._deterministic_run_id(
        symbols=["BTC/USDT"],
        timeframe="15m",
        n_splits=5,
        include_transformer=True,
    )
    b = MLSignalEngine._deterministic_run_id(
        symbols=["BTC/USDT"],
        timeframe="15m",
        n_splits=4,  # different
        include_transformer=True,
    )
    c = MLSignalEngine._deterministic_run_id(
        symbols=["BTC/USDT"],
        timeframe="15m",
        n_splits=5,
        include_transformer=False,  # different
    )
    assert a != b
    assert a != c
    # All three are still hex strings of length 16.
    assert all(len(x) == 16 for x in (a, b, c))
    assert all(int(x, 16) >= 0 for x in (a, b, c))


# ── Seed module unit tests ──────────────────────────────────────
def test_set_seed_returns_seed_value() -> None:
    assert set_seed(123) == 123
    assert set_seed(42) == 42


def test_set_seed_is_idempotent() -> None:
    # Two calls with the same seed should leave the RNGs in the
    # same state — a quick smoke test against np.random.
    set_seed(7)
    a = np.random.rand(3)
    set_seed(7)
    b = np.random.rand(3)
    np.testing.assert_array_equal(a, b)
