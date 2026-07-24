"""
Pattern Analysis Engine

Advanced chart pattern recognition:
- Candlestick patterns (doji, hammer, engulfing, etc.)
- Trend line detection (S/R from swing points)
- Elliott Wave counting (impulse 1-5, corrective A-B-C)
- Fibonacci retracement/extension levels
- Liquidity zone aggregation from SMC data
"""
import numpy as np
from typing import Optional


def _convert_numpy(obj):
    """Recursively convert numpy types to native Python types for JSON serialization"""
    if isinstance(obj, dict):
        return {k: _convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(_convert_numpy(v) for v in obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return _convert_numpy(obj.tolist())
    return obj


class PatternAnalysisEngine:
    def analyze_candlestick_patterns(self, data: list) -> dict:
        if len(data) < 5:
            return {"patterns": [], "count": 0}

        opens = np.array([d["open"] for d in data])
        highs = np.array([d["high"] for d in data])
        lows = np.array([d["low"] for d in data])
        closes = np.array([d["close"] for d in data])
        volumes = np.array([d["volume"] for d in data])

        patterns = []
        last_idx = len(data) - 1

        body = abs(closes - opens)
        upper_wick = highs - np.maximum(closes, opens)
        lower_wick = np.minimum(closes, opens) - lows
        total_range = highs - lows
        avg_body = np.mean(body[-20:]) if len(body) >= 20 else np.mean(body)
        avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)

        for i in range(last_idx, max(last_idx - 3, 2), -1):
            c, o = closes[i], opens[i]
            h, l = highs[i], lows[i]
            tr = total_range[i]
            b = body[i]

            idx_relative = i - last_idx

            if tr == 0:
                continue

            body_ratio = b / tr if tr > 0 else 0

            if body_ratio < 0.1 and tr > avg_body * 0.5:
                patterns.append({
                    "name": "Doji",
                    "type": "neutral",
                    "signal": "indecision",
                    "index": idx_relative,
                    "price": c,
                    "strength": "strong" if tr > avg_body * 1.5 else "moderate",
                })

            if i >= 1:
                prev_c, prev_o = closes[i - 1], opens[i - 1]
                prev_b = abs(prev_c - prev_o)
                prev_body_ratio = prev_b / total_range[i - 1] if total_range[i - 1] > 0 else 0

                if b > avg_body * 1.3:
                    if upper_wick[i] < b * 0.3 and lower_wick[i] < b * 0.3:
                        if c > o:
                            patterns.append({
                                "name": "Marubozu",
                                "type": "bullish",
                                "signal": "strong_bullish",
                                "index": idx_relative,
                                "price": c,
                                "strength": "strong",
                            })
                        else:
                            patterns.append({
                                "name": "Marubozu",
                                "type": "bearish",
                                "signal": "strong_bearish",
                                "index": idx_relative,
                                "price": c,
                                "strength": "strong",
                            })

                if lower_wick[i] > b * 2 and upper_wick[i] < b * 0.5 and c > o:
                    patterns.append({
                        "name": "Hammer",
                        "type": "bullish",
                        "signal": "reversal_up",
                        "index": idx_relative,
                        "price": c,
                        "strength": "strong" if lower_wick[i] > b * 3 else "moderate",
                    })

                if upper_wick[i] > b * 2 and lower_wick[i] < b * 0.5 and c < o:
                    patterns.append({
                        "name": "Shooting Star",
                        "type": "bearish",
                        "signal": "reversal_down",
                        "index": idx_relative,
                        "price": c,
                        "strength": "strong" if upper_wick[i] > b * 3 else "moderate",
                    })

                if c < o and upper_wick[i] > b * 1.5 and lower_wick[i] > b * 1.5:
                    patterns.append({
                        "name": "Dragonfly Doji",
                        "type": "bullish",
                        "signal": "reversal_up",
                        "index": idx_relative,
                        "price": c,
                        "strength": "moderate",
                    })

            if i >= 2:
                c1, o1 = closes[i - 1], opens[i - 1]
                c2, o2 = closes[i - 2], opens[i - 2]
                h1, l1 = highs[i - 1], lows[i - 1]

                if c > o and c1 < o1:
                    if c > max(o, h1) and o < min(c1, o1, l1):
                        patterns.append({
                            "name": "Bullish Engulfing",
                            "type": "bullish",
                            "signal": "strong_reversal_up",
                            "index": idx_relative,
                            "price": c,
                            "strength": "strong",
                        })

                if c < o and c1 > o1:
                    if c < min(o, l1) and o > max(c1, o1, h1):
                        patterns.append({
                            "name": "Bearish Engulfing",
                            "type": "bearish",
                            "signal": "strong_reversal_down",
                            "index": idx_relative,
                            "price": c,
                            "strength": "strong",
                        })

            if i >= 3:
                c1, o1, h1, l1 = closes[i - 1], opens[i - 1], highs[i - 1], lows[i - 1]
                c2, o2, h2, l2 = closes[i - 2], opens[i - 2], highs[i - 2], lows[i - 2]
                c3, o3 = closes[i - 3], opens[i - 3]

                if c > o and c2 < o2:
                    if body[i] > avg_body and body[i - 2] > avg_body * 0.5:
                        if c > max(c1, c2) and o < min(o1, o2):
                            patterns.append({
                                "name": "Morning Star",
                                "type": "bullish",
                                "signal": "strong_reversal_up",
                                "index": idx_relative,
                                "price": c,
                                "strength": "strong",
                            })

                if c < o and c2 > o2:

                    if body[i] > avg_body and body[i - 2] > avg_body * 0.5:
                        if c < min(c1, c2) and o > max(o1, o2):
                            patterns.append({
                                "name": "Evening Star",
                                "type": "bearish",
                                "signal": "strong_reversal_down",
                                "index": idx_relative,
                                "price": c,
                                "strength": "strong",
                            })

            if i >= 2:
                c1, o1 = closes[i - 1], opens[i - 1]
                h1, l1 = highs[i - 1], lows[i - 1]

                if c > o and o < l1 and c > h1:
                    patterns.append({
                        "name": "Piercing Line",
                        "type": "bullish",
                        "signal": "reversal_up",
                        "index": idx_relative,
                        "price": c,
                        "strength": "moderate",
                    })

                if c < o and o > h1 and c < l1:
                    patterns.append({
                        "name": "Dark Cloud Cover",
                        "type": "bearish",
                        "signal": "reversal_down",
                        "index": idx_relative,
                        "price": c,
                        "strength": "moderate",
                    })

            if volumes[i] > avg_volume * 1.5:
                if c > o and body[i] > avg_body:
                    patterns.append({
                        "name": "Volume Climax",
                        "type": "bullish",
                        "signal": "strong_momentum",
                        "index": idx_relative,
                        "price": c,
                        "strength": "moderate",
                    })
                elif c < o and body[i] > avg_body:
                    patterns.append({
                        "name": "Volume Climax",
                        "type": "bearish",
                        "signal": "strong_momentum",
                        "index": idx_relative,
                        "price": c,
                        "strength": "moderate",
                    })

            if i >= 4:
                w1 = closes[i - 4:i]
                w2 = closes[i - 3:i + 1]
                if len(w1) >= 3 and len(w2) >= 3:
                    if all(w1[j] < w1[j + 1] for j in range(3)) and c < o:
                        patterns.append({
                            "name": "Three Black Crows",
                            "type": "bearish",
                            "signal": "strong_reversal_down",
                            "index": idx_relative,
                            "price": c,
                            "strength": "strong",
                        })
                    if all(w1[j] > w1[j + 1] for j in range(3)) and c > o:
                        patterns.append({
                            "name": "Three White Soldiers",
                            "type": "bullish",
                            "signal": "strong_reversal_up",
                            "index": idx_relative,
                            "price": c,
                            "strength": "strong",
                        })

        bullish = sum(1 for p in patterns if p["type"] == "bullish")
        bearish = sum(1 for p in patterns if p["type"] == "bearish")
        neutral = sum(1 for p in patterns if p["type"] == "neutral")
        strong_bullish = sum(1 for p in patterns if p["type"] == "bullish" and p["strength"] == "strong")
        strong_bearish = sum(1 for p in patterns if p["type"] == "bearish" and p["strength"] == "strong")

        pattern_score = 0
        pattern_score += strong_bullish * 15
        pattern_score += bullish * 5
        pattern_score -= strong_bearish * 15
        pattern_score -= bearish * 5

        if pattern_score > 20:
            pattern_direction = "long"
        elif pattern_score < -20:
            pattern_direction = "short"
        else:
            pattern_direction = "neutral"

        return {
            "patterns": patterns[-12:],
            "total_count": len(patterns),
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "strong_bullish": strong_bullish,
            "strong_bearish": strong_bearish,
            "pattern_score": pattern_score,
            "pattern_direction": pattern_direction,
            "latest_pattern": patterns[0] if patterns else None,
        }

    def detect_trend_lines(self, data: list) -> dict:
        if len(data) < 20:
            return {"support_lines": [], "resistance_lines": [], "count": 0}

        highs = np.array([d["high"] for d in data])
        lows = np.array([d["low"] for d in data])
        closes = np.array([d["close"] for d in data])

        current_price = closes[-1]

        def find_swing_highs(values, window=5):
            swings = []
            for i in range(window, len(values) - window):
                if values[i] == max(values[i - window:i + window + 1]):
                    swings.append({"index": i, "price": float(values[i])})
            return swings

        def find_swing_lows(values, window=5):
            swings = []
            for i in range(window, len(values) - window):
                if values[i] == min(values[i - window:i + window + 1]):
                    swings.append({"index": i, "price": float(values[i])})
            return swings

        swing_highs = find_swing_highs(highs, 5)
        swing_lows = find_swing_lows(lows, 5)

        def fit_trend_line(points, min_touch=2):
            if len(points) < 2:
                return None
            x = np.array([p["index"] for p in points])
            y = np.array([p["price"] for p in points])
            if len(x) < 2:
                return None
            slope, intercept = np.polyfit(x, y, 1)
            touches = sum(1 for p in points if abs(p["price"] - (slope * p["index"] + intercept)) / p["price"] < 0.002)
            if touches >= min_touch:
                return {
                    "slope": float(slope),
                    "intercept": float(intercept),
                    "start_index": points[0]["index"],
                    "end_index": points[-1]["index"],
                    "start_price": float(slope * points[0]["index"] + intercept),
                    "end_price": float(slope * points[-1]["index"] + intercept),
                    "touches": touches,
                    "angle_degrees": float(np.degrees(np.arctan(slope))),
                }
            return None

        support_lines = []
        resistance_lines = []

        if len(swing_lows) >= 3:
            for i in range(len(swing_lows) - 2):
                line = fit_trend_line(swing_lows[i:i + 3], min_touch=2)
                if line and line["touches"] >= 2:
                    support_lines.append(line)

        if len(swing_highs) >= 3:
            for i in range(len(swing_highs) - 2):
                line = fit_trend_line(swing_highs[i:i + 3], min_touch=2)
                if line and line["touches"] >= 2:
                    resistance_lines.append(line)

        support_lines = support_lines[-3:]
        resistance_lines = resistance_lines[-3:]

        closest_support = None
        closest_resistance = None
        support_distance = float("inf")
        resistance_distance = float("inf")

        for s in support_lines:
            dist = abs(current_price - s["end_price"])
            if dist < support_distance:
                support_distance = dist
                closest_support = s

        for r in resistance_lines:
            dist = abs(r["end_price"] - current_price)
            if dist < resistance_distance:
                resistance_distance = dist
                closest_resistance = r

        return {
            "support_lines": support_lines,
            "resistance_lines": resistance_lines,
            "closest_support": closest_support,
            "closest_resistance": closest_resistance,
            "support_count": len(support_lines),
            "resistance_count": len(resistance_lines),
        }

    def analyze_elliott_wave(self, data: list) -> dict:
        if len(data) < 60:
            return {"count": "unknown", "waves": [], "current_phase": "insufficient_data"}

        closes = np.array([d["close"] for d in data])
        highs = np.array([d["high"] for d in data])
        lows = np.array([d["low"] for d in data])

        def find_swings(values, window=8):
            peaks = []
            for i in range(window, len(values) - window):
                if values[i] == max(values[i - window:i + window + 1]):
                    peaks.append({"index": i, "price": float(values[i]), "type": "high"})
                if values[i] == min(values[i - window:i + window + 1]):
                    peaks.append({"index": i, "price": float(values[i]), "type": "low"})
            return peaks

        swings = find_swings(closes, 8)
        if len(swings) < 5:
            return {"count": "unknown", "waves": [], "current_phase": "unclear"}

        last_90 = closes[-60:]
        last_90_high = float(max(last_90))
        last_90_low = float(min(last_90))
        range_90 = last_90_high - last_90_low if last_90_high > last_90_low else 1

        sorted_swings = sorted(swings, key=lambda x: x["index"])
        recent = sorted_swings[-12:]

        waves = []
        for i in range(1, len(recent)):
            prev_price = recent[i - 1]["price"]
            curr_price = recent[i]["price"]
            move_pct = (curr_price - prev_price) / prev_price * 100
            waves.append({
                "from_index": recent[i - 1]["index"],
                "to_index": recent[i]["index"],
                "from_price": prev_price,
                "to_price": curr_price,
                "move_percent": round(move_pct, 2),
                "direction": "up" if move_pct > 0 else "down",
                "magnitude": abs(move_pct),
            })

        current_price = closes[-1]
        position_in_range = (current_price - last_90_low) / range_90

        impulse_up = None
        impulse_down = None
        corrective_up = None
        corrective_down = None

        for i in range(len(waves) - 4):
            segment = waves[i:i + 5]
            if all(w["direction"] == "up" for w in segment[0::2]):
                total_move = sum(w["move_percent"] for w in segment[0::2])
                if total_move > 5:
                    w3 = segment[2] if len(segment) > 2 else None
                    w3_extended = w3 and abs(w3["move_percent"]) > abs(segment[0]["move_percent"]) * 1.5 if segment else False
                    impulse_up = {
                        "count": "impulse_1_5",
                        "direction": "bullish",
                        "total_move_percent": round(total_move, 2),
                        "wave3_extended": w3_extended,
                        "current_position": position_in_range * 100,
                    }
            if all(w["direction"] == "down" for w in segment[0::2]):
                total_move = sum(abs(w["move_percent"]) for w in segment[0::2])
                if total_move > 5:
                    impulse_down = {
                        "count": "impulse_1_5",
                        "direction": "bearish",
                        "total_move_percent": round(total_move, 2),
                        "current_position": position_in_range * 100,
                    }

        for i in range(len(waves) - 2):
            segment = waves[i:i + 3]
            if segment[0]["direction"] == "up" and segment[1]["direction"] == "down" and len(segment) > 2:
                if abs(segment[1]["move_percent"]) < abs(segment[0]["move_percent"]) * 0.618:
                    corrective_up = {
                        "count": "abc_corrective",
                        "direction": "bullish",
                        "retrace_percent": round(abs(segment[1]["move_percent"] / segment[0]["move_percent"]) * 100, 1),
                        "wave_a": segment[0],
                        "wave_b": segment[1],
                        "wave_c": segment[2] if len(segment) > 2 else None,
                    }
            if segment[0]["direction"] == "down" and segment[1]["direction"] == "up" and len(segment) > 2:
                if abs(segment[1]["move_percent"]) < abs(segment[0]["move_percent"]) * 0.618:
                    corrective_down = {
                        "count": "abc_corrective",
                        "direction": "bearish",
                        "retrace_percent": round(abs(segment[1]["move_percent"] / segment[0]["move_percent"]) * 100, 1),
                        "wave_a": segment[0],
                        "wave_b": segment[1],
                        "wave_c": segment[2] if len(segment) > 2 else None,
                    }

        last_3 = waves[-3:] if len(waves) >= 3 else waves
        last_direction = last_3[-1]["direction"] if last_3 else "unknown"

        zones = []
        if impulse_up:
            zones.append({
                "name": "Impulse 1-5",
                "type": "bullish",
                "description": "5-wave impulse sequence up",
                "current_position_pct": impulse_up["current_position"],
            })
        if impulse_down:
            zones.append({
                "name": "Impulse 1-5",
                "type": "bearish",
                "description": "5-wave impulse sequence down",
                "current_position_pct": impulse_down["current_position"],
            })
        if corrective_up:
            zones.append({
                "name": "ABC Corrective",
                "type": "bullish",
                "description": f"ABC corrective wave ({corrective_up['retrace_percent']}% retrace)",
                "retrace_percent": corrective_up["retrace_percent"],
            })
        if corrective_down:
            zones.append({
                "name": "ABC Corrective",
                "type": "bearish",
                "description": f"ABC corrective wave ({corrective_down['retrace_percent']}% retrace)",
                "retrace_percent": corrective_down["retrace_percent"],
            })

        return {
            "count": "impulse" if impulse_up or impulse_down else "corrective" if corrective_up or corrective_down else "unclear",
            "waves": zones,
            "current_phase": last_direction,
            "impulse_up": impulse_up,
            "impulse_down": impulse_down,
            "corrective_up": corrective_up,
            "corrective_down": corrective_down,
            "swing_points": swings[-10:],
            "current_price": float(current_price),
        }

    def calculate_fibonacci_levels(self, data: list) -> dict:
        if len(data) < 20:
            return {"levels": [], "count": 0}

        highs = np.array([d["high"] for d in data])
        lows = np.array([d["low"] for d in data])
        closes = np.array([d["close"] for d in data])

        swing_high = float(max(highs[-30:]))
        swing_low = float(min(lows[-30:]))
        range_val = swing_high - swing_low if swing_high > swing_low else 1

        retracement_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        extension_levels = [1.272, 1.414, 1.618, 2.0, 2.618, 3.618]

        retracements = [
            {"level": lvl, "price": round(swing_high - lvl * range_val, 2), "type": "retracement"}
            for lvl in retracement_levels
        ]
        extensions_up = [
            {"level": lvl, "price": round(swing_high + lvl * range_val, 2), "type": "extension_up"}
            for lvl in extension_levels
        ]
        extensions_down = [
            {"level": lvl, "price": round(swing_low - lvl * range_val, 2), "type": "extension_down"}
            for lvl in extension_levels
        ]

        nearest_bullish_target = None
        nearest_bearish_target = None
        min_bull_dist = float("inf")
        min_bear_dist = float("inf")
        current_price = float(closes[-1])

        all_levels = sorted(
            retracements + extensions_up + extensions_down,
            key=lambda x: x["price"],
        )

        for lvl in all_levels:
            if lvl["price"] > current_price:
                dist = lvl["price"] - current_price
                if dist < min_bull_dist:
                    min_bull_dist = dist
                    nearest_bullish_target = lvl
            if lvl["price"] < current_price:
                dist = current_price - lvl["price"]
                if dist < min_bear_dist:
                    min_bear_dist = dist
                    nearest_bearish_target = lvl

        current_position_in_range = (current_price - swing_low) / range_val if range_val > 0 else 0.5

        return {
            "swing_high": swing_high,
            "swing_low": swing_low,
            "range": round(range_val, 2),
            "retracements": retracements,
            "extensions_up": extensions_up,
            "extensions_down": extensions_down,
            "all_levels": all_levels,
            "nearest_bullish_target": nearest_bullish_target,
            "nearest_bearish_target": nearest_bearish_target,
            "current_price": current_price,
            "current_position_in_range": round(current_position_in_range, 2),
            "golden_zone": {
                "low": round(swing_high - 0.618 * range_val, 2),
                "high": round(swing_high - 0.382 * range_val, 2),
            },
        }

    def aggregate_liquidity_zones(self, smc_data: dict) -> dict:
        """Extract and aggregate liquidity zones from SMC engine data"""
        zones = []
        levels = {"support": [], "resistance": []}

        if smc_data.get("liquidity_pools"):
            for pool in smc_data["liquidity_pools"]:
                zone_type = "resistance" if pool["type"] == "sell_side" else "support"
                zones.append({
                    "type": zone_type,
                    "price": pool["price"],
                    "source": "liquidity_pool",
                    "strength": pool.get("strength", "moderate"),
                })
                if zone_type == "support":
                    levels["support"].append(pool["price"])
                else:
                    levels["resistance"].append(pool["price"])

        if smc_data.get("liquidity_sweep"):
            sweep = smc_data["liquidity_sweep"]
            if isinstance(sweep, dict) and sweep.get("swept_level"):
                zone_type = "support" if "buy" in sweep.get("type", "") else "resistance"
                zones.append({
                    "type": zone_type,
                    "price": sweep["swept_level"],
                    "source": "liquidity_sweep",
                    "strength": "strong",
                    "note": "Swept level - potential liquidity grab",
                })
                if zone_type == "support":
                    levels["support"].append(sweep["swept_level"])
                else:
                    levels["resistance"].append(sweep["swept_level"])

        if smc_data.get("order_blocks"):
            for ob in smc_data["order_blocks"]:
                if isinstance(ob, dict):
                    zt = "support" if ob.get("type") == "bullish" else "resistance"
                    zone = {
                        "type": zt,
                        "price_low": ob.get("price_low"),
                        "price_high": ob.get("price_high"),
                        "source": "order_block",
                        "strength": ob.get("strength", "moderate"),
                    }
                    zones.append(zone)
                    mid = (ob.get("price_low", 0) + ob.get("price_high", 0)) / 2
                    if zt == "support":
                        levels["support"].append(mid)
                    else:
                        levels["resistance"].append(mid)

        if smc_data.get("fair_value_gaps"):
            for fvg in smc_data["fair_value_gaps"]:
                if isinstance(fvg, dict) and not fvg.get("mitigated"):
                    zt = "support" if "bullish" in fvg.get("type", "") else "resistance"
                    mid = (fvg.get("low", 0) + fvg.get("high", 0)) / 2
                    zones.append({
                        "type": zt,
                        "price_low": fvg.get("low"),
                        "price_high": fvg.get("high"),
                        "source": "fvg",
                        "strength": "strong" if fvg.get("gap_size", 0) > 0 else "moderate",
                        "note": "Unmitigated FVG",
                    })
                    if zt == "support":
                        levels["support"].append(mid)
                    else:
                        levels["resistance"].append(mid)

        current_price = smc_data.get("current_price", 0)

        nearest_support = max(levels["support"]) if levels["support"] and current_price else None
        nearest_resistance = min(levels["resistance"]) if levels["resistance"] and current_price else None

        if nearest_support and nearest_support >= current_price:
            nearest_support = max([p for p in levels["support"] if p < current_price], default=None) if levels["support"] else None
        if nearest_resistance and nearest_resistance <= current_price:
            nearest_resistance = min([p for p in levels["resistance"] if p > current_price], default=None) if levels["resistance"] else None

        return {
            "zones": zones,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "support_levels": sorted(set(levels["support"])),
            "resistance_levels": sorted(set(levels["resistance"])),
            "total_zones": len(zones),
        }

    async def comprehensive_analysis(self, symbol: str, timeframe: str, ohlcv_data: list, smc_data: dict = None) -> dict:
        patterns = self.analyze_candlestick_patterns(ohlcv_data)
        trend_lines = self.detect_trend_lines(ohlcv_data)
        elliott = self.analyze_elliott_wave(ohlcv_data)
        fibonacci = self.calculate_fibonacci_levels(ohlcv_data)

        liquidity_zones = {"zones": [], "nearest_support": None, "nearest_resistance": None,
                           "support_levels": [], "resistance_levels": [], "total_zones": 0}
        if smc_data:
            liquidity_zones = self.aggregate_liquidity_zones(smc_data)

        closes = np.array([d["close"] for d in ohlcv_data])
        current_price = float(closes[-1])

        pattern_dir_score = patterns.get("pattern_score", 0)
        trend_bias = 0
        if trend_lines.get("closest_support"):
            support_dist = abs(current_price - trend_lines["closest_support"]["end_price"]) / current_price * 100
            trend_bias += min(15, 15 - support_dist)
        if trend_lines.get("closest_resistance"):
            resistance_dist = abs(trend_lines["closest_resistance"]["end_price"] - current_price) / current_price * 100
            trend_bias -= min(15, 15 - resistance_dist)

        elliott_bias = 0
        if elliott.get("impulse_up"):
            elliott_bias += 20
        if elliott.get("impulse_down"):
            elliott_bias -= 20

        fib_bias = 0
        if fibonacci.get("nearest_bullish_target"):
            fib_move = (fibonacci["nearest_bullish_target"]["price"] - current_price) / current_price * 100
            if fib_move < 5:
                fib_bias += 10
        if fibonacci.get("nearest_bearish_target"):
            fib_move = (current_price - fibonacci["nearest_bearish_target"]["price"]) / current_price * 100
            if fib_move < 5:
                fib_bias -= 10

        combined_score = pattern_dir_score + trend_bias + elliott_bias + fib_bias

        if combined_score > 15:
            direction = "long"
        elif combined_score < -15:
            direction = "short"
        else:
            direction = "neutral"

        return _convert_numpy({
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": current_price,
            "direction": direction,
            "combined_score": combined_score,
            "components": {
                "candlestick_patterns": patterns,
                "trend_lines": trend_lines,
                "elliott_wave": elliott,
                "fibonacci": fibonacci,
                "liquidity_zones": liquidity_zones,
            },
        })


pattern_engine = PatternAnalysisEngine()
