from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.models.paper_trading import PaperAccount, PaperPosition, PaperOrder
from app.core.logging import logger
from app.core.websocket_manager import ws_manager


class PaperTradingService:
    def __init__(self):
        self.logger = logger

    async def get_or_create_account(self, user_id: int, db: AsyncSession) -> PaperAccount:
        result = await db.execute(
            select(PaperAccount).where(PaperAccount.user_id == user_id)
            .options(selectinload(PaperAccount.positions), selectinload(PaperAccount.orders))
        )
        account = result.scalar_one_or_none()
        if not account:
            account = PaperAccount(user_id=user_id)
            db.add(account)
            await db.commit()
            await db.refresh(account)
        return account

    async def reset_account(self, user_id: int, db: AsyncSession) -> PaperAccount:
        account = await self.get_or_create_account(user_id, db)
        account.balance = account.initial_balance
        account.equity = account.initial_balance
        account.free_margin = account.initial_balance
        account.used_margin = 0.0
        account.total_pnl = 0.0
        account.total_trades = 0
        account.win_count = 0
        account.loss_count = 0
        account.win_rate = 0.0
        account.sharpe_ratio = 0.0
        account.max_drawdown = 0.0
        account.last_reset_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(account)
        return account

    async def create_order(self, user_id: int, data: dict, db: AsyncSession) -> dict:
        account = await self.get_or_create_account(user_id, db)

        order = PaperOrder(account_id=account.id, **data)
        db.add(order)

        if data.get("order_type") == "market":
            price = data.get("price") or 50000.0
            cost = data["quantity"] * price
            if data["side"] == "buy":
                account.free_margin -= cost / data.get("leverage", 1)
                account.used_margin += cost / data.get("leverage", 1)
            order.status = "filled"
            order.filled_quantity = data["quantity"]
            order.executed_price = price
            order.executed_at = datetime.now(timezone.utc)

            position = PaperPosition(
                account_id=account.id,
                symbol=data["symbol"],
                side="long" if data["side"] == "buy" else "short",
                size=data["quantity"],
                entry_price=price,
                mark_price=price,
                leverage=data.get("leverage", 1),
                margin=cost / data.get("leverage", 1),
            )
            db.add(position)

        await db.commit()
        return {"order": order, "position": position if data.get("order_type") == "market" else None}

    async def close_position(self, user_id: int, position_id: int, db: AsyncSession) -> Optional[dict]:
        account = await self.get_or_create_account(user_id, db)
        result = await db.execute(
            select(PaperPosition).where(
                PaperPosition.id == position_id,
                PaperPosition.account_id == account.id,
                PaperPosition.is_open == True,
            )
        )
        position = result.scalar_one_or_none()
        if not position:
            return None

        exit_price = position.mark_price or position.entry_price
        if position.side == "long":
            pnl = (exit_price - position.entry_price) * position.size
        else:
            pnl = (position.entry_price - exit_price) * position.size

        position.is_open = False
        position.realized_pnl = pnl
        position.closed_at = datetime.now(timezone.utc)

        account.balance += pnl
        account.equity = account.balance
        account.free_margin += position.margin
        account.used_margin -= position.margin
        account.total_trades += 1
        account.total_pnl += pnl
        if pnl > 0:
            account.win_count += 1
        else:
            account.loss_count += 1
        account.win_rate = (account.win_count / account.total_trades * 100) if account.total_trades > 0 else 0

        await db.commit()
        return {"position": position, "pnl": pnl}


paper_trading_service = PaperTradingService()
