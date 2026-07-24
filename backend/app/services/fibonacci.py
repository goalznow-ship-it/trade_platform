"""
Fibonacci Analysis Engine
- Automatic retracement levels (0, 0.236, 0.382, 0.5, 0.618, 0.786, 1)
- Extension levels (1.272, 1.618, 2.618)
- Golden zone detection (0.382-0.618)
- AI TP calculation based on fib levels
"""
import numpy as np
from typing import Optional


def _convert(obj):
    if isinstance(obj, dict):
        return {k: _convert(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert(v) for v in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return _convert(obj.tolist())
    return obj


FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.618, 2.618]


class FibonacciEngine:
    def calculate(self, data: list) -> dict:
        if len(data) < 20:
            return {"levels": [], "golden_zone": None, "direction": "neutral"}
        highs = np.array([d["high"] for d in data])
        lows = np.array([d["low"] for d in data])
        closes = np.array([d["close"] for d in data])
        current_price = float(closes[-1])

        swing_high = float(np.max(highs[-60:])) if len(highs) >= 60 else float(np.max(highs))
        swing_low = float(np.min(lows[-60:])) if len(lows) >= 60 else float(np.min(lows))

        recent_5_high = float(np.max(highs[-5:]))
        recent_5_low = float(np.min(lows[-5:]))

        is_uptrend = closes[-10] < closes[-1] if len(closes) >= 10 else True
        if is_uptrend:
            high = swing_high
            low = swing_low
            direction = "long"
        else:
            high = recent_5_high
            low = recent_5_low
            direction = "short"

        range_val = high - low if high > low else 0.0001

        levels = []
        for fib in FIB_LEVELS:
            if is_uptrend:
                retrace_price = high - range_val * fib
                level_type = "extension" if fib >= 1 else "retracement"
            else:
                retrace_price = low + range_val * fib
                level_type = "extension" if fib >= 1 else "retracement"
            distance_pct = abs(current_price - retrace_price) / current_price * 100 if current_price > 0 else 0
            levels.append({
                "level": fib,
                "price": round(retrace_price, 4),
                "type": level_type,
                "distance_pct": round(distance_pct, 2),
            })

        golden_zone = {
            "low": round(high - range_val * 0.618 if is_uptrend else low + range_val * 0.382, 4),
            "high": round(high - range_val * 0.382 if is_uptrend else low + range_val * 0.618, 4),
        }
        in_golden_zone = golden_zone["low"] <= current_price <= golden_zone["high"]
        golden_zone["current_price_in_zone"] = in_golden_zone

        nearest_level = min(levels, key=lambda x: abs(x["price"] - current_price))
        nearest_retracement = [l for l in levels if l["type"] == "retracement"]
        nearest_retrace = min(nearest_retracement, key=lambda x: abs(x["price"] - current_price)) if nearest_retracement else nearest_level

        support_fib = None
        resistance_fib = None
        for l in levels:
            if l["price"] < current_price:
                support_fib = l
            elif l["price"] > current_price and resistance_fib is None:
                resistance_fib = l

        ai_targets = {}
        if direction == "long":
            for ext in [l for l in levels if l["level"] in (1.272, 1.618, 2.618)]:
                ai_targets[f"tp_{ext['level']}"] = round(ext["price"], 4)
        else:
            for ext in [l for l in levels if l["level"] in (1.272, 1.618, 2.618)]:
                ai_targets[f"tp_{ext['level']}"] = round(ext["price"], 4)

        return _convert({
            "levels": levels,
            "golden_zone": golden_zone,
            "direction": direction,
            "swing_high": round(high, 4),
            "swing_low": round(low, 4),
            "nearest_level": nearest_level,
            "nearest_retracement": nearest_retrace,
            "support_level": support_fib,
            "resistance_level": resistance_fib,
            "ai_targets": ai_targets if ai_targets else None,
            "range": round(range_val, 4),
            "current_price": round(current_price, 4),
        })

    def calculate_tp_from_fib(self, entry: float, direction: str, fib_levels: list) -> dict:
        tps = {}
        for lvl in fib_levels:
            if lvl["level"] in (1.272, 1.618, 2.618):
                label = f"TP_{lvl['level']}".replace(".", "_")
                if direction == "long" and lvl["price"] > entry:
                    tps[label] = round(lvl["price"], 4)
                elif direction == "short" and lvl["price"] < entry:
                    tps[label] = round(lvl["price"], 4)
        return tps


fibonacci = FibonacciEngine()
