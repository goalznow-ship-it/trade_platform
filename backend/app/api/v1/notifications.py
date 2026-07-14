from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.notification import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def get_notifications(unread_only: bool = Query(default=False),
                             notification_type: str = Query(default=None),
                             limit: int = Query(default=50, ge=1, le=200),
                             offset: int = Query(default=0, ge=0),
                             user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    notifications = await notification_service.get_notifications(
        user.id, db, limit, offset, unread_only, notification_type,
    )
    return [
        {
            "id": n.id, "type": n.type, "title": n.title,
            "message": n.message, "channel": n.channel,
            "is_read": n.is_read, "related_id": n.related_id,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@router.get("/unread-count")
async def get_unread_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    count = await notification_service.get_unread_count(user.id, db)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: int, user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    if not await notification_service.mark_read(notification_id, user.id, db):
        raise HTTPException(404, "Notification not found")
    return {"message": "Marked as read"}


@router.post("/read-all")
async def mark_all_read(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await notification_service.mark_all_read(user.id, db)
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: int, user: User = Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    if not await notification_service.delete_notification(notification_id, user.id, db):
        raise HTTPException(404, "Notification not found")
    return {"message": "Notification deleted"}
