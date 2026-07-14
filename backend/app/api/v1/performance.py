"""AI Performance Tracking API"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.performance import performance_service

router = APIRouter(prefix="/performance", tags=["Performance"])

@router.get("/stats")
async def performance_stats(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await performance_service.get_stats(db, days)

@router.get("/accuracy")
async def accuracy_over_time(
    days: int = Query(90, ge=1, le=365),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await performance_service.accuracy_over_time(db, days)
