from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.models.user import User
from app.services.auto_scalper import auto_scalper_service

router = APIRouter(prefix="/auto-scalper", tags=["Auto Scalper"])


class AutoScalperConfig(BaseModel):
    mode: str = Field(default="paper", pattern="^paper$")
    capital_usdt: float = Field(default=10, ge=5, le=10000)
    risk_per_trade_pct: float = Field(default=0.5, ge=0.1, le=2)
    daily_loss_limit_pct: float = Field(default=3, ge=0.5, le=10)
    max_positions: int = Field(default=1, ge=1, le=3)
    min_score: float = Field(default=82, ge=70, le=99)
    max_leverage: int = Field(default=3, ge=1, le=10)
    scan_interval_seconds: int = Field(default=20, ge=10, le=300)


@router.get("/status")
async def status(user: User = Depends(get_current_user)):
    return await auto_scalper_service.get_state(user.id)


@router.post("/scan")
async def scan(user: User = Depends(get_current_user)):
    return await auto_scalper_service.scan(user.id)


@router.post("/arm")
async def arm(config: AutoScalperConfig, user: User = Depends(get_current_user)):
    try:
        return await auto_scalper_service.arm(user.id, config.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.post("/disarm")
async def disarm(user: User = Depends(get_current_user)):
    return await auto_scalper_service.disarm(user.id)
