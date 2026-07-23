"""Enhanced Signal API with lifecycle tracking & subscription limits"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limiter import daily_tracker
from app.models.user import User
from app.models.analysis import Signal
from app.ai_engine.engine import ai_engine

router = APIRouter(prefix="/signals", tags=["Signals"])


async def _enforce_signal_limit(user: User):
    tier = user.subscription_tier or "free"
    limits = {"free": 3, "pro": 999999, "elite": 999999}
    daily_max = limits.get(tier, 3)
    allowed, remaining = daily_tracker.check(user.id, daily_max)
    if not allowed:
        used = daily_tracker.daily_usage(user.id)
        raise HTTPException(
            429,
            f"Daily signal limit reached ({used}/{daily_max}). Upgrade to Pro for unlimited signals.",
        )
    return remaining


async def get_signal(
    symbol: str, timeframe: str = "1h",
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await _enforce_signal_limit(user)
    signal = await ai_engine.generate_signal(symbol, timeframe)
    if not signal:
        raise HTTPException(503, "Unable to generate signal - data unavailable")
    signal["remaining_daily"] = max(0, {"free": 3, "pro": 999999, "elite": 999999}.get(user.subscription_tier or "free", 3) - daily_tracker.daily_usage(user.id))
    return signal

@router.get("/generate/{symbol}")
async def generate_signal(
    symbol: str, timeframe: str = "1h",
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await _enforce_signal_limit(user)
    signal = await ai_engine.generate_signal(symbol, timeframe)
    if not signal:
        raise HTTPException(503, "Unable to generate signal - data unavailable")
    signal["remaining_daily"] = max(0, {"free": 3, "pro": 999999, "elite": 999999}.get(user.subscription_tier or "free", 3) - daily_tracker.daily_usage(user.id))
    return signal

@router.get("/scan")
async def scan_all(
    min_confidence: float = Query(50, ge=0, le=100),
    user: User = Depends(get_current_user)
):
    await _enforce_signal_limit(user)
    signals = await ai_engine.scan_all(min_confidence=min_confidence)
    signals["remaining_daily"] = max(0, {"free": 3, "pro": 999999, "elite": 999999}.get(user.subscription_tier or "free", 3) - daily_tracker.daily_usage(user.id))
    return signals

@router.get("/history")
async def signal_history(
    symbol: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    q = select(Signal)
    if symbol:
        q = q.where(Signal.symbol == symbol)
    q = q.order_by(Signal.created_at.desc()).limit(limit)
    result = await db.execute(q)
    signals = result.scalars().all()
    return [{
        "id": s.id, "symbol": s.symbol, "direction": s.direction,
        "confidence": s.confidence, "entry_price": s.entry_price,
        "stop_loss": s.stop_loss, "take_profit_1": s.take_profit_1,
        "risk_reward": s.risk_reward, "reason": s.reason,
        "result": getattr(s, 'result', None),
        "created_at": str(s.created_at),
    } for s in signals]


@router.get("/{symbol}")
async def get_signal_legacy(
    symbol: str,
    timeframe: str = "1h",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_signal(symbol, timeframe, user, db)
