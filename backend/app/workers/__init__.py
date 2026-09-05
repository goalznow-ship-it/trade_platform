import asyncio
import json  # noqa: F401
import logging
from datetime import UTC, datetime, timezone  # noqa: F401
from typing import Optional  # noqa: F401

from celery import Celery
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.services.ai_analysis import ai_engine
from app.services.indicators import indicator_service  # noqa: F401
from app.services.market import market_service
from app.services.news import news_service
from app.services.notifications import notifications_service
from app.services.signal_outcome import signal_outcome_resolver
from app.services.signal_pipeline import signal_pipeline
from app.services.signals import signal_service

from app.core.celery_beat_schedule import load_beat_schedule

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
    # ML retrain is a long, multi-CPU job — don't time it out at
    # the broker level. The task itself can take 10–30 minutes on
    # 30 symbols with the Transformer included.
    task_time_limit=3600,
    task_soft_time_limit=3300,
    # Phase 4: the central beat schedule — see
    # ``app/core/celery_beat_schedule.py`` for the cron strings
    # and per-task rationale.
    beat_schedule=load_beat_schedule(),
)


# Reuse a long-lived event loop per worker process instead of
# spinning a new one for every task. Spinning a new loop leaks
# asyncpg connection pools because the engine binds to whatever
# loop first touches it; the old loop's pool becomes orphaned.
_loop: asyncio.AbstractEventLoop | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


def run_async(coro):
    loop = _get_loop()
    return loop.run_until_complete(coro)


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
                from app.models.analysis import AIAnalysis
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

                # Phase 1: every emitted signal goes through the
                # canonical pipeline so the rows written here carry
                # the same factor_payload / weights_used / ml_boost
                # provenance as the API endpoints.
                for sig in signals.get("signals", []):
                    sig.setdefault("symbol", symbol)
                    sig.setdefault("timeframe", timeframe)
                    await signal_pipeline.persist_composed(sig, db=session)
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
                    select(User).where(User.is_active)
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


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def adjust_scoring_weights(self):
    """Recompute the self-learning weights from the SQL trade store.

    Phase 2: scheduled by the beat scheduler (e.g. once an hour) so
    the orchestrator's ``current_weights`` stays fresh. ``adjust_weights``
    is idempotent — if a recent successful run already captured the
    same trade window, the orchestrator's audit row will reflect a
    skip and the in-memory weights stay where they were.
    """
    try:
        from app.services.weight_orchestrator import weight_orchestrator

        async def _run():
            return await weight_orchestrator.adjust_weights()

        return run_async(_run())
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def resolve_signal_outcomes(self):
    """Resolve every active signal that has no ``signal_outcomes``
    row yet. Phase 3: writes both ``signals.result`` and
    ``signal_outcomes`` so the quality gate in Phase 5 has
    forward-return / MAE / MFE telemetry to act on.
    """
    try:

        async def _run():
            return await signal_outcome_resolver.resolve_all()

        return run_async(_run())
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=600)
def retrain_ml_models(self):
    """Retrain the ML ensemble on the configured top-N symbols.

    Phase 4: scheduled daily. The task only runs if
    ``MLSignalEngine.needs_retrain()`` returns True OR the
    ``force_retrain`` Redis flag is set. The freshly-trained
    model replaces the live one in ``model_dir/registry.json``
    only when its OOS hit rate clears
    ``settings.ML_MIN_OOS_HIT_RATE`` — otherwise the previous
    version stays.
    """
    try:
        from app.core.config import settings

        async def _run():
            from app.services.ml.signal_engine import get_ml_engine
            from app.services.market_coverage import market_coverage
            from app.services.ml.training.oos_backtest import OOSBacktester

            engine = get_ml_engine()
            if not engine.needs_retrain():
                return {
                    "status": "skipped",
                    "reason": "needs_retrain_false",
                    "last_train_at": str(engine.last_train_at),
                }

            symbols = await market_coverage.get_top_symbols(
                settings.ML_RETRAIN_SYMBOLS_TOP_N
            )
            train_result = await engine.train(symbols=symbols)
            mlflow_run_id = train_result.get("mlflow_run_id")

            backtest = OOSBacktester(
                n_splits=4,
                train_size=2000,
                test_size=500,
            )
            oos = await backtest.run(symbols=symbols)
            oos_hit_rate = float(oos.get("oof_hit_rate", 0.0))
            promoted = oos_hit_rate >= settings.ML_MIN_OOS_HIT_RATE
            return {
                "status": "ok" if promoted else "below_threshold",
                "mlflow_run_id": mlflow_run_id,
                "oos_hit_rate": oos_hit_rate,
                "promoted": promoted,
                "threshold": settings.ML_MIN_OOS_HIT_RATE,
                "n_symbols": len(symbols),
            }

        return run_async(_run())
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=300)
def prune_stale_signals(self):
    """Mark signals whose ``expires_at`` has passed as inactive
    and set ``result='expired'`` if they were never resolved.

    The resolver is the primary exit path for a signal, but
    when a symbol leaves the top-N market_coverage list, the
    candle fetch can fail forever and the signal would sit
    ``is_active=True`` indefinitely. This sweep catches those
    so the quality gate in Phase 5 isn't skewed by signals
    that never had a chance to resolve.
    """
    try:
        from datetime import UTC, datetime
        from sqlalchemy import update
        from app.core.database import async_session_factory
        from app.models.analysis import Signal, SignalOutcome

        async def _run():
            async with async_session_factory() as session:
                # Find active signals past their expiry that have
                # no outcome yet.
                now = datetime.now(UTC).replace(tzinfo=None)
                stmt = (
                    update(Signal)
                    .where(Signal.is_active.is_(True))
                    .where(Signal.expires_at.is_not(None))
                    .where(Signal.expires_at < now)
                    .where(~Signal.id.in_(
                        select(SignalOutcome.signal_id)
                    ))
                    .values(is_active=False, result="expired")
                )
                result = await session.execute(stmt)
                await session.commit()
                return {"pruned": result.rowcount or 0}

        return run_async(_run())
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def evaluate_quality(self):
    """Phase 5: run the per-engine quality evaluation.

    Iterates every distinct ``source_engine`` that has emitted
    in the last 7 days, computes a fresh hit-rate / MAE / MFE
    row, and flips ``is_disabled`` for engines that fall
    below ``settings.QUALITY_MIN_HIT_RATE``. The signal
    pipeline reads the latest row to decide whether to emit.

    The task is idempotent — a fast re-run writes a second
    row for the same window; the pipeline only cares about
    the most-recent row.
    """
    try:
        from app.services.quality_gate import (
            evaluate_engine,
            list_active_engines,
        )
        from app.services.observability import registry as metrics

        async def _run():
            engines = await list_active_engines()
            evaluated = 0
            disabled = 0
            for engine in engines:
                try:
                    res = await evaluate_engine(engine)
                    evaluated += 1
                    metrics.quality_evaluations.inc(
                        result=res.status, engine=engine,
                    )
                    if res.is_disabled:
                        disabled += 1
                        metrics.signals_blocked_quality.inc(engine=engine)
                    metrics.engines_disabled.set(
                        1.0 if res.is_disabled else 0.0,
                        engine=engine,
                    )
                except Exception as exc:
                    # A single engine's evaluation shouldn't
                    # blow up the rest of the batch.
                    import logging
                    logging.getLogger(__name__).warning(
                        f"quality_eval_failed engine={engine}: {exc}"
                    )
            return {
                "engines_evaluated": evaluated,
                "engines_disabled": disabled,
            }

        return run_async(_run())
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
                        published_at=datetime.fromisoformat(article.get("published_at", datetime.now(UTC).isoformat())),
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


