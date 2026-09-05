from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.portfolio import BacktestResult
from app.models.user import User
from app.services.backtest import backtest_service
from app.services.market import market_service

router = APIRouter(prefix="/backtest", tags=["Backtest"])

class SaveBacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"
    strategy_name: str = "Default"
    parameters: dict | None = None

@router.get("/run")
async def run_backtest(
    symbol: str = Query(..., description="Symbol (use - instead of /)"),
    timeframe: str = Query(default="1h", pattern="^(5m|15m|1h|4h|1d)$"),
    limit: int = Query(default=500, ge=120, le=1000),
    initial_balance: float = Query(default=10000, ge=100, le=100_000_000),
    leverage: int = Query(default=1, ge=1, le=125),
    risk_per_trade: float = Query(default=0.02, ge=0.001, le=0.1),
    fee_rate: float = Query(default=0.0004, ge=0, le=0.01),
    slippage_bps: float = Query(default=2.0, ge=0, le=100),
    mode: str = Query(default="balanced", pattern="^(strict|balanced|exploratory)$"),
    user: User = Depends(get_current_user)
):
    sym = symbol.replace("-", "/")
    data = await market_service.get_ohlcv(sym, 'binance', timeframe, limit)
    if not data:
        return {
            "error": "No data available",
            "error_reason": "provider xətası",
            "provider_status": "unavailable",
            "source": "Binance",
        }
    # Exchange OHLCV responses may contain the candle currently being formed.
    # Backtests only accept fully closed candles.
    closed_data = data[:-1]
    funding_rates = []
    provider_errors = {}
    try:
        binance_symbol = sym.replace("/", "")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://fapi.binance.com/fapi/v1/fundingRate",
                params={"symbol": binance_symbol, "limit": 1000},
            )
            response.raise_for_status()
            funding_rates = [
                {"time": int(row["fundingTime"] // 1000), "rate": float(row["fundingRate"])}
                for row in response.json()
            ]
    except Exception as exc:
        provider_errors["historical_funding"] = f"{type(exc).__name__}: {str(exc)[:240]}"
    result = await backtest_service.run_backtest(
        symbol=sym, data=closed_data, timeframe=timeframe,
        initial_balance=initial_balance, leverage=leverage,
        risk_per_trade=risk_per_trade, fee_rate=fee_rate,
        slippage_bps=slippage_bps, mode=mode, funding_rates=funding_rates,
    )
    result["provider_errors"] = provider_errors
    result["module_errors"] = dict(provider_errors)
    result["funding_accounted"] = bool(funding_rates)
    return result


# Cache for the expensive OOS walk-forward ML backtest. The
# walk-forward is deterministic given the data + hyperparameters,
# so caching for an hour across users is safe — they all see the
# same metrics for the same symbol set within the TTL window.
# Redis is the natural place for it (we already have a client);
# we keep the dict here so the import stays local and the test
# suite can monkeypatch it without touching the live cache.
_ml_backtest_cache: dict[str, tuple[float, dict]] = {}


def _ml_backtest_cache_get(key: str) -> dict | None:
    import time
    entry = _ml_backtest_cache.get(key)
    if not entry:
        return None
    expires_at, payload = entry
    if expires_at < time.time():
        _ml_backtest_cache.pop(key, None)
        return None
    return payload


def _ml_backtest_cache_set(key: str, payload: dict) -> None:
    import time
    _ml_backtest_cache[key] = (time.time() + settings.BACKTEST_ML_CACHE_TTL, payload)


@router.get("/ml")
async def run_ml_backtest(
    symbols: str = Query(
        default="BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,XRP/USDT",
        description="Comma-separated list of symbols (use - instead of /).",
    ),
    timeframe: str = Query(default="15m", pattern="^(5m|15m|1h|4h|1d)$"),
    n_splits: int = Query(default=4, ge=2, le=8),
    train_size: int = Query(default=2000, ge=500, le=10_000),
    test_size: int = Query(default=500, ge=100, le=5_000),
    user: User = Depends(get_current_user),
):
    """Out-of-sample walk-forward backtest for the ML ensemble.

    Phase 4 endpoint. Returns the OOS hit rate, in-sample hit
    rate, train/test gap, per-fold breakdown, cumulative
    return, and max drawdown for the configured symbol list.
    Cached for ``settings.BACKTEST_ML_CACHE_TTL`` seconds
    because a single walk-forward on 15 symbols can take a
    few minutes.
    """
    sym_list = [s.strip().replace("-", "/") for s in symbols.split(",") if s.strip()]
    if not sym_list:
        raise HTTPException(400, "symbols parameter must contain at least one symbol")

    cache_key = f"{','.join(sorted(sym_list))}|{timeframe}|{n_splits}|{train_size}|{test_size}"
    cached = _ml_backtest_cache_get(cache_key)
    if cached is not None:
        return {**cached, "cached": True, "cache_key": cache_key}

    from app.services.ml.training.oos_backtest import OOSBacktester

    backtester = OOSBacktester(
        n_splits=n_splits,
        train_size=train_size,
        test_size=test_size,
    )
    result = await backtester.run(symbols=sym_list, timeframe=timeframe)
    result["symbols"] = sym_list
    result["timeframe"] = timeframe
    if "error" not in result:
        _ml_backtest_cache_set(cache_key, result)
    return {**result, "cached": False, "cache_key": cache_key}


@router.post("/save")
async def save_backtest(
    req: SaveBacktestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sym = req.symbol.replace("-", "/")
    data = await market_service.get_ohlcv(sym, "binance", req.timeframe, 500)
    if len(data) < 2:
        raise HTTPException(400, "No data available")
    parameters = req.parameters or {}
    result = await backtest_service.run_backtest(
        symbol=sym,
        data=data[:-1],
        timeframe=req.timeframe,
        initial_balance=float(parameters.get("initial_balance", 10_000)),
        leverage=int(parameters.get("leverage", 1)),
        risk_per_trade=float(parameters.get("risk_per_trade", 0.02)),
        fee_rate=float(parameters.get("fee_rate", 0.0004)),
        slippage_bps=float(parameters.get("slippage_bps", 2.0)),
        mode=str(parameters.get("mode", "balanced")),
    )
    if "error" in result:
        raise HTTPException(400, result["error"])

    bt = BacktestResult(
        user_id=user.id, symbol=sym, timeframe=req.timeframe,
        strategy_name=req.strategy_name, parameters=parameters,
        start_date=datetime.fromtimestamp(data[0]["time"], tz=UTC).replace(tzinfo=None),
        end_date=datetime.fromtimestamp(data[-2]["time"], tz=UTC).replace(tzinfo=None),
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
