"""
XGBoost classifier for crypto signal generation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit


class XGBoostSignalModel:
    """XGBoost-based directional classifier."""

    DEFAULT_PARAMS = {
        "objective": "multi:softprob",
        "num_class": 3,
        "max_depth": 6,
        "learning_rate": 0.05,
        "n_estimators": 400,
        "subsample": 0.8,
        "colsample_bytree": 0.7,
        "min_child_weight": 5,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "gamma": 0.1,
        "tree_method": "hist",
        "device": "cpu",
        "random_state": 42,
        "n_jobs": -1,
        "verbosity": 0,
    }

    def __init__(self, params: Optional[dict] = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_names: list[str] = []
        self.metrics: dict = {}

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = 5,
        early_stopping_rounds: int = 30,
    ) -> dict:
        self.feature_names = list(X.columns)
        y_mapped = y.map({-1: 0, 0: 1, 1: 2})

        tscv = TimeSeriesSplit(n_splits=n_splits)
        oof_preds = np.zeros((len(X), 3))

        for fold, (tr_idx, val_idx) in enumerate(tscv.split(X)):
            X_tr, X_val = X.iloc[tr_idx], X.iloc[val_idx]
            y_tr, y_val = y_mapped.iloc[tr_idx], y_mapped.iloc[val_idx]

            model = xgb.XGBClassifier(**self.params)
            model.fit(
                X_tr,
                y_tr,
                eval_set=[(X_val, y_val)],
                verbose=False,
            )
            oof_preds[val_idx] = model.predict_proba(X_val)
            print(f"  fold {fold + 1}/{n_splits} done")

        self.model = xgb.XGBClassifier(**self.params)
        self.model.fit(X, y_mapped, verbose=False)

        preds_class = oof_preds.argmax(axis=1)
        self.metrics = self._compute_metrics(y_mapped.values, preds_class, oof_preds)
        return self.metrics

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model not trained yet")
        X = X[self.feature_names] if all(c in X.columns for c in self.feature_names) else X
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
        self.model.save_model(path)
        meta = {
            "params": self.params,
            "feature_names": self.feature_names,
            "metrics": self.metrics,
            "feature_version": "v1.0",
        }
        meta_path = path.replace(".json", ".meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2, default=str)

    def load(self, path: str) -> None:
        self.model = xgb.XGBClassifier(**self.params)
        self.model.load_model(path)
        meta_path = path.replace(".json", ".meta.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            self.feature_names = meta.get("feature_names", [])
            self.metrics = meta.get("metrics", {})

    @staticmethod
    def _compute_metrics(
        y_true: np.ndarray, y_pred: np.ndarray, proba: np.ndarray
    ) -> dict:
        from sklearn.metrics import (
            accuracy_score,
            classification_report,
            log_loss,
        )

        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "log_loss": float(log_loss(y_true, proba, labels=[0, 1, 2])),
            "n_samples": int(len(y_true)),
            "class_distribution": {
                int(c): int((y_true == c).sum()) for c in (0, 1, 2)
            },
        }
