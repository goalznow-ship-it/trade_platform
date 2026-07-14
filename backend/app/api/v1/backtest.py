from fastapi import APIRouter, Query, Depends
from app.services.backtest import backtest_service
from app.services.market import market_service
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/backtest", tags=["Backtest"])

@router.get("/run")
async def run_backtest(
    symbol: str = Query(..., description="Symbol (use - instead of /)"),
    timeframe: str = "1h",
    limit: int = 500,
    initial_balance: float = 10000,
    leverage: int = 1,
    user: User = Depends(get_current_user)
):
    sym = symbol.replace("-", "/")
    data = await market_service.get_ohlcv(sym, 'binance', timeframe, limit)
    if not data:
        return {"error": "No data available"}
    return backtest_service.run_backtest(data, initial_balance, leverage=leverage)
