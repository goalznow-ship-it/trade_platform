"""
Trading-specific metrics.
Standard accuracy is misleading in trading — these are what actually matter.
"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


class TradingMetrics:
    """
    Compute trading-relevant performance metrics from predictions and price series.
    """

    @staticmethod
    def hit_rate(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Directional accuracy on non-zero signals."""
        mask = y_pred != 0
        if mask.sum() == 0:
            return 0.0
        return float((y_true[mask] == y_pred[mask]).mean())

    @staticmethod
    def precision_recall(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """Per-class precision/recall."""
        out = {}
        for cls in (-1, 0, 1):
            tp = ((y_pred == cls) & (y_true == cls)).sum()
            fp = ((y_pred == cls) & (y_true != cls)).sum()
            fn = ((y_pred != cls) & (y_true == cls)).sum()
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            out[f"class_{cls}"] = {
                "precision": float(precision),
                "recall": float(recall),
            }
        return out

    @staticmethod
    def simulate_returns(
        y_pred: np.ndarray, returns: np.ndarray, fee: float = 0.001
    ) -> Dict:
        """
        Simulate PnL from signals.
        y_pred: -1, 0, 1
        returns: actual forward returns per bar
        fee: round-trip fee
        """
        if len(y_pred) != len(returns):
            return {"error": "length mismatch"}

        # Strategy returns = signal * actual return
        strat = y_pred * returns

        # Subtract fees when signal changes
        signal_changes = np.diff(y_pred, prepend=0) != 0
        strat[signal_changes] -= fee

        cum_returns = (1 + strat).cumprod()
        total_return = float(cum_returns[-1] - 1) if len(cum_returns) else 0

        # Sharpe (annualized, assuming hourly bars)
        if strat.std() > 0:
            sharpe = float(strat.mean() / strat.std() * np.sqrt(365 * 24))
        else:
            sharpe = 0.0

        # Max drawdown
        peak = np.maximum.accumulate(cum_returns)
        drawdown = (cum_returns - peak) / peak
        max_dd = float(drawdown.min()) if len(drawdown) else 0

        # Win rate
        wins = (strat > 0).sum()
        total = (strat != 0).sum()
        win_rate = float(wins / total) if total > 0 else 0

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "n_trades": int(total),
            "profit_factor": float(strat[strat > 0].sum() / abs(strat[strat < 0].sum()))
            if (strat < 0).sum() > 0
            else 0.0,
        }
