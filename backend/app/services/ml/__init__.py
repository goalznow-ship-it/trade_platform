"""
ML Signal Engine — Phase 21
============================
Production-grade machine learning pipeline for crypto trading signals.
Combines XGBoost + LightGBM + Transformer models into an ensemble.
"""

from .signal_engine import MLSignalEngine, ml_signal_engine
from .features.engineer import FeatureEngineer
from .models.ensemble import EnsemblePredictor
from .training.data_pipeline import TrainingDataPipeline
from .inference.predictor import RealTimePredictor

__all__ = [
    "MLSignalEngine",
    "ml_signal_engine",
    "FeatureEngineer",
    "EnsemblePredictor",
    "TrainingDataPipeline",
    "RealTimePredictor",
]
