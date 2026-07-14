from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.trade import Trade, TradeHistory
from app.models.portfolio import Portfolio, PortfolioAsset

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

@router.get("/summary")
async def get_portfolio_summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    open_trades = await db.execute(
        select(Trade).where(Trade.user_id == user.id, Trade.status == 'open')
    )
    open_positions = open_trades.scalars().all()
    trade_history = await db.execute(
        select(TradeHistory).where(TradeHistory.user_id == user.id).order_by(TradeHistory.closed_at.desc()).limit(50)
    )
    history = trade_history.scalars().all()

    total_pnl = sum(t.pnl for t in history) if history else 0
    wins = len([t for t in history if t.pnl > 0]) if history else 0
    total = len(history) if history else 0
    win_rate = (wins / total * 100) if total > 0 else 0

    return {
        "balance": user.balance,
        "total_pnl": total_pnl,
        "win_rate": round(win_rate, 1),
        "total_trades": total,
        "open_positions": len(open_positions),
        "recent_trades": [{
            "symbol": t.symbol, "side": t.side, "pnl": t.pnl,
            "pnl_percent": t.pnl_percent, "closed_at": str(t.closed_at),
        } for t in history[:10]],
    }
