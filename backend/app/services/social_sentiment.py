"""Social sentiment provider facade.

No value is fabricated. Until provider credentials and collectors are configured,
callers receive an explicit unavailable state.
"""
import asyncio
from datetime import UTC, datetime

from app.core.provider_health import provider_health


def _unavailable(source: str, symbol: str | None = None) -> dict:
    return {
        "available": False,
        "source": source,
        "symbol": symbol,
        "reason": "No real-time social data provider configured",
        "timestamp": datetime.now(UTC).isoformat(),
    }


class SocialSentimentEngine:
    def analyze_twitter(self, keywords: list[str]) -> dict:
        return _unavailable("twitter", ",".join(keywords[:3]))

    def analyze_reddit(self, subreddits: list[str] | None = None) -> dict:
        return _unavailable("reddit")

    def analyze_telegram(self, channels: list[str] | None = None) -> dict:
        return _unavailable("telegram")

    def analyze_github(self, symbol: str, repo_url: str | None = None) -> dict:
        return _unavailable("github", symbol)

    def get_community_growth(self, symbol: str) -> dict:
        return _unavailable("community", symbol)

    def get_trending_narratives(self) -> list[dict]:
        return []

    def get_social_sentiment_snapshot(self, symbol: str) -> dict:
        return {
            **_unavailable("social_sentiment", symbol),
            "combined_score": None,
            "classification": "unavailable",
            "fomo_index": None,
            "fear_index": None,
        }

    async def stream_updates(self, interval: int = 120):
        while True:
            yield self.get_social_sentiment_snapshot("MARKET")
            await asyncio.sleep(interval)


social_sentiment = SocialSentimentEngine()
provider_health.configure("social_sentiment", False)
