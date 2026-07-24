from fastapi import APIRouter
from app.services.news import news_service
from app.services.news_intelligence_v2 import news_intelligence_engine

router = APIRouter(prefix="/news", tags=["News"])

@router.get("/latest")
async def get_latest_news():
    return await news_service.fetch_all()


@router.get("/intelligence")
async def get_news_intelligence(limit: int = 50):
    return await news_intelligence_engine.scan_with_status(limit=min(max(limit, 1), 100))
