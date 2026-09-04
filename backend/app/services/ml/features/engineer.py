"""
Unified feature engineering pipeline.
Combines technical + microstructure + cross-asset + sentiment into one matrix.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from .technical import TechnicalFeatures
from .microstructure import MicrostructureFeatures
from .cross_asset import CrossAssetFeatures
from .sentiment import SentimentFeatures


class FeatureEngineer:
    """
    Production-grade feature builder.
    Usage:
        fe = FeatureEngineer()
        X = fe.build(ohlcv_df, benchmark_df, news_events, funding, oi)
    """

    FEATURE_VERSION = "v1.0"

    def __init__(self, lookback: int = 250):
        self.lookback = lookback

    def build(
        self,
        df: pd.DataFrame,
        benchmark_df: Optional[pd.DataFrame] = None,
        news_events: Optional[list] = None,
        funding: Optional[pd.DataFrame] = None,
        oi: Optional[pd.DataFrame] = None,
        market_basket: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> pd.DataFrame:
        if df.empty or len(df) < 200:
            return pd.DataFrame()

        df = df.sort_index().tail(self.lookback).copy()

        parts: list[pd.DataFrame] = []
        parts.append(TechnicalFeatures.build_all(df))
        parts.append(MicrostructureFeatures.build_all(df))
        parts.append(CrossAssetFeatures.regime_features(df, benchmark_df))

        idx = df.index
        parts.append(SentimentFeatures.combine_all(idx, news_events, funding, oi))

        if market_basket:
            breadth = CrossAssetFeatures.market_breadth(market_basket)
            if not breadth.empty:
                breadth = breadth.reindex(idx, method="ffill")
                parts.append(breadth)

        feats = pd.concat(parts, axis=1)
        feats = feats.replace([np.inf, -np.inf], np.nan)

        # Forward-fill then drop remaining NaNs
        feats = feats.ffill().dropna()
        return feats

    @staticmethod
    def make_labels(
        df: pd.DataFrame, horizon: int = 12, threshold: float = 0.005
    ) -> pd.Series:
        """
        Triple-barrier label generation:
        - 1 = buy (forward return > +threshold)
        - -1 = sell (forward return < -threshold)
        - 0 = neutral
        """
        if df.empty or len(df) <= horizon:
            return pd.Series(dtype=int)

        future_ret = df["close"].pct_change(horizon).shift(-horizon)
        labels = pd.Series(0, index=df.index, dtype=int)
        labels[future_ret > threshold] = 1
        labels[future_ret < -threshold] = -1
        return labels

    @staticmethod
    def make_regression_target(
        df: pd.DataFrame, horizon: int = 12
    ) -> pd.Series:
        """Forward return for regression models."""
        if df.empty or len(df) <= horizon:
            return pd.Series(dtype=float)
        return df["close"].pct_change(horizon).shift(-horizon)
