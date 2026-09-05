"""Tests for the OOS walk-forward backtester.

The backtester is model-agnostic by design — it slices the
labelled dataset into walk-forward folds, fits a fresh XGBoost
on each train slice, and reports hit-rate / drawdown metrics on
the held-out slice. These tests stub the data pipeline so we
don't need a live exchange.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

from app.services.ml.training.oos_backtest import (
    DEFAULT_SL_BPS,
    DEFAULT_TP_BPS,
    OOSBacktester,
)


def _build_synthetic_xy(n: int = 3000, n_features: int = 12) -> tuple[pd.DataFrame, pd.Series]:
    """Return a labelled dataset with a learnable signal.

    The target is a noisy threshold on ``f0`` mapped to the
    same {-1, 0, 1} class space the production data pipeline
    uses (short=−1, flat=0, long=+1). 3000 rows is enough for
    the default ``train_size=2000 + test_size=500 * 2 folds``.
    """
    rng = np.random.default_rng(11)
    X = pd.DataFrame(
        rng.normal(0, 1, (n, n_features)),
        columns=[f"f{i}" for i in range(n_features)],
    )
    raw = X["f0"] + rng.normal(0, 0.5, n)
    # Map to {-1, 0, +1} so the trainer sees the same shape
    # of label the production pipeline produces.
    y = pd.Series(np.where(raw > 0.3, 1, np.where(raw < -0.3, -1, 0)).astype(int))
    return X, y


@pytest.fixture
def stub_data_pipeline(monkeypatch):
    """Stub the data pipeline so the backtester doesn't hit
    the exchange. Returns the same XY for every symbol.
    """
    async def fake_build(self, symbols, benchmark):
        return _build_synthetic_xy()
    monkeypatch.setattr(
        "app.services.ml.training.data_pipeline.TrainingDataPipeline.build_multi_symbol_dataset",
        fake_build,
    )


@pytest.mark.asyncio
async def test_backtest_returns_required_metrics(stub_data_pipeline):
    """The metric surface is what the quality gate reads.
    Confirming the keys are present (even at degenerate
    values) is enough for a smoke test.
    """
    bt = OOSBacktester(n_splits=2, train_size=500, test_size=200)
    out = await bt.run(symbols=["BTC/USDT", "ETH/USDT"], timeframe="15m")
    required = {
        "oof_hit_rate",
        "in_sample_hit_rate",
        "train_test_gap",
        "per_fold",
        "cumulative_return_bps",
        "max_drawdown_bps",
        "n_folds",
    }
    assert required.issubset(out.keys()), f"missing keys: {required - out.keys()}"


@pytest.mark.asyncio
async def test_backtest_hit_rate_in_reasonable_range(stub_data_pipeline):
    """The OOS hit rate is bounded in [0, 1]. With random
    data a 50/50 mix should land somewhere in [0.2, 0.8] —
    if it's 1.0 the backtester is cheating, if it's 0.0 the
    trainer is broken.
    """
    bt = OOSBacktester(n_splits=2, train_size=500, test_size=200)
    out = await bt.run(symbols=["BTC/USDT"], timeframe="15m")
    hr = out["oof_hit_rate"]
    assert 0.2 <= hr <= 0.8, f"hit rate out of range: {hr}"


@pytest.mark.asyncio
async def test_backtest_gap_is_small(stub_data_pipeline):
    """``train_test_gap`` measures look-ahead fit. With a
    fresh XGB on a noisy threshold we expect the gap to be
    under 0.4 — a wider gap means the trainer is overfitting
    to the training window so badly that it can't generalise
    to the held-out slice. The threshold is generous because
    the synthetic data doesn't have the market's structure;
    production gap is enforced tighter via
    ``settings.ML_MIN_OOS_HIT_RATE``.
    """
    bt = OOSBacktester(n_splits=2, train_size=500, test_size=200)
    out = await bt.run(symbols=["BTC/USDT", "ETH/USDT"], timeframe="15m")
    gap = out["train_test_gap"]
    assert gap < 0.4, f"look-ahead gap too wide: {gap}"


@pytest.mark.asyncio
async def test_backtest_per_fold_listed(stub_data_pipeline):
    """``per_fold`` is the per-fold breakdown the operator
    can use to spot which slice is dragging the headline
    number down. Every fold should be a dict with fold
    index, n_test, hit_rate.
    """
    bt = OOSBacktester(n_splits=2, train_size=500, test_size=200)
    out = await bt.run(symbols=["BTC/USDT"], timeframe="15m")
    pf = out["per_fold"]
    assert isinstance(pf, list)
    assert len(pf) >= 1
    for fold in pf:
        assert {"fold", "n_test", "hit_rate"}.issubset(fold.keys())


@pytest.mark.asyncio
async def test_backtest_cumulative_return_bps(stub_data_pipeline):
    """``cumulative_return_bps`` is the headline PnL number.
    It must be a finite number — NaN / inf means the equity
    curve walked off the rails.
    """
    bt = OOSBacktester(n_splits=2, train_size=500, test_size=200)
    out = await bt.run(symbols=["BTC/USDT"], timeframe="15m")
    cum = out["cumulative_return_bps"]
    assert np.isfinite(cum), f"cumulative_return_bps not finite: {cum}"


@pytest.mark.asyncio
async def test_backtest_drawdown_bounded(stub_data_pipeline):
    """``max_drawdown_bps`` must be non-negative — a negative
    drawdown would mean the equity curve is in the wrong
    direction.
    """
    bt = OOSBacktester(n_splits=2, train_size=500, test_size=200)
    out = await bt.run(symbols=["BTC/USDT"], timeframe="15m")
    dd = out["max_drawdown_bps"]
    assert dd >= 0, f"drawdown negative: {dd}"


@pytest.mark.asyncio
async def test_backtest_insufficient_data_handled(monkeypatch):
    """If the data pipeline returns < train_size + test_size
    rows, the backtester returns an error dict rather than
    throwing. This is the call site the cron job reads.
    """
    async def tiny_build(self, symbols, benchmark):
        X, y = _build_synthetic_xy(n=200, n_features=8)
        return X, y
    monkeypatch.setattr(
        "app.services.ml.training.data_pipeline.TrainingDataPipeline.build_multi_symbol_dataset",
        tiny_build,
    )
    bt = OOSBacktester(n_splits=2, train_size=500, test_size=200)
    out = await bt.run(symbols=["BTC/USDT"], timeframe="15m")
    assert "error" in out, f"expected error key, got: {out}"


def test_default_tp_sl_bps_sane():
    """The defaults are 50 / 30 bps — about 2:1 reward:risk.
    Wider tp or tighter sl would inflate the equity curve
    and make the headline number meaningless.
    """
    assert DEFAULT_TP_BPS > 0
    assert DEFAULT_SL_BPS > 0
    assert DEFAULT_TP_BPS / DEFAULT_SL_BPS >= 1.5, (
        "TP/SL ratio should be at least 1.5 — lower means the "
        "backtest needs a >50% hit rate to be profitable, "
        "which is a stricter bar than the model can meet."
    )


def test_split_yields_walk_forward_slices():
    """The internal ``_split`` yields walk-forward slices:
    each fold's training set strictly contains the previous
    fold's training set (monotonically growing), and the test
    slice is the next ``test_size`` rows after the train end.
    Walk-forward means we never peek behind.
    """
    bt = OOSBacktester(n_splits=3, train_size=100, test_size=50)
    X, y = _build_synthetic_xy(n=400)
    slices = list(bt._split(X, y))
    assert len(slices) == 3
    prev_train_size = 0
    for fold_idx, (X_tr, _, X_te, _) in enumerate(slices):
        # Train slice grows by ``test_size`` per fold:
        #   fold 0: 100, fold 1: 150, fold 2: 200.
        expected_train_size = bt.train_size + fold_idx * bt.test_size
        assert len(X_tr) == expected_train_size, (
            f"fold {fold_idx}: expected {expected_train_size} train rows, "
            f"got {len(X_tr)}"
        )
        assert len(X_te) == bt.test_size
        # Monotonically growing — the defining property of walk-forward.
        assert len(X_tr) > prev_train_size
        prev_train_size = len(X_tr)
