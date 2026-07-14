from fastapi import APIRouter, Query
from app.services.indicators import indicator_service
from app.services.ai_analysis import ai_engine
from app.services.market import market_service

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def _fix_symbol(symbol: str) -> str:
    return symbol.replace("-", "/")


@router.get("/indicators/{symbol:path}")
async def get_indicators(symbol: str, timeframe: str = "1h", exchange: str = "binance"):
    symbol = _fix_symbol(symbol)
    data = await market_service.get_ohlcv(symbol, exchange, timeframe, 200)
    if not data:
        return {"error": "No data available"}
    return {
        "sma_20": indicator_service.sma(data, 20),
        "sma_50": indicator_service.sma(data, 50),
        "sma_200": indicator_service.sma(data, 200),
        "ema_12": indicator_service.ema(data, 12),
        "ema_26": indicator_service.ema(data, 26),
        "ema_50": indicator_service.ema(data, 50),
        "rsi": indicator_service.rsi(data),
        "macd": indicator_service.macd(data),
        "bollinger": indicator_service.bollinger(data),
        "adx": indicator_service.adx(data),
        "atr": indicator_service.atr(data),
        "supertrend": indicator_service.supertrend(data),
        "vwap": indicator_service.vwap(data),
        "obv": indicator_service.obv(data),
        "cmf": indicator_service.cmf(data),
        "stochastic_rsi": indicator_service.stochastic_rsi(data),
        "ichimoku": indicator_service.ichimoku(data),
        "volume_profile": indicator_service.volume_profile(data),
        "pivot_points": indicator_service.pivot_points(data),
        "last_price": data[-1]['close'] if data else None,
    }


@router.get("/ai/{symbol:path}")
async def get_ai_analysis(symbol: str, timeframe: str = "1h", exchange: str = "binance"):
    symbol = _fix_symbol(symbol)
    data = await market_service.get_ohlcv(symbol, exchange, timeframe, 200)
    if not data:
        return {"error": "No data available"}
    return await ai_engine.analyze(symbol, data, timeframe)


@router.get("/full/{symbol:path}")
async def get_full_analysis(symbol: str, timeframe: str = "1h", exchange: str = "binance"):
    symbol = _fix_symbol(symbol)
    data = await market_service.get_ohlcv(symbol, exchange, timeframe, 200)
    if not data:
        return {"error": "No data available"}
    indicators = {
        "sma_20": indicator_service.sma(data, 20),
        "sma_50": indicator_service.sma(data, 50),
        "ema_12": indicator_service.ema(data, 12),
        "ema_26": indicator_service.ema(data, 26),
        "rsi": indicator_service.rsi(data),
        "macd": indicator_service.macd(data),
        "bollinger": indicator_service.bollinger(data),
        "adx": indicator_service.adx(data),
        "atr": indicator_service.atr(data),
        "supertrend": indicator_service.supertrend(data),
        "stochastic_rsi": indicator_service.stochastic_rsi(data),
        "ichimoku": indicator_service.ichimoku(data),
    }
    ai = await ai_engine.analyze(symbol, data, timeframe)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "current_price": data[-1]['close'] if data else None,
        "indicators": indicators,
        "ai_analysis": ai,
    }
