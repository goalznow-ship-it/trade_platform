from fastapi import APIRouter
from app.services.news import news_service

router = APIRouter(prefix="/news", tags=["News"])

@router.get("/latest")
async def get_latest_news():
    return await news_service.fetch_all()
