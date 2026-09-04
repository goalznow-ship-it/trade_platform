"""
ML Training Script — run as standalone job to (re)train the ensemble.

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
from datetime import datetime

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from app.core.logging import logger
from app.services.exchange.manager import exchange_manager
from app.services.ml import MLSignalEngine


# Default top-30 Binance perpetual symbols
DEFAULT_SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "LINK/USDT", "TRX/USDT",
    "DOT/USDT", "MATIC/USDT", "LTC/USDT", "SHIB/USDT", "TON/USDT",
    "ICP/USDT", "BCH/USDT", "ATOM/USDT", "NEAR/USDT", "UNI/USDT",
    "APT/USDT", "STX/USDT", "FIL/USDT", "ARB/USDT", "OP/USDT",
    "INJ/USDT", "RNDR/USDT", "IMX/USDT", "SUI/USDT", "TIA/USDT",
]


async def run_training(
    symbols: list[str],
    timeframe: str = "15m",
    include_transformer: bool = True,
    save: bool = True,
):
    """Async training entry point."""
    print(f"🚀 Starting ML training")
    print(f"   Symbols: {len(symbols)}")
    print(f"   Timeframe: {timeframe}")
    print(f"   Transformer: {include_transformer}")
    print(f"   Timestamp: {datetime.utcnow().isoformat()}Z")
    print()

    engine = MLSignalEngine()

    # Use the existing exchange manager
    exchange = await exchange_manager.get_primary()
    if exchange is None:
        print("❌ No exchange client available. Start the platform first to connect Binance.")
        return

    try:
        results = await engine.train(
            symbols=symbols,
            exchange_client=exchange,
            timeframe=timeframe,
            include_transformer=include_transformer,
            save=save,
        )

        print()
        print("=" * 60)
        print("✅ Training complete")
        print("=" * 60)
        print(json.dumps(results, indent=2, default=str))

        if "error" not in results:
            print()
            print("Models saved to app/models_store/")
            print("Restart the platform to load the new models.")

    except Exception as e:
        logger.error(f"Training failed: {e}")
        print(f"❌ Training failed: {e}")
        raise
    finally:
        await exchange_manager.shutdown()


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
