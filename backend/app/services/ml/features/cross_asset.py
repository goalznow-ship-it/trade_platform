"""
Cross-asset and macro features.
Captures correlation and lead-lag relationships with broader market.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd


class CrossAssetFeatures:
    """
    Cross-asset correlation and lead-lag features.
    When BTC moves, alts follow with some delay — capture that.
    """

    @staticmethod
    def rolling_correlation(
        series_a: pd.Series, series_b: pd.Series, window: int = 30
    ) -> pd.Series:
        return series_a.rolling(window).corr(series_b)

    @staticmethod
    def beta(
        target: pd.Series, benchmark: pd.Series, window: int = 60
    ) -> pd.Series:
        """Rolling beta vs benchmark (BTC by default)."""
        log_ret_t = np.log(target / target.shift())
        log_ret_b = np.log(benchmark / benchmark.shift())
        cov = log_ret_t.rolling(window).cov(log_ret_b)
        var = log_ret_b.rolling(window).var()
        return cov / var.replace(0, np.nan)

    @staticmethod
    def relative_strength(
        target: pd.Series, benchmark: pd.Series, period: int = 20
    ) -> pd.Series:
        """Ratio of returns — alt out/under performing BTC."""
        log_ret_t = np.log(target / target.shift())
        log_ret_b = np.log(benchmark / benchmark.shift())
        rs = (log_ret_t - log_ret_b).rolling(period).sum()
        return rs

    @staticmethod
    def regime_features(
        target: pd.DataFrame, benchmark_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Build cross-asset features for a single symbol.
        If benchmark_df is None, target's own close is used.
        """
        if target.empty or len(target) < 100:
            return pd.DataFrame()

        close = target["close"]
        feats = pd.DataFrame(index=target.index)

        if benchmark_df is not None and not benchmark_df.empty:
            btc_close = benchmark_df["close"].reindex(target.index, method="ffill")
            feats["btc_corr_30"] = CrossAssetFeatures.rolling_correlation(
                close.pct_change(), btc_close.pct_change(), 30
            )
            feats["btc_corr_90"] = CrossAssetFeatures.rolling_correlation(
                close.pct_change(), btc_close.pct_change(), 90
            )
            feats["btc_beta_60"] = CrossAssetFeatures.beta(close, btc_close, 60)
            feats["btc_rs_20"] = CrossAssetFeatures.relative_strength(
                close, btc_close, 20
            )
            # Lead-lag: did BTC move before us?
            btc_ret = btc_close.pct_change()
            tgt_ret = close.pct_change()
            feats["btc_lead_corr"] = (
                btc_ret.shift(1).rolling(20).corr(tgt_ret)
            )

        return feats

    @staticmethod
    def market_breadth(market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Compute market-wide breadth from a basket of symbols.
        Returns: % of symbols above EMA20, EMA50, EMA200, etc.
        """
        if not market_data:
            return pd.DataFrame()

        all_close = pd.DataFrame(
            {sym: df["close"] for sym, df in market_data.items() if not df.empty}
        )
        if all_close.empty:
            return pd.DataFrame()

        ema20 = all_close.ewm(span=20, adjust=False).mean()
        ema50 = all_close.ewm(span=50, adjust=False).mean()

        feats = pd.DataFrame(index=all_close.index)
        feats["pct_above_ema20"] = (all_close > ema20).mean(axis=1)
        feats["pct_above_ema50"] = (all_close > ema50).mean(axis=1)
        feats["advancers"] = (all_close.pct_change() > 0).mean(axis=1)
        feats["market_ret_1h"] = all_close.pct_change().mean(axis=1)
        return feats
