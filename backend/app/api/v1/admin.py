import os, psutil
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import require_admin
from app.core.websocket_manager import ws_manager
from app.models.user import User
from app.models.analysis import Signal, AIAnalysis
from app.models.trade import Trade
from app.models.market import Symbol
from app.models.admin import AuditLog, Subscription, Subscription

router = APIRouter(prefix="/admin", tags=["Admin"])

class UserUpdate(BaseModel):
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    subscription_tier: Optional[str] = None

class SymbolCreate(BaseModel):
    name: str
    exchange: str = "binance"
    asset_type: str = "crypto"

# System Health
@router.get("/health")
async def system_health(admin: User = Depends(require_admin)):
    from app.core.redis import redis_client
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {},
    }
    try:
        await redis_client.ping()
        health["services"]["redis"] = "connected"
    except Exception:
        health["services"]["redis"] = "disconnected"
        health["status"] = "degraded"
    try:
        async with get_db() as session:
            await session.execute(text("SELECT 1"))
            health["services"]["postgres"] = "connected"
    except Exception:
        health["services"]["postgres"] = "disconnected"
        health["status"] = "degraded"
    health["services"]["websocket"] = f"{ws_manager.stats['total_clients']} clients"
    return health


@router.get("/system")
async def system_info(admin: User = Depends(require_admin)):
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "total": psutil.disk_usage("/").total,
            "used": psutil.disk_usage("/").used,
            "free": psutil.disk_usage("/").free,
            "percent": psutil.disk_usage("/").percent,
        },
        "process": {
            "pid": os.getpid(),
            "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "cpu_percent": psutil.Process().cpu_percent(interval=0.1),
        },
        "python_version": __import__("sys").version,
        "platform": os.uname().sysname,
    }


@router.get("/ws-clients")
async def ws_clients(admin: User = Depends(require_admin)):
    return ws_manager.stats


# Dashboard Stats
@router.get("/stats")
async def get_stats(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active == True))
    total_signals = await db.scalar(select(func.count(Signal.id)))
    active_signals = await db.scalar(select(func.count(Signal.id)).where(Signal.is_active == True))
    total_symbols = await db.scalar(select(func.count(Symbol.id)))
    total_trades = await db.scalar(select(func.count(Trade.id)))

    return {
        "total_users": total_users or 0,
        "active_users": active_users or 0,
        "total_signals": total_signals or 0,
        "active_signals": active_signals or 0,
        "total_symbols": total_symbols or 0,
        "total_trades": total_trades or 0,
    }

# Users
@router.get("/users")
async def list_users(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{
        "id": u.id, "username": u.username, "email": u.email,
        "is_admin": u.is_admin, "is_active": u.is_active,
        "subscription_tier": u.subscription_tier,
        "total_trades": u.total_trades, "win_rate": u.win_rate,
        "created_at": str(u.created_at),
    } for u in users]

@router.put("/users/{user_id}")
async def update_user(user_id: int, update: UserUpdate,
                      admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    if update.is_admin is not None:
        user.is_admin = update.is_admin
    if update.is_active is not None:
        user.is_active = update.is_active
    if update.subscription_tier is not None:
        user.subscription_tier = update.subscription_tier
    await db.commit()
    return {"message": "User updated"}

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}

# Symbols
@router.get("/symbols")
async def list_symbols(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Symbol))
    symbols = result.scalars().all()
    return [{"id": s.id, "name": s.name, "exchange": s.exchange, "asset_type": s.asset_type, "is_active": s.is_active} for s in symbols]

@router.post("/symbols")
async def add_symbol(req: SymbolCreate, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Symbol).where(Symbol.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Symbol already exists")
    symbol = Symbol(name=req.name, exchange=req.exchange, asset_type=req.asset_type)
    db.add(symbol)
    await db.commit()
    return {"message": "Symbol added", "id": symbol.id}

@router.delete("/symbols/{symbol_id}")
async def delete_symbol(symbol_id: int, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Symbol).where(Symbol.id == symbol_id))
    symbol = result.scalar_one_or_none()
    if not symbol:
        raise HTTPException(404, "Symbol not found")
    await db.delete(symbol)
    await db.commit()
    return {"message": "Symbol deleted"}

# Signals
@router.get("/signals")
async def list_signals(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Signal).order_by(Signal.created_at.desc()).limit(100))
    signals = result.scalars().all()
    return [{
        "id": s.id, "symbol": s.symbol, "direction": s.direction,
        "confidence": s.confidence, "entry_price": s.entry_price,
        "reason": s.reason, "is_active": s.is_active,
        "created_at": str(s.created_at),
    } for s in signals]

