"""Whale Transaction Tracking API"""

from fastapi import APIRouter, Depends, Query
from app.core.security import require_subscription
from app.models.user import User
from app.services.whale import whale_tracker

router = APIRouter(prefix="/whales", tags=["Whales"])

@router.get("/recent")
async def recent_whales(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(require_subscription("elite"))
):
    return await whale_tracker.get_recent(limit)

@router.get("/alerts")
async def whale_alerts(
    hours: int = Query(24, ge=1, le=168),
    user: User = Depends(require_subscription("elite"))
):
    return await whale_tracker.get_alerts(hours)
