import pytest
from app.services.scanner import scanner_service


@pytest.mark.asyncio
async def test_scan_market():
    results = await scanner_service.scan_market(symbols=["BTC/USDT", "ETH/USDT"])
    assert isinstance(results, list)
    for r in results:
        assert "symbol" in r
        assert "confidence" in r
