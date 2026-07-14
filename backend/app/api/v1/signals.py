"""Enhanced Signal API with lifecycle tracking"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.analysis import Signal
from app.ai_engine.engine import ai_engine
from app.core.logging import logger

router = APIRouter(prefix="/signals", tags=["Signals"])

@router.get("/{symbol}")
async def get_signal(
    symbol: str, timeframe: str = "1h",
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    signal = await ai_engine.generate_signal(symbol, timeframe)
    if not signal:
        raise HTTPException(503, "Unable to generate signal - data unavailable")
    return signal

@router.get("/generate/{symbol}")
async def generate_signal(
    symbol: str, timeframe: str = "1h",
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    signal = await ai_engine.generate_signal(symbol, timeframe)
    if not signal:
        raise HTTPException(503, "Unable to generate signal - data unavailable")
    return signal

@router.get("/scan")
async def scan_all(
    min_confidence: float = Query(50, ge=0, le=100),
    user: User = Depends(get_current_user)
):
    signals = await ai_engine.scan_all(min_confidence=min_confidence)
    return signals

@router.get("/history")
async def signal_history(
    symbol: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    q = select(Signal).where(Signal.symbol_id == user.id)
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
