"""
Unified feature engineering pipeline.
Combines technical + microstructure + cross-asset + sentiment into one matrix.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .cross_asset import CrossAssetFeatures
from .microstructure import MicrostructureFeatures
from .sentiment import SentimentFeatures
from .technical import TechnicalFeatures


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
        benchmark_df: pd.DataFrame | None = None,
        news_events: list | None = None,
        funding: pd.DataFrame | None = None,
        oi: pd.DataFrame | None = None,
        market_basket: dict[str, pd.DataFrame] | None = None,
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
        df: pd.DataFrame, horizon: int = 12, threshold: float = 0.005,
        volatility_scaled: bool = True,
    ) -> pd.Series:
        """
        Triple-barrier label generation:
        - 1 = buy (forward return > +threshold)
        - -1 = sell (forward return < -threshold)
        - 0 = neutral

        When volatility_scaled=True, threshold is interpreted as a
        multiple of recent realized volatility (ATR(14) / close) rather
        than an absolute price move. The previous implementation used
        a flat 0.5% threshold, which produced wildly imbalanced labels:
        on a quiet weekend a 0.5% move was rare (almost everything
        neutral), and on a BTC leverage flush 0.5% was so easy to clear
        that the model degenerated to "always long, always short"
        noise. A volatility-scaled threshold makes "buy" and "sell"
        regimes self-consistent across symbols and timeframes.
        """
        if df.empty or len(df) <= horizon:
            return pd.Series(dtype=int)

        future_ret = df["close"].pct_change(horizon).shift(-horizon)
        if volatility_scaled and len(df) >= 16:
            # Realized volatility: 14-bar ATR divided by close.
            high_low = df["high"] - df["low"]
            high_close = (df["high"] - df["close"].shift(1)).abs()
            low_close = (df["low"] - df["close"].shift(1)).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr_14 = tr.rolling(14, min_periods=5).mean()
            realized_vol = atr_14 / df["close"]
            # Scale threshold so it represents 0.005 / vol. A 1% ATR on
            # BTC means a 0.5% move is 0.5 ATR (still meaningful); on
            # altcoins with 3% ATR it's 0.17 ATR (much easier to clear,
            # so the threshold stays high enough to avoid trivial buys).
            scaled_threshold = (threshold / realized_vol).clip(lower=0.001, upper=0.05)
            # The effective threshold is `scaled_threshold` expressed as
            # a fraction (i.e. multiply future_ret by 1/scaled_threshold
            # and compare against 1). Equivalent to: is forward return
            # greater than scaled_threshold * 100%? We do the math
            # directly here to keep the meaning obvious.
            labels = pd.Series(0, index=df.index, dtype=int)
            labels[future_ret > scaled_threshold] = 1
            labels[future_ret < -scaled_threshold] = -1
        else:
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
