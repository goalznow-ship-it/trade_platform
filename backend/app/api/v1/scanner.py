from fastapi import APIRouter, Query
from app.services.scanner import scanner_service

router = APIRouter(prefix="/scanner", tags=["Scanner"])

@router.get("/market")
async def scan_market(timeframe: str = "1h"):
    return await scanner_service.scan_market(timeframe=timeframe)

@router.get("/top-signals")
async def top_signals(min_confidence: float = Query(default=70, ge=0, le=100)):
    return await scanner_service.scan_top_signals(min_confidence)
