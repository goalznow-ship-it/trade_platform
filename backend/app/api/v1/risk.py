from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.risk import risk_service
from app.schemas.risk import RiskProfileCreate, RiskProfileResponse, RiskSnapshotResponse

router = APIRouter(prefix="/risk", tags=["Risk Management"])


@router.get("/dashboard")
async def get_risk_dashboard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await risk_service.get_dashboard(user.id, db)


@router.get("/profile", response_model=RiskProfileResponse)
async def get_risk_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await risk_service.get_profile(user.id, db)


@router.put("/profile", response_model=RiskProfileResponse)
async def update_risk_profile(req: RiskProfileCreate,
                               user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await risk_service.update_profile(user.id, req.model_dump(exclude_none=True), db)


@router.get("/exposure")
async def get_exposure(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.trade import Position
    result = await db.execute(
        select(Position).where(Position.user_id == user.id, Position.is_open == True)
    )
    positions = result.scalars().all()
    total = sum(p.size * p.mark_price for p in positions if p.size and p.mark_price) if positions else 0
    return {
        "total_exposure": total,
        "positions": [
            {"symbol": p.symbol, "side": p.side, "size": p.size,
             "entry_price": p.entry_price, "mark_price": p.mark_price,
             "unrealized_pnl": p.unrealized_pnl}
            for p in positions
        ] if positions else [],
    }


@router.get("/snapshot", response_model=RiskSnapshotResponse)
async def get_risk_snapshot(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await risk_service.compute_snapshot(user.id, db)
