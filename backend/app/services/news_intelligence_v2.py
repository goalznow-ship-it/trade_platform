from datetime import datetime, timedelta
from app.services.market import market_service
from app.services.news import news_service
from app.services.news_intelligence import news_intelligence


class NewsIntelligenceEngine:
    MACRO_EVENTS = [
        "fed", "fomc", "interest rate", "cpi", "inflation", "gdp",
        "employment", "nonfarm", "unemployment", "central bank",
        "treasury", "yield", "recession", "quantitative easing", "tapering",
    ]

    REGULATION_KEYWORDS = [
        "sec", "regulation", "regulatory", "compliance", "legal",
        "ban", "approve", "etf", "bitcoin etf", "crypto bill", "license",
    ]

    WHALE_KEYWORDS = [
        "whale", "large transaction", "accumulation", "distribution",
        "million", "billion", "institutional", "major holder",
    ]

    async def analyze_news_event(self, article: dict) -> dict:
        title = article.get("title", "")
        content = article.get("content", "") or title
        text = f"{title} {content}".lower()

        intelligence = news_intelligence.analyze_article(title, content)
        sentiment = intelligence.get("sentiment", "neutral")
        impact_score = intelligence.get("impact_score", 0)
        affected = intelligence.get("affected_assets", [])

        is_macro = any(kw in text for kw in self.MACRO_EVENTS)
        is_regulation = any(kw in text for kw in self.REGULATION_KEYWORDS)
        is_whale = any(kw in text for kw in self.WHALE_KEYWORDS)

        event_type = "general"
        if is_macro:
            event_type = "macro"
        elif is_regulation:
            event_type = "regulation"
        elif is_whale:
            event_type = "whale"
        elif "hack" in text or "exploit" in text or "breach" in text:
            event_type = "security"
        elif "listing" in text or "delisting" in text:
            event_type = "listing"
        elif "partnership" in text or "collaboration" in text or "integrate" in text:
            event_type = "partnership"

        impact = "high" if impact_score > 7 else "medium" if impact_score > 4 else "low"
        if is_macro:
            impact = "high"
        if is_regulation and ("sec" in text or "ban" in text or "approve" in text):
            impact = "high"

        confidence = min(impact_score * 10 + 20, 95)

        # Determine direction for affected assets
        asset_impact = []
        for asset in affected:
            if sentiment == "bullish":
                direction = "bullish"
            elif sentiment == "bearish":
                direction = "bearish"
            else:
                direction = "neutral"
            asset_impact.append({"asset": asset, "direction": direction, "confidence": round(confidence, 1)})

        return {
            "title": title,
            "source": article.get("source", "unknown"),
            "url": article.get("url", ""),
            "published_at": article.get("published_at", datetime.utcnow().isoformat()),
            "sentiment": sentiment,
            "sentiment_score": round(intelligence.get("sentiment_score", 0), 2),
            "impact": impact,
            "impact_score": round(impact_score, 1),
            "event_type": event_type,
            "is_macro": is_macro,
            "is_regulation": is_regulation,
            "is_whale": is_whale,
            "affected_assets": affected,
            "asset_impact": asset_impact,
            "category": intelligence.get("category", "general"),
            "summary": intelligence.get("summary", title[:200]),
            "confidence": round(confidence, 1),
        }

    async def scan_all_news(self, limit: int = 20) -> list:
        articles = await news_service.fetch_all()
        analyzed = []
        for article in articles[:limit]:
            result = await self.analyze_news_event(article)
            analyzed.append(result)
        analyzed.sort(key=lambda x: x["impact_score"], reverse=True)
        return analyzed


news_intelligence_engine = NewsIntelligenceEngine()
