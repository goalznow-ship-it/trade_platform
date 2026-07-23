from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.watchlist import watchlist_service
from app.schemas.watchlist import (
    WatchlistCreate, WatchlistUpdate, WatchlistResponse,
    WatchlistSymbolCreate, WatchlistSymbolReorder, WatchlistSymbolResponse,
)

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


@router.get("", response_model=list[WatchlistResponse])
async def get_watchlists(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    watchlists = await watchlist_service.get_watchlists(user.id, db)
    result = []
    for wl in watchlists:
        result.append(WatchlistResponse(
            id=wl.id, name=wl.name, description=wl.description,
            is_default=wl.is_default, sort_order=wl.sort_order or 0,
            symbol_count=len(wl.symbols),
            symbols=[WatchlistSymbolResponse(
                id=s.id, symbol=s.symbol, exchange=s.exchange,
                is_favorite=s.is_favorite, notes=s.notes,
                sort_order=s.sort_order or 0, added_at=s.added_at,
            ) for s in wl.symbols],
            created_at=wl.created_at, updated_at=wl.updated_at,
        ))
    return result


@router.post("", response_model=WatchlistResponse, status_code=201)
async def create_watchlist(req: WatchlistCreate, user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    wl = await watchlist_service.create_watchlist(user.id, req.name, req.description, db)
    return WatchlistResponse(
        id=wl.id, name=wl.name, description=wl.description,
        is_default=wl.is_default, sort_order=wl.sort_order or 0,
        symbol_count=0, symbols=[],
        created_at=wl.created_at, updated_at=wl.updated_at,
    )


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(watchlist_id: int, req: WatchlistUpdate,
                            user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    wl = await watchlist_service.update_watchlist(watchlist_id, user.id, req.model_dump(exclude_none=True), db)
    if not wl:
        raise HTTPException(404, "Watchlist not found")
    return WatchlistResponse(
        id=wl.id, name=wl.name, description=wl.description,
        is_default=wl.is_default, sort_order=wl.sort_order or 0,
        symbol_count=len(wl.symbols),
        symbols=[WatchlistSymbolResponse(
            id=s.id, symbol=s.symbol, exchange=s.exchange,
            is_favorite=s.is_favorite, notes=s.notes,
            sort_order=s.sort_order or 0, added_at=s.added_at,
        ) for s in wl.symbols],
        created_at=wl.created_at, updated_at=wl.updated_at,
    )


@router.delete("/{watchlist_id}")
async def delete_watchlist(watchlist_id: int, user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    if not await watchlist_service.delete_watchlist(watchlist_id, user.id, db):
        raise HTTPException(404, "Watchlist not found")
    return {"message": "Watchlist deleted"}


@router.post("/{watchlist_id}/symbols")
async def add_symbol(watchlist_id: int, req: WatchlistSymbolCreate,
                      user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await watchlist_service.add_symbol(watchlist_id, user.id, req.symbol, req.exchange, req.notes, db)
    if not ws:
        raise HTTPException(404, "Watchlist not found")
    return WatchlistSymbolResponse(
        id=ws.id, symbol=ws.symbol, exchange=ws.exchange,
        is_favorite=ws.is_favorite, notes=ws.notes,
        sort_order=ws.sort_order or 0, added_at=ws.added_at,
    )


@router.delete("/{watchlist_id}/symbols/{symbol}")
async def remove_symbol(watchlist_id: int, symbol: str,
                         user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not await watchlist_service.remove_symbol(watchlist_id, user.id, symbol, db):
        raise HTTPException(404, "Symbol not found in watchlist")
    return {"message": "Symbol removed"}


@router.post("/{watchlist_id}/symbols/{symbol}/favorite")
async def toggle_favorite(watchlist_id: int, symbol: str,
                           user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await watchlist_service.toggle_favorite(watchlist_id, user.id, symbol, db)
    if not ws:
        raise HTTPException(404, "Symbol not found")
    return WatchlistSymbolResponse(
        id=ws.id, symbol=ws.symbol, exchange=ws.exchange,
        is_favorite=ws.is_favorite, notes=ws.notes,
        sort_order=ws.sort_order or 0, added_at=ws.added_at,
    )


@router.put("/{watchlist_id}/symbols/reorder")
async def reorder_symbols(watchlist_id: int, req: WatchlistSymbolReorder,
                           user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not await watchlist_service.reorder_symbols(watchlist_id, user.id, req.symbols, db):
        raise HTTPException(404, "Watchlist not found")
    return {"message": "Symbols reordered"}
