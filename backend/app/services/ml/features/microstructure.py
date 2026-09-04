"""
Microstructure features — order book, CVD, trade flow signals.
These features capture short-term supply/demand imbalance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class MicrostructureFeatures:
    """Order book and trade-flow microstructure features."""

    @staticmethod
    def cvd_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Cumulative Volume Delta — net aggressive buying pressure.
        +CVD = buyers in control; -CVD = sellers in control.
        """
        close = df["close"]
        open_ = df["open"]
        volume = df["volume"]

        buy_vol = volume.where(close >= open_, 0)
        sell_vol = volume.where(close < open_, 0)
        delta = buy_vol - sell_vol
        cvd = delta.cumsum()

        feats = pd.DataFrame(index=df.index)
        feats["cvd"] = cvd
        feats["cvd_slope_5"] = cvd.diff(5)
        feats["cvd_slope_20"] = cvd.diff(20)
        feats["cvd_ema_ratio"] = cvd / cvd.ewm(span=21, adjust=False).mean().replace(
            0, np.nan
        )
        feats["cvd_divergence"] = (close.pct_change(20) - cvd.pct_change(20)).fillna(0)
        return feats

    @staticmethod
    def absorption_features(df: pd.DataFrame) -> pd.DataFrame:
        """Detect absorption — high volume with small price move."""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        range_ = (high - low).replace(0, np.nan)
        vol_per_range = volume / range_

        feats = pd.DataFrame(index=df.index)
        feats["absorption_5"] = vol_per_range.rolling(5).mean()
        feats["absorption_20"] = vol_per_range.rolling(20).mean()
        feats["absorption_zscore"] = (
            vol_per_range - vol_per_range.rolling(50).mean()
        ) / vol_per_range.rolling(50).std().replace(0, np.nan)
        feats["price_efficiency"] = (close.diff().abs() / volume.replace(0, np.nan)).rolling(
            20
        ).mean()
        return feats

    @staticmethod
    def volatility_regime(df: pd.DataFrame) -> pd.DataFrame:
        """Classify current volatility regime vs history."""
        close = df["close"]
        log_ret = np.log(close / close.shift())
        vol_20 = log_ret.rolling(20).std()
        vol_100 = log_ret.rolling(100).std()

        feats = pd.DataFrame(index=df.index)
        feats["vol_regime_ratio"] = vol_20 / vol_100.replace(0, np.nan)
        feats["vol_regime_zscore"] = (
            vol_20 - vol_20.rolling(100).mean()
        ) / vol_20.rolling(100).std().replace(0, np.nan)
        feats["vol_expansion"] = (vol_20 > vol_100 * 1.5).astype(int)
        feats["vol_contraction"] = (vol_20 < vol_100 * 0.5).astype(int)
        return feats

    @staticmethod
    def trade_intensity(df: pd.DataFrame) -> pd.DataFrame:
        """Approximate trade intensity from volume and bar structure."""
        high = df["high"]
        low = df["low"]
        close = df["close"]
        open_ = df["open"]
        volume = df["volume"]

        bar_range = (high - low).replace(0, np.nan)
        feats = pd.DataFrame(index=df.index)

        # Approximate buy/sell trade count via tick method
        signed_vol = np.sign(close - open_) * volume
        feats["trade_imbalance"] = signed_vol.rolling(20).sum()
        feats["buy_sell_ratio"] = (
            volume.where(close >= open_, 0).rolling(20).sum()
            / volume.where(close < open_, 0).rolling(20).sum().replace(0, np.nan)
        )
        feats["intensity"] = volume / bar_range
        feats["intensity_zscore"] = (
            feats["intensity"] - feats["intensity"].rolling(50).mean()
        ) / feats["intensity"].rolling(50).std().replace(0, np.nan)
        return feats

    @classmethod
    def build_all(cls, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < 100:
            return pd.DataFrame()
        df = df.sort_index().copy()
        parts = [
            cls.cvd_features(df),
            cls.absorption_features(df),
            cls.volatility_regime(df),
            cls.trade_intensity(df),
        ]
        feats = pd.concat(parts, axis=1)
        return feats.replace([np.inf, -np.inf], np.nan)
