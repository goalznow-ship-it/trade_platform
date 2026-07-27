import asyncio
import json
import math
from datetime import datetime, timezone
from typing import Any

from app.core.logging import logger
from app.core.redis import redis_client
from app.services.institutional_signals import institutional_signal_engine
from app.services.market import market_service


class AutoScalperService:
    SCAN_INTERVAL = 20
    MAX_DEEP_ANALYSIS = 12

    def __init__(self):
        self._tasks: dict[int, asyncio.Task] = {}

    @staticmethod
    def default_config() -> dict:
        return {
            "mode": "paper",
            "capital_usdt": 10.0,
            "risk_per_trade_pct": 0.5,
            "daily_loss_limit_pct": 3.0,
            "max_positions": 1,
            "min_score": 82.0,
            "max_leverage": 3,
            "scan_interval_seconds": AutoScalperService.SCAN_INTERVAL,
        }

    async def get_state(self, user_id: int) -> dict:
        raw = await redis_client.get(f"auto_scalper:{user_id}:state")
        if raw:
            return json.loads(raw)
        return {
            "armed": False,
            "mode": "paper",
            "config": self.default_config(),
            "last_scan": None,
            "market_count": 0,
            "candidates": [],
            "error": None,
        }

    async def _save_state(self, user_id: int, state: dict) -> None:
        await redis_client.set(f"auto_scalper:{user_id}:state", json.dumps(state))

    async def arm(self, user_id: int, config: dict) -> dict:
        if config.get("mode") != "paper":
            raise ValueError("Live Auto Scalper is locked until paper validation is complete")
        state = await self.get_state(user_id)
        state.update({"armed": True, "mode": "paper", "config": config, "error": None})
        await self._save_state(user_id, state)
        if user_id not in self._tasks or self._tasks[user_id].done():
            self._tasks[user_id] = asyncio.create_task(self._monitor(user_id))
        return state

    async def disarm(self, user_id: int) -> dict:
        state = await self.get_state(user_id)
        state["armed"] = False
        await self._save_state(user_id, state)
        task = self._tasks.pop(user_id, None)
        if task:
            task.cancel()
        return state

    async def _monitor(self, user_id: int) -> None:
        while True:
            try:
                state = await self.get_state(user_id)
                if not state.get("armed"):
                    return
                await self.scan(user_id)
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.error(f"Auto Scalper scan error for user {user_id}: {exc}")
                state = await self.get_state(user_id)
                state["error"] = str(exc)
                await self._save_state(user_id, state)
            await asyncio.sleep(self.SCAN_INTERVAL)

    @staticmethod
    def _pre_score(ticker: dict) -> float:
        bid = float(ticker.get("bid") or 0)
        ask = float(ticker.get("ask") or 0)
        last = float(ticker.get("last") or 0)
        volume = float(ticker.get("quoteVolume") or 0)
        change = abs(float(ticker.get("percentage") or 0))
        if not last or volume <= 0:
            return 0
        spread_pct = (ask - bid) / last * 100 if bid and ask and ask > bid else None
        if spread_pct is not None and spread_pct > 0.12:
            return 0
        liquidity = min(45, max(0, (math.log10(max(volume, 1)) - 5) * 12))
        momentum = min(35, change * 4)
        spread_quality = max(0, 20 - spread_pct * 150) if spread_pct is not None else 0
        return round(liquidity + momentum + spread_quality, 2)

    async def _market_snapshot(self) -> list[dict]:
        exchange = market_service.exchanges["binance"]
        markets, tickers = await asyncio.gather(
            market_service._call_exchange(exchange.load_markets),
            market_service._call_exchange(exchange.fetch_tickers),
        )
        rows = []
        for symbol, market in markets.items():
            info = market.get("info") or {}
            if not (
                market.get("active", True)
                and market.get("swap")
                and market.get("linear")
                and market.get("settle") == "USDT"
                and market.get("quote") == "USDT"
                and info.get("contractType") == "PERPETUAL"
                and info.get("underlyingType") == "COIN"
            ):
                continue
            ticker = tickers.get(symbol) or {}
            score = self._pre_score(ticker)
            if score <= 0:
                continue
            rows.append({
                "symbol": f"{market.get('base')}/USDT",
                "pre_score": score,
                "price": ticker.get("last"),
                "change_percent": ticker.get("percentage"),
                "quote_volume": ticker.get("quoteVolume"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
            })
        rows.sort(key=lambda item: item["pre_score"], reverse=True)
        return rows

    async def scan(self, user_id: int) -> dict:
        state = await self.get_state(user_id)
        config = {**self.default_config(), **state.get("config", {})}
        universe = await self._market_snapshot()
        semaphore = asyncio.Semaphore(4)

        async def analyze(row: dict) -> dict | None:
            async with semaphore:
                signal = await institutional_signal_engine.generate_signal(
                    row["symbol"], timeframe="5m",
                    capital=config["capital_usdt"],
                    risk_percent=config["risk_per_trade_pct"] / 100,
                )
                confidence = float(signal.get("confidence") or 0)
                direction = signal.get("direction", "neutral")
                execution = signal.get("execution") or {}
                entry = float((signal.get("entry_zone") or {}).get("mid") or signal.get("current_price") or 0)
                tp = float(signal.get("take_profit_1") or 0)
                gross_edge = abs(tp - entry) / entry * 100 if entry and tp else 0
                estimated_cost = 0.13
                net_edge = gross_edge - estimated_cost
                eligible = (
                    direction in ("long", "short")
                    and confidence >= config["min_score"]
                    and execution.get("approved", False)
                    and net_edge >= 0.15
                )
                return {
                    **row,
                    "direction": direction,
                    "confidence": confidence,
                    "quality_score": signal.get("quality_score", confidence),
                    "entry": entry,
                    "stop_loss": signal.get("stop_loss"),
                    "take_profit": tp or None,
                    "gross_edge_pct": round(gross_edge, 3),
                    "estimated_cost_pct": estimated_cost,
                    "net_edge_pct": round(net_edge, 3),
                    "execution_approved": execution.get("approved", False),
                    "eligible": eligible,
                    "reasons": signal.get("reasons", [])[:4],
                    "rejection_reasons": execution.get("rejection_reasons", [])[:4],
                }

        analyzed = await asyncio.gather(
            *(analyze(row) for row in universe[:self.MAX_DEEP_ANALYSIS]),
            return_exceptions=True,
        )
        candidates = [item for item in analyzed if isinstance(item, dict)]
        candidates.sort(
            key=lambda item: (item["eligible"], item["quality_score"], item["pre_score"]),
            reverse=True,
        )
        state.update({
            "config": config,
            "last_scan": datetime.now(timezone.utc).isoformat(),
            "market_count": len(universe),
            "deep_analyzed": len(candidates),
            "eligible_count": sum(1 for item in candidates if item["eligible"]),
            "candidates": candidates[:10],
            "error": None,
        })
        await self._save_state(user_id, state)
        return state


auto_scalper_service = AutoScalperService()
