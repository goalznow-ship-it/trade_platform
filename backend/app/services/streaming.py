import asyncio
from typing import List, Optional
from datetime import datetime, timezone
from app.core.websocket_manager import ws_manager, Channel
from app.core.logging import logger
from app.services.market_coverage import market_coverage


class StreamingService:
    WORKER_INTERVALS = {
        "orderflow": 2,
        "derivatives": 10,
        "news": 60,
        "sentiment": 120,
        "onchain": 300,
        "macro": 300,
        "brain": 60,
        "fear_greed": 60,
        "breadth": 60,
        "signals": 60,
        "outcomes": 60,
        "heartbeat": 5,
    }

    def __init__(self):
        self._tasks: List[asyncio.Task] = []
        self._running = False
        self._heartbeats: dict[str, float] = {}
        self._watchdog_task: Optional[asyncio.Task] = None
        self._stale_workers: set[str] = set()

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
            ("outcomes", self._resolve_signal_outcomes()),
            ("heartbeat", self._stream_heartbeat()),
        ]

        for name, coro in workers:
            task = asyncio.create_task(self._run_worker(name, coro))
            self._tasks.append(task)

        logger.info(f"StreamingService started with {len(workers)} workers")
        self._watchdog_task = asyncio.create_task(self._watchdog())

    async def stop(self):
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        if self._watchdog_task:
            self._watchdog_task.cancel()
            await asyncio.gather(self._watchdog_task, return_exceptions=True)
            self._watchdog_task = None
        logger.info("StreamingService stopped")

    async def _run_worker(self, name: str, coro):
        try:
            self._heartbeats[name] = datetime.now(timezone.utc).timestamp()
            await coro
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Streaming worker %s terminated", name)

    def _beat(self, name: str) -> None:
        self._heartbeats[name] = datetime.now(timezone.utc).timestamp()

    def _stale_after(self, name: str) -> int:
        return self.WORKER_INTERVALS.get(name, 60) + 90

    async def _watchdog(self):
        while self._running:
            await asyncio.sleep(30)
            now = datetime.now(timezone.utc).timestamp()
            for name, last in list(self._heartbeats.items()):
                if now - last > self._stale_after(name):
                    if name not in self._stale_workers:
                        self._stale_workers.add(name)
                        logger.warning("Streaming worker %s is stale", name)
                elif name in self._stale_workers:
                    self._stale_workers.remove(name)
                    logger.info("Streaming worker %s recovered", name)
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
        from app.services.market import market_service
        while self._running:
            for sym in symbols:
                self._beat("orderflow")
                try:
                    orderbook, trades = await asyncio.gather(
                        market_service.get_orderbook(sym, limit=50),
                        market_service.get_trades(sym, limit=100),
                    )
                    bids = [
                        {"price": level[0], "amount": level[1]}
                        for level in orderbook.get("bids", [])
                    ]
                    asks = [
                        {"price": level[0], "amount": level[1]}
                        for level in orderbook.get("asks", [])
                    ]
                    if not bids or not asks:
                        continue
                    snapshot = orderflow_engine.get_aggregated_snapshot(
                        sym, bids, asks, trades,
                    )
                    await ws_manager.broadcast(Channel.ORDERFLOW, "orderflow_update", {
                        "symbol": sym,
                        "data": snapshot,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass
            self._beat("orderflow")
            await asyncio.sleep(2)

    async def _stream_derivatives(self, symbols: List[str]):
        from app.services.derivatives import derivatives_engine
        from app.services.market import market_service
        while self._running:
            for sym in symbols:
                self._beat("derivatives")
                try:
                    funding, oi, ticker = await asyncio.gather(
                        market_service.get_funding_rate(sym),
                        market_service.get_open_interest(sym),
                        market_service.get_ticker(sym),
                    )
                    if funding.get("funding_rate") is None or oi.get("open_interest") is None:
                        continue
                    funding_time = funding.get("funding_time")
                    next_funding = (
                        datetime.fromtimestamp(funding_time / 1000, tz=timezone.utc)
                        if isinstance(funding_time, (int, float))
                        else None
                    )
                    snapshot = derivatives_engine.get_aggregated_derivatives_snapshot(
                        sym,
                        funding_rate=funding["funding_rate"],
                        next_funding_time=next_funding,
                        oi_current=oi["open_interest"],
                        price_change_24h=ticker.get("change_percent"),
                    )
                    snapshot["long_short_ratio"] = {
                        "available": False,
                        "reason": "Real long/short provider not configured",
                    }
                    snapshot["liquidations"] = {
                        "available": False,
                        "reason": "Real liquidation provider not configured",
                    }
                    await ws_manager.broadcast(Channel.DERIVATIVES, "derivatives_update", {
                        "symbol": sym,
                        "data": snapshot,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass
            self._beat("derivatives")
            await asyncio.sleep(10)

    async def _stream_news(self):
        from app.services.news_intelligence_v2 import news_intelligence_engine
        while self._running:
            self._beat("news")
            try:
                articles = await asyncio.wait_for(
                    news_intelligence_engine.scan_all_news(10),
                    timeout=30,
                )
                for article in articles[:5]:
                    await ws_manager.broadcast(Channel.NEWS, "news_article", {
                        "data": article,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception:
                pass
            self._beat("news")
            await asyncio.sleep(60)

    async def _stream_sentiment(self, symbols: List[str]):
        from app.services.social_sentiment import social_sentiment
        while self._running:
            for sym in symbols:
                self._beat("sentiment")
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
            self._beat("sentiment")
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
            self._beat("onchain")
            await asyncio.sleep(300)

    async def _stream_macro(self):
        from app.services.macro_engine import macro_engine
        while self._running:
            self._beat("macro")
            try:
                snapshot = await asyncio.wait_for(
                    asyncio.to_thread(macro_engine.get_macro_snapshot),
                    timeout=60,
                )
                await ws_manager.broadcast(Channel.MACRO, "macro_update", {
                    "data": snapshot,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                pass
            self._beat("macro")
            await asyncio.sleep(300)

    async def _stream_brain(self, symbols: List[str]):
        from app.services.brain import ai_brain
        while self._running:
            for sym in symbols:
                self._beat("brain")
                try:
                    assessment = await ai_brain.assess_market(sym)
                    await ws_manager.broadcast(Channel.BRAIN, "brain_assessment", {
                        "symbol": sym,
                        "data": assessment,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass
            self._beat("brain")
            await asyncio.sleep(60)

    async def _stream_fear_greed(self):
        while self._running:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get("https://api.alternative.me/fng/?limit=1")
                    response.raise_for_status()
                    data = response.json()["data"][0]
                if data:
                    await ws_manager.broadcast(Channel.FEAR_GREED, "fear_greed_update", {
                        "data": data,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception:
                logger.exception("Fear/greed stream failed")
            self._beat("fear_greed")
            await asyncio.sleep(60)

    async def _stream_breadth(self, symbols: List[str]):
        while self._running:
            try:
                tickers = await asyncio.gather(
                    *(self._ticker_or_none(symbol) for symbol in symbols),
                    return_exceptions=False,
                )
                changes = [
                    change
                    for ticker in tickers
                    if isinstance(ticker, dict)
                    and isinstance((change := ticker.get("change_percent")), (int, float))
                ]
                advancing = sum(1 for change in changes if change > 0)
                unchanged = sum(1 for change in changes if change == 0)
                declining = sum(1 for change in changes if change < 0)
                breadth_ratio = advancing / max(declining, 1)
                await ws_manager.broadcast(Channel.BREADTH, "breadth_update", {
                    "data": {
                        "advancing": advancing,
                        "declining": declining,
                        "unchanged": unchanged,
                        "breadth_ratio": round(breadth_ratio, 2),
                        "total_symbols": len(symbols),
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                logger.exception("Market breadth stream failed")
            self._beat("breadth")
            await asyncio.sleep(60)

    async def _ticker_or_none(self, symbol: str):
        from app.services.market import market_service
        try:
            return await market_service.get_ticker(symbol)
        except Exception:
            return None

    async def _stream_signals(self, symbols: List[str]):
        from app.services.institutional_signals import institutional_signal_engine
        from app.services.early_signal_monitor import early_signal_monitor
        while self._running:
            self._beat("signals")
            try:
                results = await asyncio.wait_for(
                    institutional_signal_engine.scan_all(min_score=0, limit=30),
                    timeout=100,
                )
            except Exception:
                logger.exception("Institutional signal stream scan failed")
                results = []
            results.sort(
                key=lambda signal: early_signal_monitor.quality_score(signal),
                reverse=True,
            )
            transitions = await early_signal_monitor.process(results)
            visible = [
                signal for signal in results
                if signal.get("direction") in {"long", "short"}
                and signal.get("confidence", 0) >= 50
            ]
            if visible:
                await ws_manager.broadcast(Channel.SIGNALS, "signal_update", {
                    "data": visible[:10],
                    "transitions": transitions,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            self._beat("signals")
            await asyncio.sleep(60)

    async def _resolve_signal_outcomes(self):
        from app.services.signal_outcome import signal_outcome_resolver

        while self._running:
            try:
                await signal_outcome_resolver.resolve_open_signals()
            except Exception:
                logger.exception("Signal outcome resolver failed")
            self._beat("outcomes")
            await asyncio.sleep(60)


    def get_stats(self) -> dict:
        now = datetime.now(timezone.utc).timestamp()
        return {
            "running": self._running,
            "workers": {
                name: {
                    "last_heartbeat_ago_secs": round(now - ts, 1),
                    "alive": now - ts < self._stale_after(name),
                }
                for name, ts in self._heartbeats.items()
            },
            "worker_count": len(self._tasks),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


streaming_service = StreamingService()
