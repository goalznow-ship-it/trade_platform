"""
ML Signal Engine — central entry point.
Combines feature engineering, ensemble prediction, and trading intelligence.
Integrates with existing 100-point scoring system as a confidence booster.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from app.core.logging import logger

from .features.engineer import FeatureEngineer
from .inference.predictor import RealTimePredictor
from .models.xgboost_model import XGBoostSignalModel


class MLSignalEngine:
    """
    Top-level orchestrator for ML-powered signal generation.
    Wraps training, inference, and integration with the broader platform.
    """

    def __init__(
        self,
        model_dir: str = "app/models_store",
        default_horizon_bars: int = 12,
        default_label_threshold: float = 0.005,
        retrain_interval_hours: int = 24,
    ):
        self.model_dir = model_dir
        self.predictor = RealTimePredictor(model_dir)
        self.fe = FeatureEngineer()
        self.default_horizon_bars = default_horizon_bars
        self.default_label_threshold = default_label_threshold
        self.retrain_interval_hours = retrain_interval_hours
        self.last_train_at: datetime | None = None

    # ── TRAINING ─────────────────────────────────────────────────────
    async def train(
        self,
        symbols: list[str],
        exchange_client=None,
        benchmark_symbol: str = "BTC/USDT",
        timeframe: str = "15m",
        include_transformer: bool = True,
        n_splits: int = 5,
        save: bool = True,
    ) -> dict:
        """
        Train the full ensemble on multi-symbol historical data.
        Returns aggregated metrics.

        Phase 3: wraps the run in a deterministic seed + MLflow run
        + ``models_store/registry.json`` update. ``mlflow_run_id`` is
        derived from the seed so two runs with the same inputs
        produce the same id (see ``test_ml_reproducibility.py``).
        """
        from app.services.ml.seed import DEFAULT_SEED, set_seed
        set_seed(DEFAULT_SEED)

        mlflow_run_id = self._deterministic_run_id(
            symbols=symbols, timeframe=timeframe, n_splits=n_splits,
            include_transformer=include_transformer,
        )

        logger.info(
            f"Starting ML training on {len(symbols)} symbols, tf={timeframe}, "
            f"mlflow_run_id={mlflow_run_id}"
        )

        mlflow_metrics: dict = {}
        try:
            import mlflow
            mlflow.set_tracking_uri("file:./mlruns")
            with mlflow.start_run(run_name=mlflow_run_id):
                mlflow.log_params({
                    "n_symbols": len(symbols),
                    "timeframe": timeframe,
                    "n_splits": n_splits,
                    "include_transformer": include_transformer,
                    "seed": DEFAULT_SEED,
                })
                results = await self._train_core(
                    symbols=symbols,
                    exchange_client=exchange_client,
                    benchmark_symbol=benchmark_symbol,
                    timeframe=timeframe,
                    include_transformer=include_transformer,
                    n_splits=n_splits,
                    save=save,
                )
                # Flatten the per-model metrics into one log call so
                # MLflow's UI shows them grouped under the run.
                for model_name, model_metrics in results.items():
                    if isinstance(model_metrics, dict):
                        for k, v in model_metrics.items():
                            if isinstance(v, (int, float)):
                                mlflow.log_metric(f"{model_name}.{k}", v)
                                mlflow_metrics[f"{model_name}.{k}"] = v
        except Exception as exc:
            # MLflow is best-effort — the training run still
            # produces a usable model + metrics even if the MLflow
            # server is down.
            logger.warning(f"mlflow_logging_skipped: {exc}")
            results = await self._train_core(
                symbols=symbols,
                exchange_client=exchange_client,
                benchmark_symbol=benchmark_symbol,
                timeframe=timeframe,
                include_transformer=include_transformer,
                n_splits=n_splits,
                save=save,
            )

        # Phase 3: persist a registry.json so a process restart
        # knows which model versions are live without re-scanning
        # the model_dir contents.
        if save:
            self._update_registry(
                run_id=mlflow_run_id,
                metrics={**mlflow_metrics, "last_train_at": datetime.now(UTC).isoformat()},
            )

        # Expose the run id for callers that want to log it to
        # ``signals`` or ``adjustment_runs`` downstream.
        self.last_run_id = mlflow_run_id
        results["mlflow_run_id"] = mlflow_run_id
        return results

    async def _train_core(
        self,
        *,
        symbols: list[str],
        exchange_client,
        benchmark_symbol: str,
        timeframe: str,
        include_transformer: bool,
        n_splits: int,
        save: bool,
    ) -> dict:
        # The actual training body — split out from ``train`` so
        # the MLflow wrapper doesn't have to know about the model
        # internals. Mirrors the previous monolithic ``train``
        # implementation.
        from app.services.ml.models.lightgbm_model import LightGBMSignalModel
        from app.services.ml.models.transformer import TransformerSignalWrapper
        from app.services.ml.models.xgboost_model import XGBoostSignalModel
        from app.services.ml.training.data_pipeline import TrainingDataPipeline
        from app.services.ml.training.walk_forward import WalkForwardValidator

        pipeline = TrainingDataPipeline(
            exchange_client=exchange_client,
            timeframe=timeframe,
            horizon_bars=self.default_horizon_bars,
            label_threshold=self.default_label_threshold,
        )

        X, y = await pipeline.build_multi_symbol_dataset(symbols, benchmark_symbol)
        if X.empty or len(X) < 500:
            return {"error": f"insufficient training data: {len(X)} samples"}

        logger.info(f"Built dataset: {X.shape}, class dist: {y.value_counts().to_dict()}")

        results = {}

        # 1. XGBoost
        logger.info("Training XGBoost...")
        xgb_model = XGBoostSignalModel()
        xgb_metrics = xgb_model.train(X, y, n_splits=n_splits)
        results["xgboost"] = xgb_metrics
        self.predictor.ensemble.add_xgboost(xgb_model)

        # 2. LightGBM
        logger.info("Training LightGBM...")
        lgb_model = LightGBMSignalModel()
        lgb_metrics = lgb_model.train(X, y, n_splits=n_splits)
        results["lightgbm"] = lgb_metrics
        self.predictor.ensemble.add_lightgbm(lgb_model)

        # 3. Transformer (optional — needs more data)
        if include_transformer and len(X) > 5000:
            logger.info("Training Transformer...")
            tf_model = TransformerSignalWrapper(seq_len=60, epochs=20)
            tf_metrics = tf_model.train(X, y)
            results["transformer"] = tf_metrics
            self.predictor.ensemble.add_transformer(tf_model)
        else:
            logger.info("Skipping Transformer (insufficient data or disabled)")

        # 4. Walk-forward validation on the ensemble
        logger.info("Running walk-forward validation...")
        validator = WalkForwardValidator(n_splits=4, train_size=2000, test_size=500)
        wf_summary = validator.evaluate(self._ensemble_train_fn(X, y), X, y)
        results["walk_forward"] = wf_summary

        if save:
            self.predictor.ensemble.save(self.model_dir)
            logger.info(f"Models saved to {self.model_dir}")

        self.last_train_at = datetime.now(UTC)
        self.predictor._loaded = True
        return results

    @staticmethod
    def _deterministic_run_id(
        *,
        symbols: list[str],
        timeframe: str,
        n_splits: int,
        include_transformer: bool,
    ) -> str:
        """A stable hash of the training inputs.

        The test suite asserts that two ``train()`` calls with the
        same inputs produce the same ``mlflow_run_id``. We don't
        use a random uuid here because that would defeat
        reproducibility — the run id is the seed the rest of the
        training reads.
        """
        import hashlib
        canonical = "|".join(sorted(symbols)) + f"|{timeframe}|{n_splits}|{int(include_transformer)}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def _update_registry(self, *, run_id: str, metrics: dict) -> None:
        """Write / append to ``models_store/registry.json``.

        The registry is a JSON list of {run_id, metrics, timestamp}
        entries, ordered most-recent-first. Process restarts read
        this file to know which model version is live.
        """
        import json
        from pathlib import Path
        registry = Path(self.model_dir) / "registry.json"
        registry.parent.mkdir(parents=True, exist_ok=True)
        if registry.exists():
            try:
                entries = json.loads(registry.read_text())
            except Exception:
                entries = []
        else:
            entries = []
        entries.insert(0, {"run_id": run_id, "metrics": metrics})
        # Cap at 20 entries to keep the file from growing forever.
        entries = entries[:20]
        registry.write_text(json.dumps(entries, indent=2, default=str))

    def _ensemble_train_fn(self, X: pd.DataFrame, y: pd.Series):
        """Factory for walk-forward training (re-trains a fresh XGB each fold)."""
        def _train(X_tr, y_tr):
            m = XGBoostSignalModel()
            m.train(X_tr, y_tr, n_splits=3)
            return m
        return _train

    # ── INFERENCE ───────────────────────────────────────────────────
    def predict(
        self,
        symbol: str,
        df: pd.DataFrame,
        benchmark_df: pd.DataFrame | None = None,
        news_events: list | None = None,
        funding: pd.DataFrame | None = None,
        oi: pd.DataFrame | None = None,
    ) -> dict:
        """Run inference for a single symbol."""
        return self.predictor.predict(df, benchmark_df, news_events, funding, oi)

    async def predict_batch(
        self,
        symbols: list[str],
        ohlcv_provider,
        benchmark_symbol: str = "BTC/USDT",
    ) -> list[dict]:
        """Run inference for many symbols in one call."""
        self.predictor.reload_if_stale()

        btc_df = await ohlcv_provider(benchmark_symbol)
        out = []
        for sym in symbols:
            try:
                df = await ohlcv_provider(sym)
                if df is None or df.empty or len(df) < 200:
                    continue
                pred = self.predictor.predict(df, btc_df)
                pred["symbol"] = sym
                out.append(pred)
            except Exception as e:
                logger.error(f"Predict failed for {sym}: {e}")
        return out

    # ── INTEGRATION WITH EXISTING 100-POINT SCORING ──────────────────
    def augment_institutional_score(
        self,
        base_score: float,
        ml_prediction: dict,
    ) -> dict:
        """
        Boost or reduce the existing 100-point institutional score
        based on ML confidence and agreement.

        Rule of thumb:
        - High ML confidence + high agreement = strong boost
        - ML confidence low = neutral
        - ML predicts opposite of institutional = penalty
        """
        if "error" in ml_prediction:
            return {"final_score": base_score, "ml_adjustment": 0, "note": "ml_unavailable"}

        direction = ml_prediction.get("direction", 0)
        confidence = ml_prediction.get("confidence", 0)
        agreement = ml_prediction.get("agreement", 0)

        # Directional alignment: 1=buy, -1=sell
        if direction == 0:
            return {"final_score": base_score, "ml_adjustment": 0, "note": "ml_neutral"}

        # ML boost: up to ±10 points
        ml_strength = confidence * agreement
        max_adjustment = 10.0
        adjustment = direction * ml_strength * max_adjustment

        new_score = max(0, min(100, base_score + adjustment))
        return {
            "final_score": float(new_score),
            "ml_adjustment": float(adjustment),
            "ml_direction": direction,
            "ml_confidence": float(confidence),
            "ml_agreement": float(agreement),
        }

    # ── SCHEDULED RETRAINING ────────────────────────────────────────
    def needs_retrain(self) -> bool:
        if self.last_train_at is None:
            return True
        elapsed = (datetime.now(UTC) - self.last_train_at).total_seconds() / 3600
        return elapsed > self.retrain_interval_hours


# Global singleton — initialised on first use
_ml_engine: MLSignalEngine | None = None


def get_ml_engine() -> MLSignalEngine:
    global _ml_engine
    if _ml_engine is None:
        _ml_engine = MLSignalEngine()
        _ml_engine.predictor.load()
    return _ml_engine


# Convenience alias for imports
ml_signal_engine: MLSignalEngine | None = None


def init_ml_engine() -> MLSignalEngine:
    """Initialise the global ML engine. Called at app startup."""
    global ml_signal_engine
    ml_signal_engine = MLSignalEngine()
    ml_signal_engine.predictor.load()
    return ml_signal_engine
