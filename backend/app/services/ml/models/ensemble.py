"""
Ensemble predictor — combines XGBoost + LightGBM + Transformer.
Uses weighted soft-voting with weights tuned on validation performance.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .xgboost_model import XGBoostSignalModel
from .lightgbm_model import LightGBMSignalModel
from .transformer import TransformerSignalWrapper


class EnsemblePredictor:
    """
    Weighted soft-voting ensemble.
    Each model outputs probabilities for [-1, 0, 1]; we combine with weights.
    """

    DEFAULT_WEIGHTS = {
        "xgboost": 0.40,
        "lightgbm": 0.40,
        "transformer": 0.20,
    }

    def __init__(self, weights: Optional[dict] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.xgb: Optional[XGBoostSignalModel] = None
        self.lgb: Optional[LightGBMSignalModel] = None
        self.transformer: Optional[TransformerSignalWrapper] = None
        self.is_trained: bool = False

    def add_xgboost(self, model: XGBoostSignalModel):
        self.xgb = model
        self.is_trained = True

    def add_lightgbm(self, model: LightGBMSignalModel):
        self.lgb = model
        self.is_trained = True

    def add_transformer(self, model: TransformerSignalWrapper):
        self.transformer = model
        self.is_trained = True

    def predict_proba(self, X: pd.DataFrame) -> dict:
        """
        Returns per-model and ensemble probabilities.
        Format: {"xgboost": [...], "lightgbm": [...], "transformer": [...], "ensemble": [...]}
        """
        if not self.is_trained:
            raise RuntimeError("Ensemble has no trained models")

        out = {}
        total_w = 0.0
        ensemble = np.zeros((len(X), 3))

        if self.xgb is not None:
            out["xgboost"] = self.xgb.predict_proba(X)
            ensemble += self.weights["xgboost"] * out["xgboost"]
            total_w += self.weights["xgboost"]

        if self.lgb is not None:
            out["lightgbm"] = self.lgb.predict_proba(X)
            ensemble += self.weights["lightgbm"] * out["lightgbm"]
            total_w += self.weights["lightgbm"]

        if self.transformer is not None:
            out["transformer"] = self.transformer.predict_proba(X)
            ensemble += self.weights["transformer"] * out["transformer"]
            total_w += self.weights["transformer"]

        if total_w > 0:
            ensemble /= total_w

        out["ensemble"] = ensemble
        return out

    def predict(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns (predictions, ensemble_proba, confidence).
        predictions: -1, 0, 1
        confidence: max probability (0-1)
        """
        proba = self.predict_proba(X)["ensemble"]
        preds = np.array([-1, 0, 1])[proba.argmax(axis=1)]
        confidence = proba.max(axis=1)
        return preds, proba, confidence

    def agreement_score(self, X: pd.DataFrame) -> np.ndarray:
        """
        How much do the models agree?
        1.0 = all models predict same class
        0.0 = each model predicts different class
        """
        all_preds = []
        if self.xgb is not None:
            all_preds.append(self.xgb.predict(X))
        if self.lgb is not None:
            all_preds.append(self.lgb.predict(X))
        if self.transformer is not None:
            all_preds.append(np.array([-1, 0, 1])[self.transformer.predict_proba(X).argmax(axis=1)])

        if not all_preds:
            return np.zeros(len(X))

        all_preds = np.array(all_preds)
        n_models = len(all_preds)
        majority = np.zeros(len(X))
        for i in range(len(X)):
            counts = np.bincount(all_preds[:, i] + 1, minlength=3)
            majority[i] = counts.max() / n_models
        return majority

    def save(self, directory: str) -> None:
        Path(directory).mkdir(parents=True, exist_ok=True)
        if self.xgb:
            self.xgb.save(os.path.join(directory, "xgboost.json"))
        if self.lgb:
            self.lgb.save(os.path.join(directory, "lightgbm.txt"))
        if self.transformer:
            self.transformer.save(os.path.join(directory, "transformer.pt"))
        meta = {
            "weights": self.weights,
            "trained_models": {
                "xgboost": self.xgb is not None,
                "lightgbm": self.lgb is not None,
                "transformer": self.transformer is not None,
            },
        }
        with open(os.path.join(directory, "ensemble.json"), "w") as f:
            json.dump(meta, f, indent=2)

    def load(self, directory: str) -> None:
        meta_path = os.path.join(directory, "ensemble.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            self.weights = meta.get("weights", self.DEFAULT_WEIGHTS)

        if os.path.exists(os.path.join(directory, "xgboost.json")):
            self.xgb = XGBoostSignalModel()
            self.xgb.load(os.path.join(directory, "xgboost.json"))

        if os.path.exists(os.path.join(directory, "lightgbm.txt")):
            self.lgb = LightGBMSignalModel()
            self.lgb.load(os.path.join(directory, "lightgbm.txt"))

        if os.path.exists(os.path.join(directory, "transformer.pt")):
            self.transformer = TransformerSignalWrapper()
            self.transformer.load(os.path.join(directory, "transformer.pt"))

        self.is_trained = any(
            m is not None for m in (self.xgb, self.lgb, self.transformer)
        )
