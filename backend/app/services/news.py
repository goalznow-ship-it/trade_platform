"""Configurable, provider-isolated real news ingestion."""

import asyncio
import hashlib
import os
from datetime import UTC
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

from app.core.cache import cache_get, cache_set
from app.core.logging import logger
from app.core.provider_health import provider_health
from app.services.data_contract import data_meta, utc_now


class NewsService:
    LAST_VALID_CACHE_KEY = "news:last_valid:v1"
    DEFAULT_RSS_PROVIDERS = {
        "Cointelegraph": "https://cointelegraph.com/rss",
        "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "Decrypt": "https://decrypt.co/feed",
    }

    def __init__(self) -> None:
        configured = os.getenv("NEWS_RSS_PROVIDERS", "").strip()
        self.providers = dict(self.DEFAULT_RSS_PROVIDERS)
        if configured:
            self.providers = {
                name.strip(): url.strip()
                for pair in configured.split(",")
                if "=" in pair
                for name, url in [pair.split("=", 1)]
            }
        for name in self.providers:
            provider_health.configure(self._health_key(name), True)

    @staticmethod
    def _health_key(source: str) -> str:
        return f"news_rss_{source.lower().replace(' ', '_')}"

    async def _fetch_provider(self, source: str, url: str) -> list[dict]:
        key = self._health_key(source)
        if not provider_health.allow_request(key):
            raise RuntimeError("Provider circuit breaker is open")
        try:
            rows = await self._fetch_feed(source, url)
            provider_health.success(key)
            return rows
        except Exception as exc:
            provider_health.failure(key, exc)
            raise

    async def _fetch_feed(self, source: str, url: str) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; TradeAnalystPro/1.0; +https://localhost)",
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        }
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
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
                published = parsedate_to_datetime(published_raw).astimezone(UTC).isoformat()
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
        tasks = [self._fetch_provider(name, url) for name, url in self.providers.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        provider_errors = {}
        available = []
        all_news = []
        for (name, _), result in zip(self.providers.items(), results, strict=False):
            if isinstance(result, Exception):
                provider_errors[name] = f"{type(result).__name__}: {str(result)[:240]}"
                logger.warning("News provider %s failed: %s", name, result)
            else:
                available.append(name)
                all_news.extend(result)

        deduped = {}
        for article in all_news:
            key = "".join(ch for ch in article["title"].lower() if ch.isalnum())[:180]
            current = deduped.get(key)
            if not current or article["published_at"] > current["published_at"]:
                deduped[key] = article
        articles = sorted(
            deduped.values(),
            key=lambda row: row["published_at"],
            reverse=True,
        )[:limit]

        if articles:
            saved_at = utc_now()
            await cache_set(
                self.LAST_VALID_CACHE_KEY,
                {"articles": articles, "saved_at": saved_at},
                ttl=86_400,
            )
            return {
                "articles": articles,
                "provider_errors": provider_errors,
                "module_errors": {},
                "providers": list(self.providers),
                "available_providers": available,
                **data_meta(
                    ", ".join(available),
                    last_updated=saved_at,
                    fallback_used=bool(provider_errors),
                    max_age_seconds=300,
                ),
            }

        reason = "Configured RSS providers returned no reliable articles"
        cached = await cache_get(self.LAST_VALID_CACHE_KEY)
        if isinstance(cached, dict) and cached.get("articles"):
            return {
                "articles": cached["articles"][:limit],
                "provider_errors": provider_errors,
                "module_errors": {"news": reason},
                "providers": list(self.providers),
                "available_providers": [],
                **data_meta(
                    "Last valid real RSS cache",
                    last_updated=cached.get("saved_at"),
                    max_age_seconds=900,
                    fallback_used=True,
                ),
            }

        return {
            "articles": [],
            "provider_errors": provider_errors,
            "module_errors": {"news": reason},
            "providers": list(self.providers),
            "available_providers": [],
            **data_meta("Configured RSS providers", error_reason=reason),
        }

    async def fetch_all(self) -> list:
        return (await self.fetch_with_status())["articles"]


news_service = NewsService()
