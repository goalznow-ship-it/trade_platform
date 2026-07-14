from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.alert import alert_service
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse, AlertTriggerResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertResponse])
async def get_alerts(active_only: bool = Query(default=False),
                      user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    alerts = await alert_service.get_alerts(user.id, db, active_only)
    return [AlertResponse(
        id=a.id, user_id=a.user_id, name=a.name, alert_type=a.alert_type,
        symbol=a.symbol, exchange=a.exchange, timeframe=a.timeframe,
        condition=a.condition, value=a.value, value_secondary=a.value_secondary,
        channels=a.channels, cooldown_minutes=a.cooldown_minutes or 0,
        max_triggers=a.max_triggers or 0, is_active=a.is_active,
        is_recurring=a.is_recurring, trigger_count=a.trigger_count or 0,
        last_triggered_at=a.last_triggered_at, created_at=a.created_at,
        updated_at=a.updated_at,
        triggers=[AlertTriggerResponse(
            id=t.id, triggered_value=t.triggered_value,
            triggered_at_price=t.triggered_at_price, channel=t.channel,
            delivered=t.delivered, triggered_at=t.triggered_at,
        ) for t in (a.triggers or [])],
    ) for a in alerts]


@router.post("", response_model=AlertResponse, status_code=201)
async def create_alert(req: AlertCreate, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    alert = await alert_service.create_alert(user.id, req.model_dump(), db)
    return AlertResponse(
        id=alert.id, user_id=alert.user_id, name=alert.name,
        alert_type=alert.alert_type, symbol=alert.symbol,
        exchange=alert.exchange, timeframe=alert.timeframe,
        condition=alert.condition, value=alert.value,
        value_secondary=alert.value_secondary, channels=alert.channels,
        cooldown_minutes=alert.cooldown_minutes or 0,
        max_triggers=alert.max_triggers or 0, is_active=alert.is_active,
        is_recurring=alert.is_recurring, trigger_count=alert.trigger_count or 0,
        last_triggered_at=alert.last_triggered_at, created_at=alert.created_at,
        updated_at=alert.updated_at, triggers=[],
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int, user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    alert = await alert_service.get_alert(alert_id, user.id, db)
    if not alert:
        raise HTTPException(404, "Alert not found")
    return AlertResponse(
        id=alert.id, user_id=alert.user_id, name=alert.name,
        alert_type=alert.alert_type, symbol=alert.symbol,
        exchange=alert.exchange, timeframe=alert.timeframe,
        condition=alert.condition, value=alert.value,
        value_secondary=alert.value_secondary, channels=alert.channels,
        cooldown_minutes=alert.cooldown_minutes or 0,
        max_triggers=alert.max_triggers or 0, is_active=alert.is_active,
        is_recurring=alert.is_recurring, trigger_count=alert.trigger_count or 0,
        last_triggered_at=alert.last_triggered_at, created_at=alert.created_at,
        updated_at=alert.updated_at,
        triggers=[AlertTriggerResponse(
            id=t.id, triggered_value=t.triggered_value,
            triggered_at_price=t.triggered_at_price, channel=t.channel,
            delivered=t.delivered, triggered_at=t.triggered_at,
        ) for t in (alert.triggers or [])],
    )


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: int, req: AlertUpdate,
                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    alert = await alert_service.update_alert(alert_id, user.id, req.model_dump(exclude_none=True), db)
    if not alert:
        raise HTTPException(404, "Alert not found")
    return AlertResponse(
        id=alert.id, user_id=alert.user_id, name=alert.name,
        alert_type=alert.alert_type, symbol=alert.symbol,
        exchange=alert.exchange, timeframe=alert.timeframe,
        condition=alert.condition, value=alert.value,
        value_secondary=alert.value_secondary, channels=alert.channels,
        cooldown_minutes=alert.cooldown_minutes or 0,
        max_triggers=alert.max_triggers or 0, is_active=alert.is_active,
        is_recurring=alert.is_recurring, trigger_count=alert.trigger_count or 0,
        last_triggered_at=alert.last_triggered_at, created_at=alert.created_at,
        updated_at=alert.updated_at, triggers=[],
    )


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    if not await alert_service.delete_alert(alert_id, user.id, db):
        raise HTTPException(404, "Alert not found")
    return {"message": "Alert deleted"}
