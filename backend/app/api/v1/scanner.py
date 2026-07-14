from fastapi import APIRouter, Depends, Query
from app.core.security import get_current_user
from app.models.user import User
from app.services.scanner import scanner_service

router = APIRouter(prefix="/scanner", tags=["Scanner"])

@router.get("/market")
async def scan_market(
    timeframe: str = "1h",
    user: User = Depends(get_current_user),
):
    return await scanner_service.scan_market(timeframe=timeframe)

@router.get("/top-signals")
async def top_signals(
    min_confidence: float = Query(default=70, ge=0, le=100),
    user: User = Depends(get_current_user),
):
    return await scanner_service.scan_top_signals(min_confidence)
