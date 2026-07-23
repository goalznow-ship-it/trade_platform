from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.bootstrap import ensure_default_admin
from app.core.database import async_session_factory, init_db
from app.core.logging import logger
from app.core.rate_limiter import RateLimitMiddleware
from app.core.security import AuditMiddleware
from app.core.websocket_manager import ws_manager
from app.api.v1 import auth, market, analysis, signals, trading, news, admin, scanner, backtest, portfolio
from app.api.v1 import performance as performance_router
from app.api.v1 import whales as whales_router
from app.api.v1 import watchlists as watchlists_router
from app.api.v1 import alerts as alerts_router
from app.api.v1 import risk as risk_router
from app.api.v1 import journal as journal_router
from app.api.v1 import paper_trading as paper_router
from app.api.v1 import notifications as notifications_router
from app.api.v1 import enterprise as enterprise_router
from app.api.v1 import institutional as institutional_router
from app.api.v1.websocket_v2 import router as ws_v2_router
from app.services.alert import alert_service
from app.services.binance_ws import binance_ws
from app.services.market_coverage import market_coverage
from app.services.streaming import streaming_service
from app.services.exchange.manager import exchange_manager
from app.services.paper_trading import paper_trading_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.redis import redis_client
    if settings.ENVIRONMENT.lower() != "production":
        await init_db()
    async with async_session_factory() as db:
        await ensure_default_admin(db)
    await ws_manager.start()
    if settings.ENABLE_BACKGROUND_SERVICES:
        await binance_ws.start()
        top_symbols = await market_coverage.get_top_symbols(30)
        await binance_ws.subscribe_price(top_symbols)
        await binance_ws.subscribe_klines(top_symbols[:10], "1m")
        await binance_ws.subscribe_depth(top_symbols[:5])
        await alert_service.start()
        await streaming_service.start()
        await exchange_manager.start_reconnect_loop("binance")
        await paper_trading_service.start_monitoring()
    try:
        await redis_client.ping()
        logger.info("Redis connected")
    except Exception:
        logger.warning("Redis not available")
    logger.info("Database initialized")
    logger.info(f"Server starting on port {settings.PORT}")
    yield
    if settings.ENABLE_BACKGROUND_SERVICES:
        await alert_service.stop()
        await streaming_service.stop()
        await paper_trading_service.stop_monitoring()
        await binance_ws.stop()
    await exchange_manager.shutdown()
    await ws_manager.stop()
    logger.info("Server shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url=None if settings.ENVIRONMENT.lower() == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT.lower() == "production" else "/redoc",
)

allowed_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials="*" not in allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=settings.RATE_LIMIT_MAX, window_seconds=settings.RATE_LIMIT_WINDOW)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(signals.router, prefix="/api/v1")
app.include_router(trading.router, prefix="/api/v1")
app.include_router(news.router, prefix="/api/v1")

app.include_router(performance_router.router, prefix="/api/v1")
app.include_router(whales_router.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(scanner.router, prefix="/api/v1")
app.include_router(backtest.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(watchlists_router.router, prefix="/api/v1")
app.include_router(alerts_router.router, prefix="/api/v1")
app.include_router(risk_router.router, prefix="/api/v1")
app.include_router(journal_router.router, prefix="/api/v1")
app.include_router(paper_router.router, prefix="/api/v1")
app.include_router(notifications_router.router, prefix="/api/v1")
app.include_router(enterprise_router.router, prefix="/api/v1")
app.include_router(institutional_router.router, prefix="")
app.include_router(ws_v2_router)


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "version": settings.VERSION, "status": "running"}


@app.get("/health")
async def health():
    from datetime import datetime, timezone
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG, workers=1)
