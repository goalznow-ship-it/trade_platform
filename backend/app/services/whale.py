"""Whale transaction provider facade; returns no records without a real source."""
from typing import List


class WhaleTracker:
    async def get_recent(self, limit: int = 10) -> List[dict]:
        return []

    async def get_alerts(self, since_hours: int = 24) -> List[dict]:
        return []


whale_tracker = WhaleTracker()
