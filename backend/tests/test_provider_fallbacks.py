from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_news_uses_last_valid_real_cache_when_all_feeds_fail(monkeypatch):
    from app.services.news import NewsService

    service = NewsService()
    monkeypatch.setattr(
        service,
        "_fetch_provider",
        AsyncMock(side_effect=RuntimeError("feed unavailable")),
    )
    monkeypatch.setattr(
        "app.services.news.cache_get",
        AsyncMock(return_value={
            "articles": [{"id": "real-1", "title": "Cached real article"}],
            "saved_at": "2026-07-27T00:00:00+00:00",
        }),
    )

    result = await service.fetch_with_status()

    assert result["articles"][0]["id"] == "real-1"
    assert result["fallback_used"] is True
    assert result["source"] == "Last valid real RSS cache"


@pytest.mark.asyncio
async def test_news_saves_successful_real_result(monkeypatch):
    from app.services.news import NewsService

    service = NewsService()
    article = {
        "id": "real-2",
        "title": "Live real article",
        "published_at": "2026-07-27T00:00:00+00:00",
    }
    monkeypatch.setattr(service, "_fetch_provider", AsyncMock(return_value=[article]))
    cache_set = AsyncMock()
    monkeypatch.setattr("app.services.news.cache_set", cache_set)

    result = await service.fetch_with_status()

    assert result["articles"][0]["id"] == "real-2"
    cache_set.assert_awaited_once()


def test_macro_uses_last_valid_value_while_circuit_is_open(monkeypatch):
    from app.services.macro_engine import MacroEngine

    engine = MacroEngine()
    engine._last_valid["dxy"] = {
        "available": True,
        "symbol": "DX-Y.NYB",
        "value": 100.5,
        "timestamp": "2026-07-27T00:00:00+00:00",
        "last_updated": "2026-07-27T00:00:00+00:00",
    }
    monkeypatch.setattr(
        "app.services.macro_engine.provider_health.allow_request",
        lambda provider: False,
    )

    result = engine.get_dxy()

    assert result["available"] is True
    assert result["value"] == 100.5
    assert result["fallback_used"] is True
    assert result["provider_error"] == "Provider circuit breaker is open"