@router.delete("/signals/{signal_id}")
async def delete_signal(signal_id: int, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Signal).where(Signal.id == signal_id))
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(404, "Signal not found")
    await db.delete(signal)
    await db.commit()
    return {"message": "Signal deleted"}

# Subscriptions
@router.get("/subscriptions")
async def list_subscriptions(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscription))
    subs = result.scalars().all()
    return [{
        "id": s.id, "user_id": s.user_id, "tier": s.tier, "price": s.price,
        "signals_per_day": s.signals_per_day, "max_watchlist": s.max_watchlist,
        "has_backtest": s.has_backtest, "has_api_access": s.has_api_access,
        "start_date": str(s.start_date) if s.start_date else None,
        "end_date": str(s.end_date) if s.end_date else None,
        "is_active": s.is_active,
    } for s in subs]

@router.get("/revenue")
async def revenue_stats(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.sum(Subscription.price)).where(Subscription.is_active == True))
    total_revenue = result.scalar() or 0
    result = await db.execute(
        select(func.count(Subscription.id)).where(Subscription.is_active == True, Subscription.tier != "free")
    )
    paid_subs = result.scalar() or 0
    result = await db.execute(
        select(Subscription.tier, func.count(Subscription.id)).where(Subscription.is_active == True).group_by(Subscription.tier)
    )
    tier_breakdown = {row[0]: row[1] for row in result.all()}
    return {
        "total_revenue": total_revenue,
        "paid_subscriptions": paid_subs,
        "tier_breakdown": tier_breakdown,
        "monthly_recurring": paid_subs * 29 if paid_subs > 0 else 0,
    }

# AI Brain Monitoring
@router.get("/brain/status")
async def brain_status(admin: User = Depends(require_admin)):
    from app.services.brain import ai_brain
    return {
        "available": True,
        "cache_size": len(ai_brain._assessment_cache),
        "cache_ttl_seconds": ai_brain._cache_ttl_seconds,
        "weights": {
            "technical": ai_brain.TECHNICAL_WEIGHT,
            "smc": ai_brain.SMC_WEIGHT,
            "orderflow": ai_brain.ORDERFLOW_WEIGHT,
            "derivatives": ai_brain.DERIVATIVES_WEIGHT,
            "macro": ai_brain.MACRO_WEIGHT,
            "onchain": ai_brain.ONCHAIN_WEIGHT,
            "sentiment": ai_brain.SENTIMENT_WEIGHT,
            "whale": ai_brain.WHALE_WEIGHT,
            "risk": ai_brain.RISK_WEIGHT,
        },
    }


@router.get("/brain/engines")
async def brain_engines(admin: User = Depends(require_admin)):
    from app.services.brain import (
        orderflow_engine, derivatives_engine, smc_engine,
        institutional_scorer, multi_timeframe_engine, market_coverage,
        macro_engine, onchain_engine, social_sentiment, whale_tracker,
    )
    return {
        "engines": {
            "orderflow": orderflow_engine is not None,
            "derivatives": derivatives_engine is not None,
            "smc": smc_engine is not None,
            "institutional_scorer": institutional_scorer is not None,
            "multi_timeframe": multi_timeframe_engine is not None,
            "market_coverage": market_coverage is not None,
            "macro": macro_engine is not None,
            "onchain": onchain_engine is not None,
            "social_sentiment": social_sentiment is not None,
            "whale_tracker": whale_tracker is not None,
        },
        "loaded_count": sum(1 for v in [
            orderflow_engine, derivatives_engine, smc_engine,
            institutional_scorer, multi_timeframe_engine, market_coverage,
            macro_engine, onchain_engine, social_sentiment, whale_tracker,
        ] if v is not None),
        "total_engines": 10,
    }


@router.get("/brain/assessment")
async def brain_assessment(
    symbol: str = "BTCUSDT",
    admin: User = Depends(require_admin),
):
    from app.services.brain import ai_brain
    assessment = await ai_brain.assess_market(symbol)
    return assessment


@router.get("/brain/self-learning")
async def brain_self_learning(admin: User = Depends(require_admin)):
    from app.services.self_learning import self_learning
    report = self_learning.get_learning_report()
    return report


@router.get("/brain/system")
async def brain_system(admin: User = Depends(require_admin)):
    from app.services.streaming import streaming_service
    ws_stats = ws_manager.stats
    stream_stats = streaming_service.get_stats()
    return {
        "websocket": ws_stats,
        "streaming": stream_stats,
    }


# Audit Logs
@router.get("/logs")
async def get_logs(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100))
    logs = result.scalars().all()
    return [{"id": l.id, "user_id": l.user_id, "action": l.action, "resource": l.resource, "details": l.details, "ip_address": l.ip_address, "created_at": str(l.created_at)} for l in logs]
