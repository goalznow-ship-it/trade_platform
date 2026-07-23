from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.redis import redis_client
from app.models.user import User
from app.models.trade import TradeHistory, Order
from app.services.exchange.manager import exchange_manager
from app.services.exchange.base import OrderRequest as ExchangeOrderRequest
import csv
import io

router = APIRouter(prefix="/trade", tags=["Trading"])


class OrderRequest(BaseModel):
    exchange: str = Field(default="binance", pattern="^binance$")
    symbol: str = Field(min_length=3, max_length=20)
    side: str = Field(pattern="^(buy|sell)$")
    amount: float = Field(gt=0)
    order_type: str = Field(default="market", pattern="^(market|limit|stop|stop_market|take_profit_market)$")
    price: Optional[float] = Field(default=None, gt=0)
    stop_price: Optional[float] = Field(default=None, gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    leverage: int = Field(default=1, ge=1, le=125)
    reduce_only: bool = False
    margin_mode: str = Field(default="isolated", pattern="^(isolated|cross)$")
    client_order_id: Optional[str] = Field(
        default=None, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$",
    )

    @model_validator(mode="after")
    def validate_protection(self):
        if self.order_type == "limit" and self.price is None:
            raise ValueError("price is required for limit orders")
        if not self.reduce_only and (self.stop_loss is None or self.take_profit is None):
            raise ValueError("stop_loss and take_profit are required for opening orders")
        return self


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
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.execution_engine import execution_engine

    if not settings.TRADING_ENABLED:
        raise HTTPException(503, "Live trading is disabled by server configuration")
    try:
        if await redis_client.get("trading:kill_switch") == "1":
            raise HTTPException(503, "Emergency trading kill switch is active")
    except HTTPException:
        raise
    except Exception:
        pass

    client_order_id = idempotency_key or req.client_order_id
    if client_order_id:
        existing = await db.execute(
            select(Order).where(
                Order.user_id == user.id,
                Order.client_order_id == client_order_id,
            )
        )
        existing_order = existing.scalar_one_or_none()
        if existing_order:
            return {
                "order_id": existing_order.exchange_order_id,
                "symbol": existing_order.symbol,
                "side": existing_order.side,
                "status": existing_order.status,
                "filled_quantity": existing_order.filled_quantity,
                "avg_price": existing_order.price,
                "idempotent_replay": True,
            }

    exchange = await exchange_manager.get_user_exchange(user.id, req.exchange, db)
    if not exchange:
        raise HTTPException(400, "Exchange not connected")
    ticker = await exchange.get_ticker(req.symbol)
    entry_price = req.price or (ticker or {}).get("price")
    balance = await exchange.get_balance()
    if not req.reduce_only:
        if not entry_price:
            raise HTTPException(503, "Current market price unavailable")
        open_positions = await exchange.get_positions()
        portfolio = {
            "symbols": [position.symbol for position in open_positions],
            "exposures": {
                position.symbol: abs(position.size * position.mark_price)
                for position in open_positions
            },
        }
        approval = await execution_engine.get_trade_approval({
            "symbol": req.symbol,
            "direction": "long" if req.side == "buy" else "short",
            "entry_price": entry_price,
            "price": entry_price,
            "stop_loss": req.stop_loss,
            "take_profit": req.take_profit,
            "leverage": req.leverage,
            "balance": balance.free,
            "quantity": req.amount,
            "portfolio": portfolio,
        })
        if not approval.get("approved", False):
            raise HTTPException(422, {
                "message": "Trade rejected by execution gate",
                "reasons": approval.get("rejection_reasons", []),
                "risk_score": approval.get("risk_score"),
            })

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
        client_order_id=client_order_id,
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
        client_order_id=client_order_id,
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


@router.post("/orders/reconcile")
async def reconcile_orders(
    exchange: str = Query(default="binance", pattern="^binance$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ex = await exchange_manager.get_user_exchange(user.id, exchange, db)
    if not ex:
        raise HTTPException(400, "Exchange not connected")
    result = await db.execute(
        select(Order).where(
            Order.user_id == user.id,
            Order.exchange == exchange,
            Order.status.in_(("pending", "open", "new", "partially_filled")),
        )
    )
    local_orders = result.scalars().all()
    reconciled = []
    unavailable = []
    for local_order in local_orders:
        if not local_order.exchange_order_id:
            unavailable.append(local_order.id)
            continue
        remote = await ex.get_order(local_order.symbol, local_order.exchange_order_id)
        if remote is None:
            unavailable.append(local_order.id)
            continue
        changed = (
            local_order.status != remote.status
            or local_order.filled_quantity != remote.filled_quantity
        )
        local_order.status = remote.status
        local_order.filled_quantity = remote.filled_quantity
        if remote.avg_price is not None:
            local_order.price = remote.avg_price
        if changed:
            reconciled.append(local_order.id)
    await db.commit()
    return {
        "checked": len(local_orders),
        "updated": len(reconciled),
        "updated_order_ids": reconciled,
        "unavailable_order_ids": unavailable,
    }


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
