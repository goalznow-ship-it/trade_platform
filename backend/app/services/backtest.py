import pandas as pd
import numpy as np
import math
from typing import Optional
from collections import defaultdict
from app.core.logging import logger


class BacktestService:
    def __init__(self):
        self.logger = logger

    async def run_backtest(
        self,
        symbol: str,
        data: list,
        timeframe: str = "1h",
        initial_balance: float = 10000,
        fee_rate: float = 0.0004,
        slippage_bps: float = 2.0,
        leverage: int = 1,
        risk_per_trade: float = 0.02,
    ) -> dict:
        if len(data) < 100:
            return {"error": "Insufficient data"}

        df = pd.DataFrame(data)
        if "time" in df.columns:
            df["datetime"] = pd.to_datetime(df["time"], unit="ms")
        elif "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")

        from app.services.institutional_scoring import institutional_scorer
        from app.services.smc_engine import smc_engine

        balance = initial_balance
        peak_balance = initial_balance
        position = None
        trades = []
        equity_curve = [initial_balance]
        monthly_pnl = defaultdict(float)
        daily_balances = []

        num_bars = len(df)
        lookback = 50

        for i in range(lookback, num_bars):
            current = df.iloc[i]
            prev_data = df.iloc[:i + 1].to_dict("records")

            signal = await self._generate_institutional_signal(
                symbol, prev_data, institutional_scorer, smc_engine,
            )

            if signal and signal["action"] != 0 and position is None:
                position = self._open_position(
                    signal, current, balance, risk_per_trade, leverage, i,
                    slippage_bps,
                )
                trade_entry_balance = balance

            elif position:
                exit_price, exit_reason = self._check_exit(
                    position, current, i, num_bars,
                )

                if exit_price:
                    pnl, pnl_pct = self._close_trade(
                        position, exit_price, fee_rate, slippage_bps,
                    )
                    balance += pnl

                    trade_duration = 0
                    entry_idx = position.get("entry_index", i)
                    if entry_idx < i:
                        entry_time = df.iloc[entry_idx].get("datetime")
                        exit_time = current.get("datetime")
                        if entry_time is not None and exit_time is not None:
                            trade_duration = (exit_time - entry_time).total_seconds() / 3600

                    trades.append({
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "entry_time": str(df.iloc[entry_idx].get("datetime", "")) if entry_idx < len(df) else "",
                        "exit_time": str(current.get("datetime", "")),
                        "side": position["side"],
                        "pnl": round(pnl, 2),
                        "pnl_percent": round(pnl_pct, 2),
                        "return_pct": round((pnl / trade_entry_balance) * 100, 2) if position.get("entry_balance") else 0,
                        "exit_reason": exit_reason,
                        "duration_hours": round(trade_duration, 1),
                        "risk_reward": round(abs(pnl) / abs(position.get("risk_amount", 1)), 2) if position.get("risk_amount") else 0,
                    })

                    month_key = str(current.get("datetime", pd.Timestamp.now()))[:7]
                    monthly_pnl[month_key] += pnl

                    position = None

            equity_curve.append(balance)
            daily_balances.append(balance)

            if balance > peak_balance:
                peak_balance = balance

        return self._compute_metrics(
            trades, equity_curve, daily_balances, monthly_pnl,
            initial_balance, balance, symbol, timeframe,
        )

    async def _generate_institutional_signal(
        self, symbol: str, data: list,
        scorer, smc,
    ) -> Optional[dict]:
        try:
            if len(data) < 50:
                return None

            smc_data = smc.analyze(data)
            score_result = await scorer.score(symbol, data, "1h", smc_data)

            direction = score_result.get("direction", "neutral")
            abs_score = score_result.get("abs_score", 0)

            if direction == "neutral" or abs_score < 70:
                return None

            current_price = data[-1]["close"]
            details = score_result.get("details", {})
            atr = details.get("atr", 0) or self._calc_atr(data, 14)

            entry_zone = self._calc_entry_zone(current_price, atr, direction)
            stop_loss = self._calc_stop(current_price, atr, data, direction, smc_data)
            tp1, tp2, tp3 = self._calc_targets(entry_zone["mid"], stop_loss, direction, abs_score)

            return {
                "action": 1 if direction == "long" else -1,
                "direction": direction,
                "entry_price": entry_zone["mid"],
                "stop_loss": stop_loss,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "take_profit_3": tp3,
                "atr": atr,
                "score": abs_score,
                "classification": score_result.get("classification", "reject"),
            }
        except Exception:
            return None

    def _open_position(self, signal: dict, current_row, balance: float,
                       risk_per_trade: float, leverage: int, entry_index: int,
                       slippage_bps: float) -> dict:
        entry = signal["entry_price"]
        sl = signal["stop_loss"]
        direction = signal["direction"]

        risk_amount = balance * risk_per_trade
        risk_per_unit = abs(entry - sl)
        risk_sized_quantity = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
        max_quantity = (balance * leverage) / entry if entry > 0 else 0
        position_size = min(risk_sized_quantity, max_quantity)

        if direction == "long":
            side = 1
        else:
            side = -1
        entry *= 1 + (slippage_bps / 10000) * side

        return {
            "entry_price": entry,
            "stop_loss": sl,
            "side": side,
            "size": position_size,
            "leverage": leverage,
            "risk_amount": risk_amount,
            "entry_balance": balance,
            "entry_index": entry_index,
            "take_profit_1": signal.get("take_profit_1"),
            "take_profit_2": signal.get("take_profit_2"),
            "take_profit_3": signal.get("take_profit_3"),
            "score": signal.get("score", 0),
            "classification": signal.get("classification", ""),
        }

    def _check_exit(self, position: dict, current_row, idx: int, num_bars: int) -> tuple:
        high = current_row["high"]
        low = current_row["low"]
        close = current_row["close"]
        sl = position["stop_loss"]
        ep = position["entry_price"]

        if position["side"] == 1:
            if low <= sl:
                return sl, "stop_loss"
            tp = position.get("take_profit_1")
            if tp and high >= tp:
                return tp, "take_profit_1"
            tp2 = position.get("take_profit_2")
            if tp2 and high >= tp2:
                return tp2, "take_profit_2"
            tp3 = position.get("take_profit_3")
            if tp3 and high >= tp3:
                return tp3, "take_profit_3"
        else:
            if high >= sl:
                return sl, "stop_loss"
            tp = position.get("take_profit_1")
            if tp and low <= tp:
                return tp, "take_profit_1"
            tp2 = position.get("take_profit_2")
            if tp2 and low <= tp2:
                return tp2, "take_profit_2"
            tp3 = position.get("take_profit_3")
            if tp3 and low <= tp3:
                return tp3, "take_profit_3"

        if idx == num_bars - 1:
            return close, "end_of_data"

        invalidation_pct = 2.0
        if position["side"] == 1 and close < ep * (1 - invalidation_pct / 100):
            return close, "invalidation"
        elif position["side"] == -1 and close > ep * (1 + invalidation_pct / 100):
            return close, "invalidation"

        return None, None

    def _close_trade(
        self, position: dict, exit_price: float, fee_rate: float,
        slippage_bps: float,
    ) -> tuple:
        ep = position["entry_price"]
        size = position["size"]
        side = position["side"]

        exit_price *= 1 - (slippage_bps / 10000) * side
        gross_pnl = (exit_price - ep) * size * side
        fee = (abs(ep * size) + abs(exit_price * size)) * fee_rate
        pnl = gross_pnl - fee

        entry_balance = position.get("entry_balance", 10000)
        pnl_pct = (pnl / entry_balance) * 100

        return pnl, pnl_pct

    def _calc_entry_zone(self, price: float, atr: float, direction: str) -> dict:
        offset = atr * 0.3
        if direction == "long":
            return {"low": price - offset, "mid": price, "high": price + offset * 0.5}
        return {"low": price - offset * 0.5, "mid": price, "high": price + offset}

    def _calc_stop(self, price: float, atr: float, data: list, direction: str, smc_data: dict) -> float:
        try:
            order_blocks = smc_data.get("order_blocks", [])
            if order_blocks and direction == "long":
                recent_obs = [ob for ob in order_blocks if ob.get("type") == "bullish"]
                if recent_obs:
                    ob_low = min(ob.get("low", ob.get("price", 0)) for ob in recent_obs)
                    return min(price - atr * 1.5, ob_low)
            elif order_blocks and direction == "short":
                recent_obs = [ob for ob in order_blocks if ob.get("type") == "bearish"]
                if recent_obs:
                    ob_high = max(ob.get("high", ob.get("price", 0)) for ob in recent_obs)
                    return max(price + atr * 1.5, ob_high)
        except Exception:
            pass
        if direction == "long":
            return price - atr * 1.5
        return price + atr * 1.5

    def _calc_targets(self, entry: float, stop: float, direction: str, score: float) -> tuple:
        risk = abs(entry - stop)
        multiplier = min(3.0, 1.5 + (max(70, score) - 70) / 30 * 1.5)
        if direction == "long":
            return entry + risk * multiplier, entry + risk * multiplier * 2, entry + risk * multiplier * 3.5
        return entry - risk * multiplier, entry - risk * multiplier * 2, entry - risk * multiplier * 3.5

    def _calc_atr(self, data: list, period: int = 14) -> float:
        if len(data) < period + 1:
            return 0
        tr_values = []
        for i in range(1, len(data)):
            high = data[i]["high"]
            low = data[i]["low"]
            prev_close = data[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_values.append(tr)
            if len(tr_values) >= period:
                break
        return sum(tr_values) / len(tr_values) if tr_values else 0

    def _compute_metrics(
        self, trades: list, equity_curve: list, daily_balances: list,
        monthly_pnl: dict, initial_balance: float, final_balance: float,
        symbol: str, timeframe: str,
    ) -> dict:
        total_trades = len(trades)
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        total_pnl = final_balance - initial_balance
        total_return = ((final_balance / initial_balance) - 1) * 100 if initial_balance > 0 else 0

        gross_profit = sum(t["pnl"] for t in wins) if wins else 0
        gross_loss = abs(sum(t["pnl"] for t in losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)

        eq_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(eq_array)
        drawdowns = (running_max - eq_array) / running_max * 100
        max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0

        pnl_values = [t["pnl"] for t in trades]
        avg_pnl = np.mean(pnl_values) if pnl_values else 0
        std_pnl = np.std(pnl_values) if len(pnl_values) > 1 else 0

        annualization = math.sqrt(365)
        if timeframe in ("1h", "60m"):
            annualization = math.sqrt(8760)
        elif timeframe in ("4h", "240m"):
            annualization = math.sqrt(2190)
        elif timeframe in ("15m",):
            annualization = math.sqrt(35040)
        elif timeframe in ("5m",):
            annualization = math.sqrt(105120)

        sharpe = (avg_pnl / std_pnl * annualization) if std_pnl > 0 else 0

        avg_win = np.mean([t["pnl"] for t in wins]) if wins else 0
        avg_loss = abs(np.mean([t["pnl"] for t in losses])) if losses else 0
        avg_rr = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0

        expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss) if avg_loss > 0 else avg_win
        expectancy = round(expectancy, 2)

        avg_duration = np.mean([t.get("duration_hours", 0) for t in trades]) if trades else 0

        return_pcts = [t.get("return_pct", 0) for t in trades]
        avg_return = np.mean(return_pcts) if return_pcts else 0

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "strategy": "institutional_signals",
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": round(win_rate, 2),
            "total_return": round(total_return, 2),
            "total_pnl": round(total_pnl, 2),
            "final_balance": round(final_balance, 2),
            "max_drawdown_percent": round(max_drawdown, 2),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 2),
            "avg_risk_reward": avg_rr,
            "expectancy": expectancy,
            "avg_return_per_trade": round(avg_return, 2),
            "avg_duration_hours": round(avg_duration, 1),
            "best_trade": round(max(t["pnl"] for t in trades), 2) if trades else 0,
            "worst_trade": round(min(t["pnl"] for t in trades), 2) if trades else 0,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "initial_balance": initial_balance,
            "monthly_returns": dict(monthly_pnl),
            "trades": trades[-50:],
            "equity_curve": equity_curve[::max(1, len(equity_curve) // 200)],
        }


backtest_service = BacktestService()
