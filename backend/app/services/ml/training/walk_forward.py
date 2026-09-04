"""
Walk-forward validation — the gold standard for time-series ML evaluation.
Prevents look-ahead bias, gives realistic performance estimates.
"""

from __future__ import annotations

from typing import Callable, Dict, List

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit


class WalkForwardValidator:
    """
    Walk-forward validation:
    Train on [t0, t1], test on [t1, t2], then slide forward.
    Aggregates out-of-sample metrics.
    """

    def __init__(self, n_splits: int = 5, train_size: int = 1000, test_size: int = 250):
        self.n_splits = n_splits
        self.train_size = train_size
        self.test_size = test_size

    def split(self, X: pd.DataFrame, y: pd.Series):
        """Yield (X_train, y_train, X_test, y_test) tuples."""
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

    def evaluate(
        self,
        train_fn: Callable,
        X: pd.DataFrame,
        y: pd.Series,
        metric_fns: Dict[str, Callable] = None,
    ) -> Dict:
        """
        train_fn(X_train, y_train) -> fitted model with .predict(X)
        Returns aggregated metrics across all folds.
        """
        from sklearn.metrics import accuracy_score, f1_score, log_loss

        if metric_fns is None:
            metric_fns = {
                "accuracy": lambda yt, yp, ypr: accuracy_score(yt, yp),
                "f1_macro": lambda yt, yp, ypr: f1_score(yt, yp, average="macro", zero_division=0),
                "log_loss": lambda yt, yp, ypr: log_loss(yt, ypr, labels=[-1, 0, 1]),
            }

        results = {k: [] for k in metric_fns}
        oof_preds = np.full(len(X), np.nan)
        oof_proba = np.full((len(X), 3), np.nan)

        for fold, (X_tr, y_tr, X_te, y_te) in enumerate(self.split(X, y)):
            try:
                model = train_fn(X_tr, y_tr)
                preds = model.predict(X_te)
                proba = model.predict_proba(X_te)
                idx = X_te.index
                for i, ix in enumerate(idx):
                    pos = X.index.get_loc(ix)
                    if isinstance(pos, slice):
                        pos = pos.start
                    oof_preds[pos] = preds[i]
                    oof_proba[pos] = proba[i]

                for name, fn in metric_fns.items():
                    results[name].append(fn(y_te.values, preds, proba))
            except Exception as e:
                print(f"Fold {fold} failed: {e}")

        summary = {
            "n_folds": len(next(iter(results.values()), [])),
            "metrics": {k: {"mean": float(np.mean(v)), "std": float(np.std(v)), "values": v} for k, v in results.items()},
        }
        return summary
