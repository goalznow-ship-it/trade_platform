"""Configurable, provider-isolated real news ingestion."""

import asyncio
import hashlib
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

from app.core.logging import logger
from app.services.data_contract import data_meta, utc_now


class NewsService:
    DEFAULT_RSS_PROVIDERS = {
        "Cointelegraph": "https://cointelegraph.com/rss",
        "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "Decrypt": "https://decrypt.co/feed",
    }

    def __init__(self) -> None:
        configured = os.getenv("NEWS_RSS_PROVIDERS", "").strip()
        self.providers = dict(self.DEFAULT_RSS_PROVIDERS)
        if configured:
            # Format: Provider=https://feed,Provider2=https://feed
            self.providers = {
                name.strip(): url.strip()
                for pair in configured.split(",")
                if "=" in pair
                for name, url in [pair.split("=", 1)]
            }

    async def _fetch_feed(self, source: str, url: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TradeAnalystPro/1.0"})
            response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        rows = []
        for item in root.findall(".//item")[:30]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            raw_summary = item.findtext("description") or item.findtext("content") or ""
            summary = BeautifulSoup(raw_summary, "html.parser").get_text(" ", strip=True)
            published_raw = item.findtext("pubDate") or item.findtext("date")
            try:
                published = parsedate_to_datetime(published_raw).astimezone(timezone.utc).isoformat()
            except (TypeError, ValueError):
                published = utc_now()
            if title and link:
                rows.append({
                    "id": hashlib.sha256(f"{title.lower()}|{link}".encode()).hexdigest()[:20],
                    "title": title,
                    "url": urljoin(url, link),
                    "source": source,
                    "content": summary,
                    "summary": summary[:500],
                    "published_at": published,
                })
        return rows

    async def fetch_with_status(self, limit: int = 50) -> dict:
        tasks = [self._fetch_feed(name, url) for name, url in self.providers.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        provider_errors = {}
        available = []
        all_news = []
        for (name, _), result in zip(self.providers.items(), results):
            if isinstance(result, Exception):
                provider_errors[name] = f"{type(result).__name__}: {str(result)[:240]}"
                logger.warning("News provider %s failed: %s", name, result)
            else:
                available.append(name)
                all_news.extend(result)

        # URL and normalized-title deduplication across providers.
        deduped = {}
        for article in all_news:
            key = "".join(ch for ch in article["title"].lower() if ch.isalnum())[:180]
            current = deduped.get(key)
            if not current or article["published_at"] > current["published_at"]:
                deduped[key] = article
        articles = sorted(deduped.values(), key=lambda row: row["published_at"], reverse=True)[:limit]
        reason = None
        if not articles:
            reason = "Konfiqurasiya edilmiş xəbər provider-lərindən etibarlı RSS nəticəsi gəlmədi"
        return {
            "articles": articles,
            "provider_errors": provider_errors,
            "module_errors": {"news": reason} if reason else {},
            "providers": list(self.providers),
            "available_providers": available,
            **data_meta(
                ", ".join(available) if available else "Configured RSS providers",
                error_reason=reason,
                fallback_used=bool(provider_errors) and bool(articles),
            ),
        }

    async def fetch_all(self) -> list:
        return (await self.fetch_with_status())["articles"]


news_service = NewsService()
