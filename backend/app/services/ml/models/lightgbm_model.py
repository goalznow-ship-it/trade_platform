"""
LightGBM classifier — provides diversity to the XGBoost ensemble.
Often outperforms XGBoost on high-dimensional sparse data.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)


class LightGBMSignalModel:
    DEFAULT_PARAMS = {
        "objective": "multiclass",
        "num_class": 3,
        "metric": "multi_logloss",
        "boosting_type": "gbdt",
        "num_leaves": 64,
        "learning_rate": 0.05,
        "n_estimators": 500,
        "feature_fraction": 0.7,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "min_child_samples": 20,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
        "n_jobs": -1,
        "verbosity": -1,
    }

    def __init__(self, params: dict | None = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        self.model: lgb.LGBMClassifier | None = None
        self.feature_names: list[str] = []
        self.metrics: dict = {}

    def train(
        self, X: pd.DataFrame, y: pd.Series, n_splits: int = 5
    ) -> dict:
        # Phase 3: same reproducibility contract as XGBoost — see
        # ``app/services/ml/seed.py`` for the rationale.
        from app.services.ml.seed import set_seed
        set_seed(self.params.get("random_state", 42))

        self.feature_names = list(X.columns)
        y_mapped = y.map({-1: 0, 0: 1, 1: 2})

        tscv = TimeSeriesSplit(n_splits=n_splits)
        oof_preds = np.zeros((len(X), 3))

        for fold, (tr_idx, val_idx) in enumerate(tscv.split(X)):
            X_tr, X_val = X.iloc[tr_idx], X.iloc[val_idx]
            y_tr, y_val = y_mapped.iloc[tr_idx], y_mapped.iloc[val_idx]

            model = lgb.LGBMClassifier(**self.params)
            model.fit(
                X_tr,
                y_tr,
                eval_set=[(X_val, y_val)],
                callbacks=[lgb.early_stopping(30, verbose=False)],
            )
            oof_preds[val_idx] = model.predict_proba(X_val)
            logger.info("LightGBM fold %d/%d done", fold + 1, n_splits)

        self.model = lgb.LGBMClassifier(**self.params)
        self.model.fit(X, y_mapped)

        preds_class = oof_preds.argmax(axis=1)
        self.metrics = self._compute_metrics(y_mapped.values, preds_class, oof_preds)
        return self.metrics

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model not trained")
        return self.model.predict_proba(X)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        proba = self.predict_proba(X)
        classes = proba.argmax(axis=1)
        return np.array([-1, 0, 1])[classes]

    def feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        if self.model is None:
            return pd.DataFrame()
        imp = self.model.feature_importances_
        df = pd.DataFrame(
            {"feature": self.feature_names, "importance": imp}
        ).sort_values("importance", ascending=False)
        return df.head(top_n)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.model.booster_.save_model(path)
        meta = {
            "params": self.params,
            "feature_names": self.feature_names,
            "metrics": self.metrics,
        }
        with open(path.replace(".txt", ".meta.json"), "w") as f:
            json.dump(meta, f, indent=2, default=str)

    def load(self, path: str) -> None:
        self.model = lgb.LGBMClassifier(**self.params)
        self.model.booster_ = lgb.Booster(model_file=path)
        meta_path = path.replace(".txt", ".meta.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            self.feature_names = meta.get("feature_names", [])
            self.metrics = meta.get("metrics", {})

    @staticmethod
    def _compute_metrics(y_true, y_pred, proba) -> dict:
        from sklearn.metrics import accuracy_score, log_loss
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "log_loss": float(log_loss(y_true, proba, labels=[0, 1, 2])),
            "n_samples": int(len(y_true)),
        }
