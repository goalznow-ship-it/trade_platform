from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.models.watchlist import Watchlist, WatchlistSymbol
from app.core.logging import logger


class WatchlistService:
    def __init__(self):
        self.logger = logger

    async def get_watchlists(self, user_id: int, db: AsyncSession) -> list:
        result = await db.execute(
            select(Watchlist)
            .where(Watchlist.user_id == user_id)
            .options(selectinload(Watchlist.symbols))
            .order_by(Watchlist.sort_order, Watchlist.name)
        )
        return result.scalars().all()

    async def get_watchlist(self, watchlist_id: int, user_id: int, db: AsyncSession) -> Optional[Watchlist]:
        result = await db.execute(
            select(Watchlist)
            .where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
            .options(selectinload(Watchlist.symbols))
        )
        return result.scalar_one_or_none()

    async def create_watchlist(self, user_id: int, name: str, description: Optional[str], db: AsyncSession) -> Watchlist:
        wl = Watchlist(user_id=user_id, name=name, description=description)
        db.add(wl)
        await db.commit()
        await db.refresh(wl)
        return wl

    async def update_watchlist(self, watchlist_id: int, user_id: int, data: dict, db: AsyncSession) -> Optional[Watchlist]:
        wl = await self.get_watchlist(watchlist_id, user_id, db)
        if not wl:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(wl, key, value)
        await db.commit()
        await db.refresh(wl)
        return wl

    async def delete_watchlist(self, watchlist_id: int, user_id: int, db: AsyncSession) -> bool:
        wl = await self.get_watchlist(watchlist_id, user_id, db)
        if not wl:
            return False
        await db.delete(wl)
        await db.commit()
        return True

    async def add_symbol(self, watchlist_id: int, user_id: int, symbol: str, exchange: str,
                         notes: Optional[str], db: AsyncSession) -> Optional[WatchlistSymbol]:
        wl = await self.get_watchlist(watchlist_id, user_id, db)
        if not wl:
            return None
        ws = WatchlistSymbol(watchlist_id=watchlist_id, symbol=symbol, exchange=exchange, notes=notes)
        db.add(ws)
        await db.commit()
        await db.refresh(ws)
        return ws

    async def remove_symbol(self, watchlist_id: int, user_id: int, symbol: str, db: AsyncSession) -> bool:
        wl = await self.get_watchlist(watchlist_id, user_id, db)
        if not wl:
            return False
        result = await db.execute(
            select(WatchlistSymbol).where(
                WatchlistSymbol.watchlist_id == watchlist_id,
                WatchlistSymbol.symbol == symbol,
            )
        )
        ws = result.scalar_one_or_none()
        if not ws:
            return False
        await db.delete(ws)
        await db.commit()
        return True

    async def toggle_favorite(self, watchlist_id: int, user_id: int, symbol: str, db: AsyncSession) -> Optional[WatchlistSymbol]:
        wl = await self.get_watchlist(watchlist_id, user_id, db)
        if not wl:
            return None
        result = await db.execute(
            select(WatchlistSymbol).where(
                WatchlistSymbol.watchlist_id == watchlist_id,
                WatchlistSymbol.symbol == symbol,
            )
        )
        ws = result.scalar_one_or_none()
        if not ws:
            return None
        ws.is_favorite = not ws.is_favorite
        await db.commit()
        return ws

    async def reorder_symbols(self, watchlist_id: int, user_id: int, symbols: List[str], db: AsyncSession) -> bool:
        wl = await self.get_watchlist(watchlist_id, user_id, db)
        if not wl:
            return False
        for i, sym in enumerate(symbols):
            await db.execute(
                update(WatchlistSymbol)
                .where(WatchlistSymbol.watchlist_id == watchlist_id, WatchlistSymbol.symbol == sym)
                .values(sort_order=i)
            )
        await db.commit()
        return True


watchlist_service = WatchlistService()
