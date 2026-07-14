from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.paper_trading import PaperAccount, PaperPosition, PaperOrder
from app.services.paper_trading import paper_trading_service
from app.schemas.paper_trading import (
    PaperOrderCreate, PaperAccountResponse, PaperPositionResponse,
    PaperOrderResponse, PaperResetResponse,
)

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
async def get_paper_orders(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await paper_trading_service.get_or_create_account(user.id, db)
    result = await db.execute(
        select(PaperOrder).where(PaperOrder.account_id == account.id)
        .order_by(PaperOrder.created_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.post("/orders", status_code=201)
async def create_paper_order(req: PaperOrderCreate,
                              user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await paper_trading_service.create_order(user.id, req.model_dump(), db)
    return result


@router.post("/positions/{position_id}/close")
async def close_paper_position(position_id: int,
                                user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await paper_trading_service.close_position(user.id, position_id, db)
    if not result:
        raise HTTPException(404, "Position not found")
    return result
