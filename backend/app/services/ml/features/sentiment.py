"""
Sentiment & news features.
Combines news, social, and on-chain signals into ML features.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class SentimentFeatures:
    """
    Convert news/social/on-chain signals into time-series features
    that align with price bar timestamps.
    """

    @staticmethod
    def news_to_features(
        news_events: list, index: pd.DatetimeIndex, window: str = "4h"
    ) -> pd.DataFrame:
        """
        news_events: list of {timestamp, sentiment, impact, category}
        Returns: per-bar rolling counts and aggregate scores.
        """
        if not news_events:
            return pd.DataFrame(index=index)

        df = pd.DataFrame(news_events)
        if df.empty or "timestamp" not in df.columns:
            return pd.DataFrame(index=index)

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()
        df = df.reindex(index, method="ffill").fillna(0)

        feats = pd.DataFrame(index=index)
        for w in (4, 12, 24, 72):
            feats[f"news_count_{w}h"] = (
                df["sentiment"].rolling(f"{w}h", min_periods=1).count() if "sentiment" in df else 0
            )
            if "sentiment" in df:
                feats[f"news_sentiment_{w}h"] = (
                    df["sentiment"].rolling(f"{w}h", min_periods=1).mean()
                )
            if "impact" in df:
                feats[f"news_impact_{w}h"] = (
                    df["impact"].rolling(f"{w}h", min_periods=1).sum()
                )
        return feats.fillna(0)

    @staticmethod
    def funding_features(
        funding_history: pd.DataFrame, index: pd.DatetimeIndex
    ) -> pd.DataFrame:
        """
        funding_history: DataFrame with columns [funding_rate, timestamp]
        """
        if funding_history is None or funding_history.empty:
            return pd.DataFrame(index=index)

        df = funding_history.copy()
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")
        df = df.reindex(index, method="ffill")

        feats = pd.DataFrame(index=index)
        feats["funding_rate"] = df["funding_rate"]
        feats["funding_zscore"] = (
            df["funding_rate"] - df["funding_rate"].rolling(30).mean()
        ) / df["funding_rate"].rolling(30).std().replace(0, np.nan)
        feats["funding_extreme"] = (
            (df["funding_rate"].abs() > 0.01).astype(int)
        )
        return feats.fillna(0)

    @staticmethod
    def oi_features(
        oi_history: pd.DataFrame, index: pd.DatetimeIndex
    ) -> pd.DataFrame:
        """
        Open Interest change features.
        Rising OI + rising price = strong trend.
        """
        if oi_history is None or oi_history.empty:
            return pd.DataFrame(index=index)

        df = oi_history.copy()
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")
        df = df.reindex(index, method="ffill")

        feats = pd.DataFrame(index=index)
        feats["oi"] = df["open_interest"] if "open_interest" in df else 0
        feats["oi_change_1h"] = df["open_interest"].pct_change(1) if "open_interest" in df else 0
        feats["oi_change_4h"] = df["open_interest"].pct_change(4) if "open_interest" in df else 0
        feats["oi_change_24h"] = df["open_interest"].pct_change(24) if "open_interest" in df else 0
        return feats.fillna(0)

    @staticmethod
    def combine_all(
        index: pd.DatetimeIndex,
        news_events: list | None = None,
        funding: pd.DataFrame | None = None,
        oi: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        parts = []
        if news_events:
            parts.append(SentimentFeatures.news_to_features(news_events, index))
        if funding is not None:
            parts.append(SentimentFeatures.funding_features(funding, index))
        if oi is not None:
            parts.append(SentimentFeatures.oi_features(oi, index))
        if not parts:
            return pd.DataFrame(index=index)
        out = pd.concat(parts, axis=1)
        return out.fillna(0)
