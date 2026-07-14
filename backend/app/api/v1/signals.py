from fastapi import APIRouter, Depends
from app.services.signals import signal_service
from app.services.market import market_service
from app.services.scanner import scanner_service
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/signals", tags=["Signals"])


def _fix_symbol(symbol: str) -> str:
    return symbol.replace("-", "/")


@router.get("/scanner/all")
async def scan_all(timeframe: str = "1h", min_confidence: float = 70):
    return await scanner_service.scan_top_signals(min_confidence)


@router.get("/scanner/{symbol:path}")
async def scan_symbol(symbol: str, timeframe: str = "1h"):
    symbol = _fix_symbol(symbol)
    return await scanner_service.scan_market([symbol], timeframe)


@router.get("/{symbol:path}")
async def get_signals(symbol: str, timeframe: str = "1h", exchange: str = "binance"):
    symbol = _fix_symbol(symbol)
    data = await market_service.get_ohlcv(symbol, exchange, timeframe, 200)
    if not data:
        return {"error": "No data available"}
    return await signal_service.generate_signals(symbol, data, timeframe)
