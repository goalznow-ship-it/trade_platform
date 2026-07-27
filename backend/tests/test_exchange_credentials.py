import pytest

from app.services.exchange.manager import exchange_manager


class FakeExchange:
    def __init__(self, connected: bool = True):
        self.connected = connected
        self.disconnected = False
        self.received = None

    async def connect(self, api_key, secret_key, passphrase=None):
        self.received = (api_key, secret_key, passphrase)
        return self.connected

    async def disconnect(self):
        self.disconnected = True


@pytest.mark.asyncio
async def test_credentials_are_verified_without_persisting(monkeypatch):
    client = FakeExchange(connected=True)
    monkeypatch.setitem(exchange_manager._exchange_factories, "test", lambda: client)

    result = await exchange_manager.test_credentials(
        "test", "api-key-value", "secret-value", "passphrase",
    )

    assert result is True
    assert client.received == ("api-key-value", "secret-value", "passphrase")
    assert client.disconnected is True


@pytest.mark.asyncio
async def test_failed_connection_is_disconnected(monkeypatch):
    client = FakeExchange(connected=False)
    monkeypatch.setitem(exchange_manager._exchange_factories, "test", lambda: client)

    result = await exchange_manager.test_credentials(
        "test", "bad-api-key", "bad-secret",
    )

    assert result is False
    assert client.disconnected is True


@pytest.mark.asyncio
async def test_unsupported_exchange_is_rejected():
    result = await exchange_manager.test_credentials(
        "unsupported", "api-key-value", "secret-value",
    )

    assert result is False
