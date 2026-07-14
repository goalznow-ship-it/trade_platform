from fastapi import APIRouter, Query
from app.services.enterprise_signals import enterprise_signal_engine
from app.services.prediction import prediction_engine
from app.services.news_intelligence_v2 import news_intelligence_engine
from app.services.market import market_service
from app.services.scanner import scanner_service

router = APIRouter(prefix="/enterprise", tags=["Enterprise"])


def _fix_symbol(symbol: str) -> str:
    return symbol.replace("-", "/")


@router.get("/signal/{symbol:path}")
async def get_enterprise_signal(symbol: str, timeframe: str = "1h"):
    symbol = _fix_symbol(symbol)
    return await enterprise_signal_engine.generate_enterprise_signal(symbol, timeframe)


@router.get("/market-structure/{symbol:path}")
async def get_market_structure(symbol: str, timeframe: str = "1h"):
    symbol = _fix_symbol(symbol)
    data = await market_service.get_ohlcv(symbol, "binance", timeframe, 200)
    if not data:
        return {"error": "No data available"}
    return await enterprise_signal_engine.analyze_market_structure(data)


@router.get("/futures/{symbol:path}")
async def get_futures_analysis(symbol: str):
    symbol = _fix_symbol(symbol)
    return await enterprise_signal_engine.analyze_futures(symbol)


@router.get("/predict/{symbol:path}")
async def get_price_prediction(symbol: str, timeframe: str = "4h"):
    symbol = _fix_symbol(symbol)
    return await prediction_engine.predict(symbol, timeframe)


@router.get("/predict")
async def predict_all(timeframe: str = "4h", min_confidence: float = 0):
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "AVAX/USDT"]
    results = []
    for s in symbols:
        pred = await prediction_engine.predict(s, timeframe)
        if pred.get("confidence", 0) >= min_confidence:
            results.append(pred)
    results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return results


@router.get("/news-intelligence")
async def get_news_intelligence(limit: int = Query(default=20, le=50)):
    return await news_intelligence_engine.scan_all_news(limit)


@router.get("/futures-dashboard")
async def get_futures_dashboard():
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "AVAX/USDT", "DOGE/USDT"]
    results = []
    for s in symbols:
        try:
            signal = await enterprise_signal_engine.generate_enterprise_signal(s, "1h")
            futures = signal.get("futures", {})
            results.append({
                "symbol": s,
                "price": signal.get("current_price", 0),
                "direction": signal.get("direction", "neutral"),
                "confidence": signal.get("confidence", 0),
                "funding_rate": futures.get("funding_rate", 0),
                "funding_pressure": futures.get("funding_pressure", "neutral"),
                "long_probability": signal.get("long_probability", 50),
                "short_probability": signal.get("short_probability", 50),
            })
        except Exception:
            continue
    results.sort(key=lambda x: abs(x.get("funding_rate", 0)), reverse=True)
    return results


@router.get("/market-scan")
async def scan_market(timeframe: str = "1h"):
    return await scanner_service.scan_market(timeframe=timeframe)


@router.get("/top-opportunities")
async def top_opportunities(limit: int = Query(default=10, le=30)):
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "LINK/USDT"]
    results = []
    for s in symbols:
        try:
            sig = await enterprise_signal_engine.generate_enterprise_signal(s, "1h")
            if sig.get("confidence", 0) > 60 and sig.get("direction") != "neutral":
                results.append(sig)
        except Exception:
            continue
    results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return results[:limit]
