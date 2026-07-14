"""
Professional Risk Engine

Position sizing and risk management:
- Maximum Risk %
- ATR-based stop loss
- Volatility-adjusted stop
- Kelly fraction
- Position size calculation
- Recommended leverage
- Liquidation distance
- Risk category classification
"""
import math
from typing import Optional, Dict, Any
from app.services.indicators import indicator_service
from app.core.logging import logger


class ProfessionalRiskEngine:
    MAX_RISK_PER_TRADE = 0.02  # 2% default
    MAX_LEVERAGE = 125
    MIN_LIQUIDATION_DISTANCE = 0.05  # 5%

    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss: float,
        risk_percent: Optional[float] = None,
        leverage: Optional[int] = None,
        atr_value: Optional[float] = None,
    ) -> dict:
        risk_pct = risk_percent or self.MAX_RISK_PER_TRADE

        if not entry_price or not stop_loss or entry_price == stop_loss:
            return {"error": "Invalid entry or stop price"}

        risk_per_unit = abs(entry_price - stop_loss) / entry_price
        if risk_per_unit <= 0:
            return {"error": "Stop loss equals entry price"}

        max_risk_amount = capital * risk_pct

        if leverage and leverage > 1:
            effective_risk = risk_per_unit * leverage
            position_size = max_risk_amount / (entry_price * risk_per_unit * leverage)
        else:
            position_size = max_risk_amount / (entry_price * risk_per_unit)
            leverage = 1

        position_size = max(0, position_size)
        max_risk_pct = risk_per_unit * leverage * 100

        recommended_leverage = self._recommended_leverage(risk_per_unit, atr_value) if not leverage or leverage == 1 else leverage

        liquidation_price = self._estimate_liquidation(
            entry_price, stop_loss, recommended_leverage, position_size > 0
        )

        distance_to_liq = abs(entry_price - liquidation_price) / entry_price * 100 if liquidation_price else 0

        risk_category = self._categorize_risk(max_risk_pct, distance_to_liq, risk_per_unit)

        return {
            "entry_price": round(entry_price, 4),
            "stop_loss": round(stop_loss, 4),
            "risk_per_trade": round(risk_pct * 100, 2),
            "risk_amount": round(max_risk_amount, 2),
            "position_size": round(position_size, 6),
            "position_value": round(position_size * entry_price, 2),
            "leverage": recommended_leverage,
            "margin_required": round((position_size * entry_price) / recommended_leverage, 2) if recommended_leverage > 0 else 0,
            "max_risk_percent": round(max_risk_pct, 2),
            "liquidation_price": round(liquidation_price, 4) if liquidation_price else None,
            "distance_to_liquidation": round(distance_to_liq, 2),
            "risk_category": risk_category,
            "atr_stop": round(atr_value, 4) if atr_value else None,
        }

    def calculate_atr_stop(
        self,
        data: list,
        multiplier: float = 1.5,
        direction: str = "long",
    ) -> Optional[float]:
        if len(data) < 20:
            return None

        atr = indicator_service.atr(data)
        if not atr:
            return None

        current_price = data[-1]["close"]

        if direction == "long":
            stop = current_price - (atr * multiplier)
            return max(stop, min(d["low"] for d in data[-10:]))
        else:
            stop = current_price + (atr * multiplier)
            return min(stop, max(d["high"] for d in data[-10:]))

    def calculate_kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> dict:
        if avg_loss <= 0 or win_rate <= 0:
            return {"kelly_percent": 0, "fraction": 0}

        if win_rate >= 1:
            return {"kelly_percent": 25, "fraction": 0.25}

        r = avg_win / abs(avg_loss) if avg_loss != 0 else 0
        p = win_rate
        q = 1 - p

        kelly = (p * r - q) / r if r > 0 else 0
        kelly_pct = max(0, min(kelly * 100, 25))
        half_kelly = kelly_pct / 2
        quarter_kelly = kelly_pct / 4

        return {
            "kelly_percent": round(kelly_pct, 2),
            "half_kelly": round(half_kelly, 2),
            "quarter_kelly": round(quarter_kelly, 2),
            "kelly_fraction": round(kelly, 4),
            "win_rate": round(win_rate * 100, 1) if win_rate <= 1 else round(win_rate, 1),
            "risk_reward": round(r, 2),
        }

    def validate_trade(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        leverage: int,
        balance: float,
        atr_value: Optional[float] = None,
        data: Optional[list] = None,
    ) -> dict:
        checks = []
        passed = True

        if not entry_price or entry_price <= 0:
            checks.append({"check": "price_validation", "passed": False, "reason": "Invalid entry price"})
            passed = False

        if not stop_loss or stop_loss <= 0:
            checks.append({"check": "stop_loss", "passed": False, "reason": "Invalid stop loss"})
            passed = False
        elif entry_price == stop_loss:
            checks.append({"check": "stop_loss_distance", "passed": False, "reason": "Stop equals entry price"})
            passed = False

        if leverage < 1 or leverage > self.MAX_LEVERAGE:
            checks.append({"check": "leverage", "passed": False, "reason": f"Leverage {leverage}x outside valid range (1-{self.MAX_LEVERAGE})"})
            passed = False

        if balance <= 0:
            checks.append({"check": "balance", "passed": False, "reason": "Insufficient balance"})
            passed = False

        risk_pct = abs(entry_price - stop_loss) / entry_price * leverage * 100
        if risk_pct > self.MAX_RISK_PER_TRADE * 100:
            checks.append({"check": "max_risk", "passed": False,
                            "reason": f"Risk {risk_pct:.1f}% exceeds max {self.MAX_RISK_PER_TRADE * 100:.0f}%"})
            passed = False

        if take_profit and stop_loss:
            rr = abs(take_profit - entry_price) / abs(entry_price - stop_loss) if abs(entry_price - stop_loss) > 0 else 0
            if rr < 1.5:
                checks.append({"check": "risk_reward", "passed": False,
                                "reason": f"R:R {rr:.2f} below minimum 1.5"})
                passed = False

        if atr_value and atr_value > 0:
            atr_stop_dist = abs(entry_price - stop_loss) / atr_value
            if atr_stop_dist < 0.5:
                checks.append({"check": "atr_stop", "passed": False,
                                "reason": f"Stop too tight: {atr_stop_dist:.1f}x ATR"})
                passed = False

        if data and len(data) >= 20:
            closes = [d["close"] for d in data]
            spreads = [abs(d["high"] - d["low"]) / d["close"] * 100 for d in data[-5:]]
            avg_spread = sum(spreads) / len(spreads) if spreads else 0
            if avg_spread > 3:
                checks.append({"check": "spread", "passed": True,
                                "reason": f"High spread: {avg_spread:.2f}% (warning only)"})

            volatility = max(d["high"] for d in data[-5:]) / min(d["low"] for d in data[-5:]) - 1
            if volatility > 0.1:
                checks.append({"check": "volatility", "passed": True,
                                "reason": f"High volatility: {volatility * 100:.1f}% (warning only)"})

        checks.append({"check": "overall", "passed": passed,
                        "reason": "All checks passed" if passed else f"{sum(1 for c in checks if not c['passed'])} checks failed"})

        return {
            "passed": passed,
            "checks": checks,
            "max_risk_percent": round(risk_pct, 2) if 'risk_pct' in locals() else 0,
        }

    def _recommended_leverage(self, risk_per_unit: float, atr_value: Optional[float] = None) -> int:
        if risk_per_unit <= 0.005:
            return 20
        elif risk_per_unit <= 0.01:
            return 10
        elif risk_per_unit <= 0.02:
            return 5
        elif risk_per_unit <= 0.03:
            return 3
        elif risk_per_unit <= 0.05:
            return 2
        return 1

    def _estimate_liquidation(
        self, entry: float, stop: float, leverage: int, has_size: bool
    ) -> Optional[float]:
        if leverage <= 1:
            return stop

        diff = abs(entry - stop)
        liq_buffer = diff * 1.3

        if entry > stop:
            return entry - liq_buffer
        return entry + liq_buffer

    def _categorize_risk(self, max_risk_pct: float, dist_to_liq: float, risk_per_unit: float) -> str:
        risk_score = 0
        if max_risk_pct > 10:
            risk_score += 3
        elif max_risk_pct > 5:
            risk_score += 2
        elif max_risk_pct > 2:
            risk_score += 1

        if dist_to_liq < 3:
            risk_score += 3
        elif dist_to_liq < 5:
            risk_score += 2
        elif dist_to_liq < 10:
            risk_score += 1

        if risk_per_unit > 0.03:
            risk_score += 2
        elif risk_per_unit > 0.02:
            risk_score += 1

        if risk_score >= 5:
            return "very_high"
        elif risk_score >= 3:
            return "high"
        elif risk_score >= 2:
            return "medium"
        return "low"


professional_risk = ProfessionalRiskEngine()
