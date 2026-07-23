from app.core.provider_health import ProviderHealthRegistry


def test_circuit_opens_and_recovers(monkeypatch):
    clock = [10.0]
    monkeypatch.setattr("app.core.provider_health.time.monotonic", lambda: clock[0])
    registry = ProviderHealthRegistry(failure_threshold=2, recovery_seconds=30)
    registry.configure("provider", True)

    assert registry.allow_request("provider")
    registry.failure("provider", "first")
    assert registry.allow_request("provider")
    registry.failure("provider", "second")
    assert not registry.allow_request("provider")
    assert registry.snapshot()["provider"]["status"] == "circuit_open"

    clock[0] = 41.0
    assert registry.allow_request("provider")
    registry.success("provider")
    assert registry.snapshot()["provider"]["status"] == "healthy"


def test_unconfigured_provider_is_not_called():
    registry = ProviderHealthRegistry()
    registry.configure("provider", False)
    assert not registry.allow_request("provider")
    assert registry.snapshot()["provider"]["status"] == "not_configured"
