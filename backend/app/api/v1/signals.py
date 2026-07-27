"""Enhanced Signal API with lifecycle tracking & subscription limits"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limiter import daily_tracker
from app.models.user import User
from app.models.analysis import Signal
from app.models.market import Symbol as SymbolModel
from app.ai_engine.engine import ai_engine

router = APIRouter(prefix="/signals", tags=["Signals"])


async def _persist_signal(signal: dict, db: AsyncSession) -> None:
    direction = str(signal.get("direction", "")).lower()
    if direction not in {"long", "short"} or float(signal.get("confidence") or 0) < 50:
        return
    symbol = str(signal.get("symbol", ""))
    timeframe = str(signal.get("timeframe") or "1h")
    symbol_result = await db.execute(
        select(SymbolModel).where(SymbolModel.name == symbol)
    )
    symbol_row = symbol_result.scalar_one_or_none()
    if not symbol_row:
        from app.services.market_coverage import market_coverage

        covered = await market_coverage.get_top_symbols(30)
        if symbol not in covered:
            return
        base, _, quote = symbol.partition("/")
        symbol_row = SymbolModel(
            name=symbol,
            base_asset=base,
            quote_asset=quote or "USDT",
            exchange=market_coverage.get_symbol_exchange(symbol),
            asset_type="crypto",
            is_active=True,
            is_futures=True,
        )
        db.add(symbol_row)
        await db.flush()
    existing = await db.execute(
        select(Signal).where(
            Signal.symbol == symbol,
            Signal.timeframe == timeframe,
            Signal.direction == direction,
            Signal.is_active.is_(True),
        ).limit(1)
    )
    if existing.scalar_one_or_none():
        return
    targets = signal.get("take_profit") or []
    db.add(Signal(
        symbol_id=symbol_row.id,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        confidence=signal.get("confidence"),
        entry_price=signal.get("entry_price"),
        stop_loss=signal.get("stop_loss"),
        take_profit_1=targets[0] if len(targets) > 0 else None,
        take_profit_2=targets[1] if len(targets) > 1 else None,
        take_profit_3=targets[2] if len(targets) > 2 else None,
        risk_reward=signal.get("risk_reward"),
        reason=" | ".join(signal.get("reasons") or []),
        signal_type="ai_terminal",
        result="new",
        is_active=True,
        expires_at=(
            datetime.now(timezone.utc) + {
                "1m": timedelta(hours=2),
                "5m": timedelta(hours=8),
                "15m": timedelta(hours=18),
                "30m": timedelta(days=1),
                "1h": timedelta(days=3),
                "4h": timedelta(days=10),
                "1d": timedelta(days=30),
            }.get(timeframe, timedelta(days=3))
        ).replace(tzinfo=None),
    ))
    await db.commit()


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
    await _persist_signal(signal, db)
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
    await _persist_signal(signal, db)
    signal["remaining_daily"] = max(0, {"free": 3, "pro": 999999, "elite": 999999}.get(user.subscription_tier or "free", 3) - daily_tracker.daily_usage(user.id))
    return signal

@router.get("/scan")
async def scan_all(
    min_confidence: float = Query(50, ge=0, le=100),
    user: User = Depends(get_current_user)
):
    await _enforce_signal_limit(user)
    signals = await ai_engine.scan_all(min_confidence=min_confidence)
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
