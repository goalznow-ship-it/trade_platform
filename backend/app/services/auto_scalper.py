import asyncio
import json
import math
from datetime import datetime, timezone
from typing import Any

from app.core.logging import logger
from app.core.redis import redis_client
from app.core.database import async_session_factory
from app.models.paper_trading import PaperPosition
from app.services.institutional_signals import institutional_signal_engine
from app.services.market import market_service
from sqlalchemy import func, select


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
        state = await self.get_state(user_id)
        state.update({"armed": True, "mode": config["mode"], "config": config, "error": None})
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
        if state.get("armed"):
            eligible = next((item for item in candidates if item["eligible"]), None)
            if eligible:
                await self._execute_candidate(user_id, eligible, config, state)
        return state

    @staticmethod
    def _position_size(candidate: dict, config: dict) -> float:
        entry = float(candidate.get("entry") or 0)
        stop = float(candidate.get("stop_loss") or 0)
        if entry <= 0 or stop <= 0 or entry == stop:
            return 0
        capital = float(config["capital_usdt"])
        risk_budget = capital * float(config["risk_per_trade_pct"]) / 100
        risk_quantity = risk_budget / abs(entry - stop)
        leverage_cap = capital * int(config["max_leverage"]) / entry
        return max(0, min(risk_quantity, leverage_cap))

    async def _execute_candidate(
        self, user_id: int, candidate: dict, config: dict, state: dict,
    ) -> None:
        lock_key = f"auto_scalper:{user_id}:execution_lock"
        if not await redis_client.set(lock_key, "1", ex=60, nx=True):
            return
        quantity = self._position_size(candidate, config)
        if quantity <= 0:
            return
        try:
            if config["mode"] == "paper":
                result = await self._execute_paper(user_id, candidate, config, quantity)
            else:
                result = await self._execute_live(user_id, candidate, config, quantity)
            state["last_execution"] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": candidate["symbol"],
                "direction": candidate["direction"],
                "quantity": quantity,
                "mode": config["mode"],
                "result": result,
            }
            await self._save_state(user_id, state)
        except Exception as exc:
            state["error"] = f"Execution blocked: {exc}"
            await self._save_state(user_id, state)

    async def _execute_paper(
        self, user_id: int, candidate: dict, config: dict, quantity: float,
    ) -> dict:
        from app.services.paper_trading import paper_trading_service

        async with async_session_factory() as db:
            account = await paper_trading_service.get_or_create_account(user_id, db)
            loss_limit = (
                float(config["capital_usdt"])
                * float(config["daily_loss_limit_pct"]) / 100
            )
            if account.total_pnl <= -loss_limit:
                return {"status": "skipped", "reason": "daily_loss_limit reached"}
            count_result = await db.execute(
                select(func.count(PaperPosition.id)).where(
                    PaperPosition.account_id == account.id,
                    PaperPosition.is_open == True,
                )
            )
            if int(count_result.scalar_one()) >= int(config["max_positions"]):
                return {"status": "skipped", "reason": "max_positions reached"}
            result = await paper_trading_service.create_order(user_id, {
                "symbol": candidate["symbol"],
                "side": "buy" if candidate["direction"] == "long" else "sell",
                "order_type": "market",
                "quantity": quantity,
                "leverage": config["max_leverage"],
                "stop_loss": candidate["stop_loss"],
                "take_profit": candidate["take_profit"],
            }, db)
            if result.get("error"):
                return {"status": "rejected", "reason": result["error"]}
            position = result.get("position")
            if position:
                position.stop_loss = candidate["stop_loss"]
                position.take_profit = candidate["take_profit"]
                await db.commit()
            return {
                "status": "opened" if position else "pending",
                "position_id": getattr(position, "id", None),
            }

    async def _execute_live(
        self, user_id: int, candidate: dict, config: dict, quantity: float,
    ) -> dict:
        from app.api.v1.trading import OrderRequest, create_order
        from app.models.user import User

        async with async_session_factory() as db:
            user = await db.get(User, user_id)
            if not user:
                raise ValueError("User not found")
            request = OrderRequest(
                exchange="binance",
                symbol=candidate["symbol"],
                side="buy" if candidate["direction"] == "long" else "sell",
                amount=quantity,
                order_type="market",
                stop_loss=candidate["stop_loss"],
                take_profit=candidate["take_profit"],
                leverage=config["max_leverage"],
                margin_mode="isolated",
                client_order_id=f"scalp_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
            )
            entry = await create_order(request, None, user, db)
            close_side = "sell" if candidate["direction"] == "long" else "buy"
            base_id = f"scalp_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
            stop = None
            try:
                stop = await create_order(OrderRequest(
                    exchange="binance", symbol=candidate["symbol"],
                    side=close_side, amount=quantity, order_type="stop_market",
                    stop_price=candidate["stop_loss"], reduce_only=True,
                    leverage=config["max_leverage"],
                    client_order_id=f"{base_id}_sl",
                ), None, user, db)
                target = await create_order(OrderRequest(
                    exchange="binance", symbol=candidate["symbol"],
                    side=close_side, amount=quantity, order_type="take_profit_market",
                    stop_price=candidate["take_profit"], reduce_only=True,
                    leverage=config["max_leverage"],
                    client_order_id=f"{base_id}_tp",
                ), None, user, db)
            except Exception as bracket_error:
                if stop and stop.get("order_id"):
                    try:
                        from app.services.exchange.manager import exchange_manager
                        exchange = await exchange_manager.get_user_exchange(
                            user_id, "binance", db,
                        )
                        if exchange:
                            await exchange.cancel_order(
                                candidate["symbol"], stop["order_id"],
                            )
                    except Exception:
                        pass
                emergency = await create_order(OrderRequest(
                    exchange="binance", symbol=candidate["symbol"],
                    side=close_side, amount=quantity, order_type="market",
                    reduce_only=True, leverage=config["max_leverage"],
                    client_order_id=f"{base_id}_emergency",
                ), None, user, db)
                raise RuntimeError(
                    f"Protective bracket failed; emergency close status: "
                    f"{emergency.get('status', 'unknown')}; cause: {bracket_error}"
                )
            return {"entry": entry, "stop_loss": stop, "take_profit": target}


auto_scalper_service = AutoScalperService()
