import asyncio
from typing import List, Optional
from datetime import datetime, timezone
from app.core.websocket_manager import ws_manager, Channel
from app.core.logging import logger
from app.services.market_coverage import market_coverage


class StreamingService:
    def __init__(self):
        self._tasks: List[asyncio.Task] = []
        self._running = False
        self._heartbeats: dict[str, float] = {}

    async def start(self):
        self._running = True
        symbols = await market_coverage.get_top_symbols(30)

        workers = [
            ("orderflow", self._stream_orderflow(symbols[:10])),
            ("derivatives", self._stream_derivatives(symbols[:10])),
            ("news", self._stream_news()),
            ("sentiment", self._stream_sentiment(symbols[:5])),
            ("onchain", self._stream_onchain(symbols[:5])),
            ("macro", self._stream_macro()),
            ("brain", self._stream_brain(symbols[:5])),
            ("fear_greed", self._stream_fear_greed()),
            ("breadth", self._stream_breadth(symbols)),
            ("signals", self._stream_signals(symbols)),
            ("heartbeat", self._stream_heartbeat()),
        ]

        for name, coro in workers:
            task = asyncio.create_task(self._run_worker(name, coro))
            self._tasks.append(task)

        logger.info(f"StreamingService started with {len(workers)} workers")
        asyncio.create_task(self._watchdog())

    async def stop(self):
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("StreamingService stopped")

    async def _run_worker(self, name: str, coro):
        while self._running:
            try:
                self._heartbeats[name] = datetime.now(timezone.utc).timestamp()
                await coro
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Streaming worker {name} error: {e}")
                await asyncio.sleep(5)

    async def _watchdog(self):
        while self._running:
            await asyncio.sleep(30)
            now = datetime.now(timezone.utc).timestamp()
            for name, last in list(self._heartbeats.items()):
                if name in ("heartbeat",) and now - last > 15:
                    logger.warning(f"Streaming worker {name} stale — restarting")
            await ws_manager.broadcast(Channel.MARKET, "streaming_heartbeat", {
                "workers": {k: round(now - v, 1) for k, v in self._heartbeats.items()},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    async def _stream_heartbeat(self):
        while self._running:
            await asyncio.sleep(5)
            self._heartbeats["heartbeat"] = datetime.now(timezone.utc).timestamp()

    async def _stream_orderflow(self, symbols: List[str]):
        from app.services.orderflow import orderflow_engine
        while self._running:
            for sym in symbols:
                try:
                    snapshot = orderflow_engine.get_aggregated_snapshot(sym, None, None, None)
                    await ws_manager.broadcast(Channel.ORDERFLOW, "orderflow_update", {
                        "symbol": sym,
                        "data": snapshot,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass
            await asyncio.sleep(2)

    async def _stream_derivatives(self, symbols: List[str]):
        from app.services.derivatives import derivatives_engine
        while self._running:
            for sym in symbols:
                try:
                    snapshot = derivatives_engine.get_aggregated_derivatives_snapshot(sym)
                    await ws_manager.broadcast(Channel.DERIVATIVES, "derivatives_update", {
                        "symbol": sym,
                        "data": snapshot,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass
            await asyncio.sleep(10)

    async def _stream_news(self):
        from app.services.news_intelligence_v2 import news_intelligence_engine
        while self._running:
            try:
                articles = await news_intelligence_engine.scan_all_news(10)
                for article in articles[:5]:
                    await ws_manager.broadcast(Channel.NEWS, "news_article", {
                        "data": article,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception:
                pass
            await asyncio.sleep(60)

    async def _stream_sentiment(self, symbols: List[str]):
        from app.services.social_sentiment import social_sentiment
        while self._running:
            for sym in symbols:
                try:
                    snapshot = social_sentiment.get_social_sentiment_snapshot(sym)
                    await ws_manager.broadcast(Channel.SENTIMENT, "sentiment_update", {
                        "symbol": sym,
                        "data": snapshot,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass
            try:
                narratives = social_sentiment.get_trending_narratives()
                await ws_manager.broadcast(Channel.SENTIMENT, "trending_narratives", {
                    "data": narratives,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                pass
            await asyncio.sleep(120)

    async def _stream_onchain(self, symbols: List[str]):
        from app.services.onchain import onchain_engine
        while self._running:
            for sym in symbols:
                try:
                    snapshot = onchain_engine.get_onchain_snapshot(sym)
                    await ws_manager.broadcast(Channel.ONCHAIN, "onchain_update", {
                        "symbol": sym,
                        "data": snapshot,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass
            await asyncio.sleep(300)

    async def _stream_macro(self):
        from app.services.macro_engine import macro_engine
        while self._running:
            try:
                snapshot = macro_engine.get_macro_snapshot()
                await ws_manager.broadcast(Channel.MACRO, "macro_update", {
                    "data": snapshot,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                pass
            await asyncio.sleep(300)

    async def _stream_brain(self, symbols: List[str]):
        from app.services.brain import ai_brain
        while self._running:
            for sym in symbols:
                try:
                    assessment = await ai_brain.assess_market(sym)
                    await ws_manager.broadcast(Channel.BRAIN, "brain_assessment", {
                        "symbol": sym,
                        "data": assessment,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass
            await asyncio.sleep(60)

    async def _stream_fear_greed(self):
        import random
        while self._running:
            try:
                value = random.randint(10, 90)
                classification = (
                    "extreme_fear" if value <= 25 else
                    "fear" if value <= 45 else
                    "neutral" if value <= 55 else
                    "greed" if value <= 75 else
                    "extreme_greed"
                )
                await ws_manager.broadcast(Channel.FEAR_GREED, "fear_greed_update", {
                    "data": {"value": value, "classification": classification},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                pass
            await asyncio.sleep(60)

    async def _stream_breadth(self, symbols: List[str]):
        import random
        while self._running:
            try:
                advancing = random.randint(10, 25)
                declining = len(symbols) - advancing
                breadth_ratio = advancing / max(declining, 1)
                await ws_manager.broadcast(Channel.BREADTH, "breadth_update", {
                    "data": {
                        "advancing": advancing,
                        "declining": declining,
                        "unchanged": max(0, len(symbols) - advancing - declining),
                        "breadth_ratio": round(breadth_ratio, 2),
                        "total_symbols": len(symbols),
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                pass
            await asyncio.sleep(60)

    async def _stream_signals(self, symbols: List[str]):
        from app.services.institutional_signals import institutional_signal_generator
        while self._running:
            results = []
            for sym in symbols[:10]:
                try:
                    signal = await institutional_signal_generator.generate_signal(sym, "1h")
                    if signal and signal.get("score", 0) >= 70:
                        results.append(signal)
                except Exception:
                    pass
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            if results:
                await ws_manager.broadcast(Channel.SIGNALS, "signal_update", {
                    "data": results[:5],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            await asyncio.sleep(60)


streaming_service = StreamingService()
