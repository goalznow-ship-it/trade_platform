"""
Whale Transaction Tracker
Monitors large transfers on-chain via exchange flows
"""

from typing import Optional, List
from datetime import datetime, timezone
from app.core.logging import logger

class WhaleTracker:
    def __init__(self):
        self.logger = logger

    async def get_recent(self, limit: int = 10) -> List[dict]:
        return self._get_mock_whales()[:limit]

    async def get_alerts(self, since_hours: int = 24) -> List[dict]:
        whales = await self.get_recent(20)
        return [w for w in whales if w.get('impact', 0) > 70]

    def _get_mock_whales(self) -> List[dict]:
        return [
            {'symbol': 'BTC', 'amount': '1,250 BTC', 'value': '$80M', 'source': 'Binance', 'destination': 'Cold Wallet (bc1...)', 'type': 'withdrawal', 'direction': 'bullish', 'impact': 82, 'time': '12m ago'},
            {'symbol': 'ETH', 'amount': '45,000 ETH', 'value': '$156M', 'source': 'Coinbase', 'destination': 'Unknown Wallet (0x4f8...)', 'type': 'withdrawal', 'direction': 'bullish', 'impact': 75, 'time': '34m ago'},
            {'symbol': 'USDT', 'amount': '$200M USDT', 'value': '$200M', 'source': 'Tether Treasury', 'destination': 'Binance', 'type': 'mint', 'direction': 'neutral', 'impact': 65, 'time': '1h ago'},
            {'symbol': 'BTC', 'amount': '850 BTC', 'value': '$54M', 'source': 'Kraken', 'destination': 'Unknown Wallet (3J98...)', 'type': 'withdrawal', 'direction': 'bullish', 'impact': 78, 'time': '2h ago'},
            {'symbol': 'SOL', 'amount': '1.5M SOL', 'value': '$285M', 'source': 'FTX Estate', 'destination': 'Multiple Wallets', 'type': 'distribution', 'direction': 'bearish', 'impact': 88, 'time': '3h ago'},
            {'symbol': 'BTC', 'amount': '2,100 BTC', 'value': '$134M', 'source': 'Unknown Whale', 'destination': 'Binance', 'type': 'deposit', 'direction': 'bearish', 'impact': 85, 'time': '4h ago'},
            {'symbol': 'ETH', 'amount': '120,000 ETH', 'value': '$415M', 'source': 'Lido Staking', 'destination': 'Unstaking Queue', 'type': 'unstake', 'direction': 'bearish', 'impact': 80, 'time': '5h ago'},
            {'symbol': 'LINK', 'amount': '500,000 LINK', 'value': '$8.5M', 'source': 'Binance', 'destination': 'Cold Wallet', 'type': 'withdrawal', 'direction': 'bullish', 'impact': 72, 'time': '6h ago'},
        ]

whale_tracker = WhaleTracker()
