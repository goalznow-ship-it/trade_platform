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
from datetime import datetime, timezone
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
    exchange: str = Field(pattern="^(binance|bybit)$")
    api_key: str = Field(min_length=8, max_length=255)
    secret_key: str = Field(min_length=8, max_length=255)
    passphrase: Optional[str] = None
    label: Optional[str] = Field(default=None, max_length=100)


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


class ClosePositionRequest(BaseModel):
    exchange: str = Field(default="binance", pattern="^(binance|bybit)$")
    symbol: str = Field(min_length=3, max_length=30)
    percentage: int = Field(default=100, ge=1, le=100)
    client_order_id: str = Field(
        min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$",
    )


def _canonical_symbol(symbol: str) -> str:
    return symbol.upper().split(":")[0].replace("/", "").replace("-", "")


@router.get("/status")
async def trading_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.exchange import ExchangeCredentials

    result = await db.execute(
        select(ExchangeCredentials.exchange).where(
            ExchangeCredentials.user_id == user.id,
            ExchangeCredentials.is_active == True,
        )
    )
    configured_exchanges = list(result.scalars().all())
    from app.core.kill_switch import get_kill_switch_status
    state, _ = await get_kill_switch_status()
    # "unknown" → fail-closed for accepting orders; surface the
    # underlying state to the UI so the user can see Redis is down.
    kill_switch_active = (state == "active")
    kill_switch_unknown = (state == "unknown")
    return {
        "default_mode": "paper",
        "live_trading_enabled": settings.TRADING_ENABLED,
        "kill_switch_active": kill_switch_active,
        "kill_switch_state": state,
        "kill_switch_unknown": kill_switch_unknown,
        "accepting_live_orders": (
            settings.TRADING_ENABLED
            and not kill_switch_active
            and bool(configured_exchanges)
        ),
        "configured_exchanges": configured_exchanges,
    }


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
    from app.core.kill_switch import is_kill_switch_active
    if await is_kill_switch_active():
        raise HTTPException(503, "Emergency trading kill switch is active")

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


