"""On-chain provider facade that never fabricates transactions or metrics."""
import asyncio
from datetime import datetime, timezone
from typing import Dict, List
from app.core.provider_health import provider_health


def _unavailable(source: str, symbol: str | None = None) -> Dict:
    return {
        "available": False,
        "source": source,
        "symbol": symbol,
        "reason": "No real-time on-chain data provider configured",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class OnChainEngine:
    def get_exchange_inflow(self, symbol: str) -> Dict:
        return _unavailable("exchange_inflow", symbol)

    def get_exchange_outflow(self, symbol: str) -> Dict:
        return _unavailable("exchange_outflow", symbol)

    def get_whale_activity(self, symbol: str) -> Dict:
        return _unavailable("whale_activity", symbol)

    def get_stablecoin_flow(self) -> Dict:
        return _unavailable("stablecoin_flow")

    def get_exchange_reserves(self, symbol: str) -> Dict:
        return _unavailable("exchange_reserves", symbol)

    def get_dormant_supply(self, symbol: str) -> Dict:
        return _unavailable("dormant_supply", symbol)

    def get_miner_activity(self, symbol: str) -> Dict:
        return _unavailable("miner_activity", symbol)

    def get_large_transfers(self, threshold_usd: float = 500000) -> List[Dict]:
        return []

    def get_onchain_snapshot(self, symbol: str) -> Dict:
        return {
            **_unavailable("onchain", symbol),
            "combined_score": None,
            "combined_signal": "unavailable",
        }

    def get_onchain_snapshot_lite(self, symbol: str) -> Dict:
        return self.get_onchain_snapshot(symbol)

    async def stream_updates(self, interval: int = 300):
        while True:
            yield self.get_onchain_snapshot("MARKET")
            await asyncio.sleep(interval)


onchain_engine = OnChainEngine()
provider_health.configure("onchain", False)
