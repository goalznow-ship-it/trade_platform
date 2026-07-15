from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.trade import TradeHistory, Trade, Order, Position
from app.services.exchange.manager import exchange_manager
from app.services.exchange.base import OrderRequest as ExchangeOrderRequest
from datetime import datetime, timezone
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
    reduce_only: bool = False
    margin_mode: str = "isolated"


class APIKeyRequest(BaseModel):
    exchange: str
    api_key: str
    secret_key: str
    passphrase: Optional[str] = None
    label: Optional[str] = None


class TradeNoteUpdate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[list[str]] = None


class CancelOrderRequest(BaseModel):
    exchange: str = "binance"
    symbol: str
    order_id: str


class ModifyOrderRequest(BaseModel):
    exchange: str = "binance"
    symbol: str
    order_id: str
    price: Optional[float] = None
    quantity: Optional[float] = None
    stop_price: Optional[float] = None


@router.post("/order")
async def create_order(
    req: OrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ex_req = ExchangeOrderRequest(
        symbol=req.symbol,
        side=req.side,
        quantity=req.amount,
        order_type=req.order_type,
        price=req.price,
        stop_price=req.stop_price,
        leverage=req.leverage,
        reduce_only=req.reduce_only,
        margin_mode=req.margin_mode,
    )
    result = await exchange_manager.create_order(user.id, req.exchange, ex_req, db)
    if result.error:
        raise HTTPException(400, result.error)

    order_record = Order(
        user_id=user.id,
        symbol=req.symbol,
        side=req.side,
        type=req.order_type,
        price=req.price,
        stop_price=req.stop_price,
        quantity=req.amount,
        filled_quantity=result.filled_quantity,
        status=result.status,
        exchange=req.exchange,
        exchange_order_id=result.order_id,
    )
    db.add(order_record)
    await db.commit()

    return {
        "order_id": result.order_id,
        "symbol": result.symbol,
        "side": result.side,
        "status": result.status,
        "filled_quantity": result.filled_quantity,
        "avg_price": result.avg_price,
        "error": result.error,
    }


@router.post("/cancel")
async def cancel_order(
    req: CancelOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ex = await exchange_manager.get_user_exchange(user.id, req.exchange, db)
    if not ex:
        raise HTTPException(400, "Exchange not connected")
    success = await ex.cancel_order(req.symbol, req.order_id)
    if success:
        result = await db.execute(
            select(Order).where(
                Order.exchange_order_id == req.order_id,
                Order.user_id == user.id,
            )
        )
        order = result.scalar_one_or_none()
        if order:
            order.status = "canceled"
            await db.commit()
    return {"success": success}


@router.post("/modify")
async def modify_order(
    req: ModifyOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ex = await exchange_manager.get_user_exchange(user.id, req.exchange, db)
    if not ex:
        raise HTTPException(400, "Exchange not connected")
    result = await ex.modify_order(
        req.symbol, req.order_id,
        price=req.price, quantity=req.quantity, stop_price=req.stop_price,
    )
    return {
        "order_id": result.order_id,
        "status": result.status,
        "avg_price": result.avg_price,
        "filled_quantity": result.filled_quantity,
        "error": result.error,
    }


@router.get("/positions")
async def get_positions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    positions = []
    for exchange_name in ("binance", "bybit"):
        ex = await exchange_manager.get_user_exchange(user.id, exchange_name, db)
        if ex and ex.is_connected:
            pos = await ex.get_positions()
            for p in pos:
                positions.append({
                    "symbol": p.symbol,
                    "side": p.side,
                    "size": p.size,
                    "entry_price": p.entry_price,
                    "mark_price": p.mark_price,
                    "liquidation_price": p.liquidation_price,
                    "leverage": p.leverage,
                    "margin": p.margin,
                    "unrealized_pnl": p.unrealized_pnl,
                    "realized_pnl": p.realized_pnl,
                    "exchange": exchange_name,
                })
    return positions


@router.get("/balance")
async def get_balance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    balances = {}
    for exchange_name in ("binance", "bybit"):
        ex = await exchange_manager.get_user_exchange(user.id, exchange_name, db)
        if ex and ex.is_connected:
            bal = await ex.get_balance()
            balances[exchange_name] = {
                "total": bal.total,
                "free": bal.free,
                "used": bal.used,
                "unrealized_pnl": bal.unrealized_pnl,
            }
    return balances


@router.get("/orders")
async def get_open_orders(
    exchange: str = "binance",
    symbol: str = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ex = await exchange_manager.get_user_exchange(user.id, exchange, db)
    if not ex:
        return []
    orders = await ex.get_open_orders(symbol)
    return [
        {
            "order_id": o.order_id,
            "symbol": o.symbol,
            "side": o.side,
            "order_type": o.order_type,
            "quantity": o.quantity,
            "filled_quantity": o.filled_quantity,
            "price": o.price,
            "avg_price": o.avg_price,
            "status": o.status,
        }
        for o in orders
    ]


@router.post("/leverage")
async def set_leverage(
    exchange: str = "binance",
    symbol: str = None,
    leverage: int = 1,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ex = await exchange_manager.get_user_exchange(user.id, exchange, db)
    if not ex:
        raise HTTPException(400, "Exchange not connected")
    success = await ex.set_leverage(symbol, leverage)
    return {"success": success}


@router.post("/margin-mode")
async def set_margin_mode(
    exchange: str = "binance",
    symbol: str = None,
    mode: str = "isolated",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ex = await exchange_manager.get_user_exchange(user.id, exchange, db)
    if not ex:
        raise HTTPException(400, "Exchange not connected")
    success = await ex.set_margin_mode(symbol, mode)
    return {"success": success}


@router.get("/history")
async def get_trade_history(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    symbol: str = Query(default=None),
    side: str = Query(default=None),
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
async def save_api_keys(
    req: APIKeyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await exchange_manager.save_credentials(
        user.id, req.exchange, req.api_key, req.secret_key,
        passphrase=req.passphrase, label=req.label, db=db,
    )
    if not success:
        raise HTTPException(400, "Failed to save API keys")
    return {"message": "API keys saved securely"}


@router.delete("/api-keys/{exchange}")
async def remove_api_keys(
    exchange: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await exchange_manager.remove_credentials(user.id, exchange, db)
    return {"message": "API keys removed"}
