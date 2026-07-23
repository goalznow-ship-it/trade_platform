import json
import asyncio
from typing import Optional
from celery import Celery
from app.core.config import settings
from app.core.database import async_session_factory
from app.services.market import market_service
from app.services.news import news_service
from app.services.indicators import indicator_service
from app.services.ai_analysis import ai_engine
from app.services.signals import signal_service
from app.services.notifications import notifications_service
from sqlalchemy import select
from datetime import datetime, timezone

celery_app = Celery(
    "trading_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_market_data(self, symbol: str, timeframe: str = "1h"):
    try:
        data = run_async(market_service.get_ohlcv(symbol, "binance", timeframe, 100))
        if not data or len(data) < 50:
            return {"symbol": symbol, "status": "insufficient_data", "error": f"Only {len(data) if data else 0} candles"}

        analysis = run_async(ai_engine.analyze(symbol, data, timeframe))
        signals = run_async(signal_service.generate_signals(symbol, data, timeframe))

        async def save_results():
            async with async_session_factory() as session:
                from app.models.analysis import AIAnalysis, Signal
                from app.models.market import Symbol as SymbolModel
                result = await session.execute(select(SymbolModel).where(SymbolModel.name == symbol))
                sym = result.scalar_one_or_none()
                sym_id = sym.id if sym else None

                ai_record = AIAnalysis(
                    symbol_id=sym_id, symbol=symbol, timeframe=timeframe,
                    trend_score=analysis.get("scores", {}).get("trend"),
                    momentum_score=analysis.get("scores", {}).get("momentum"),
                    volume_score=analysis.get("scores", {}).get("volume"),
                    volatility_score=analysis.get("scores", {}).get("volatility"),
                    market_structure_score=analysis.get("scores", {}).get("market_structure"),
                    smc_score=analysis.get("scores", {}).get("smc"),
                    news_sentiment_score=analysis.get("scores", {}).get("news_sentiment"),
                    fear_greed_score=analysis.get("scores", {}).get("fear_greed"),
                    overall_score=analysis.get("overall_score"),
                    confidence=analysis.get("confidence"),
                    risk_level=analysis.get("risk_level"),
                    prediction=analysis.get("prediction"),
                    long_probability=analysis.get("long_probability"),
                    short_probability=analysis.get("short_probability"),
                    summary=analysis.get("summary"),
                    details=analysis.get("details"),
                )
                session.add(ai_record)

                for sig in signals.get("signals", []):
                    signal_record = Signal(
                        symbol_id=sym_id, symbol=symbol, timeframe=timeframe,
                        direction=sig.get("direction"), confidence=sig.get("confidence"),
                        risk_score=sig.get("risk_score"), probability=sig.get("probability"),
                        entry_price=sig.get("entry_price"), stop_loss=sig.get("stop_loss"),
                        take_profit_1=sig.get("take_profit_1"),
                        take_profit_2=sig.get("take_profit_2"),
                        take_profit_3=sig.get("take_profit_3"),
                        risk_reward=sig.get("risk_reward"), leverage=sig.get("leverage", 1),
                        reason=sig.get("reason"), ai_summary=sig.get("ai_summary"),
                        signal_type=sig.get("signal_type"), is_active=True,
                    )
                    session.add(signal_record)
                await session.commit()

        run_async(save_results())
        return {"symbol": symbol, "status": "success", "confidence": analysis.get("confidence")}
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_signal_notification(self, signal_id: int):
    try:
        async def get_and_send():
            async with async_session_factory() as session:
                from app.models.analysis import Signal
                from app.models.user import User
                result = await session.execute(select(Signal).where(Signal.id == signal_id))
                signal = result.scalar_one_or_none()
                if not signal:
                    return {"error": "Signal not found", "signal_id": signal_id}

                users_result = await session.execute(
                    select(User).where(User.is_active == True)
                )
                users = users_result.scalars().all()

                signal_data = {
                    "symbol": signal.symbol,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit_1": signal.take_profit_1,
                    "take_profit_2": signal.take_profit_2,
                    "risk_reward": signal.risk_reward,
                    "leverage": signal.leverage,
                    "reason": signal.reason,
                }

                sent_count = 0
                for user in users:
                    channels = []
                    if user.telegram_id:
                        channels.append("telegram")
                    if user.discord_id:
                        channels.append("discord")
                    if channels:
                        await notifications_service.send_signal_alert(user.id, signal_data)
                        sent_count += 1
                return {"signal_id": signal_id, "users_notified": sent_count}

        return run_async(get_and_send())
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def collect_news(self):
    try:
        articles = run_async(news_service.fetch_all())

        async def save_news():
            async with async_session_factory() as session:
                from app.models.news import News, NewsAnalysis
                saved = 0
                for article in articles:
                    existing = await session.execute(
                        select(News).where(News.url == article.get("url", ""))
                    )
                    if existing.scalar_one_or_none():
                        continue

                    news_record = News(
                        title=article.get("title", ""),
                        url=article.get("url", ""),
                        source=article.get("source", ""),
                        category=article.get("category", "crypto"),
                        summary=article.get("summary", ""),
                        published_at=datetime.fromisoformat(article.get("published_at", datetime.now(timezone.utc).isoformat())),
                        is_analyzed=True,
                    )
                    session.add(news_record)
                    await session.flush()

                    analysis = NewsAnalysis(
                        news_id=news_record.id,
                        sentiment=article.get("sentiment", "neutral"),
                        sentiment_score=article.get("sentiment_score", 0.0),
                        impact_score=article.get("impact_score", 0.0),
                        market_impact=article.get("market_impact", "neutral"),
                    )
                    session.add(analysis)
                    saved += 1
                await session.commit()
                return {"total": len(articles), "new_saved": saved}

        return run_async(save_news())
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def update_market_data(self):
    try:
        symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
                    "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
                    "SUI/USDT", "ATOM/USDT", "UNI/USDT", "ARB/USDT", "OP/USDT",
                    "INJ/USDT", "SEI/USDT", "APT/USDT", "NEAR/USDT", "FIL/USDT"]

        async def update():
            async with async_session_factory() as session:
                from app.models.market import Ticker
                updated = 0
                for symbol in symbols:
                    try:
                        ticker = await market_service.get_ticker(symbol)
                        if ticker:
                            existing = await session.execute(
                                select(Ticker).where(Ticker.symbol == symbol)
                            )
                            ticker_record = existing.scalar_one_or_none()
                            if ticker_record:
                                ticker_record.price = ticker.get("price")
                                ticker_record.price_change_24h = ticker.get("change_24h")
                                ticker_record.price_change_percent_24h = ticker.get("change_percent")
                                ticker_record.high_24h = ticker.get("high_24h")
                                ticker_record.low_24h = ticker.get("low_24h")
                                ticker_record.volume_24h = ticker.get("volume_24h")
                            else:
                                ticker_record = Ticker(
                                    symbol=symbol,
                                    price=ticker.get("price"),
                                    price_change_24h=ticker.get("change_24h"),
                                    price_change_percent_24h=ticker.get("change_percent"),
                                    high_24h=ticker.get("high_24h"),
                                    low_24h=ticker.get("low_24h"),
                                    volume_24h=ticker.get("volume_24h"),
                                )
                                session.add(ticker_record)
                            updated += 1
                    except Exception:
                        continue
                await session.commit()
                return {"symbols_updated": updated}

        return run_async(update())
    except Exception as exc:
        self.retry(exc=exc)
