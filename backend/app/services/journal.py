from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.journal import TradeJournal
from app.core.logging import logger


class JournalService:
    def __init__(self):
        self.logger = logger

    async def get_entries(self, user_id: int, db: AsyncSession, limit: int = 50, offset: int = 0) -> list:
        result = await db.execute(
            select(TradeJournal)
            .where(TradeJournal.user_id == user_id)
            .order_by(TradeJournal.created_at.desc())
            .offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def get_entry(self, entry_id: int, user_id: int, db: AsyncSession):
        result = await db.execute(
            select(TradeJournal).where(TradeJournal.id == entry_id, TradeJournal.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_entry(self, user_id: int, data: dict, db: AsyncSession) -> TradeJournal:
        entry = TradeJournal(user_id=user_id, **data)
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    async def update_entry(self, entry_id: int, user_id: int, data: dict, db: AsyncSession):
        entry = await self.get_entry(entry_id, user_id, db)
        if not entry:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(entry, key, value)
        await db.commit()
        await db.refresh(entry)
        return entry

    async def delete_entry(self, entry_id: int, user_id: int, db: AsyncSession) -> bool:
        entry = await self.get_entry(entry_id, user_id, db)
        if not entry:
            return False
        await db.delete(entry)
        await db.commit()
        return True


journal_service = JournalService()
