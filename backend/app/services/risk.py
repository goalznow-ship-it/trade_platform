import numpy as np
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.risk import RiskProfile, RiskSnapshot
from app.models.trade import TradeHistory, Position
from app.core.logging import logger


class RiskService:
    def __init__(self):
        self.logger = logger

    async def get_profile(self, user_id: int, db: AsyncSession) -> RiskProfile:
        result = await db.execute(select(RiskProfile).where(RiskProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if not profile:
            profile = RiskProfile(user_id=user_id)
            db.add(profile)
            await db.commit()
            await db.refresh(profile)
        return profile

    async def update_profile(self, user_id: int, data: dict, db: AsyncSession) -> RiskProfile:
        profile = await self.get_profile(user_id, db)
        for key, value in data.items():
            if value is not None:
                setattr(profile, key, value)
        await db.commit()
        await db.refresh(profile)
        return profile

    async def get_current_snapshot(self, user_id: int, db: AsyncSession) -> RiskSnapshot:
        result = await db.execute(
            select(RiskSnapshot).where(RiskSnapshot.user_id == user_id)
            .order_by(RiskSnapshot.snapshot_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def compute_snapshot(self, user_id: int, db: AsyncSession) -> RiskSnapshot:
        trades_result = await db.execute(
            select(TradeHistory).where(TradeHistory.user_id == user_id)
        )
        trades = trades_result.scalars().all()

        positions_result = await db.execute(
            select(Position).where(Position.user_id == user_id, Position.is_open == True)
        )
        positions = positions_result.scalars().all()

        pnls = [t.pnl for t in trades if t.pnl is not None] if trades else []
        wins = [p for p in pnls if p > 0] if pnls else []
        losses = [p for p in pnls if p < 0] if pnls else []

        daily_pnl = sum(pnls[-20:]) if pnls else 0
        weekly_pnl = sum(pnls[-100:]) if pnls else 0
        monthly_pnl = sum(pnls) if pnls else 0

        total_exposure = sum(p.size * p.mark_price for p in positions if p.size and p.mark_price) if positions else 0

        profile = await self.get_profile(user_id, db)

        risk_score = min(total_exposure / (profile.max_position_size * max(len(positions), 1)), 1.0) if profile.max_position_size else 0

        snapshot = RiskSnapshot(
            user_id=user_id,
            total_exposure=total_exposure,
            daily_pnl=daily_pnl,
            weekly_pnl=weekly_pnl,
            monthly_pnl=monthly_pnl,
            total_balance=profile.max_daily_loss * 10,
            open_position_count=len(positions),
            portfolio_risk_score=risk_score,
            profit_factor=abs(sum(wins) / sum(abs(l) for l in losses)) if losses and sum(abs(l) for l in losses) > 0 else (len(wins) * 10 if wins else 0),
            sharpe_ratio=np.mean(pnls) / np.std(pnls) * np.sqrt(365) if len(pnls) > 1 and np.std(pnls) > 0 else 0,
            sortino_ratio=np.mean(pnls) / np.std([p for p in pnls if p < 0]) * np.sqrt(365) if any(p < 0 for p in pnls) and np.std([p for p in pnls if p < 0]) > 0 else 0,
            win_rate=len(wins) / len(pnls) * 100 if pnls else 0,
            expectancy=np.mean(pnls) if pnls else 0,
            kelly_percent=(len(wins) / len(pnls) - (1 - len(wins) / len(pnls)) / (abs(np.mean(wins) / np.mean(losses)) if wins and losses else 1)) * 100 if pnls else 0,
        )
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)
        return snapshot

    async def get_dashboard(self, user_id: int, db: AsyncSession) -> dict:
        profile = await self.get_profile(user_id, db)
        current = await self.compute_snapshot(user_id, db)

        positions_result = await db.execute(
            select(Position).where(Position.user_id == user_id, Position.is_open == True)
        )
        positions = positions_result.scalars().all()

        exposure_by_symbol = []
        for p in positions:
            if p.symbol and p.size and p.mark_price:
                exposure_by_symbol.append({"symbol": p.symbol, "exposure": p.size * p.mark_price, "pnl": p.unrealized_pnl})

        warnings = []
        if current.daily_pnl < -profile.max_daily_loss:
            warnings.append(f"Daily loss limit exceeded: {current.daily_pnl:.2f} / {profile.max_daily_loss:.2f}")
        if current.open_position_count >= profile.max_open_positions:
            warnings.append(f"Max open positions reached: {current.open_position_count} / {profile.max_open_positions}")
        if current.portfolio_risk_score > profile.risk_score_threshold:
            warnings.append(f"Portfolio risk score too high: {current.portfolio_risk_score:.2f}")

        return {
            "profile": profile,
            "current": current,
            "exposure_by_symbol": exposure_by_symbol,
            "risk_signals": [],
            "warnings": warnings,
        }


risk_service = RiskService()
