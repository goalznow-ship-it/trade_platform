from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import redis_client
from app.core.security import get_current_user
from app.models.exchange import ExchangeCredentials
from app.models.user import User
from app.services.auto_scalper import auto_scalper_service

router = APIRouter(prefix="/auto-scalper", tags=["Auto Scalper"])


class AutoScalperConfig(BaseModel):
    mode: str = Field(default="paper", pattern="^(paper|live)$")
    capital_usdt: float = Field(default=10, ge=5, le=10000)
    risk_per_trade_pct: float = Field(default=0.5, ge=0.1, le=2)
    daily_loss_limit_pct: float = Field(default=3, ge=0.5, le=10)
    max_positions: int = Field(default=1, ge=1, le=3)
    min_score: float = Field(default=82, ge=70, le=99)
    max_leverage: int = Field(default=3, ge=1, le=10)
    scan_interval_seconds: int = Field(default=20, ge=10, le=300)
    live_confirmation: str | None = Field(default=None, max_length=40)

class SoakTestRequest(BaseModel):
    duration_hours: int = Field(default=72, ge=24, le=168)
    capital_usdt: float = Field(default=10, ge=5, le=10000)
    risk_per_trade_pct: float = Field(default=0.5, ge=0.1, le=2)
    min_score: float = Field(default=82, ge=70, le=99)


@router.get("/status")
async def status(user: User = Depends(get_current_user)):
    return await auto_scalper_service.get_state(user.id)


@router.post("/scan")
async def scan(user: User = Depends(get_current_user)):
    return await auto_scalper_service.scan(user.id)


@router.post("/arm")
async def arm(
    config: AutoScalperConfig,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = config.model_dump()
        if config.mode == "live":
            if config.live_confirmation != "REAL PULLA AUTO TRADE":
                raise HTTPException(422, "Live ARM confirmation phrase is invalid")
            if not settings.TRADING_ENABLED:
                raise HTTPException(503, "Live trading is disabled by server configuration")
            if await redis_client.get("trading:kill_switch") == "1":
                raise HTTPException(503, "Emergency trading kill switch is active")
            credentials = await db.execute(
                select(ExchangeCredentials.id).where(
                    ExchangeCredentials.user_id == user.id,
                    ExchangeCredentials.exchange == "binance",
                    ExchangeCredentials.is_active == True,
                )
            )
            if credentials.scalar_one_or_none() is None:
                raise HTTPException(400, "Active Binance API connection is required")
        data.pop("live_confirmation", None)
        return await auto_scalper_service.arm(user.id, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.post("/disarm")
async def disarm(user: User = Depends(get_current_user)):
    return await auto_scalper_service.disarm(user.id)

@router.get("/soak/status")
async def soak_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await auto_scalper_service.get_soak_status(user.id, db)

@router.post("/soak/start")
async def start_soak(
    request: SoakTestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await auto_scalper_service.start_soak(
            user.id,
            request.duration_hours,
            {
                "capital_usdt": request.capital_usdt,
                "risk_per_trade_pct": request.risk_per_trade_pct,
                "min_score": request.min_score,
            },
            db,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc))

@router.post("/soak/stop")
async def stop_soak(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await auto_scalper_service.stop_soak(user.id, db)
