from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.journal import journal_service
from app.schemas.journal import JournalCreate, JournalUpdate, JournalResponse

router = APIRouter(prefix="/journal", tags=["Trading Journal"])


@router.get("", response_model=list[JournalResponse])
async def get_journal_entries(limit: int = Query(default=50, ge=1, le=200),
                                offset: int = Query(default=0, ge=0),
                                user: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)):
    entries = await journal_service.get_entries(user.id, db, limit, offset)
    return [JournalResponse(
        id=e.id, user_id=e.user_id, trade_id=e.trade_id,
        symbol=e.symbol, side=e.side, notes=e.notes, lessons=e.lessons,
        emotion=e.emotion, mistakes=e.mistakes or [], tags=e.tags or [],
        strategy=e.strategy, setup_description=e.setup_description,
        entry_reason=e.entry_reason, exit_reason=e.exit_reason,
        rating=e.rating, win_loss_reason=e.win_loss_reason,
        screenshot_urls=e.screenshot_urls or [],
        executed_plan=e.executed_plan, followed_rules=e.followed_rules,
        psychological_state=e.psychological_state,
        created_at=e.created_at, updated_at=e.updated_at,
    ) for e in entries]


@router.post("", response_model=JournalResponse, status_code=201)
async def create_journal_entry(req: JournalCreate,
                                user: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)):
    entry = await journal_service.create_entry(user.id, req.model_dump(), db)
    return JournalResponse(
        id=entry.id, user_id=entry.user_id, trade_id=entry.trade_id,
        symbol=entry.symbol, side=entry.side, notes=entry.notes,
        lessons=entry.lessons, emotion=entry.emotion,
        mistakes=entry.mistakes or [], tags=entry.tags or [],
        strategy=entry.strategy, setup_description=entry.setup_description,
        entry_reason=entry.entry_reason, exit_reason=entry.exit_reason,
        rating=entry.rating, win_loss_reason=entry.win_loss_reason,
        screenshot_urls=entry.screenshot_urls or [],
        executed_plan=entry.executed_plan, followed_rules=entry.followed_rules,
        psychological_state=entry.psychological_state,
        created_at=entry.created_at, updated_at=entry.updated_at,
    )


@router.get("/{entry_id}", response_model=JournalResponse)
async def get_journal_entry(entry_id: int, user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    entry = await journal_service.get_entry(entry_id, user.id, db)
    if not entry:
        raise HTTPException(404, "Journal entry not found")
    return JournalResponse(
        id=entry.id, user_id=entry.user_id, trade_id=entry.trade_id,
        symbol=entry.symbol, side=entry.side, notes=entry.notes,
        lessons=entry.lessons, emotion=entry.emotion,
        mistakes=entry.mistakes or [], tags=entry.tags or [],
        strategy=entry.strategy, setup_description=entry.setup_description,
        entry_reason=entry.entry_reason, exit_reason=entry.exit_reason,
        rating=entry.rating, win_loss_reason=entry.win_loss_reason,
        screenshot_urls=entry.screenshot_urls or [],
        executed_plan=entry.executed_plan, followed_rules=entry.followed_rules,
        psychological_state=entry.psychological_state,
        created_at=entry.created_at, updated_at=entry.updated_at,
    )


@router.put("/{entry_id}", response_model=JournalResponse)
async def update_journal_entry(entry_id: int, req: JournalUpdate,
                                user: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)):
    entry = await journal_service.update_entry(entry_id, user.id, req.model_dump(exclude_none=True), db)
    if not entry:
        raise HTTPException(404, "Journal entry not found")
    return JournalResponse(
        id=entry.id, user_id=entry.user_id, trade_id=entry.trade_id,
        symbol=entry.symbol, side=entry.side, notes=entry.notes,
        lessons=entry.lessons, emotion=entry.emotion,
        mistakes=entry.mistakes or [], tags=entry.tags or [],
        strategy=entry.strategy, setup_description=entry.setup_description,
        entry_reason=entry.entry_reason, exit_reason=entry.exit_reason,
        rating=entry.rating, win_loss_reason=entry.win_loss_reason,
        screenshot_urls=entry.screenshot_urls or [],
        executed_plan=entry.executed_plan, followed_rules=entry.followed_rules,
        psychological_state=entry.psychological_state,
        created_at=entry.created_at, updated_at=entry.updated_at,
    )


@router.delete("/{entry_id}")
async def delete_journal_entry(entry_id: int, user: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)):
    if not await journal_service.delete_entry(entry_id, user.id, db):
        raise HTTPException(404, "Journal entry not found")
    return {"message": "Journal entry deleted"}
