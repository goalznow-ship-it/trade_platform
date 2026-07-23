import asyncio
from typing import Optional, Dict
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, func
from sqlalchemy.orm import selectinload
from app.models.paper_trading import PaperAccount, PaperPosition, PaperOrder
from app.models.trade import TradeHistory
from app.core.logging import logger
from app.core.websocket_manager import ws_manager, Channel
from app.services.market import market_service

COMMISSION_RATE = 0.0004
FUNDING_INTERVAL_HOURS = 8
LIQUIDATION_MAINTENANCE_MARGIN = 0.005


class PaperTradingService:
    def __init__(self):
        self.logger = logger
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._price_cache: Dict[str, float] = {}

    async def start_monitoring(self):
        if self._monitoring:
            return
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Paper trading monitoring started")

    async def stop_monitoring(self):
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None
        logger.info("Paper trading monitoring stopped")

    async def _get_live_price(self, symbol: str) -> Optional[float]:
        if symbol in self._price_cache:
            return self._price_cache[symbol]
        try:
            ticker = await market_service.get_ticker(symbol)
            if ticker:
                price = ticker.get("price") or ticker.get("last")
                if price:
                    self._price_cache[symbol] = float(price)
                    return float(price)
            return None
        except Exception:
            return None

    def update_price_cache(self, symbol: str, price: float):
        self._price_cache[symbol] = price

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
        await db.execute(delete(PaperOrder).where(PaperOrder.account_id == account.id))
        await db.execute(delete(PaperPosition).where(PaperPosition.account_id == account.id))
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
        account.best_trade = 0.0
        account.worst_trade = 0.0
        account.profit_factor = 0.0
        account.last_reset_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(account)
        return account

    async def create_order(self, user_id: int, data: dict, db: AsyncSession) -> dict:
        account = await self.get_or_create_account(user_id, db)
        order_type = data.get("order_type", "market")
        side = data.get("side", "buy")
        symbol = data.get("symbol", "")
        quantity = float(data.get("quantity", 0))
        price = data.get("price")
        stop_price = data.get("stop_price")
        leverage = int(data.get("leverage", 1))
        reduce_only = data.get("reduce_only", False)
        time_in_force = data.get("time_in_force", "GTC")

        order = PaperOrder(
            account_id=account.id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            quantity=quantity,
            filled_quantity=0,
            status="pending",
            leverage=leverage,
            reduce_only=reduce_only,
            time_in_force=time_in_force,
        )
        db.add(order)

        live_price = await self._get_live_price(symbol)

        if order_type == "market":
            return await self._fill_market_order(account, order, live_price, db)
        elif order_type == "limit":
            if time_in_force == "IOC":
                return await self._fill_limit_order_immediate(account, order, live_price, db)
            return {"order": order, "position": None}
        elif order_type in ("stop", "stop_market", "stop_limit"):
            return {"order": order, "position": None}
        else:
            order.status = "rejected"
            await db.commit()
            return {"order": order, "position": None, "error": f"Unsupported order type: {order_type}"}

    async def _fill_market_order(self, account: PaperAccount, order: PaperOrder,
                                  live_price: Optional[float], db: AsyncSession) -> dict:
        price = live_price
        if not price:
            price = order.price
        if not price:
            order.status = "rejected"
            await db.commit()
            return {"order": order, "position": None, "error": "Live or user-supplied price unavailable"}
        slippage = self._compute_slippage(order.symbol, order.quantity, order.side, price)
        fill_price = price * (1 + slippage) if order.side == "buy" else price * (1 - slippage)

        commission = order.quantity * fill_price * COMMISSION_RATE
        cost = order.quantity * fill_price
        margin_required = cost / order.leverage

        if order.side == "buy" and margin_required > account.free_margin:
            order.status = "rejected"
            order.filled_quantity = 0
            await db.commit()
            return {"order": order, "position": None, "error": "Insufficient margin"}
        if order.side == "sell" and margin_required > account.free_margin:
            order.status = "rejected"
            await db.commit()
            return {"order": order, "position": None, "error": "Insufficient margin"}

        order.status = "filled"
        order.filled_quantity = order.quantity
        order.executed_price = fill_price
        order.executed_at = datetime.now(timezone.utc)

        account.free_margin -= margin_required
        account.used_margin += margin_required
        account.balance -= commission
        position_side = "long" if order.side == "buy" else "short"

        position = PaperPosition(
            account_id=account.id,
            symbol=order.symbol,
            side=position_side,
            size=order.quantity,
            entry_price=fill_price,
            mark_price=fill_price,
            leverage=order.leverage,
            margin=margin_required,
            stop_loss=order.stop_price if order.side == "sell" else None,
            take_profit=order.price if order.side == "buy" else None,
        )
        position.liquidation_price = self._compute_liquidation_price(position, account)
        db.add(position)
        pnl_result = await db.execute(
            select(func.coalesce(func.sum(PaperPosition.unrealized_pnl), 0.0)).where(
                PaperPosition.account_id == account.id,
                PaperPosition.is_open == True,
            )
        )
        account.equity = account.balance + float(pnl_result.scalar_one())
        await db.commit()

        await self._broadcast_update(account, position, order)
        return {"order": order, "position": position}

    async def _fill_limit_order_immediate(self, account: PaperAccount, order: PaperOrder,
                                           live_price: Optional[float], db: AsyncSession) -> dict:
        price = order.price or live_price
        if not price:
            order.status = "pending"
            await db.commit()
            return {"order": order, "position": None}

        can_fill = False
        if order.side == "buy" and live_price and live_price <= price:
            can_fill = True
        elif order.side == "sell" and live_price and live_price >= price:
            can_fill = True

        if not can_fill:
            if order.time_in_force == "IOC":
                order.status = "canceled"
                await db.commit()
                return {"order": order, "position": None, "note": "IOC not filled"}
            order.status = "pending"
            await db.commit()
            return {"order": order, "position": None}

        return await self._fill_market_order(account, order, price, db)

    async def close_position(self, user_id: int, position_id: int, db: AsyncSession,
                             exit_price: Optional[float] = None) -> Optional[dict]:
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

        if not exit_price:
            exit_price = await self._get_live_price(position.symbol)
        if not exit_price:
            exit_price = position.mark_price or position.entry_price

        commission = position.size * exit_price * COMMISSION_RATE

        if position.side == "long":
            pnl = (exit_price - position.entry_price) * position.size - commission
        else:
            pnl = (position.entry_price - exit_price) * position.size - commission

        position.is_open = False
        position.realized_pnl = pnl
        position.mark_price = exit_price
        position.closed_at = datetime.now(timezone.utc)

        account.balance += pnl
        account.used_margin -= position.margin
        account.equity = account.balance
        account.free_margin = account.equity - account.used_margin
        account.total_trades += 1
        account.total_pnl += pnl
        if pnl > 0:
            account.win_count += 1
            if pnl > account.best_trade:
                account.best_trade = pnl
        else:
            account.loss_count += 1
            if pnl < account.worst_trade:
                account.worst_trade = pnl
        account.win_rate = (account.win_count / account.total_trades * 100) if account.total_trades > 0 else 0
        opened_at = position.opened_at
        if opened_at and opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        duration_minutes = int(
            (position.closed_at - opened_at).total_seconds() / 60
        ) if opened_at else 0
        pnl_percent = (
            pnl / max(position.margin, 0.00000001) * 100
        )
        history = TradeHistory(
            user_id=user_id,
            symbol=position.symbol,
            side=position.side,
            type="paper",
            quantity=position.size,
            entry_price=position.entry_price,
            exit_price=exit_price,
            pnl=pnl,
            pnl_percent=pnl_percent,
            roi=pnl_percent,
            leverage=position.leverage,
            duration_minutes=duration_minutes,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            risk_reward=abs(pnl) / max(position.margin, 0.00000001),
            reason="paper_position_closed",
            exchange="paper",
            closed_at=position.closed_at,
        )
        db.add(history)
        await db.flush()
        from app.services.self_learning import self_learning
        self_learning.record_trade({
            "source_trade_id": history.id,
            "symbol": history.symbol,
            "direction": history.side,
            "entry_price": history.entry_price,
            "exit_price": history.exit_price,
            "pnl_percent": history.pnl_percent,
            "risk_reward": history.risk_reward,
            "duration_hours": duration_minutes / 60,
            "actual_outcome": "win" if pnl > 0 else "loss",
            "entry_time": opened_at.isoformat() if opened_at else None,
        })
        self._update_account_metrics(account)

        await db.commit()
        await self._broadcast_update(account, position, None)
        return {"position": position, "pnl": pnl, "exit_price": exit_price}

    def _compute_slippage(self, symbol: str, quantity: float, side: str, price: float) -> float:
        notional = quantity * price
        if notional > 100000:
            return 0.001
        elif notional > 50000:
            return 0.0005
        return 0.0002

    def _compute_liquidation_price(self, position: PaperPosition, account: PaperAccount) -> float:
        ep = position.entry_price
        lev = position.leverage
        mm = LIQUIDATION_MAINTENANCE_MARGIN
        if position.side == "long":
            return ep * (1 - (1 / lev) + mm)
        else:
            return ep * (1 + (1 / lev) - mm)

    def _compute_funding_fee(self, position: PaperPosition, mark_price: float) -> float:
        funding_rate = 0.0001
        return position.size * mark_price * funding_rate

    def _update_account_metrics(self, account: PaperAccount):
        if account.total_trades < 2:
            return
        from app.services.self_learning import self_learning
        metrics = self_learning.get_performance_metrics("all")
        account.profit_factor = metrics.get("profit_factor", 0)
        account.sharpe_ratio = metrics.get("sharpe_ratio", 0)
        account.max_drawdown = metrics.get("max_drawdown_percent", 0)

    def _update_unrealized_pnl(self, position: PaperPosition, mark_price: float):
        position.mark_price = mark_price
        if position.side == "long":
            position.unrealized_pnl = (mark_price - position.entry_price) * position.size
        else:
            position.unrealized_pnl = (position.entry_price - mark_price) * position.size

    async def _monitor_loop(self):
        while self._monitoring:
            try:
                from app.core.database import async_session_factory
                async with async_session_factory() as db:
                    result = await db.execute(
                        select(PaperPosition).where(PaperPosition.is_open == True)
                        .options(selectinload(PaperPosition.account))
                    )
                    positions = result.scalars().all()

                    for pos in positions:
                        symbol = pos.symbol
                        live_price = await self._get_live_price(symbol)
                        if not live_price:
                            continue

                        self._update_unrealized_pnl(pos, live_price)

                        account = pos.account
                        if pos.side == "long":
                            account.equity = account.balance + pos.unrealized_pnl
                        else:
                            account.equity = account.balance + pos.unrealized_pnl

                        if pos.leverage > 1:
                            liq_price = self._compute_liquidation_price(pos, account)
                            pos.liquidation_price = liq_price
                            if (pos.side == "long" and live_price <= liq_price) or \
                               (pos.side == "short" and live_price >= liq_price):
                                liq_pnl = -(pos.margin * 0.9)
                                pos.is_open = False
                                pos.realized_pnl = liq_pnl
                                pos.closed_at = datetime.now(timezone.utc)
                                account.balance += liq_pnl
                                account.used_margin = max(0.0, account.used_margin - pos.margin)
                                account.equity = account.balance
                                account.free_margin = account.equity - account.used_margin
                                account.total_trades += 1
                                account.loss_count += 1
                                account.total_pnl += liq_pnl
                                await self._broadcast_update(account, pos, None, "liquidated")
                                logger.warning(f"Paper position {pos.id} liquidated at {live_price}")
                                continue

                        sl = pos.stop_loss
                        tp = pos.take_profit
                        if sl:
                            if (pos.side == "long" and live_price <= sl) or \
                               (pos.side == "short" and live_price >= sl):
                                await self.close_position(
                                    account.user_id, pos.id, db, exit_price=sl,
                                )
                                continue
                        if tp:
                            if (pos.side == "long" and live_price >= tp) or \
                               (pos.side == "short" and live_price <= tp):
                                await self.close_position(
                                    account.user_id, pos.id, db, exit_price=tp,
                                )
                                continue

                        funding_hours = FUNDING_INTERVAL_HOURS
                        now = datetime.now(timezone.utc)
                        funding_anchor = pos.last_funding_at or pos.opened_at
                        if funding_anchor.tzinfo is None:
                            funding_anchor = funding_anchor.replace(tzinfo=timezone.utc)
                        funding_age = (now - funding_anchor).total_seconds() / 3600
                        if funding_age >= funding_hours:
                            funding_fee = self._compute_funding_fee(pos, live_price)
                            account.balance -= funding_fee
                            account.equity -= funding_fee
                            account.free_margin -= funding_fee
                            pos.last_funding_at = now

                    await db.commit()
            except Exception as e:
                logger.error(f"Paper trading monitor error: {e}")
            await asyncio.sleep(2)

    async def _broadcast_update(self, account: PaperAccount,
                                 position: Optional[PaperPosition],
                                 order: Optional[PaperOrder],
                                 event: str = "update"):
        try:
            data = {
                "event": event,
                "account": {
                    "balance": account.balance,
                    "equity": account.equity,
                    "free_margin": account.free_margin,
                    "used_margin": account.used_margin,
                    "total_pnl": account.total_pnl,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if position:
                data["position"] = {
                    "id": position.id,
                    "symbol": position.symbol,
                    "side": position.side,
                    "size": position.size,
                    "entry_price": position.entry_price,
                    "mark_price": position.mark_price,
                    "liquidation_price": position.liquidation_price,
                    "unrealized_pnl": position.unrealized_pnl,
                    "is_open": position.is_open,
                }
            if order:
                data["order"] = {
                    "id": order.id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "order_type": order.order_type,
                    "quantity": order.quantity,
                    "filled_quantity": order.filled_quantity,
                    "status": order.status,
                    "executed_price": order.executed_price,
                }
            await ws_manager.send_to_user(account.user_id, "paper_trade_update", data, Channel.POSITIONS)
        except Exception as exc:
            logger.exception("Paper trade broadcast failed: %s", exc)


paper_trading_service = PaperTradingService()
