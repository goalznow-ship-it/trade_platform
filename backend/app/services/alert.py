import asyncio
from typing import Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.alert import Alert, AlertTrigger
from app.core.logging import logger
from app.core.websocket_manager import ws_manager


class AlertService:
    def __init__(self):
        self.logger = logger
        self._check_task: Optional[asyncio.Task] = None

    async def start(self):
        self._check_task = asyncio.create_task(self._periodic_check())
        self.logger.info("Alert service started")

    async def stop(self):
        if self._check_task:
            self._check_task.cancel()

    async def get_alerts(self, user_id: int, db: AsyncSession, active_only: bool = False) -> list:
        q = select(Alert).where(Alert.user_id == user_id).options(selectinload(Alert.triggers))
        if active_only:
            q = q.where(Alert.is_active == True)
        q = q.order_by(Alert.created_at.desc())
        result = await db.execute(q)
        return result.scalars().all()

    async def get_alert(self, alert_id: int, user_id: int, db: AsyncSession) -> Optional[Alert]:
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

    async def update_alert(self, alert_id: int, user_id: int, data: dict, db: AsyncSession) -> Optional[Alert]:
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

    async def trigger_alert(self, alert: Alert, triggered_value: float, price: Optional[float], db: AsyncSession):
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
        alert.last_triggered_at = datetime.now(timezone.utc)
        if alert.cooldown_minutes > 0:
            alert.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=alert.cooldown_minutes)
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
        while True:
            await asyncio.sleep(10)
            try:
                pass
            except Exception as e:
                self.logger.error(f"Alert check error: {e}")


alert_service = AlertService()
