"""
Technical feature engineering.
Computes a comprehensive set of price/volume based indicators
that capture momentum, volatility, trend, and mean-reversion dynamics.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


class TechnicalFeatures:
    """Vectorised technical-analysis feature builder."""

    # ── Moving averages & trend ────────────────────────────────────────────
    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).mean()

    @staticmethod
    def trend_features(df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        feats = pd.DataFrame(index=df.index)

        for p in (5, 8, 13, 21, 34, 55, 89, 144, 200):
            ema = TechnicalFeatures.ema(close, p)
            feats[f"ema_{p}_dist"] = (close - ema) / ema
            feats[f"ema_{p}_slope"] = ema.pct_change(5)

        # MACD
        ema12 = TechnicalFeatures.ema(close, 12)
        ema26 = TechnicalFeatures.ema(close, 26)
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        feats["macd"] = macd
        feats["macd_signal"] = signal
        feats["macd_hist"] = macd - signal
        feats["macd_hist_norm"] = (macd - signal) / close

        # ADX (Average Directional Index)
        high = df["high"]
        low = df["low"]
        plus_dm = (high.diff()).clip(lower=0)
        minus_dm = (-low.diff()).clip(lower=0)
        tr = pd.concat(
            [
                (high - low),
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr14 = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / atr14.replace(0, np.nan))
        minus_di = 100 * (minus_dm.rolling(14).mean() / atr14.replace(0, np.nan))
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        feats["adx"] = dx.rolling(14).mean()
        feats["plus_di"] = plus_di
        feats["minus_di"] = minus_di

        return feats

    # ── Momentum oscillators ─────────────────────────────────────────────
    @staticmethod
    def momentum_features(df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        feats = pd.DataFrame(index=df.index)

        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        feats["rsi_14"] = 100 - (100 / (1 + rs))
        feats["rsi_7"] = 100 - (
            100
            / (
                1
                + delta.clip(lower=0).rolling(7).mean()
                / (-delta.clip(upper=0)).rolling(7).mean().replace(0, np.nan)
            )
        )

        # Stochastic RSI
        rsi = feats["rsi_14"]
        stoch_rsi = (rsi - rsi.rolling(14).min()) / (
            rsi.rolling(14).max() - rsi.rolling(14).min()
        ).replace(0, np.nan)
        feats["stoch_rsi"] = stoch_rsi
        feats["stoch_rsi_smooth"] = stoch_rsi.rolling(3).mean()

        # Williams %R
        high_14 = df["high"].rolling(14).max()
        low_14 = df["low"].rolling(14).min()
        feats["williams_r"] = -100 * (high_14 - close) / (high_14 - low_14).replace(
            0, np.nan
        )

        # CCI
        tp = (df["high"] + df["low"] + close) / 3
        sma_tp = tp.rolling(20).mean()
        mad = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
        feats["cci"] = (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))

        # ROC (Rate of Change)
        for p in (5, 10, 20):
            feats[f"roc_{p}"] = close.pct_change(p)

        return feats

    # ── Volatility & bands ────────────────────────────────────────────────
    @staticmethod
    def volatility_features(df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        feats = pd.DataFrame(index=df.index)

        # Bollinger Bands
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        feats["bb_upper_dist"] = (close - (sma20 + 2 * std20)) / close
        feats["bb_lower_dist"] = (close - (sma20 - 2 * std20)) / close
        feats["bb_width"] = (4 * std20) / sma20.replace(0, np.nan)
        feats["bb_pct_b"] = (close - (sma20 - 2 * std20)) / (
            4 * std20.replace(0, np.nan)
        )

        # ATR (multiple periods)
        tr = pd.concat(
            [
                (high - low),
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ],
            axis=1,
        ).max(axis=1)
        for p in (7, 14, 21):
            atr = tr.rolling(p).mean()
            feats[f"atr_{p}"] = atr
            feats[f"atr_{p}_norm"] = atr / close

        # Historical volatility
        log_ret = np.log(close / close.shift())
        for p in (5, 10, 20, 50):
            feats[f"vol_{p}"] = log_ret.rolling(p).std() * math.sqrt(365 * 24 * 60)  # crypto yearly

        # Keltner channels
        ema20 = close.ewm(span=20, adjust=False).mean()
        atr14 = tr.rolling(14).mean()
        feats["keltner_upper_dist"] = (close - (ema20 + 2 * atr14)) / close
        feats["keltner_lower_dist"] = (close - (ema20 - 2 * atr14)) / close

        return feats

    # ── Volume features ─────────────────────────────────────────────────
    @staticmethod
    def volume_features(df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        volume = df["volume"]
        feats = pd.DataFrame(index=df.index)

        # VWAP distance
        tp = (df["high"] + df["low"] + close) / 3
        vwap = (tp * volume).rolling(20).sum() / volume.rolling(20).sum().replace(0, np.nan)
        feats["vwap_dist"] = (close - vwap) / vwap

        # OBV trend
        sign = np.sign(close.diff()).fillna(0)
        obv = (sign * volume).cumsum()
        feats["obv_slope"] = obv.pct_change(10)
        feats["obv_ema_ratio"] = obv / obv.ewm(span=21, adjust=False).mean().replace(
            0, np.nan
        )

        # Volume relative
        for p in (5, 10, 20):
            mean_v = volume.rolling(p).mean()
            feats[f"vol_ratio_{p}"] = volume / mean_v.replace(0, np.nan)

        # Volume profile
        feats["vol_zscore"] = (volume - volume.rolling(50).mean()) / volume.rolling(
            50
        ).std().replace(0, np.nan)

        # Money Flow Index
        tp = (df["high"] + df["low"] + close) / 3
        mf = tp * volume
        pos_mf = mf.where(tp > tp.shift(), 0).rolling(14).sum()
        neg_mf = mf.where(tp < tp.shift(), 0).rolling(14).sum()
        mfr = pos_mf / neg_mf.replace(0, np.nan)
        feats["mfi"] = 100 - (100 / (1 + mfr))

        return feats

    # ── Price action / structure ────────────────────────────────────────
    @staticmethod
    def structure_features(df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        feats = pd.DataFrame(index=df.index)

        # Higher-highs / higher-lows
        hh = (high > high.shift(1)).rolling(10).sum()
        hl = (low > low.shift(1)).rolling(10).sum()
        lh = (high < high.shift(1)).rolling(10).sum()
        ll = (low < low.shift(1)).rolling(10).sum()
        feats["hh_count"] = hh
        feats["hl_count"] = hl
        feats["lh_count"] = lh
        feats["ll_count"] = ll
        feats["structure_score"] = (hh + hl) - (lh + ll)

        # Candle body / shadow ratios
        body = (close - df["open"]).abs()
        full_range = (high - low).replace(0, np.nan)
        feats["body_ratio"] = body / full_range
        upper_shadow = high - pd.concat([close, df["open"]], axis=1).max(axis=1)
        lower_shadow = pd.concat([close, df["open"]], axis=1).min(axis=1) - low
        feats["upper_shadow_ratio"] = upper_shadow / full_range
        feats["lower_shadow_ratio"] = lower_shadow / full_range

        # Gap detection
        feats["gap"] = (df["open"] - close.shift()) / close.shift()

        return feats

    @classmethod
    def build_all(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Build complete technical feature matrix from OHLCV dataframe."""
        if df.empty or len(df) < 200:
            return pd.DataFrame()

        df = df.sort_index().copy()
        parts = [
            cls.trend_features(df),
            cls.momentum_features(df),
            cls.volatility_features(df),
            cls.volume_features(df),
            cls.structure_features(df),
        ]
        feats = pd.concat(parts, axis=1)
        feats = feats.replace([np.inf, -np.inf], np.nan)
        return feats
