from datetime import datetime, timezone

from app.services.streaming import StreamingService


def test_worker_health_uses_worker_specific_intervals():
    service = StreamingService()
    now = datetime.now(timezone.utc).timestamp()
    service._running = True
    service._heartbeats = {
        "orderflow": now - 100,
        "onchain": now - 100,
    }

    stats = service.get_stats()

    assert stats["workers"]["orderflow"]["alive"] is False
    assert stats["workers"]["onchain"]["alive"] is True


def test_beat_refreshes_worker_timestamp():
    service = StreamingService()
    service._heartbeats["signals"] = 0

    service._beat("signals")

    assert service._heartbeats["signals"] > 0
