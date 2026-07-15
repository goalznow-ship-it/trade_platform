from datetime import datetime, timezone
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.services.backtest import backtest_service
from app.services.market import market_service
from app.core.security import get_current_user
from app.models.user import User
from app.models.portfolio import BacktestResult
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/backtest", tags=["Backtest"])

class SaveBacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"
    strategy_name: str = "Default"
    parameters: Optional[dict] = None

@router.get("/run")
async def run_backtest(
    symbol: str = Query(..., description="Symbol (use - instead of /)"),
    timeframe: str = "1h",
    limit: int = 500,
    initial_balance: float = 10000,
    leverage: int = 1,
    risk_per_trade: float = 0.02,
    user: User = Depends(get_current_user)
):
    sym = symbol.replace("-", "/")
    data = await market_service.get_ohlcv(sym, 'binance', timeframe, limit)
    if not data:
        return {"error": "No data available"}
    result = await backtest_service.run_backtest(
        symbol=sym, data=data, timeframe=timeframe,
        initial_balance=initial_balance, leverage=leverage,
        risk_per_trade=risk_per_trade,
    )
    return result


@router.post("/save")
async def save_backtest(
    req: SaveBacktestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sym = req.symbol.replace("-", "/")
    data = await market_service.get_ohlcv(sym, "binance", req.timeframe, 500)
    if not data:
        raise HTTPException(400, "No data available")
    result = await backtest_service.run_backtest(symbol=sym, data=data, timeframe=req.timeframe, leverage=3)
    if "error" in result:
        raise HTTPException(400, result["error"])

    bt = BacktestResult(
        user_id=user.id, symbol=sym, timeframe=req.timeframe,
        strategy_name=req.strategy_name, parameters=req.parameters or {},
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc),
        total_trades=result.get("total_trades", 0),
        win_rate=result.get("win_rate", 0),
        profit_factor=result.get("profit_factor", 0),
        sharpe_ratio=result.get("sharpe_ratio", 0),
        max_drawdown=result.get("max_drawdown_percent", 0),
        total_return=result.get("total_return", 0),
        avg_risk_reward=result.get("avg_risk_reward", 0),
        monthly_results=result.get("monthly_returns"),
    )
    db.add(bt)
    await db.commit()
    await db.refresh(bt)
    return {"message": "Backtest saved", "id": bt.id, "result": result}


@router.get("/history")
async def get_backtest_history(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BacktestResult).where(BacktestResult.user_id == user.id)
        .order_by(BacktestResult.created_at.desc()).limit(50)
    )
    return [
        {
            "id": b.id, "symbol": b.symbol, "timeframe": b.timeframe,
            "strategy_name": b.strategy_name, "total_trades": b.total_trades,
            "win_rate": b.win_rate, "profit_factor": b.profit_factor,
            "sharpe_ratio": b.sharpe_ratio, "max_drawdown": b.max_drawdown,
            "total_return": b.total_return, "avg_risk_reward": b.avg_risk_reward,
            "created_at": str(b.created_at),
        }
        for b in result.scalars().all()
    ]


@router.get("/history/{backtest_id}")
async def get_backtest_detail(
    backtest_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BacktestResult).where(BacktestResult.id == backtest_id, BacktestResult.user_id == user.id)
    )
    bt = result.scalar_one_or_none()
    if not bt:
        raise HTTPException(404, "Backtest not found")
    return {
        "id": bt.id, "symbol": bt.symbol, "timeframe": bt.timeframe,
        "strategy_name": bt.strategy_name, "parameters": bt.parameters,
        "total_trades": bt.total_trades, "win_rate": bt.win_rate,
        "profit_factor": bt.profit_factor, "sharpe_ratio": bt.sharpe_ratio,
        "max_drawdown": bt.max_drawdown, "total_return": bt.total_return,
        "avg_risk_reward": bt.avg_risk_reward,
        "start_date": str(bt.start_date) if bt.start_date else None,
        "end_date": str(bt.end_date) if bt.end_date else None,
        "created_at": str(bt.created_at),
    }


@router.delete("/history/{backtest_id}")
async def delete_backtest(
    backtest_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BacktestResult).where(BacktestResult.id == backtest_id, BacktestResult.user_id == user.id)
    )
    bt = result.scalar_one_or_none()
    if not bt:
        raise HTTPException(404, "Backtest not found")
    await db.delete(bt)
    await db.commit()
    return {"message": "Backtest deleted"}
