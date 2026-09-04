"""
Real-time predictor — serves predictions from latest features.
Caches the model in memory for low-latency inference.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Optional

import numpy as np
import pandas as pd

from app.core.logging import logger
from ..features.engineer import FeatureEngineer
from ..models.ensemble import EnsemblePredictor


class RealTimePredictor:
    """
    Production inference path:
    live_data → features → ensemble → prediction + confidence
    """

    def __init__(self, model_dir: str = "app/models_store"):
        self.model_dir = model_dir
        self.ensemble = EnsemblePredictor()
        self.fe = FeatureEngineer()
        self._loaded = False
        self._last_load: Optional[datetime] = None

    def load(self) -> bool:
        """Load persisted ensemble from disk. Returns True on success."""
        if not os.path.isdir(self.model_dir):
            return False
        try:
            self.ensemble.load(self.model_dir)
            self._loaded = True
            self._last_load = datetime.utcnow()
            logger.info(f"ML ensemble loaded from {self.model_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to load ML ensemble: {e}")
            return False

    def reload_if_stale(self, max_age_minutes: int = 60) -> None:
        if self._last_load is None:
            self.load()
            return
        age = (datetime.utcnow() - self._last_load).total_seconds() / 60
        if age > max_age_minutes:
            self.load()

    def is_ready(self) -> bool:
        if not self._loaded:
            self.load()
        return self._loaded and self.ensemble.is_trained

    def predict(
        self,
        df: pd.DataFrame,
        benchmark_df: Optional[pd.DataFrame] = None,
        news_events: Optional[list] = None,
        funding: Optional[pd.DataFrame] = None,
        oi: Optional[pd.DataFrame] = None,
    ) -> Dict:
        """
        Generate prediction for current market state.

        Returns:
            {
                "direction": -1 | 0 | 1,
                "direction_label": "sell" | "hold" | "buy",
                "confidence": 0-1,
                "agreement": 0-1,
                "proba": {"sell": x, "hold": y, "buy": z},
                "per_model": {...},
                "timestamp": ISO,
            }
        """
        if not self.is_ready():
            return {"error": "model not ready", "direction": 0, "confidence": 0}

        X = self.fe.build(df, benchmark_df, news_events, funding, oi)
        if X.empty:
            return {"error": "feature build failed", "direction": 0, "confidence": 0}

        # Use only the latest row for inference
        latest = X.tail(1)
        preds, proba, conf = self.ensemble.predict(latest)
        agreement = self.ensemble.agreement_score(latest)
        per_model = self.ensemble.predict_proba(latest)

        direction = int(preds[0])
        proba_dict = {
            "sell": float(proba[0, 0]),
            "hold": float(proba[0, 1]),
            "buy": float(proba[0, 2]),
        }
        direction_label = {-1: "sell", 0: "hold", 1: "buy"}[direction]

        per_model_clean = {}
        for k, v in per_model.items():
            per_model_clean[k] = {
                "sell": float(v[0, 0]),
                "hold": float(v[0, 1]),
                "buy": float(v[0, 2]),
            }

        return {
            "direction": direction,
            "direction_label": direction_label,
            "confidence": float(conf[0]),
            "agreement": float(agreement[0]),
            "proba": proba_dict,
            "per_model": per_model_clean,
            "feature_version": self.fe.FEATURE_VERSION,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def feature_importance(self, top_n: int = 20) -> Dict:
        """Get feature importance from each base model."""
        out = {}
        if self.ensemble.xgb:
            out["xgboost"] = self.ensemble.xgb.feature_importance(top_n).to_dict("records")
        if self.ensemble.lgb:
            out["lightgbm"] = self.ensemble.lgb.feature_importance(top_n).to_dict("records")
        return out
