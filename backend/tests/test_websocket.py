import pytest
import json
from fastapi.testclient import TestClient
from app.main import app


def test_websocket_stats():
    client = TestClient(app)
    resp = client.get("/ws/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_clients" in data
    assert "channel_subscriptions" in data


@pytest.mark.asyncio
async def test_websocket_connect():
    from fastapi import WebSocket
    from app.core.websocket_manager import ws_manager

    assert ws_manager.stats["total_clients"] >= 0
    channels = ws_manager.channel_subscriptions
    assert "market" in channels
    assert "ticker" in channels
    assert "orderbook" in channels
    assert "signals" in channels
    assert "trades" in channels
    assert "positions" in channels
    assert "portfolio" in channels
    assert "notifications" in channels
