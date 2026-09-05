"""
ML Training Script — run as standalone job to (re)train the ensemble.

This script is intended to be executed in the `ml_trainer` profile
(see docker-compose.yml) or any environment that can reach the public
Binance API. It builds a fresh, self-contained exchange client and
does not touch the global exchange_manager used by the live server.

Usage:
    python -m app.services.ml.training.train_script
    python -m app.services.ml.training.train_script --symbols BTC ETH SOL --tf 15m
    python -m app.services.ml.training.train_script --no-transformer
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import ccxt.async_support as ccxt

from app.core.logging import logger
from app.services.ml import MLSignalEngine
from app.services.ml.seed import set_seed

# Phase 3: seed the world before any model touches an RNG. The same
# seed is read by XGBoost / LightGBM / Transformer at their own
# ``train()`` entry points, but the dataset builder and any helper
# code that runs here also benefits from a deterministic start.
set_seed()

# Default top-30 Binance perpetual symbols
DEFAULT_SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "LINK/USDT", "TRX/USDT",
    "DOT/USDT", "MATIC/USDT", "LTC/USDT", "SHIB/USDT", "TON/USDT",
    "ICP/USDT", "BCH/USDT", "ATOM/USDT", "NEAR/USDT", "UNI/USDT",
    "APT/USDT", "STX/USDT", "FIL/USDT", "ARB/USDT", "OP/USDT",
    "INJ/USDT", "RNDR/USDT", "IMX/USDT", "SUI/USDT", "TIA/USDT",
]


class _CcxtClient:
    """
    Minimal adapter that exposes `fetch_ohlcv` to the training pipeline.

    The pipeline only calls `await client.fetch_ohlcv(symbol, tf, limit=...)`,
    so we wrap the ccxt async client and do not share any state with the
    live server's exchange_manager.
    """

    def __init__(self, client):
        self._client = client
        # Public Binance market data — no auth needed.
        self.api_key: str | None = None
        self.secret: str | None = None

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 500):
        return await self._client.fetch_ohlcv(symbol, timeframe, limit=limit)

    async def close(self):
        await self._client.close()


async def _build_public_exchange() -> _CcxtClient:
    """
    Create a fresh ccxt Binance futures client using only public endpoints.
    No API key is needed for OHLCV reads.
    """
    client = ccxt.binanceusdm({
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
    })
    return _CcxtClient(client)


async def run_training(
    symbols: list[str],
    timeframe: str = "15m",
    include_transformer: bool = True,
    save: bool = True,
) -> dict:
    """Async training entry point. Returns the training-results dict."""
    print("🚀 Starting ML training")
    print(f"   Symbols: {len(symbols)}")
    print(f"   Timeframe: {timeframe}")
    print(f"   Transformer: {include_transformer}")
    print(f"   Timestamp: {datetime.now(UTC).isoformat()}")
    print()

    engine = MLSignalEngine()
    exchange = await _build_public_exchange()
    try:
        results = await engine.train(
            symbols=symbols,
            exchange_client=exchange,
            timeframe=timeframe,
            include_transformer=include_transformer,
            save=save,
        )
    finally:
        try:
            await exchange.close()
        except Exception as e:
            logger.warning(f"Exchange close error: {e}")

    print()
    print("=" * 60)
    print("✅ Training complete")
    print("=" * 60)
    print(json.dumps(results, indent=2, default=str))

    if "error" not in results:
        print()
        print("Models saved to app/models_store/")
        print("Restart the platform to load the new models.")
    return results


def main():
    parser = argparse.ArgumentParser(description="Train ML signal ensemble")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help="Symbols to train on (default: top 30)",
    )
    parser.add_argument("--tf", default="15m", help="Timeframe (1m, 5m, 15m, 1h, 4h)")
    parser.add_argument(
        "--no-transformer",
        action="store_true",
        help="Skip transformer training (faster)",
    )
    parser.add_argument(
        "--no-save", action="store_true", help="Don't save models to disk"
    )
    args = parser.parse_args()

    asyncio.run(
        run_training(
            symbols=args.symbols,
            timeframe=args.tf,
            include_transformer=not args.no_transformer,
            save=not args.no_save,
        )
    )


if __name__ == "__main__":
    main()
