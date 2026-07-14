from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.admin import Notification
from app.core.logging import logger
from app.core.websocket_manager import ws_manager
from app.core.redis import redis_client


class NotificationService:
    def __init__(self):
        self.logger = logger

    async def get_notifications(self, user_id: int, db: AsyncSession, limit: int = 50,
                                offset: int = 0, unread_only: bool = False,
                                notification_type: Optional[str] = None) -> list:
        q = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            q = q.where(Notification.is_read == False)
        if notification_type:
            q = q.where(Notification.type == notification_type)
        q = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(q)
        return result.scalars().all()

    async def create_notification(self, user_id: int, notification_type: str, title: str,
                                   message: Optional[str] = None, channel: str = "in_app",
                                   related_id: Optional[int] = None, db: Optional[AsyncSession] = None) -> Notification:
        notification = Notification(
            user_id=user_id, type=notification_type, title=title,
            message=message, channel=channel, related_id=related_id,
        )
        if db:
            db.add(notification)
            await db.commit()
            await db.refresh(notification)

        await ws_manager.send_to_user(
            user_id, "notification", {
                "id": getattr(notification, 'id', None),
                "type": notification_type,
                "title": title,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, channel="notifications"
        )
        return notification

    async def mark_read(self, notification_id: int, user_id: int, db: AsyncSession) -> bool:
        result = await db.execute(
            update(Notification).where(
                Notification.id == notification_id, Notification.user_id == user_id
            ).values(is_read=True)
        )
        await db.commit()
        return result.rowcount > 0

    async def mark_all_read(self, user_id: int, db: AsyncSession):
        await db.execute(
            update(Notification).where(
                Notification.user_id == user_id, Notification.is_read == False
            ).values(is_read=True)
        )
        await db.commit()

    async def delete_notification(self, notification_id: int, user_id: int, db: AsyncSession) -> bool:
        result = await db.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return False
        await db.delete(notification)
        await db.commit()
        return True

    async def get_unread_count(self, user_id: int, db: AsyncSession) -> int:
        result = await db.execute(
            select(Notification).where(Notification.user_id == user_id, Notification.is_read == False)
        )
        return len(result.scalars().all())


notification_service = NotificationService()
