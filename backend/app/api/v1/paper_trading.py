from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.paper_trading import PaperPosition, PaperOrder
from app.services.paper_trading import paper_trading_service
from app.schemas.paper_trading import (
    PaperOrderCreate, PaperAccountResponse, PaperPositionResponse,
    PaperOrderResponse, PaperResetResponse,
)
from typing import Optional

router = APIRouter(prefix="/paper", tags=["Paper Trading"])


@router.get("/account", response_model=PaperAccountResponse)
async def get_paper_account(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await paper_trading_service.get_or_create_account(user.id, db)
    return account


@router.post("/account/reset", response_model=PaperResetResponse)
async def reset_paper_account(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await paper_trading_service.reset_account(user.id, db)
    return {"message": "Paper account reset", "account": account}


@router.get("/positions", response_model=list[PaperPositionResponse])
async def get_paper_positions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await paper_trading_service.get_or_create_account(user.id, db)
    result = await db.execute(
        select(PaperPosition).where(
            PaperPosition.account_id == account.id, PaperPosition.is_open == True
        )
    )
    return result.scalars().all()


@router.get("/orders", response_model=list[PaperOrderResponse])
async def get_paper_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
):
    account = await paper_trading_service.get_or_create_account(user.id, db)
    q = select(PaperOrder).where(PaperOrder.account_id == account.id)
    if status:
        q = q.where(PaperOrder.status == status)
    q = q.order_by(PaperOrder.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/orders", status_code=201)
async def create_paper_order(
    req: PaperOrderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await paper_trading_service.create_order(user.id, req.model_dump(), db)
    return result


@router.post("/positions/{position_id}/close")
async def close_paper_position(
    position_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await paper_trading_service.close_position(user.id, position_id, db)
    if not result:
        raise HTTPException(404, "Position not found")
    return result


@router.delete("/orders/{order_id}")
async def cancel_paper_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await paper_trading_service.get_or_create_account(user.id, db)
    result = await db.execute(
        select(PaperOrder).where(
            PaperOrder.id == order_id,
            PaperOrder.account_id == account.id,
            PaperOrder.status == "pending",
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pending order not found")
    order.status = "canceled"
    await db.commit()
    return {"message": "Order canceled"}


@router.put("/positions/{position_id}/sl-tp")
async def update_position_sl_tp(
    position_id: int,
    stop_loss: Optional[float] = Query(default=None),
    take_profit: Optional[float] = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await paper_trading_service.get_or_create_account(user.id, db)
    result = await db.execute(
        select(PaperPosition).where(
            PaperPosition.id == position_id,
            PaperPosition.account_id == account.id,
            PaperPosition.is_open == True,
        )
    )
    pos = result.scalar_one_or_none()
    if not pos:
        raise HTTPException(404, "Open position not found")
    if stop_loss is not None:
        pos.stop_loss = stop_loss
    if take_profit is not None:
        pos.take_profit = take_profit
    await db.commit()
    return {"message": "SL/TP updated", "stop_loss": pos.stop_loss, "take_profit": pos.take_profit}


@router.get("/closed-positions")
async def get_closed_positions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=200),
):
    account = await paper_trading_service.get_or_create_account(user.id, db)
    result = await db.execute(
        select(PaperPosition).where(
            PaperPosition.account_id == account.id,
            PaperPosition.is_open == False,
        )
        .order_by(PaperPosition.closed_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": p.id,
            "symbol": p.symbol,
            "side": p.side,
            "size": p.size,
            "entry_price": p.entry_price,
            "exit_price": p.mark_price,
            "pnl": p.realized_pnl,
            "leverage": p.leverage,
            "stop_loss": p.stop_loss,
            "take_profit": p.take_profit,
            "opened_at": str(p.opened_at) if p.opened_at else None,
            "closed_at": str(p.closed_at) if p.closed_at else None,
        }
        for p in result.scalars().all()
    ]