@celery_app.task(
    bind=True,
    name="app.workers.retrain_ml_models",
    # Training runs XGBoost + LightGBM + Transformer on up to 30
    # symbols with ~1500 candles each. On the dedicated ml_trainer
    # profile this is bounded; cap to 1h hard, 55m soft, so the
    # worker doesn't get stuck if a model write hangs.
    max_retries=1,
    default_retry_delay=300,
    time_limit=3600,
    soft_time_limit=3300,
)
def retrain_ml_models(
    self,
    symbols: list,
    timeframe: str = "15m",
    include_transformer: bool = True,
):
    """
    Long-running ML ensemble retraining. Runs in the dedicated
    celery worker (not the live API process) so a single retrain
    cannot block user requests.

    Returns a dict with the training summary from MLSignalEngine.
    """
    import ccxt.async_support as ccxt

    from app.services.ml import MLSignalEngine

    class _ClientAdapter:
        """Minimal fetch_ohlcv adapter wrapping a public ccxt client."""
        def __init__(self, c):
            self._c = c
        async def fetch_ohlcv(self, sym, tf, limit=500):
            return await self._c.fetch_ohlcv(sym, tf, limit=limit)
        async def close(self):
            await self._c.close()

    async def _run():
        client = ccxt.binanceusdm({
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        })
        adapter = _ClientAdapter(client)
        engine = MLSignalEngine()
        try:
            results = await engine.train(
                symbols=symbols,
                exchange_client=adapter,
                timeframe=timeframe,
                include_transformer=include_transformer,
                save=True,
            )
            return results
        finally:
            try:
                await adapter.close()
            except Exception as e:
                logging.warning(f"retrain exchange close error: {e}")

    try:
        return run_async(_run())
    except Exception as exc:
        # Do not retry a failed training — it usually means a data
        # issue, not a transient network blip. Log and let the
        # operator inspect.
        logging.error(f"ML retrain failed: {exc}")
        return {"error": str(exc), "symbols": len(symbols)}
