"""Resolve persisted signal outcomes from real exchange candles."""

from datetime import datetime, timezone, timedelta

from sqlalchemy import or_, select

from app.core.database import async_session_factory
from app.core.logging import logger
from app.models.analysis import Signal
from app.services.market import market_service


class SignalOutcomeResolver:
    HORIZONS = {
        "1m": timedelta(hours=2),
        "5m": timedelta(hours=8),
        "15m": timedelta(hours=18),
        "30m": timedelta(days=1),
        "1h": timedelta(days=3),
        "4h": timedelta(days=10),
        "1d": timedelta(days=30),
    }

    @staticmethod
    def _aware(value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _candle_result(signal: Signal, candle: dict) -> str | None:
        high = float(candle["high"])
        low = float(candle["low"])
        entry = float(signal.entry_price)
        stop = float(signal.stop_loss)
        target = float(signal.take_profit_1)

        if not signal.is_triggered and low <= entry <= high:
            signal.is_triggered = True
            signal.triggered_price = entry
        if not signal.is_triggered:
            return None

        if str(signal.direction).lower() == "long":
            stop_hit = low <= stop
            target_hit = high >= target
        else:
            stop_hit = high >= stop
            target_hit = low <= target

        # Intrabar order is unknown without tick data; conservative resolution
        # prevents inflated historical accuracy.
        if stop_hit:
            return "sl_hit"
        if target_hit:
            return "tp_hit"
        return None

    async def resolve_open_signals(self, limit: int = 100) -> dict:
        now = datetime.now(timezone.utc)
        async with async_session_factory() as db:
            rows = await db.execute(
                select(Signal)
                .where(
                    Signal.is_active.is_(True),
                    or_(Signal.result.is_(None), Signal.result.in_(["new", "active"])),
                    Signal.entry_price.is_not(None),
                    Signal.stop_loss.is_not(None),
                    Signal.take_profit_1.is_not(None),
                )
                .order_by(Signal.created_at)
                .limit(limit)
            )
            signals = rows.scalars().all()
            resolved = {"tp_hit": 0, "sl_hit": 0, "expired": 0}

            for signal in signals:
                created = self._aware(signal.created_at)
                timeframe = signal.timeframe or "1h"
                expires = self._aware(signal.expires_at) if signal.expires_at else (
                    created + self.HORIZONS.get(timeframe, timedelta(days=3))
                )
                if now >= expires:
                    signal.result = "expired"
                    signal.is_active = False
                    resolved["expired"] += 1
                    continue

                candles = await market_service.get_ohlcv(
                    signal.symbol,
                    timeframe=timeframe,
                    limit=500,
                )
                for candle in candles:
                    candle_time = datetime.fromtimestamp(
                        float(candle["time"]),
                        tz=timezone.utc,
                    )
                    if candle_time < created:
                        continue
                    result = self._candle_result(signal, candle)
                    if result:
                        signal.result = result
                        signal.is_active = False
                        resolved[result] += 1
                        break

            await db.commit()
            if any(resolved.values()):
                logger.info("Signal outcomes resolved: %s", resolved)
            return {
                "checked": len(signals),
                "resolved": resolved,
                "timestamp": now.isoformat(),
            }


signal_outcome_resolver = SignalOutcomeResolver()
