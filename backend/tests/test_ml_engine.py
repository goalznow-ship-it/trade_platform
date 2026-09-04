"""
Unit tests for the ML signal engine.
Run with: pytest backend/tests/test_ml_engine.py -v
"""

import numpy as np
import pandas as pd
import pytest

from app.services.ml.features.technical import TechnicalFeatures
from app.services.ml.features.microstructure import MicrostructureFeatures
from app.services.ml.features.engineer import FeatureEngineer
from app.services.ml.models.ensemble import EnsemblePredictor
from app.services.ml.models.xgboost_model import XGBoostSignalModel
from app.services.ml.models.lightgbm_model import LightGBMSignalModel
from app.services.ml.training.metrics import TradingMetrics


def make_synthetic_ohlcv(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Build a synthetic OHLCV dataframe for testing."""
    np.random.seed(seed)
    rets = np.random.normal(0.0001, 0.01, n)
    prices = 100 * np.exp(np.cumsum(rets))
    idx = pd.date_range("2025-01-01", periods=n, freq="15min")
    df = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.001, n)),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.005, n))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.005, n))),
            "close": prices,
            "volume": np.random.lognormal(10, 1, n),
        },
        index=idx,
    )
    return df


def test_technical_features_build():
    df = make_synthetic_ohlcv(300)
    feats = TechnicalFeatures.build_all(df)
    assert not feats.empty
    assert "rsi_14" in feats.columns
    assert "macd_hist" in feats.columns
    assert "bb_pct_b" in feats.columns
    assert len(feats) < len(df)
    assert not feats.isna().all().any()


def test_microstructure_features_build():
    df = make_synthetic_ohlcv(300)
    feats = MicrostructureFeatures.build_all(df)
    assert not feats.empty
    assert "cvd" in feats.columns
    assert "vol_regime_ratio" in feats.columns


def test_feature_engineer_integration():
    df = make_synthetic_ohlcv(400)
    fe = FeatureEngineer()
    X = fe.build(df)
    assert not X.empty
    assert X.shape[1] > 50
    labels = fe.make_labels(df, horizon=12, threshold=0.005)
    assert len(labels) == len(df)
    assert set(labels.dropna().unique()).issubset({-1, 0, 1})


def test_xgboost_train_predict():
    df = make_synthetic_ohlcv(800)
    fe = FeatureEngineer()
    X = fe.build(df)
    y = fe.make_labels(df, horizon=12, threshold=0.005)
    y = y.reindex(X.index).dropna()
    X = X.loc[y.index]

    model = XGBoostSignalModel()
    metrics = model.train(X, y, n_splits=2)
    assert "accuracy" in metrics
    assert metrics["n_samples"] > 0

    preds = model.predict(X.tail(5))
    assert len(preds) == 5
    assert set(preds).issubset({-1, 0, 1})

    proba = model.predict_proba(X.tail(5))
    assert proba.shape == (5, 3)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)


def test_lightgbm_train_predict():
    df = make_synthetic_ohlcv(800)
    fe = FeatureEngineer()
    X = fe.build(df)
    y = fe.make_labels(df, horizon=12, threshold=0.005)
    y = y.reindex(X.index).dropna()
    X = X.loc[y.index]

    model = LightGBMSignalModel()
    metrics = model.train(X, y, n_splits=2)
    assert "accuracy" in metrics

    preds = model.predict(X.tail(5))
    assert set(preds).issubset({-1, 0, 1})


def test_ensemble_predict():
    df = make_synthetic_ohlcv(800)
    fe = FeatureEngineer()
    X = fe.build(df)
    y = fe.make_labels(df, horizon=12, threshold=0.005)
    y = y.reindex(X.index).dropna()
    X = X.loc[y.index]

    xgb = XGBoostSignalModel()
    xgb.train(X, y, n_splits=2)
    lgb = LightGBMSignalModel()
    lgb.train(X, y, n_splits=2)

    ens = EnsemblePredictor()
    ens.add_xgboost(xgb)
    ens.add_lightgbm(lgb)

    preds, proba, conf = ens.predict(X.tail(5))
    assert len(preds) == 5
    assert proba.shape == (5, 3)
    assert (conf >= 0).all() and (conf <= 1).all()

    agreement = ens.agreement_score(X.tail(5))
    assert (agreement >= 0).all() and (agreement <= 1).all()


def test_trading_metrics():
    np.random.seed(0)
    y_true = np.random.choice([-1, 0, 1], 100)
    y_pred = np.random.choice([-1, 0, 1], 100)
    rets = np.random.normal(0, 0.01, 100)
    m = TradingMetrics.simulate_returns(y_pred, rets)
    assert "sharpe_ratio" in m
    assert "win_rate" in m
    assert "max_drawdown" in m
    assert m["max_drawdown"] <= 0


def test_augment_institutional_score():
    from app.services.ml.signal_engine import MLSignalEngine

    eng = MLSignalEngine()
    base = 80.0

    out = eng.augment_institutional_score(base, {"error": "test"})
    assert out["final_score"] == 80
    assert out["ml_adjustment"] == 0

    out = eng.augment_institutional_score(
        base,
        {
            "direction": 1,
            "confidence": 0.9,
            "agreement": 1.0,
        },
    )
    assert out["final_score"] > base
    assert out["final_score"] <= 100
    assert out["ml_adjustment"] > 0

    out = eng.augment_institutional_score(
        base,
        {
            "direction": -1,
            "confidence": 0.9,
            "agreement": 1.0,
        },
    )
    assert out["final_score"] < base
