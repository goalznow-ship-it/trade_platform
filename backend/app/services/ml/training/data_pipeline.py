"""
Training data pipeline.
Fetches historical OHLCV + builds features + labels for ML training.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.logging import logger
from ..features.engineer import FeatureEngineer


class TrainingDataPipeline:
    """
    Pulls historical data from ccxt, engineers features, builds labels.
    Designed for retraining on a schedule.
    """

    def __init__(
        self,
        exchange_client=None,
        timeframe: str = "15m",
        lookback_days: int = 180,
        horizon_bars: int = 12,
        label_threshold: float = 0.005,
    ):
        self.exchange_client = exchange_client
        self.timeframe = timeframe
        self.lookback_days = lookback_days
        self.horizon_bars = horizon_bars
        self.label_threshold = label_threshold
        self.fe = FeatureEngineer()

    async def fetch_ohlcv(
        self, symbol: str, days: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Fetch OHLCV from exchange client. Returns DataFrame with DatetimeIndex.

        The previous implementation called fetch_ohlcv once with limit=1500
        even when lookback_days=180. 180 days at 15m timeframe is
        ~17,280 candles, so the training set was actually 6 days of data
        dressed up as 180 days. Walk-forward validation on that produces
        a model that overfits the latest week and cannot generalize.

        This now paginates in 1500-candle chunks, walking forward in time
        from `since` until either we hit `days` days back or the exchange
        returns an empty page.
        """
        days = days or self.lookback_days
        if self.exchange_client is None:
            logger.warning(f"No exchange client for {symbol}, returning empty")
            return pd.DataFrame()

        try:
            since = int(
                (datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000
            )
            page_size = 1500
            all_rows: list = []
            last_ts = since
            # Page until we get less than a full page (exchange has
            # nothing newer than `last_ts` + page_size worth of bars)
            # or we accumulate enough history to cover the window.
            # 4 pages of 1500 = 6000 candles = 62.5 days at 15m; the
            # loop auto-terminates when the exchange is exhausted.
            for _ in range(16):  # hard cap: 16 * 1500 = 24k candles
                page = await self.exchange_client.fetch_ohlcv(
                    symbol, self.timeframe, since=last_ts, limit=page_size,
                )
                if not page:
                    break
                all_rows.extend(page)
                # Advance since to the timestamp of the last row + 1 ms
                # so the next page picks up where this one stopped.
                last_ts = int(page[-1][0]) + 1
                if len(page) < page_size:
                    # Short page: no more data available.
                    break
            if not all_rows:
                return pd.DataFrame()
            df = pd.DataFrame(
                all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df = df.set_index("timestamp").sort_index()
            df = df[~df.index.duplicated(keep="first")]
            return df
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    async def build_dataset(
        self,
        symbol: str,
        benchmark_symbol: str = "BTC/USDT",
        news_events: Optional[list] = None,
        funding: Optional[pd.DataFrame] = None,
        oi: Optional[pd.DataFrame] = None,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Build (X, y) for one symbol.
        Returns empty if data insufficient.
        """
        df = await self.fetch_ohlcv(symbol)
        if df.empty or len(df) < 250:
            return pd.DataFrame(), pd.Series(dtype=int)

        benchmark_df = await self.fetch_ohlcv(benchmark_symbol, days=self.lookback_days)
        if benchmark_df.empty:
            benchmark_df = None

        X = self.fe.build(df, benchmark_df, news_events, funding, oi)
        if X.empty or len(X) < 100:
            return pd.DataFrame(), pd.Series(dtype=int)

        y = self.fe.make_labels(df, self.horizon_bars, self.label_threshold)
        y = y.reindex(X.index).dropna()
        X = X.loc[y.index]
        return X, y

    async def build_multi_symbol_dataset(
        self, symbols: List[str], benchmark_symbol: str = "BTC/USDT"
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Concatenate features from multiple symbols.
        Each symbol's data is treated as independent samples.
        """
        all_X, all_y = [], []
        for sym in symbols:
            try:
                X, y = await self.build_dataset(sym, benchmark_symbol)
                if not X.empty and not y.empty:
                    X = X.copy()
                    X["symbol"] = sym
                    all_X.append(X)
                    all_y.append(y)
            except Exception as e:
                logger.error(f"Failed dataset for {sym}: {e}")
                continue

        if not all_X:
            return pd.DataFrame(), pd.Series(dtype=int)

        X = pd.concat(all_X, axis=0).drop(columns=["symbol"], errors="ignore")
        y = pd.concat(all_y, axis=0)
        return X, y
