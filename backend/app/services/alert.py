import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.websocket_manager import ws_manager
from app.models.alert import Alert, AlertTrigger


class AlertService:
    def __init__(self):
        self.logger = logger
        self._check_task: asyncio.Task | None = None

    async def start(self):
        self._check_task = asyncio.create_task(self._periodic_check())
        self.logger.info("Alert service started")

    async def stop(self):
        if self._check_task:
            self._check_task.cancel()

    async def get_alerts(self, user_id: int, db: AsyncSession, active_only: bool = False) -> list:
        q = select(Alert).where(Alert.user_id == user_id).options(selectinload(Alert.triggers))
        if active_only:
            q = q.where(Alert.is_active)
        q = q.order_by(Alert.created_at.desc())
        result = await db.execute(q)
        return result.scalars().all()

    async def get_alert(self, alert_id: int, user_id: int, db: AsyncSession) -> Alert | None:
        result = await db.execute(
            select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
            .options(selectinload(Alert.triggers))
        )
        return result.scalar_one_or_none()

    async def create_alert(self, user_id: int, data: dict, db: AsyncSession) -> Alert:
        alert = Alert(user_id=user_id, **data)
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        return alert

    async def update_alert(self, alert_id: int, user_id: int, data: dict, db: AsyncSession) -> Alert | None:
        alert = await self.get_alert(alert_id, user_id, db)
        if not alert:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(alert, key, value)
        await db.commit()
        await db.refresh(alert)
        return alert

    async def delete_alert(self, alert_id: int, user_id: int, db: AsyncSession) -> bool:
        alert = await self.get_alert(alert_id, user_id, db)
        if not alert:
            return False
        await db.delete(alert)
        await db.commit()
        return True

    async def trigger_alert(self, alert: Alert, triggered_value: float, price: float | None, db: AsyncSession):
        channels = alert.channels if isinstance(alert.channels, list) else ["in_app"]
        for channel in channels:
            trigger = AlertTrigger(
                alert_id=alert.id,
                triggered_value=triggered_value,
                triggered_at_price=price,
                channel=channel,
            )
            db.add(trigger)

        alert.trigger_count += 1
        alert.last_triggered_at = datetime.now(UTC)
        if alert.cooldown_minutes > 0:
            alert.cooldown_until = datetime.now(UTC) + timedelta(minutes=alert.cooldown_minutes)
        if alert.max_triggers > 0 and alert.trigger_count >= alert.max_triggers:
            alert.is_active = False

        await db.commit()

        await ws_manager.send_to_user(
            alert.user_id, "alert_triggered", {
                "alert_id": alert.id,
                "name": alert.name,
                "type": alert.alert_type,
                "symbol": alert.symbol,
                "value": triggered_value,
                "price": price,
            }, channel="notifications"
        )

    async def _periodic_check(self):
        """
        Evaluate active alerts every 10s.

        The previous implementation was a no-op (the try block was just
        `pass`) — alerts were created in the DB but never evaluated, so
        users who set up a "BTC crosses 100k" alert got nothing. This
        pulls all active alerts, computes the current value for the
        alert type, and dispatches a trigger if the condition is met.

        Cooldown, max_triggers, and is_active are all honored so the
        loop doesn't spam the same alert every 10s.
        """
        from app.core.database import async_session_factory
        from app.services.indicators import indicator_service
        from app.services.market import market_service

        while True:
            await asyncio.sleep(10)
            try:
                now = datetime.now(UTC)
                async with async_session_factory() as db:
                    q = (
                        select(Alert)
                        .where(Alert.is_active == True)  # noqa: E712
                        .where(
                            (Alert.cooldown_until.is_(None))
                            | (Alert.cooldown_until <= now)
                        )
                    )
                    result = await db.execute(q)
                    alerts = result.scalars().all()
                    for alert in alerts:
                        try:
                            triggered = await self._evaluate_alert(
                                alert, market_service, indicator_service,
                            )
                            if triggered is not None:
                                value, price = triggered
                                await self.trigger_alert(alert, value, price, db)
                        except Exception as inner_exc:
                            # One bad alert must not poison the whole loop.
                            self.logger.error(
                                f"Alert {alert.id} ({alert.name}) evaluation failed: {inner_exc}"
                            )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.error(f"Alert check error: {e}")

    async def _evaluate_alert(self, alert, market_service, indicator_service):
        """
        Return (triggered_value, current_price) if the condition is met,
        else None. Each alert type evaluates the indicator that matches
        the alert and compares against alert.value using alert.condition.
        """
        symbol = alert.symbol
        timeframe = alert.timeframe or "15m"
        value = alert.value
        condition = alert.condition

        # PRICE: simple ticker threshold
        if alert.alert_type == "price":
            ticker = await market_service.get_ticker(symbol)
            price = ticker.get("price") if isinstance(ticker, dict) else None
            if price is None or value is None:
                return None
            if condition == "above" and price > value:
                return (price, price)
            if condition == "below" and price < value:
                return (price, price)
            return None

        # RSI, EMA_CROSS, MACD, GOLDEN_CROSS, DEATH_CROSS: need OHLCV
        needs_ohlcv = alert.alert_type in {
            "rsi", "ema_cross", "macd", "golden_cross", "death_cross",
        }
        if not needs_ohlcv:
            # Other types (FUNDING_RATE, OPEN_INTEREST, FEAR_GREED, etc.)
            # can be added when the matching service is in place — for
            # now we deliberately return None rather than raising so a
            # future-dated alert type doesn't crash the loop.
            return None

        ohlcv = await market_service.get_ohlcv(symbol, alert.exchange or "binance", timeframe, 100)
        if not ohlcv or len(ohlcv) < 30:
            return None
        price = ohlcv[-1][4]  # close

        if alert.alert_type == "rsi":
            rsi_series = indicator_service.rsi(ohlcv, 14)
            rsi = rsi_series.get("value", rsi_series) if isinstance(rsi_series, dict) else rsi_series
            if isinstance(rsi, list):
                rsi = rsi[-1] if rsi else None
            if rsi is None or value is None:
                return None
            if condition == "above" and rsi > value:
                return (rsi, price)
            if condition == "below" and rsi < value:
                return (rsi, price)
            return None

        if alert.alert_type == "ema_cross":
            ema_fast = indicator_service.ema(ohlcv, 9)
            ema_slow = indicator_service.ema(ohlcv, 21)
            # ema() returns a list of EMA values aligned to the input
            # candles (truncated to the warmup period). Use the last
            # available value of each.
            ema_fast_last = ema_fast[-1] if ema_fast else None
            ema_slow_last = ema_slow[-1] if ema_slow else None
            if ema_fast_last is None or ema_slow_last is None:
                return None
            spread = ema_fast_last - ema_slow_last
            if condition == "crosses_above" and spread > 0:
                return (spread, price)
            if condition == "crosses_below" and spread < 0:
                return (spread, price)
            return None

        if alert.alert_type == "macd":
            macd = indicator_service.macd(ohlcv)
            hist = macd.get("histogram", macd.get("macd")) if isinstance(macd, dict) else None
            if isinstance(hist, list):
                hist = hist[-1] if hist else None
            if hist is None or value is None:
                return None
            if condition == "above" and hist > value:
                return (hist, price)
            if condition == "below" and hist < value:
                return (hist, price)
            return None

        return None


alert_service = AlertService()