@router.post("/order/preview")
async def preview_order(
    req: OrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate and price an order without creating or persisting it."""
    from app.services.execution_engine import execution_engine

    exchange = await exchange_manager.get_user_exchange(user.id, req.exchange, db)
    if not exchange or not exchange.is_connected:
        raise HTTPException(400, "Exchange not connected")

    ticker = await exchange.get_ticker(req.symbol)
    entry_price = req.price or (ticker or {}).get("price")
    if not entry_price:
        raise HTTPException(503, "Current market price unavailable")

    balance = await exchange.get_balance()
    open_positions = await exchange.get_positions()
    portfolio = {
        "symbols": [position.symbol for position in open_positions],
        "exposures": {
            position.symbol: abs(position.size * position.mark_price)
            for position in open_positions
        },
    }
    trade_request = {
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
    }
    approval = (
        {"approved": True, "risk_score": 0, "risk_label": "reduce_only", "rejection_reasons": []}
        if req.reduce_only
        else await execution_engine.get_trade_approval(trade_request)
    )

    notional = req.amount * entry_price
    margin = notional / req.leverage
    fee_rate = 0.0004
    estimated_fees = notional * fee_rate * 2
    stop_distance = abs(entry_price - req.stop_loss) if req.stop_loss else 0
    target_distance = abs(req.take_profit - entry_price) if req.take_profit else 0
    max_loss = stop_distance * req.amount + estimated_fees
    potential_profit = max(target_distance * req.amount - estimated_fees, 0)
    risk_reward = potential_profit / max_loss if max_loss > 0 else None
    execution_plan = approval.get("execution_plan") or {}
    slippage = execution_plan.get("estimated_slippage")
    if not slippage:
        slippage = await execution_engine.estimate_slippage(req.symbol, req.amount, req.side)
    liquidation_check = (approval.get("validation") or {}).get("checks", {}).get("liquidation_distance", {})

    kill_switch_active = False
    from app.core.kill_switch import get_kill_switch_status
    state, _ = await get_kill_switch_status()
    kill_switch_active = (state == "active")

    return {
        "preview_only": True,
        "exchange": req.exchange,
        "symbol": req.symbol,
        "side": req.side,
        "order_type": req.order_type,
        "quantity": req.amount,
        "entry_price": entry_price,
        "notional": round(notional, 8),
        "required_margin": round(margin, 8),
        "estimated_fees": round(estimated_fees, 8),
        "fee_rate": fee_rate,
        "estimated_slippage": slippage,
        "liquidation_price": liquidation_check.get("liquidation_price"),
        "max_loss_at_stop": round(max_loss, 8),
        "potential_profit_at_target": round(potential_profit, 8),
        "risk_reward": round(risk_reward, 3) if risk_reward is not None else None,
        "approval": approval,
        "can_submit_live": (
            settings.TRADING_ENABLED
            and not kill_switch_active
            and approval.get("approved", False)
        ),
        "live_trading_enabled": settings.TRADING_ENABLED,
        "kill_switch_active": kill_switch_active,
        "market_data_timestamp": datetime.now(timezone.utc).isoformat(),
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


@router.post("/positions/close")
async def close_position(
    req: ClosePositionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Close all or part of an existing position using a reduce-only market order."""
    if not settings.TRADING_ENABLED:
        raise HTTPException(503, "Live trading is disabled by server configuration")
    from app.core.kill_switch import is_kill_switch_active
    if await is_kill_switch_active():
        raise HTTPException(503, "Emergency trading kill switch is active")

    existing = await db.execute(
        select(Order).where(
            Order.user_id == user.id,
            Order.client_order_id == req.client_order_id,
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
            "idempotent_replay": True,
        }

    exchange = await exchange_manager.get_user_exchange(user.id, req.exchange, db)
    if not exchange or not exchange.is_connected:
        raise HTTPException(400, "Exchange not connected")

    positions = await exchange.get_positions(req.symbol)
    target = next(
        (position for position in positions
         if _canonical_symbol(position.symbol) == _canonical_symbol(req.symbol)),
        None,
    )
    if target is None or target.size <= 0:
        raise HTTPException(404, "Open position not found")
    if target.side not in ("long", "short"):
        raise HTTPException(409, "Position side is unavailable")

    quantity = target.size * req.percentage / 100
    if quantity <= 0 or quantity > target.size:
        raise HTTPException(422, "Close quantity exceeds open position")
    close_side = "sell" if target.side == "long" else "buy"
    ex_req = ExchangeOrderRequest(
        symbol=req.symbol,
        side=close_side,
        quantity=quantity,
        order_type="market",
        leverage=max(target.leverage, 1),
        reduce_only=True,
        margin_mode="isolated" if target.isolated else "cross",
        client_order_id=req.client_order_id,
    )
    result = await exchange_manager.create_order(user.id, req.exchange, ex_req, db)
    if result.error:
        raise HTTPException(400, result.error)

    order_record = Order(
        user_id=user.id,
        symbol=req.symbol,
        side=close_side,
        type="market",
        quantity=quantity,
        filled_quantity=result.filled_quantity,
        status=result.status,
        exchange=req.exchange,
        exchange_order_id=result.order_id,
        client_order_id=req.client_order_id,
    )
    db.add(order_record)
    await db.commit()
    return {
        "order_id": result.order_id,
        "symbol": result.symbol,
        "side": result.side,
        "status": result.status,
        "requested_percentage": req.percentage,
        "requested_quantity": quantity,
        "filled_quantity": result.filled_quantity,
        "avg_price": result.avg_price,
        "reduce_only": True,
        "idempotent_replay": False,
    }


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


@router.get("/api-keys")
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.exchange import ExchangeCredentials

    result = await db.execute(
        select(ExchangeCredentials).where(
            ExchangeCredentials.user_id == user.id,
            ExchangeCredentials.is_active == True,
        ).order_by(ExchangeCredentials.exchange)
    )
    return [
        {
            "exchange": credential.exchange,
            "label": credential.label,
            "configured": True,
            "last_used": credential.last_used,
            "created_at": credential.created_at,
            "updated_at": credential.updated_at,
        }
        for credential in result.scalars().all()
    ]


@router.post("/api-keys/test")
async def test_api_keys(
    req: APIKeyRequest,
    user: User = Depends(get_current_user),
):
    connected = await exchange_manager.test_credentials(
        req.exchange, req.api_key, req.secret_key, req.passphrase,
    )
    if not connected:
        raise HTTPException(400, "Exchange connection failed")
    return {"exchange": req.exchange, "connected": True}


@router.post("/api-keys")
async def save_api_keys(
    req: APIKeyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connected = await exchange_manager.test_credentials(
        req.exchange, req.api_key, req.secret_key, req.passphrase,
    )
    if not connected:
        raise HTTPException(400, "Exchange connection failed; credentials were not saved")
    success = await exchange_manager.save_credentials(
        user.id, req.exchange, req.api_key, req.secret_key,
        passphrase=req.passphrase, label=req.label, db=db,
    )
    if not success:
        raise HTTPException(400, "Failed to save API keys")
    return {"message": "API keys verified and saved securely", "exchange": req.exchange}


@router.delete("/api-keys/{exchange}")
async def remove_api_keys(
    exchange: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if exchange not in {"binance", "bybit"}:
        raise HTTPException(400, "Unsupported exchange")
    removed = await exchange_manager.remove_credentials(user.id, exchange, db)
    if not removed:
        raise HTTPException(400, "Failed to remove API keys")
    return {"message": "API keys removed"}
