from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.trade import TradeHistory, Trade
from app.services.trading import trading_service
import csv, io

router = APIRouter(prefix="/trade", tags=["Trading"])

class OrderRequest(BaseModel):
    exchange: str = "binance"
    symbol: str
    side: str
    amount: float
    order_type: str = "market"
    price: Optional[float] = None
    stop_price: Optional[float] = None
    leverage: int = 1

class APIKeyRequest(BaseModel):
    exchange: str
    api_key: str
    secret_key: str

class TradeNoteUpdate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[list[str]] = None

@router.post("/order")
async def create_order(req: OrderRequest, user: User = Depends(get_current_user)):
    api_key = None
    secret_key = None
    if req.exchange == 'binance':
        api_key = user.binance_api_key
        secret_key = user.binance_secret_key
    if not api_key or not secret_key:
        raise HTTPException(400, "Exchange API keys not configured")
    return await trading_service.create_order(
        req.exchange, req.symbol, req.side, req.amount,
        req.order_type, req.price, req.stop_price, req.leverage,
        api_key, secret_key
    )

@router.post("/cancel")
async def cancel_order(exchange: str, symbol: str, order_id: str, user: User = Depends(get_current_user)):
    api_key = user.binance_api_key if exchange == 'binance' else user.bybit_api_key
    secret_key = user.binance_secret_key if exchange == 'binance' else user.bybit_secret_key
    return await trading_service.cancel_order(exchange, symbol, order_id, api_key, secret_key)

@router.get("/positions")
async def get_positions(user: User = Depends(get_current_user)):
    positions = []
    if user.binance_api_key:
        bp = await trading_service.get_positions('binance', user.binance_api_key, user.binance_secret_key)
        positions.extend(bp)
    if user.bybit_api_key:
        byp = await trading_service.get_positions('bybit', user.bybit_api_key, user.bybit_secret_key)
        positions.extend(byp)
    return positions

@router.get("/balance")
async def get_balance(user: User = Depends(get_current_user)):
    balances = {}
    if user.binance_api_key:
        balances['binance'] = await trading_service.get_balance('binance', user.binance_api_key, user.binance_secret_key)
    if user.bybit_api_key:
        balances['bybit'] = await trading_service.get_balance('bybit', user.bybit_api_key, user.bybit_secret_key)
    return balances

@router.get("/orders")
async def get_open_orders(exchange: str = "binance", symbol: str = None, user: User = Depends(get_current_user)):
    api_key = user.binance_api_key if exchange == 'binance' else user.bybit_api_key
    secret_key = user.binance_secret_key if exchange == 'binance' else user.bybit_secret_key
    return await trading_service.get_open_orders(exchange, symbol, api_key, secret_key)

@router.get("/history")
async def get_trade_history(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    symbol: str = Query(default=None),
    side: str = Query(default=None, pattern="^(long|short)?$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(TradeHistory).where(TradeHistory.user_id == user.id)
    if symbol:
        q = q.where(TradeHistory.symbol == symbol.replace("-", "/"))
    if side:
        q = q.where(TradeHistory.side == side)
    q = q.order_by(TradeHistory.closed_at.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    trades = result.scalars().all()
    return [
        {
            "id": t.id, "symbol": t.symbol, "side": t.side, "type": t.type,
            "quantity": t.quantity, "entry_price": t.entry_price,
            "exit_price": t.exit_price, "pnl": t.pnl, "pnl_percent": t.pnl_percent,
            "roi": t.roi, "leverage": t.leverage, "duration_minutes": t.duration_minutes,
            "stop_loss": t.stop_loss, "take_profit": t.take_profit,
            "risk_reward": t.risk_reward, "reason": t.reason,
            "exchange": t.exchange, "notes": t.notes, "tags": t.tags,
            "closed_at": str(t.closed_at) if t.closed_at else None,
        }
        for t in trades
    ]


@router.get("/history/{trade_id}")
async def get_trade_detail(
    trade_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TradeHistory).where(TradeHistory.id == trade_id, TradeHistory.user_id == user.id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Trade not found")
    return {
        "id": t.id, "symbol": t.symbol, "side": t.side, "type": t.type,
        "quantity": t.quantity, "entry_price": t.entry_price,
        "exit_price": t.exit_price, "pnl": t.pnl, "pnl_percent": t.pnl_percent,
        "roi": t.roi, "leverage": t.leverage, "duration_minutes": t.duration_minutes,
        "stop_loss": t.stop_loss, "take_profit": t.take_profit,
        "risk_reward": t.risk_reward, "reason": t.reason,
        "exchange": t.exchange, "notes": t.notes, "tags": t.tags,
        "closed_at": str(t.closed_at) if t.closed_at else None,
    }


@router.put("/history/{trade_id}")
async def update_trade_notes(
    trade_id: int, req: TradeNoteUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TradeHistory).where(TradeHistory.id == trade_id, TradeHistory.user_id == user.id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Trade not found")
    if req.notes is not None:
        t.notes = req.notes
    if req.tags is not None:
        t.tags = req.tags
    await db.commit()
    return {"message": "Trade updated"}


@router.delete("/history/{trade_id}")
async def delete_trade_history(
    trade_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TradeHistory).where(TradeHistory.id == trade_id, TradeHistory.user_id == user.id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Trade not found")
    await db.delete(t)
    await db.commit()
    return {"message": "Trade deleted"}


@router.get("/history/export/csv")
async def export_trades_csv(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TradeHistory).where(TradeHistory.user_id == user.id)
        .order_by(TradeHistory.closed_at.desc())
    )
    trades = result.scalars().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Symbol", "Side", "Entry", "Exit", "PnL", "PnL%", "ROI",
                      "Leverage", "Duration", "Risk/Reward", "Exchange", "Reason", "Closed At"])
    for t in trades:
        writer.writerow([
            t.symbol, t.side, t.entry_price, t.exit_price, t.pnl,
            t.pnl_percent, t.roi, t.leverage, t.duration_minutes,
            t.risk_reward, t.exchange, t.reason,
            str(t.closed_at) if t.closed_at else "",
        ])
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trade_history.csv"},
    )


@router.post("/api-keys")
async def save_api_keys(req: APIKeyRequest, user: User = Depends(get_current_user)):
    if req.exchange == 'binance':
        user.binance_api_key = req.api_key
        user.binance_secret_key = req.secret_key
    elif req.exchange == 'bybit':
        user.bybit_api_key = req.api_key
        user.bybit_secret_key = req.secret_key
    else:
        raise HTTPException(400, "Unsupported exchange")
    return {"message": "API keys saved"}
