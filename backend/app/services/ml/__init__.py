"""
ML Signal Engine — Phase 21
============================
Production-grade machine learning pipeline for crypto trading signals.
Combines XGBoost + LightGBM + Transformer models into an ensemble.
"""

from .features.engineer import FeatureEngineer
from .inference.predictor import RealTimePredictor
from .models.ensemble import EnsemblePredictor
from .signal_engine import MLSignalEngine, ml_signal_engine
from .training.data_pipeline import TrainingDataPipeline

__all__ = [
    "MLSignalEngine",
    "ml_signal_engine",
    "FeatureEngineer",
    "EnsemblePredictor",
    "TrainingDataPipeline",
    "RealTimePredictor",
]
