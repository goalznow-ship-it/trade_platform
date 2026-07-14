"""
Multi-Timeframe Analysis Engine

Aggregates signals across timeframes:
- 1W: Macro trend
- 1D: Daily structure
- 4H: Direction confirmation
- 1H: Setup generation
- 15M: Entry confirmation
- 5M: Execution timing

Rules:
- Signals without alignment across >= 3 timeframes are capped at 80%
- Weekly determines macro bias
- Daily confirms structure
- 4H confirms direction
- 1H generates setup
- 15M confirms entry
- 5M gives execution timing
"""
import asyncio
from typing import List, Dict, Optional
from app.services.market import market_service
from app.services.institutional_scoring import institutional_scorer
from app.services.smc_engine import smc_engine
from app.core.logging import logger

TIMEFRAMES = ["1w", "1d", "4h", "1h", "15m", "5m"]

TIMEFRAME_WEIGHTS = {
    "1w": {"trend": 0.30, "alignment": 0.25},
    "1d": {"trend": 0.25, "alignment": 0.20},
    "4h": {"trend": 0.20, "alignment": 0.20},
    "1h": {"trend": 0.15, "alignment": 0.18},
    "15m": {"trend": 0.07, "alignment": 0.10},
    "5m": {"trend": 0.03, "alignment": 0.07},
}

TIMEFRAME_LIMITS = {
    "1w": 100,
    "1d": 200,
    "4h": 200,
    "1h": 200,
    "15m": 100,
    "5m": 100,
}


class MultiTimeframeAnalyzer:
    async def analyze(self, symbol: str, timeframes: Optional[List[str]] = None) -> dict:
        if timeframes is None:
            timeframes = TIMEFRAMES

        results = {}
        errors = []

        for tf in timeframes:
            try:
                limit = TIMEFRAME_LIMITS.get(tf, 100)
                data = await market_service.get_ohlcv(symbol, "binance", tf, limit)
                if not data or len(data) < 30:
                    errors.append(f"{tf}: insufficient data ({len(data) if data else 0} candles)")
                    continue

                smc_data = smc_engine.analyze(data)
                score_result = await institutional_scorer.score(symbol, data, tf, smc_data)

                results[tf] = {
                    "score": score_result["total_score"],
                    "abs_score": score_result["abs_score"],
                    "direction": score_result["direction"],
                    "classification": score_result["classification"],
                    "scores": score_result["scores"],
                    "risk_level": score_result["risk_level"],
                    "trend": smc_data.get("trend", "unknown"),
                    "details": score_result.get("details", {}),
                    "smc": {
                        "bos_count": smc_data.get("bos_count", 0),
                        "choch_count": smc_data.get("choch_count", 0),
                        "net_bos": smc_data.get("net_bos", 0),
                        "net_choch": smc_data.get("net_choch", 0),
                        "premium_discount": smc_data.get("premium_discount", {}),
                        "liquidity_sweep": smc_data.get("liquidity_sweep"),
                        "displacement": smc_data.get("displacement"),
                    },
                    "candle_count": len(data),
                }

                await asyncio.sleep(0.05)

            except Exception as e:
                errors.append(f"{tf}: {str(e)}")
                continue

        if not results:
            return {
                "symbol": symbol,
                "error": "No timeframe analysis available",
                "errors": errors,
                "aggregated": None,
            }

        aggregated = self._aggregate(results, timeframes)
        alignment = self._check_alignment(results)

        return {
            "symbol": symbol,
            "aggregated": aggregated,
            "alignment": alignment,
            "timeframes": results,
            "errors": errors if errors else None,
        }

    def _aggregate(self, results: dict, timeframes: List[str]) -> dict:
        weighted_score = 0.0
        total_weight = 0.0
        long_count = 0
        short_count = 0
        neutral_count = 0
        classification_counts = {}

        for tf in timeframes:
            if tf not in results:
                continue

            r = results[tf]
            weight = TIMEFRAME_WEIGHTS.get(tf, {}).get("trend", 0.1)
            weighted_score += r["score"] * weight
            total_weight += weight

            if r["direction"] == "long":
                long_count += 1
            elif r["direction"] == "short":
                short_count += 1
            else:
                neutral_count += 1

            cls = r["classification"]
            classification_counts[cls] = classification_counts.get(cls, 0) + 1

        avg_score = weighted_score / total_weight if total_weight > 0 else 0
        abs_avg = abs(avg_score)

        if avg_score > 5:
            agg_direction = "long"
        elif avg_score < -5:
            agg_direction = "short"
        else:
            agg_direction = "neutral"

        first_valid = next((results[tf] for tf in timeframes if tf in results), None)
        details = first_valid["details"] if first_valid else {}

        return {
            "total_score": round(avg_score, 1),
            "abs_score": round(abs_avg, 1),
            "direction": agg_direction,
            "long_probability": round(max(0, min(100, 50 + avg_score * 0.5)), 1),
            "short_probability": round(max(0, min(100, 50 - avg_score * 0.5)), 1),
            "classification": self._classify(abs_avg),
            "timeframe_count": len(results),
            "timeframe_breakdown": {
                "long": long_count,
                "short": short_count,
                "neutral": neutral_count,
            },
            "risk_level": first_valid.get("risk_level", "medium") if first_valid else "unknown",
            "details": details,
        }

    def _check_alignment(self, results: dict) -> dict:
        directions = {}
        for tf, r in results.items():
            d = r["direction"]
            if d not in directions:
                directions[d] = []
            directions[d].append(tf)

        long_tfs = directions.get("long", [])
        short_tfs = directions.get("short", [])
        neutral_tfs = directions.get("neutral", [])

        total = len(results)
        long_weight = sum(TIMEFRAME_WEIGHTS.get(tf, {}).get("alignment", 0) for tf in long_tfs)
        short_weight = sum(TIMEFRAME_WEIGHTS.get(tf, {}).get("alignment", 0) for tf in short_tfs)

        dominant_direction = "long" if long_weight > short_weight else "short" if short_weight > long_weight else "neutral"
        dominant_tfs = long_tfs if long_weight >= short_weight else short_tfs

        major_tfs = ["1w", "1d", "4h"]
        major_aligned = all(tf in dominant_tfs for tf in major_tfs if tf in results)
        minor_aligned = len(dominant_tfs) >= 3

        return {
            "dominant_direction": dominant_direction,
            "long_timeframes": long_tfs,
            "short_timeframes": short_tfs,
            "neutral_timeframes": neutral_tfs,
            "long_weight": round(long_weight, 2),
            "short_weight": round(short_weight, 2),
            "major_aligned": major_aligned,
            "minor_aligned": minor_aligned,
            "alignment_score": round(max(long_weight, short_weight), 2),
            "total_timeframes": total,
        }

    def _classify(self, score: float) -> str:
        if score >= 95: return "institutional_grade"
        elif score >= 90: return "excellent"
        elif score >= 85: return "very_strong"
        elif score >= 80: return "strong"
        elif score >= 70: return "watchlist"
        return "reject"


multi_timeframe = MultiTimeframeAnalyzer()
