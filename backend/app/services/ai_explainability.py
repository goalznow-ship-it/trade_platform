from typing import Optional, List
from app.services.indicators import indicator_service
from app.core.logging import logger


class AIExplainabilityEngine:
    def __init__(self):
        self.logger = logger

    def explain(self, data: list, analysis: dict, profile: Optional[dict] = None) -> dict:
        reasons = []
        warnings = []
        suggestions = {}

        scores = analysis.get("scores", {})
        details = analysis.get("details", {})

        trend = scores.get("trend", 0)
        momentum = scores.get("momentum", 0)
        volume = scores.get("volume", 0)
        volatility = scores.get("volatility", 0)
        structure = scores.get("market_structure", 0)
        smc = scores.get("smc", 0)

        if trend > 0.3:
            reasons.append(f"Strong uptrend detected (score: {trend*100:.0f}%)")
        elif trend < -0.3:
            reasons.append(f"Strong downtrend detected (score: {trend*100:.0f}%)")
        else:
            reasons.append("Neutral trend conditions")

        if momentum > 0.3:
            reasons.append(f"Bullish momentum (score: {momentum*100:.0f}%)")
        elif momentum < -0.3:
            reasons.append(f"Bearish momentum (score: {momentum*100:.0f}%)")

        rsi_val = details.get("rsi", 50)
        if rsi_val and rsi_val > 70:
            warnings.append(f"RSI overbought ({rsi_val:.0f}) - potential reversal")
        elif rsi_val and rsi_val < 30:
            warnings.append(f"RSI oversold ({rsi_val:.0f}) - potential bounce")

        macd_val = details.get("macd", 0)
        if macd_val and macd_val > 0:
            reasons.append(f"MACD bullish ({macd_val:.2f})")
        elif macd_val and macd_val < 0:
            reasons.append(f"MACD bearish ({macd_val:.2f})")

        adx_val = details.get("adx", 0)
        if adx_val:
            if adx_val > 25:
                reasons.append(f"Strong trend (ADX: {adx_val:.0f})")
            else:
                reasons.append(f"Weak/choppy market (ADX: {adx_val:.0f})")

        if smc > 0.3:
            reasons.append("SMC: Bullish liquidity grab detected")
        elif smc < -0.3:
            reasons.append("SMC: Bearish liquidity grab detected")

        if structure > 0.3:
            reasons.append("Bullish market structure (higher highs/lows)")
        elif structure < -0.3:
            reasons.append("Bearish market structure (lower highs/lows)")

        if volume > 0.3:
            reasons.append("Above-average volume confirming move")
        elif volume < -0.3:
            reasons.append("Below-average volume - move may lack conviction")

        if volatility > 0.3:
            warnings.append("High volatility - consider wider stops")
        elif volatility < -0.3:
            reasons.append("Low volatility environment")

        if data and len(data) > 1:
            support = details.get("support")
            resistance = details.get("resistance")
            if support and resistance:
                current_price = data[-1]["close"]
                suggestions["stop_loss"] = round(current_price * 0.98, 4)
                suggestions["take_profit"] = round(current_price * 1.03, 4)
                suggestions["suggested_leverage"] = 3 if analysis.get("risk_level") == "low" else 2
                if profile:
                    account_balance = profile.get("balance", 10000)
                    risk_per_trade = profile.get("risk_per_trade", 0.02)
                    entry_price = current_price
                    stop_distance = abs(entry_price - suggestions["stop_loss"]) / entry_price
                    position_size = (account_balance * risk_per_trade) / stop_distance / entry_price if stop_distance > 0 else 0
                    suggestions["position_size"] = round(position_size, 4)

        bullish_pct = analysis.get("long_probability", 50)
        bearish_pct = analysis.get("short_probability", 50)

        probability_explanation = (
            f"Bullish: {bullish_pct:.0f}% | Bearish: {bearish_pct:.0f}% | "
            f"Based on {len([k for k, v in scores.items() if abs(v) > 0.1])} active factors"
        )

        return {
            "overall_confidence": analysis.get("confidence", 0),
            "bullish_percentage": bullish_pct,
            "bearish_percentage": bearish_pct,
            "trend_analysis": self._explain_component(trend, "trend"),
            "indicator_analysis": self._explain_indicators(data, details),
            "volume_analysis": self._explain_component(volume, "volume"),
            "smc_analysis": self._explain_smc(smc),
            "liquidity_analysis": {"score": smc, "signal": "bullish" if smc > 0 else "bearish" if smc < 0 else "neutral"},
            "risk_explanation": self._explain_risk(analysis.get("risk_level"), volatility),
            "probability_explanation": probability_explanation,
            "reasons": reasons,
            "warnings": warnings,
            "suggestions": suggestions,
            "key_levels": {
                "support": details.get("support"),
                "resistance": details.get("resistance"),
                "rsi": rsi_val,
                "macd": macd_val,
                "adx": adx_val,
            },
        }

    def _explain_component(self, score: float, name: str) -> dict:
        if score > 0.2:
            signal = "bullish"
            strength = "strong" if score > 0.5 else "moderate"
        elif score < -0.2:
            signal = "bearish"
            strength = "strong" if score < -0.5 else "moderate"
        else:
            signal = "neutral"
            strength = "neutral"
        return {"score": round(score, 3), "signal": signal, "strength": strength}

    def _explain_indicators(self, data: list, details: dict) -> dict:
        rsi = details.get("rsi", 50)
        macd = details.get("macd", 0)
        return {
            "rsi": {"value": rsi, "signal": "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"},
            "macd": {"value": macd, "signal": "bullish" if macd > 0 else "bearish"},
        }

    def _explain_smc(self, score: float) -> dict:
        if score > 0.2:
            return {"score": round(score, 3), "signal": "bullish_liquidity_grab", "description": "Liquidity sweep to downside, bullish reversal expected"}
        elif score < -0.2:
            return {"score": round(score, 3), "signal": "bearish_liquidity_grab", "description": "Liquidity sweep to upside, bearish reversal expected"}
        return {"score": 0, "signal": "neutral", "description": "No significant SMC pattern detected"}

    def _explain_risk(self, risk_level: Optional[str], volatility_score: float) -> dict:
        level = risk_level or "medium"
        return {
            "level": level,
            "score": round(abs(volatility_score), 3),
            "description": f"Risk level: {level.upper()}. {'Use wider stops and lower leverage.' if level in ('high', 'medium') else 'Standard risk parameters apply.'}",
        }


ai_explainability = AIExplainabilityEngine()
