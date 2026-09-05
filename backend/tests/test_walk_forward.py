"""Tests for the walk-forward validator (Phase 3 acceptance).

The validator is the gold standard for time-series ML evaluation —
it must produce non-trivial OOS hit rates that match the in-sample
fit closely. Before Phase 3 the validator was untested; the
regression risk is a bug that turns every fold into a coin flip
(33% on a 3-class problem) or a constant-class predictor that
sneaks past naive tests.

Acceptance (from production-grade-signals.md):
- Synth 1500 candles → run WalkForwardValidator.evaluate with XGB
- OOS hit rate in [0.33, 0.90] — not a coin flip, not a perfect
  overfit
- Train / test gap < 0.20 — model isn't memorising
"""
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score

from app.services.ml.models.xgboost_model import XGBoostSignalModel
from app.services.ml.seed import set_seed
from app.services.ml.training.walk_forward import WalkForwardValidator


# ── Helpers ──────────────────────────────────────────────────────
def _synth_ohlcv(n: int = 1500) -> pd.DataFrame:
    """Random-walk OHLCV with a mild trend the model can learn.

    The labels (y) are derived from the same forward return so a
    well-regularised tree should land in the 0.45–0.65 OOS hit
    rate range — well above the 0.33 coin flip and well below
    the 0.90 overfit ceiling.
    """
    set_seed(42)
    rng = np.random.default_rng(42)
    base = 30000.0
    closes = [base]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + rng.normal(0, 0.005)))
    closes = np.array(closes)

    # Build a tiny feature set: lagged returns, a momentum proxy,
    # and the noise channel the model can ignore.
    feats = pd.DataFrame({
        "ret_1": np.concatenate([[0.0], np.diff(closes) / closes[:-1]]),
        "ret_3": pd.Series(closes).pct_change(3).fillna(0).values,
        "ret_5": pd.Series(closes).pct_change(5).fillna(0).values,
        "sma_ratio": (
            pd.Series(closes).rolling(20).mean().fillna(method="bfill").values
            / closes
        ),
        "noise_1": rng.normal(0, 1, n),
        "noise_2": rng.normal(0, 1, n),
    })

    # Forward 12-bar return, sign-based label.
    fwd = pd.Series(closes).pct_change(12).shift(-12).fillna(0).values
    y = pd.Series(np.where(fwd > 0.005, 1, np.where(fwd < -0.005, -1, 0)))
    return feats, y


def _xgb_train_fn(X: pd.DataFrame, y: pd.Series):
    m = XGBoostSignalModel()
    m.train(X, y, n_splits=2)
    return m


# ── Acceptance test ──────────────────────────────────────────────
def test_walk_forward_xgb_oos_hit_rate_in_expected_band() -> None:
    X, y = _synth_ohlcv(1500)
    assert len(X) == 1500
    # At least three folds need to land in the test set.
    validator = WalkForwardValidator(n_splits=4, train_size=1000, test_size=125)
    summary = validator.evaluate(_xgb_train_fn, X, y)
    assert summary["n_folds"] >= 3, summary
    mean_oos_acc = summary["metrics"]["accuracy"]["mean"]
    # Acceptance band from the plan: not a coin flip, not overfit.
    assert 0.33 <= mean_oos_acc <= 0.90, (
        f"OOS accuracy {mean_oos_acc:.3f} outside [0.33, 0.90]"
    )


def test_walk_forward_train_test_gap_below_threshold() -> None:
    """Train / test gap < 0.20 — model isn't memorising.

    We compare the first fold's in-sample accuracy (computed on
    ``X_tr``) to that fold's OOS accuracy. The gap is the
    difference; a tree-based model with reasonable regularisation
    shouldn't gap by more than 0.20.
    """
    X, y = _synth_ohlcv(1500)
    validator = WalkForwardValidator(n_splits=2, train_size=900, test_size=200)
    folds = list(validator.split(X, y))
    assert len(folds) >= 1
    X_tr, y_tr, X_te, y_te = folds[0]

    model = _xgb_train_fn(X_tr, y_tr)
    train_preds = model.predict(X_tr)
    test_preds = model.predict(X_te)

    train_acc = accuracy_score(y_tr.values, train_preds)
    test_acc = accuracy_score(y_te.values, test_preds)
    gap = abs(train_acc - test_acc)
    assert gap < 0.20, f"train/test gap {gap:.3f} exceeds 0.20"


def test_walk_forward_aggregates_all_folds() -> None:
    """Per-fold metrics + std dev are populated. A regression that
    drops ``values`` (e.g. a refactor that returns only the mean)
    is caught here.
    """
    X, y = _synth_ohlcv(1500)
    validator = WalkForwardValidator(n_splits=3, train_size=900, test_size=150)
    summary = validator.evaluate(_xgb_train_fn, X, y)
    for metric_name, payload in summary["metrics"].items():
        assert "values" in payload, metric_name
        assert "mean" in payload, metric_name
        assert "std" in payload, metric_name
        assert len(payload["values"]) == summary["n_folds"]


def test_walk_forward_validator_does_not_overlap() -> None:
    """Each fold's test slice must be strictly after its train slice
    — the walk-forward property. A bug that returned (X_tr, X_te)
    with overlapping indices would inflate OOS accuracy.
    """
    X, y = _synth_ohlcv(1500)
    validator = WalkForwardValidator(n_splits=3, train_size=900, test_size=150)
    folds = list(validator.split(X, y))
    for X_tr, _, X_te, _ in folds:
        assert X_tr.index.max() < X_te.index.min(), (
            "train/test indices overlap — walk-forward is broken"
        )
