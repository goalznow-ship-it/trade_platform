"""
Self-Learning Engine

Stores every closed trade, evaluates performance, and auto-adjusts
scoring weights based on historical results. Operates as a singleton.

Weight adjustment uses proportional allocation:
- Categories that predict correctly gain weight (capped at 0.30)
- Poor performers lose weight (floored at 0.05)
- All weights re-normalized to sum to 1.0
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
import math
import statistics
from collections import defaultdict, deque
from app.core.logging import logger


class SelfLearningEngine:
    def __init__(self):
        self.trade_history: List[Dict] = []
        self.weight_history: List[Dict] = []
        self.default_weights = {
            "trend": 0.20, "momentum": 0.15, "volume": 0.15,
            "liquidity": 0.15, "smc": 0.20, "risk": 0.15,
        }
        self.current_weights = dict(self.default_weights)

    def record_trade(self, trade_data: Dict) -> None:
        trade_data["id"] = len(self.trade_history) + 1
        if "entry_time" not in trade_data:
            trade_data["entry_time"] = datetime.now(timezone.utc).isoformat()
        trade_data["recorded_at"] = datetime.now(timezone.utc).isoformat()
        self.trade_history.append(trade_data)
        logger.info(
            "Trade recorded",
            extra={"trade_id": trade_data["id"], "symbol": trade_data.get("symbol"),
                   "direction": trade_data.get("direction")},
        )

    def _get_trade(self, trade_id: int) -> Optional[Dict]:
        for t in self.trade_history:
            if t["id"] == trade_id:
                return t
        return None

    def _filter_trades_by_timeframe(self, timeframe: str) -> List[Dict]:
        if timeframe == "all" or not self.trade_history:
            return list(self.trade_history)

        now = datetime.now(timezone.utc)
        periods = {
            "week": timedelta(days=7),
            "month": timedelta(days=30),
            "3months": timedelta(days=90),
            "6months": timedelta(days=180),
            "year": timedelta(days=365),
        }
        delta = periods.get(timeframe)
        if not delta:
            return list(self.trade_history)

        cutoff = now - delta
        result = []
        for t in self.trade_history:
            recorded = t.get("recorded_at", t.get("entry_time"))
            if isinstance(recorded, str):
                try:
                    recorded = datetime.fromisoformat(recorded)
                except (ValueError, TypeError):
                    result.append(t)
                    continue
            if isinstance(recorded, datetime) and recorded >= cutoff:
                result.append(t)
        return result

    def evaluate_trade(self, trade_id: int) -> Dict:
        trade = self._get_trade(trade_id)
        if not trade:
            return {"error": "Trade not found", "trade_id": trade_id}

        direction = trade.get("direction", "long")
        entry = trade.get("entry_price", 0)
        exit_price = trade.get("exit_price", 0)
        outcome = trade.get("actual_outcome", "unknown")

        direction_correct = (
            (direction == "long" and exit_price > entry) or
            (direction == "short" and exit_price < entry)
        ) if entry and exit_price else False

        rr_achieved = outcome == "win"
        max_dd = trade.get("max_drawdown_percent", 0)
        dd_acceptable = max_dd < 5.0

        return {
            "trade_id": trade_id,
            "symbol": trade.get("symbol", "unknown"),
            "direction": direction,
            "direction_correct": direction_correct,
            "rr_achieved": rr_achieved,
            "actual_rr": trade.get("risk_reward", 0),
            "target_rr": trade.get("target_rr", 0),
            "max_drawdown_percent": round(max_dd, 2),
            "max_drawdown_acceptable": dd_acceptable,
            "outcome": outcome,
            "pnl_percent": round(trade.get("pnl_percent", 0), 2),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_performance_metrics(self, timeframe: str = "all") -> Dict:
        trades = self._filter_trades_by_timeframe(timeframe)
        if not trades:
            return {
                "timeframe": timeframe,
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "avg_risk_reward": 0,
                "profit_factor": 0,
                "sharpe_ratio": 0,
                "max_drawdown_percent": 0,
                "avg_duration_hours": 0,
                "best_trade": None,
                "worst_trade": None,
            }

        wins = [t for t in trades if t.get("actual_outcome") == "win"]
        losses = [t for t in trades if t.get("actual_outcome") == "loss"]
        total = len(trades)
        win_rate = len(wins) / total if total > 0 else 0

        rr_values = [t.get("risk_reward", 0) for t in trades if t.get("risk_reward", 0) > 0]
        avg_rr = statistics.mean(rr_values) if rr_values else 0

        gross_profit = sum(abs(t.get("pnl_percent", 0)) for t in wins) if wins else 0
        gross_loss = sum(abs(t.get("pnl_percent", 0)) for t in losses) if losses else 0
        profit_factor = (
            gross_profit / gross_loss if gross_loss > 0
            else (gross_profit if gross_profit > 0 else 0)
        )

        returns = [t.get("pnl_percent", 0) for t in trades]
        avg_return = statistics.mean(returns) if returns else 0
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0
        sharpe = (avg_return / std_return) * math.sqrt(max(total, 1)) if std_return > 0 else 0

        dd_values = [t.get("max_drawdown_percent", 0) for t in trades]
        max_dd = max(dd_values) if dd_values else 0

        durations = [t.get("duration_hours", 0) for t in trades if t.get("duration_hours", 0) > 0]
        avg_duration = statistics.mean(durations) if durations else 0

        best_trade = max(trades, key=lambda t: t.get("pnl_percent", 0)) if trades else None
        worst_trade = min(trades, key=lambda t: t.get("pnl_percent", 0)) if trades else None

        return {
            "timeframe": timeframe,
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate * 100, 2),
            "avg_risk_reward": round(avg_rr, 2),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_percent": round(max_dd, 2),
            "avg_duration_hours": round(avg_duration, 2),
            "best_trade": {
                "symbol": best_trade.get("symbol", "unknown"),
                "direction": best_trade.get("direction", "unknown"),
                "pnl_percent": round(best_trade.get("pnl_percent", 0), 2),
                "risk_reward": best_trade.get("risk_reward", 0),
            } if best_trade else None,
            "worst_trade": {
                "symbol": worst_trade.get("symbol", "unknown"),
                "direction": worst_trade.get("direction", "unknown"),
                "pnl_percent": round(worst_trade.get("pnl_percent", 0), 2),
                "risk_reward": worst_trade.get("risk_reward", 0),
            } if worst_trade else None,
        }

    def analyze_missed_profit(self, trade_id: int) -> Dict:
        trade = self._get_trade(trade_id)
        if not trade:
            return {"error": "Trade not found", "trade_id": trade_id}

        direction = trade.get("direction", "long")
        entry = trade.get("entry_price", 0)
        exit_price = trade.get("exit_price", 0)
        tp = trade.get("take_profit")
        mfe = trade.get("max_favorable_excursion")

        if direction == "long":
            taken_profit = exit_price - entry
            potential_profit = (
                (mfe - entry) if mfe
                else ((tp - entry) if tp else taken_profit)
            )
        else:
            taken_profit = entry - exit_price
            potential_profit = (
                (entry - mfe) if mfe
                else ((entry - tp) if tp else taken_profit)
            )

        if taken_profit <= 0:
            return {
                "trade_id": trade_id,
                "symbol": trade.get("symbol", "unknown"),
                "taken_profit": round(taken_profit, 4),
                "potential_profit": round(potential_profit, 4),
                "missed_profit": round(abs(potential_profit), 4),
                "missed_percent": 100.0,
                "reason": "Trade was a loss or breakeven",
                "recommendation": "Review entry timing and stop placement",
            }

        missed = max(0, potential_profit - taken_profit)
        missed_pct = (missed / taken_profit) * 100 if taken_profit > 0 else 0

        if missed_pct > 50:
            recommendation = "Consider trailing stops or scaling out partially"
        elif missed_pct > 20:
            recommendation = "Consider partial profit taking at key levels"
        else:
            recommendation = "Good exit execution"

        return {
            "trade_id": trade_id,
            "symbol": trade.get("symbol", "unknown"),
            "direction": direction,
            "entry_price": entry,
            "exit_price": exit_price,
            "taken_profit": round(taken_profit, 4),
            "potential_profit": round(potential_profit, 4),
            "missed_profit": round(missed, 4),
            "missed_percent": round(missed_pct, 2),
            "reason": (
                "Take profit was not reached; price exceeded TP level"
                if mfe and tp and mfe > tp
                else "Full TP target achieved"
            ) if mfe else "No MFE data available",
            "recommendation": recommendation,
        }

    def adjust_weights(self) -> None:
        recent = self.trade_history[-100:]
        if len(recent) < 10:
            logger.warning(
                "Insufficient trades for weight adjustment",
                extra={"required": 10, "available": len(recent)},
            )
            return

        categories = list(self.default_weights.keys())

        accuracies: Dict[str, float] = {}
        for cat in categories:
            outcomes = []
            for t in recent:
                score = t.get("scores_at_entry", {}).get(cat, 0)
                if score == 0:
                    continue
                direction = t.get("direction", "long")
                correct_sign = (score > 0 and direction == "long") or (
                    score < 0 and direction == "short"
                )
                won = t.get("actual_outcome") == "win"
                outcomes.append(correct_sign == won)

            if outcomes:
                accuracies[cat] = sum(outcomes) / len(outcomes)
            else:
                accuracies[cat] = 0.50

        avg_accuracy = statistics.mean(accuracies.values())

        self.weight_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "weights": dict(self.current_weights),
            "accuracies": {k: round(v, 4) for k, v in accuracies.items()},
            "avg_accuracy": round(avg_accuracy, 4),
        })

        raw_weights = {}
        for cat in categories:
            acc = accuracies.get(cat, 0.50)
            deviation = acc - avg_accuracy
            factor = 1.0 + deviation * 0.5
            new_weight = self.current_weights[cat] * factor
            raw_weights[cat] = max(0.05, min(0.30, new_weight))

        total = sum(raw_weights.values())
        self.current_weights = {k: v / total for k, v in raw_weights.items()}

        logger.info(
            "Weights adjusted",
            extra={
                "new_weights": {k: round(v, 4) for k, v in self.current_weights.items()},
                "accuracies": {k: round(v, 4) for k, v in accuracies.items()},
            },
        )

    def get_optimal_rr(self, score: float, volatility: float) -> float:
        base_rr = 1.5 + (max(0, min(100, score)) / 100) * 3.5
        vol_factor = max(0.5, min(1.0, 1.0 - (volatility / 20)))
        return round(base_rr * vol_factor, 2)

    def get_optimal_position_size(
        self, score: float, balance: float, volatility: float
    ) -> Dict:
        clamped_score = max(0, min(100, score))
        base_risk = 0.01 + (clamped_score / 100) * 0.02
        vol_penalty = min(0.5, volatility / 10) * 0.005
        risk_pct = max(0.005, base_risk - vol_penalty)

        score_range_low = max(0, int(clamped_score / 10) * 10)
        score_range_high = min(100, score_range_low + 10)
        similar_trades = [
            t for t in self.trade_history
            if abs(t.get("scores_at_entry", {}).get("total", 50) - clamped_score) <= 15
            and t.get("actual_outcome") in ("win", "loss")
        ]

        historical_win_rate = 0.50
        historical_avg_rr = 1.5
        if similar_trades:
            wins = sum(1 for t in similar_trades if t.get("actual_outcome") == "win")
            historical_win_rate = wins / len(similar_trades)
            rr_vals = [
                t.get("risk_reward", 0) for t in similar_trades
                if t.get("risk_reward", 0) > 0
            ]
            if rr_vals:
                historical_avg_rr = statistics.mean(rr_vals)

        kelly_fraction = (historical_win_rate * historical_avg_rr - (1 - historical_win_rate)) / historical_avg_rr
        kelly_fraction = max(0, min(0.25, kelly_fraction)) if historical_avg_rr > 0 else 0

        position_value = balance * risk_pct * min(5, max(1, 1 / max(0.001, volatility / 100)))
        max_position = balance * 0.5
        position_value = min(position_value, max_position)

        max_leverage = 3 if volatility > 10 else (5 if volatility > 5 else 10)

        return {
            "score": clamped_score,
            "balance": balance,
            "volatility": volatility,
            "recommended_risk_percent": round(risk_pct * 100, 2),
            "recommended_position_value": round(position_value, 2),
            "recommended_position_units": round(position_value / max(balance, 1), 4) if balance > 0 else 0,
            "max_leverage": max_leverage,
            "historical_win_rate": round(historical_win_rate * 100, 1),
            "historical_avg_rr": round(historical_avg_rr, 2),
            "kelly_percent": round(kelly_fraction * 100, 2),
            "similar_trades_analyzed": len(similar_trades),
        }

    def get_learning_report(self) -> Dict:
        weight_changes = self.weight_history[-20:] if self.weight_history else []
        metrics = self.get_performance_metrics()

        recommendations = []
        if metrics.get("total_trades", 0) < 20:
            recommendations.append("Collect more trades (20+) before relying on weight adjustments")
        if metrics.get("win_rate", 0) < 40 and metrics.get("total_trades", 0) >= 20:
            recommendations.append("Win rate below 40% — review strategy entry criteria")
        if metrics.get("profit_factor", 0) < 1.0 and metrics.get("total_trades", 0) >= 10:
            recommendations.append("Profit factor below 1.0 — strategy is losing money")
        if metrics.get("avg_risk_reward", 0) < 1.5:
            recommendations.append("Average R:R below 1.5 — target higher quality setups")
        if metrics.get("max_drawdown_percent", 0) > 10:
            recommendations.append("Max drawdown exceeds 10% — tighten risk management")
        if self.current_weights.get("smc", 0) > 0.25:
            recommendations.append("SMC weight above 25% — consider diversifying signal sources")
        if self.current_weights.get("momentum", 0) < 0.08:
            recommendations.append("Momentum weight below 8% — may miss trend continuation signals")

        weight_delta = {}
        for cat in self.default_weights:
            delta = self.current_weights.get(cat, 0) - self.default_weights.get(cat, 0)
            weight_delta[cat] = round(delta, 4)

        return {
            "current_weights": {k: round(v, 4) for k, v in self.current_weights.items()},
            "default_weights": {k: round(v, 4) for k, v in self.default_weights.items()},
            "weight_delta": weight_delta,
            "weight_change_history": weight_changes,
            "performance_metrics": metrics,
            "total_trades_recorded": len(self.trade_history),
            "total_weight_adjustments": len(self.weight_history),
            "recommendations": recommendations,
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def reset_weights(self) -> None:
        self.weight_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "weights": dict(self.current_weights),
            "reset": True,
        })
        self.current_weights = dict(self.default_weights)
        logger.info("Weights reset to defaults")


self_learning = SelfLearningEngine()
