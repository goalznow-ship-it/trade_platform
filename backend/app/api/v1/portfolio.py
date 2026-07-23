import numpy as np
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.trade import Trade, TradeHistory

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


@router.get("/analytics")
async def get_portfolio_analytics(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TradeHistory).where(TradeHistory.user_id == user.id)
        .order_by(TradeHistory.closed_at)
    )
    trades = result.scalars().all()

    if not trades:
        return {"error": "No trade history"}

    pnls = [t.pnl for t in trades if t.pnl is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    durations = [t.duration_minutes for t in trades if t.duration_minutes is not None]

    best_trade = max(trades, key=lambda t: t.pnl or 0) if trades else None
    worst_trade = min(trades, key=lambda t: t.pnl or 0) if trades else None

    monthly = {}
    for t in trades:
        if t.closed_at:
            key = t.closed_at.strftime("%Y-%m")
            if key not in monthly:
                monthly[key] = {"pnl": 0, "trades": 0, "wins": 0}
            monthly[key]["pnl"] += t.pnl or 0
            monthly[key]["trades"] += 1
            if (t.pnl or 0) > 0:
                monthly[key]["wins"] += 1

    monthly_breakdown = [
        {
            "month": m, "pnl": round(d["pnl"], 2),
            "trades": d["trades"], "win_rate": round(d["wins"] / d["trades"] * 100, 1) if d["trades"] else 0,
        }
        for m, d in sorted(monthly.items())
    ]

    return {
        "total_pnl": round(sum(pnls), 2),
        "win_rate": round(len(wins) / len(pnls) * 100, 1) if pnls else 0,
        "total_trades": len(trades),
        "avg_risk_reward": round(abs(np.mean([t.risk_reward for t in trades if t.risk_reward])) if trades else 0, 2),
        "profit_factor": round(abs(sum(wins) / sum(abs(l) for l in losses)), 2) if losses else float("inf"),
        "best_trade": {"symbol": best_trade.symbol, "pnl": best_trade.pnl} if best_trade else None,
        "worst_trade": {"symbol": worst_trade.symbol, "pnl": worst_trade.pnl} if worst_trade else None,
        "avg_holding_time": round(np.mean(durations), 1) if durations else 0,
        "avg_win": round(np.mean(wins), 2) if wins else 0,
        "avg_loss": round(np.mean(losses), 2) if losses else 0,
        "monthly_breakdown": monthly_breakdown,
    }


@router.get("/daily-pnl")
async def get_daily_pnl(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(TradeHistory).where(
            TradeHistory.user_id == user.id, TradeHistory.closed_at >= cutoff
        ).order_by(TradeHistory.closed_at)
    )
    trades = result.scalars().all()
    daily = {}
    for t in trades:
        if t.closed_at:
            day = t.closed_at.strftime("%Y-%m-%d")
            daily[day] = daily.get(day, 0) + (t.pnl or 0)
    return [{"date": d, "pnl": round(p, 2)} for d, p in sorted(daily.items())]


@router.get("/allocation")
async def get_allocation(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Trade).where(Trade.user_id == user.id, Trade.status == "open")
    )
    positions = result.scalars().all()
    total = sum(p.quantity * p.price for p in positions) if positions else 1
    allocation = [
        {"symbol": p.symbol, "value": round(p.quantity * p.price, 2),
         "percent": round(p.quantity * p.price / total * 100, 1)}
        for p in positions
    ] if positions else []
    return {"total_value": round(total, 2), "assets": allocation}
