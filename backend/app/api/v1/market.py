from fastapi import APIRouter, Query
from app.services.market import market_service
from app.core.cache import cache_get, cache_set

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/ohlcv/{symbol:path}")
async def get_ohlcv(symbol: str, exchange: str = "binance", timeframe: str = "1h", limit: int = 200):
    symbol = symbol.replace("-", "/")
    return await market_service.get_ohlcv(symbol, exchange, timeframe, limit)


@router.get("/ticker/{symbol:path}")
async def get_ticker(symbol: str, exchange: str = "binance"):
    symbol = symbol.replace("-", "/")
    return await market_service.get_ticker(symbol, exchange)


@router.get("/orderbook/{symbol:path}")
async def get_orderbook(symbol: str, exchange: str = "binance"):
    symbol = symbol.replace("-", "/")
    return await market_service.get_orderbook(symbol, exchange)


@router.get("/funding/{symbol:path}")
async def get_funding(symbol: str, exchange: str = "binance"):
    symbol = symbol.replace("-", "/")
    return await market_service.get_funding_rate(symbol, exchange)


@router.get("/open-interest/{symbol:path}")
async def get_open_interest(symbol: str, exchange: str = "binance"):
    symbol = symbol.replace("-", "/")
    return await market_service.get_open_interest(symbol, exchange)


@router.get("/overview")
async def get_overview():
    return await market_service.get_market_overview()


@router.get("/search")
async def search(q: str = Query(min_length=1)):
    return await market_service.search_symbols(q)


@router.get("/symbols")
async def get_symbols():
    cache_key = "market:symbols"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    from app.services.market_coverage import market_coverage
    top_symbols = await market_coverage.get_top_symbols(30)
    symbols = [
        {"symbol": s, "name": s.split("/")[0], "exchange": "binance"}
        for s in top_symbols
    ]
    await cache_set(cache_key, symbols, ttl=3600)
    return symbols


@router.get("/fear-greed")
async def get_fear_greed():
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.alternative.me/fng/?limit=1", timeout=10)
            data = resp.json()
            return data['data'][0]
    except Exception:
        return {"value": "50", "value_classification": "Neutral"}
