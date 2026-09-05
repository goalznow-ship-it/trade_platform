"""Whale transaction provider facade; returns no records without a real source."""


class WhaleTracker:
    async def get_recent(self, limit: int = 10) -> list[dict]:
        return []

    async def get_alerts(self, since_hours: int = 24) -> list[dict]:
        return []


whale_tracker = WhaleTracker()
