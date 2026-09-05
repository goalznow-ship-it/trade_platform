"""Out-of-sample (OOS) backtester for the ML signal engine.

What this does
--------------
A backtest that re-uses the same train/test data is a
look-ahead-biased in-sample fit. The walk-forward validator
already trains on slices and evaluates on the next slice, but
the *signal-level* outcome (would a generated signal have
profited?) is what an operator cares about.

``OOSBacktester`` runs the full pipeline:

1. Pull historical OHLCV for the symbol list.
2. Build the labelled dataset the same way the live model
   does (``TrainingDataPipeline.build_multi_symbol_dataset``).
3. For each walk-forward fold, fit a fresh model, generate
   predictions on the OOS slice, and translate them into
   pseudo-trades (long/short/flat). Track hit rate,
   cumulative return, and the worst drawdown.
4. Aggregate per-fold into a single ``summary`` dict the API
   can return.

The OOS hit rate is the headline number — the quality gate
in Phase 5 reads ``summary["oos_hit_rate"]`` to decide
whether a freshly-trained model is allowed to replace the
live one in ``model_dir/registry.json``.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from app.services.ml.seed import set_seed

logger = logging.getLogger(__name__)


# Per-trade return assumptions. The backtest is at the
# *signal* level, not the order level — we don't have
# realistic fills, slippage, or fees here. The numbers below
# are deliberately conservative defaults an operator can
# override per call.
DEFAULT_TP_BPS = 50     # +0.50% per winning trade
DEFAULT_SL_BPS = 30     # -0.30% per losing trade


class OOSBacktester:
    """Run a walk-forward backtest on the ML signal ensemble.

    The backtester is stateless. Call ``run(symbols, ...)``
    with a fitted ``predict_fn`` (model-agnostic) or use the
    convenience ``run_with_engine`` that knows how to drive
    the ``MLSignalEngine`` end-to-end.
    """

    def __init__(
        self,
        n_splits: int = 4,
        train_size: int = 2000,
        test_size: int = 500,
        tp_bps: float = DEFAULT_TP_BPS,
        sl_bps: float = DEFAULT_SL_BPS,
    ):
        self.n_splits = n_splits
        self.train_size = train_size
        self.test_size = test_size
        self.tp_bps = tp_bps
        self.sl_bps = sl_bps

    async def run(
        self,
        symbols: list[str],
        timeframe: str = "15m",
        benchmark_symbol: str = "BTC/USDT",
        exchange_client=None,
    ) -> dict[str, Any]:
        """Run the full OOS backtest on the configured symbols.

        Returns a dict with:

        - ``oos_hit_rate`` — float, the headline metric the
          quality gate reads. Range [0, 1].
        - ``in_sample_hit_rate`` — float, the per-fold mean
          train accuracy. Used to detect look-ahead fit.
        - ``train_test_gap`` — ``abs(in_sample - oos)``. Plan
          acceptance requires ``< 0.05``.
        - ``per_fold`` — list of {fold, hit_rate, n_trades}.
        - ``cumulative_return_bps`` — float.
        - ``max_drawdown_bps`` — float.
        """
        from app.services.ml.training.data_pipeline import TrainingDataPipeline

        set_seed()
        pipeline = TrainingDataPipeline(
            exchange_client=exchange_client,
            timeframe=timeframe,
            horizon_bars=12,
            label_threshold=0.005,
        )
        X, y = await pipeline.build_multi_symbol_dataset(symbols, benchmark_symbol)
        if X.empty or len(X) < (self.train_size + self.test_size):
            return {
                "error": "insufficient_data",
                "rows": int(len(X)),
                "required": self.train_size + self.test_size,
            }

        per_fold: list[dict] = []
        oos_hits = 0
        oos_total = 0
        in_sample_hits = 0
        in_sample_total = 0
        equity_curve: list[float] = []
        peak_equity = 0.0
        max_dd = 0.0
        cumulative = 0.0

        # Use the XGB model directly so we don't depend on the
        # whole ensemble being serialised on disk. The
        # walk-forward validator is the integration test
        # surface; the backtester is the OOS hit-rate surface.
        from app.services.ml.models.xgboost_model import XGBoostSignalModel

        for fold, (X_tr, y_tr, X_te, y_te) in enumerate(
            self._split(X, y)
        ):
            try:
                model = XGBoostSignalModel()
                model.train(X_tr, y_tr, n_splits=2)
            except Exception as exc:
                logger.warning("oos_backtest fold %d train failed: %s", fold, exc)
                continue

            preds = model.predict(X_te)
            train_preds = model.predict(X_tr)

            # Hit rate: did the model predict the correct sign?
            in_sample_hits += int((train_preds == y_tr.values).sum())
            in_sample_total += len(train_preds)
            oos_hits += int((preds == y_te.values).sum())
            oos_total += len(preds)

            # Trade-level PnL. Each OOS row is a "trade":
            #   - direction = sign of the predicted class
            #   - target = sign of the actual forward return
            # Wins pay +tp_bps, losses pay -sl_bps. The point
            # is to give the backtest a comparable equity
            # curve, not to model real fills.
            for p, t in zip(preds, y_te.values):
                if p == 0 or t == 0:
                    # Flat — no PnL contribution.
                    continue
                if p == t:
                    cumulative += self.tp_bps
                    equity_curve.append(cumulative)
                else:
                    cumulative -= self.sl_bps
                    equity_curve.append(cumulative)
                if cumulative > peak_equity:
                    peak_equity = cumulative
                dd = peak_equity - cumulative
                if dd > max_dd:
                    max_dd = dd

            per_fold.append({
                "fold": fold,
                "n_test": int(len(preds)),
                "hit_rate": float((preds == y_te.values).mean()),
            })

        oos_hit_rate = oos_hits / oos_total if oos_total else 0.0
        in_sample_hit_rate = (
            in_sample_hits / in_sample_total if in_sample_total else 0.0
        )

        return {
            "oof_hit_rate": oos_hit_rate,
            "in_sample_hit_rate": in_sample_hit_rate,
            "train_test_gap": abs(in_sample_hit_rate - oos_hit_rate),
            "per_fold": per_fold,
            "cumulative_return_bps": round(cumulative, 2),
            "max_drawdown_bps": round(max_dd, 2),
            "n_folds": len(per_fold),
            "n_test": oos_total,
            "config": {
                "n_splits": self.n_splits,
                "train_size": self.train_size,
                "test_size": self.test_size,
                "tp_bps": self.tp_bps,
                "sl_bps": self.sl_bps,
            },
        }

    def _split(self, X: pd.DataFrame, y: pd.Series):
        """Yield walk-forward (X_tr, y_tr, X_te, y_te) slices.

        Duplicated here (the validator has the same shape) so
        the backtester doesn't have to import
        ``WalkForwardValidator`` just to slice — keeps the
        backtest surface independent of the validator's
        metric-choice details.
        """
        n = len(X)
        for i in range(self.n_splits):
            train_end = self.train_size + i * self.test_size
            test_end = train_end + self.test_size
            if test_end > n:
                break
            yield (
                X.iloc[:train_end],
                y.iloc[:train_end],
                X.iloc[train_end:test_end],
                y.iloc[train_end:test_end],
            )


__all__ = ["OOSBacktester", "DEFAULT_TP_BPS", "DEFAULT_SL_BPS"]
