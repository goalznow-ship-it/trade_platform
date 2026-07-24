import json
import time
from datetime import datetime, timezone
from typing import Optional
from app.core.cache import cache_get, cache_set
from app.core.logging import logger

HISTORY_KEY = "skhy:signal_history"
MAX_HISTORY = 100

class SkhySignalHistory:
    async def record_signal(self, signal: dict) -> None:
        history = await self._get_all()
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signal": signal,
        }
        history.insert(0, entry)
        history = history[:MAX_HISTORY]
        await cache_set(HISTORY_KEY, history, ttl=86400 * 7)

    async def _get_all(self) -> list:
        cached = await cache_get(HISTORY_KEY)
        return cached if isinstance(cached, list) else []

    async def get_history(self, limit: int = 30) -> list:
        history = await self._get_all()
        return history[:limit]

    async def record_trade_result(self, signal_time: str, result: dict) -> None:
        history = await self._get_all()
        for entry in history:
            if entry.get("timestamp") == signal_time:
                entry["result"] = result
                break
        await cache_set(HISTORY_KEY, history, ttl=86400 * 7)

    async def get_performance(self) -> dict:
        history = await self._get_all()
        completed = [h for h in history if h.get("result") and h["result"].get("exit_price")]
        if not completed:
            return {"status": "no_trades_yet"}

        wins = [h for h in completed if h["result"].get("pnl", 0) > 0]
        losses = [h for h in completed if h["result"].get("pnl", 0) <= 0]
        total = len(completed)

        long_trades = [h for h in completed if h.get("signal", {}).get("direction", "").lower() == "long"]
        short_trades = [h for h in completed if h.get("signal", {}).get("direction", "").lower() == "short"]
        long_wins = [h for h in long_trades if h["result"].get("pnl", 0) > 0]
        short_wins = [h for h in short_trades if h["result"].get("pnl", 0) > 0]

        pnls = [h["result"].get("pnl", 0) for h in completed]
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))

        return {
            "total_signals": total,
            "win_rate": round(len(wins) / total * 100, 1) if total > 0 else 0,
            "total_wins": len(wins),
            "total_losses": len(losses),
            "long_win_rate": round(len(long_wins) / len(long_trades) * 100, 1) if long_trades else 0,
            "short_win_rate": round(len(short_wins) / len(short_trades) * 100, 1) if short_trades else 0,
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf"),
            "average_rr": round(sum(h["result"].get("rr", 0) for h in completed) / total, 2) if total > 0 else 0,
            "max_drawdown": 0,
        }


skhy_history = SkhySignalHistory()
