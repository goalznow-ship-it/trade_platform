import asyncio
from typing import Optional, List
from datetime import datetime, timezone
from textblob import TextBlob
from app.core.logging import logger


class NewsIntelligence:
    def __init__(self):
        self.logger = logger
        self.crypto_keywords = {
            "bitcoin": ["BTC", "Bitcoin"],
            "ethereum": ["ETH", "Ethereum"],
            "solana": ["SOL", "Solana"],
            "ripple": ["XRP", "Ripple"],
            "cardano": ["ADA", "Cardano"],
            "polkadot": ["DOT", "Polkadot"],
            "avalanche": ["AVAX", "Avalanche"],
            "chainlink": ["LINK", "Chainlink"],
            "polygon": ["MATIC", "Polygon"],
            "dogecoin": ["DOGE", "Dogecoin"],
        }
        self.categories = ["regulation", "defi", "nft", "mining", "exchange",
                           "hack", "partnership", "listing", "earnings", "macro"]

    def analyze_article(self, title: str, content: str = "") -> dict:
        text = f"{title} {content}"[:5000]

        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity

        if polarity > 0.2:
            sentiment = "bullish"
        elif polarity < -0.2:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        coins = self._detect_coins(text)
        category = self._categorize(text)
        importance = self._calculate_importance(text, polarity)
        is_duplicate = False

        return {
            "sentiment": sentiment,
            "sentiment_score": round(polarity, 3),
            "subjectivity": round(subjectivity, 3),
            "impact_score": round(abs(polarity) * 10, 1),
            "market_impact": "positive" if polarity > 0 else "negative" if polarity < 0 else "neutral",
            "detected_coins": coins,
            "category": category,
            "importance_score": round(importance, 1),
            "is_duplicate": is_duplicate,
            "ai_summary": self._generate_summary(text, sentiment, coins),
        }

    def _detect_coins(self, text: str) -> list:
        found = []
        text_lower = text.lower()
        for coin, names in self.crypto_keywords.items():
            for name in names:
                if name.lower() in text_lower:
                    found.append(coin.upper() if len(coin) <= 5 else coin.capitalize())
                    break
        return list(set(found))

    def _categorize(self, text: str) -> str:
        text_lower = text.lower()
        category_map = {
            "regulation": ["sec", "regulation", "regulatory", "cftc", "compliance", "legal"],
            "defi": ["defi", "lending", "staking", "yield", "liquidity", "swap"],
            "nft": ["nft", "nfts", "collectible", "digital art"],
            "mining": ["mining", "miner", "hashrate", "block reward"],
            "exchange": ["exchange", "binance", "coinbase", "listing", "delist"],
            "hack": ["hack", "exploit", "breach", "theft", "stolen", "attack"],
            "partnership": ["partner", "partnership", "alliance", "collaboration", "integrate"],
            "earnings": ["earnings", "revenue", "profit", "quarterly", "fiscal"],
            "macro": ["fed", "interest rate", "inflation", "gdp", "economic"],
        }
        for category, keywords in category_map.items():
            if any(kw in text_lower for kw in keywords):
                return category
        return "general"

    def _calculate_importance(self, text: str, polarity: float) -> float:
        score = abs(polarity) * 5
        coins = self._detect_coins(text)
        score += len(coins) * 1
        text_lower = text.lower()
        high_impact = ["breaking", "urgent", "just in", "confirmed", "official",
                       "announcement", "hack", "crash", "surge"]
        score += sum(2 for w in high_impact if w in text_lower)
        return min(score, 10)

    def _generate_summary(self, text: str, sentiment: str, coins: list) -> str:
        parts = []
        if coins:
            parts.append(f"Related to {', '.join(coins[:3])}")
        parts.append(f"Sentiment: {sentiment}")
        sentences = text.split(".")
        if len(sentences) > 2:
            parts.append(sentences[1].strip()[:100])
        return " | ".join(parts) if parts else "No summary available"


news_intelligence = NewsIntelligence()
