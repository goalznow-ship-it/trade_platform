"""
Chart Pattern Analysis Engine

Detects chart formations:
- Bullish/Bearish Flag & Pennant
- Ascending/Descending/Symmetrical Triangle
- Double Top/Bottom
- Head and Shoulders / Inverse H&S
- Rising/Falling Wedge
- Ascending/Descending Channel
- Rectangle Consolidation
- Cup and Handle
"""
import numpy as np
from typing import Optional


def _convert_numpy(obj):
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


class ChartPatternEngine:
    def detect_all(self, data: list) -> dict:
        if len(data) < 50:
            return {"patterns": [], "count": 0, "forming_patterns": []}

        highs = np.array([d["high"] for d in data])
        lows = np.array([d["low"] for d in data])
        closes = np.array([d["close"] for d in data])
        opens = np.array([d["open"] for d in data])
        volumes = np.array([d["volume"] for d in data])

        current_price = float(closes[-1])

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

        patterns = []
        forming = []

        def fit_line(points):
            if len(points) < 2:
                return None
            x = np.array([p["index"] for p in points])
            y = np.array([p["price"] for p in points])
            slope, intercept = np.polyfit(x, y, 1)
            return {"slope": float(slope), "intercept": float(intercept)}

        def line_value(line, idx):
            return line["slope"] * idx + line["intercept"]

        # Double Top
        if len(swing_highs) >= 4:
            recent_sh = swing_highs[-4:]
            if len(recent_sh) >= 2:
                p1, p2 = recent_sh[-2], recent_sh[-1]
                diff_pct = abs(p1["price"] - p2["price"]) / max(p1["price"], p2["price"]) * 100
                if diff_pct < 1.5 and p1["index"] != p2["index"]:
                    valley = min(lows[p1["index"]:p2["index"] + 1]) if p2["index"] > p1["index"] else 0
                    neckline = float(valley)
                    target = p1["price"] - (p1["price"] - neckline)
                    patterns.append({
                        "name": "Double Top",
                        "type": "bearish",
                        "signal": "reversal_down",
                        "strength": "strong" if diff_pct < 0.5 else "moderate",
                        "left_top": round(p1["price"], 4),
                        "right_top": round(p2["price"], 4),
                        "neckline": round(neckline, 4),
                        "target": round(target, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": "short",
                        "confidence": int(max(50, min(95, 80 - diff_pct * 10))),
                        "entry_trigger": f"Break below neckline at {neckline:.4f}",
                        "invalidation": f"Price closes above {p2['price']:.4f}",
                        "breakout_confirm": current_price <= neckline,
                        "measured_move": round(p1["price"] - neckline, 4),
                        "is_forming": current_price >= p2["price"] * 0.97,
                    })
                    forming.append(patterns[-1])

        # Double Bottom
        if len(swing_lows) >= 4:
            recent_sl = swing_lows[-4:]
            if len(recent_sl) >= 2:
                p1, p2 = recent_sl[-2], recent_sl[-1]
                diff_pct = abs(p1["price"] - p2["price"]) / max(p1["price"], p2["price"]) * 100
                if diff_pct < 1.5 and p1["index"] != p2["index"]:
                    peak = max(highs[p1["index"]:p2["index"] + 1]) if p2["index"] > p1["index"] else 0
                    neckline = float(peak)
                    target = p1["price"] + (neckline - p1["price"])
                    patterns.append({
                        "name": "Double Bottom",
                        "type": "bullish",
                        "signal": "reversal_up",
                        "strength": "strong" if diff_pct < 0.5 else "moderate",
                        "left_bottom": round(p1["price"], 4),
                        "right_bottom": round(p2["price"], 4),
                        "neckline": round(neckline, 4),
                        "target": round(target, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": "long",
                        "confidence": int(max(50, min(95, 80 - diff_pct * 10))),
                        "entry_trigger": f"Break above neckline at {neckline:.4f}",
                        "invalidation": f"Price closes below {p2['price']:.4f}",
                        "breakout_confirm": current_price >= neckline,
                        "measured_move": round(neckline - p1["price"], 4),
                        "is_forming": current_price <= p2["price"] * 1.03,
                    })
                    forming.append(patterns[-1])

        # Flag detection (need a strong prior move + consolidation)
        if len(data) >= 30:
            move_start = max(len(data) - 30, 0)
            move_high = float(max(highs[-30:]))
            move_low = float(min(lows[-30:]))
            move_pct = (move_high - move_low) / move_low * 100
            recent_20_high = float(max(highs[-20:]))
            recent_20_low = float(min(lows[-20:]))
            recent_20_range = (recent_20_high - recent_20_low) / recent_20_low * 100

            if move_pct > 8 and recent_20_range < move_pct * 0.5:
                # Determine direction of prior move
                prior_dir = "up" if closes[-30] < closes[-1] else "down"

                # Consolidation slope
                if len(swing_highs) >= 3 and len(swing_lows) >= 3:
                    recent_sh = swing_highs[-3:]
                    recent_sl = swing_lows[-3:]
                    sh_line = fit_line(recent_sh)
                    sl_line = fit_line(recent_sl)

                    if sh_line and sl_line:
                        sh_slope = sh_line["slope"]
                        sl_slope = sl_line["slope"]

                        # Bullish flag: prior up, consolidation slopes down/parallel
                        if prior_dir == "up" and sh_slope <= 0 and sl_slope <= 0:
                            flag_height = move_high - move_low
                            target_price = current_price + flag_height
                            patterns.append({
                                "name": "Bullish Flag",
                                "type": "bullish",
                                "signal": "continuation_up",
                                "strength": "strong" if move_pct > 15 else "moderate",
                                "flag_pole_height": round(flag_height, 4),
                                "consolidation_low": round(recent_20_low, 4),
                                "consolidation_high": round(recent_20_high, 4),
                                "target": round(target_price, 4),
                                "current_price": round(current_price, 4),
                                "projected_direction": "long",
                                "confidence": int(max(60, min(90, 70 + move_pct / 5))),
                                "entry_trigger": "Break above consolidation high with volume",
                                "invalidation": f"Price breaks below {recent_20_low:.4f}",
                                "breakout_confirm": current_price > recent_20_high,
                                "measured_move": round(flag_height, 4),
                                "pole_move_percent": round(move_pct, 1),
                                "is_forming": current_price <= recent_20_high * 1.02,
                            })
                            if patterns[-1]["is_forming"]:
                                forming.append(patterns[-1])

                        # Bearish flag: prior down, consolidation slopes up/parallel
                        elif prior_dir == "down" and sh_slope >= 0 and sl_slope >= 0:
                            flag_height = move_high - move_low
                            target_price = current_price - flag_height
                            patterns.append({
                                "name": "Bearish Flag",
                                "type": "bearish",
                                "signal": "continuation_down",
                                "strength": "strong" if move_pct > 15 else "moderate",
                                "flag_pole_height": round(flag_height, 4),
                                "consolidation_low": round(recent_20_low, 4),
                                "consolidation_high": round(recent_20_high, 4),
                                "target": round(target_price, 4),
                                "current_price": round(current_price, 4),
                                "projected_direction": "short",
                                "confidence": int(max(60, min(90, 70 + move_pct / 5))),
                                "entry_trigger": "Break below consolidation low with volume",
                                "invalidation": f"Price breaks above {recent_20_high:.4f}",
                                "breakout_confirm": current_price < recent_20_low,
                                "measured_move": round(flag_height, 4),
                                "pole_move_percent": round(move_pct, 1),
                                "is_forming": current_price >= recent_20_low * 0.98,
                            })
                            if patterns[-1]["is_forming"]:
                                forming.append(patterns[-1])

        # Pennant (converging trendlines after a move)
        if len(swing_highs) >= 3 and len(swing_lows) >= 3:
            recent_sh = swing_highs[-3:]
            recent_sl = swing_lows[-3:]
            sh_line = fit_line(recent_sh)
            sl_line = fit_line(recent_sl)

            if sh_line and sl_line:
                sh_slope = sh_line["slope"]
                sl_slope = sl_line["slope"]

                # Converging: resistance slopes down, support slopes up
                if sh_slope < 0 and sl_slope > 0:
                    convergence_idx = abs(sh_slope - sl_slope)
                    if convergence_idx > 0.001:
                        if move_pct > 8 and prior_dir == "up":
                            target_price = current_price + (move_high - move_low)
                            patterns.append({
                                "name": "Bullish Pennant",
                                "type": "bullish",
                                "signal": "continuation_up",
                                "strength": "strong",
                                "target": round(target_price, 4),
                                "current_price": round(current_price, 4),
                                "projected_direction": "long",
                                "confidence": 75,
                                "entry_trigger": "Break above pennant resistance",
                                "invalidation": f"Price breaks below pennant support at {recent_20_low:.4f}",
                                "breakout_confirm": current_price > recent_20_high,
                                "measured_move": round(move_high - move_low, 4),
                                "is_forming": True,
                            })
                            forming.append(patterns[-1])
                        elif move_pct > 8 and prior_dir == "down":
                            target_price = current_price - (move_high - move_low)
                            patterns.append({
                                "name": "Bearish Pennant",
                                "type": "bearish",
                                "signal": "continuation_down",
                                "strength": "strong",
                                "target": round(target_price, 4),
                                "current_price": round(current_price, 4),
                                "projected_direction": "short",
                                "confidence": 75,
                                "entry_trigger": "Break below pennant support",
                                "invalidation": f"Price breaks above pennant resistance at {recent_20_high:.4f}",
                                "breakout_confirm": current_price < recent_20_low,
                                "measured_move": round(move_high - move_low, 4),
                                "is_forming": True,
                            })
                            forming.append(patterns[-1])

        # Triangle detection
        if len(swing_highs) >= 3 and len(swing_lows) >= 3:
            recent_sh = swing_highs[-3:]
            recent_sl = swing_lows[-3:]
            sh_line = fit_line(recent_sh)
            sl_line = fit_line(recent_sl)

            if sh_line and sl_line:
                sh_slope = sh_line["slope"]
                sl_slope = sl_line["slope"]

                # Ascending Triangle: flat resistance, rising support
                if abs(sh_slope) < 0.05 and sl_slope > 0.05:
                    apex_idx = max(recent_sh[-1]["index"], recent_sl[-1]["index"])
                    apex_price = line_value(sh_line, apex_idx)
                    base_price = recent_sl[0]["price"]
                    height = abs(apex_price - base_price)
                    target = apex_price + height if current_price < apex_price else current_price + height
                    patterns.append({
                        "name": "Ascending Triangle",
                        "type": "bullish",
                        "signal": "breakout_up",
                        "strength": "strong",
                        "resistance": round(apex_price, 4),
                        "support_trend": "rising",
                        "target": round(target, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": "long",
                        "confidence": 80,
                        "entry_trigger": f"Break above resistance at {apex_price:.4f}",
                        "invalidation": f"Price breaks below support at {recent_sl[0]['price']:.4f}",
                        "breakout_confirm": current_price > apex_price,
                        "measured_move": round(height, 4),
                        "is_forming": current_price < apex_price * 1.02,
                    })
                    if patterns[-1]["is_forming"]:
                        forming.append(patterns[-1])

                # Descending Triangle: flat support, falling resistance
                elif abs(sl_slope) < 0.05 and sh_slope < -0.05:
                    apex_idx = max(recent_sh[-1]["index"], recent_sl[-1]["index"])
                    apex_price = line_value(sl_line, apex_idx)
                    base_price = recent_sh[0]["price"]
                    height = abs(base_price - apex_price)
                    target = apex_price - height if current_price > apex_price else current_price - height
                    patterns.append({
                        "name": "Descending Triangle",
                        "type": "bearish",
                        "signal": "breakout_down",
                        "strength": "strong",
                        "support": round(apex_price, 4),
                        "resistance_trend": "falling",
                        "target": round(target, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": "short",
                        "confidence": 80,
                        "entry_trigger": f"Break below support at {apex_price:.4f}",
                        "invalidation": f"Price breaks above resistance at {recent_sh[0]['price']:.4f}",
                        "breakout_confirm": current_price < apex_price,
                        "measured_move": round(height, 4),
                        "is_forming": current_price > apex_price * 0.98,
                    })
                    if patterns[-1]["is_forming"]:
                        forming.append(patterns[-1])

                # Symmetrical Triangle: converging slopes
                elif sh_slope < -0.05 and sl_slope > 0.05:
                    apex_idx = max(recent_sh[-1]["index"], recent_sl[-1]["index"])
                    apex_price = (line_value(sh_line, apex_idx) + line_value(sl_line, apex_idx)) / 2
                    base_width = abs(recent_sh[0]["price"] - recent_sl[0]["price"])
                    target_up = apex_price + base_width
                    target_down = apex_price - base_width
                    patterns.append({
                        "name": "Symmetrical Triangle",
                        "type": "neutral",
                        "signal": "compression",
                        "strength": "moderate",
                        "apex_price": round(apex_price, 4),
                        "target_up": round(target_up, 4),
                        "target_down": round(target_down, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": "neutral",
                        "confidence": 60,
                        "entry_trigger_up": f"Break above resistance for long",
                        "entry_trigger_down": f"Break below support for short",
                        "invalidation": "Price reaches apex without breakout",
                        "breakout_confirm_up": current_price > recent_sh[-1]["price"],
                        "breakout_confirm_down": current_price < recent_sl[-1]["price"],
                        "measured_move": round(base_width, 4),
                        "is_forming": True,
                    })
                    forming.append(patterns[-1])

        # Wedge detection
        if len(swing_highs) >= 3 and len(swing_lows) >= 3:
            recent_sh = swing_highs[-3:]
            recent_sl = swing_lows[-3:]
            sh_line = fit_line(recent_sh)
            sl_line = fit_line(recent_sl)

            if sh_line and sl_line:
                sh_slope = sh_line["slope"]
                sl_slope = sl_line["slope"]

                # Rising Wedge: both slopes up, but resistance steeper (bearish)
                if sh_slope > 0.05 and sl_slope > 0.01 and sh_slope > sl_slope * 1.3:
                    base_price = recent_sl[0]["price"]
                    height = abs(recent_sh[-1]["price"] - recent_sl[-1]["price"])
                    target = current_price - height * 0.5
                    patterns.append({
                        "name": "Rising Wedge",
                        "type": "bearish",
                        "signal": "reversal_down",
                        "strength": "strong",
                        "target": round(target, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": "short",
                        "confidence": 75,
                        "entry_trigger": "Break below wedge support",
                        "invalidation": "Price breaks above wedge resistance",
                        "breakout_confirm": current_price < recent_sl[-1]["price"],
                        "measured_move": round(height, 4),
                        "is_forming": True,
                    })
                    forming.append(patterns[-1])

                # Falling Wedge: both slopes down, but resistance steeper (bullish)
                elif sh_slope < -0.01 and sl_slope < -0.05 and abs(sh_slope) > abs(sl_slope) * 1.3:
                    base_price = recent_sh[0]["price"]
                    height = abs(recent_sh[-1]["price"] - recent_sl[-1]["price"])
                    target = current_price + height * 0.5
                    patterns.append({
                        "name": "Falling Wedge",
                        "type": "bullish",
                        "signal": "reversal_up",
                        "strength": "strong",
                        "target": round(target, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": "long",
                        "confidence": 75,
                        "entry_trigger": "Break above wedge resistance",
                        "invalidation": "Price breaks below wedge support",
                        "breakout_confirm": current_price > recent_sh[-1]["price"],
                        "measured_move": round(height, 4),
                        "is_forming": True,
                    })
                    forming.append(patterns[-1])

        # Channel detection
        if len(swing_highs) >= 3 and len(swing_lows) >= 3:
            recent_sh = swing_highs[-3:]
            recent_sl = swing_lows[-3:]
            sh_line = fit_line(recent_sh)
            sl_line = fit_line(recent_sl)

            if sh_line and sl_line:
                sh_slope = sh_line["slope"]
                sl_slope = sl_line["slope"]

                slope_diff = abs(sh_slope - sl_slope)
                if slope_diff < 0.1 and abs(sh_slope) > 0.02:
                    channel_type = "Ascending Channel" if sh_slope > 0 and sl_slope > 0 else \
                                   "Descending Channel" if sh_slope < 0 and sl_slope < 0 else "Channel"
                    channel_direction = "bullish" if sh_slope > 0 else "bearish"
                    pred_dir = "long" if sh_slope > 0 else "short"

                    channel_height = abs(recent_sh[-1]["price"] - recent_sl[-1]["price"])
                    target = current_price + channel_height * (1 if sh_slope > 0 else -1)

                    next_resistance = line_value(sh_line, len(data) + 5)
                    next_support = line_value(sl_line, len(data) + 5)

                    patterns.append({
                        "name": channel_type,
                        "type": channel_direction,
                        "signal": "trend_continuation",
                        "strength": "strong" if slope_diff < 0.05 else "moderate",
                        "resistance_line_slope": round(sh_slope, 6),
                        "support_line_slope": round(sl_slope, 6),
                        "current_resistance": round(line_value(sh_line, len(data) - 1), 4),
                        "current_support": round(line_value(sl_line, len(data) - 1), 4),
                        "next_resistance": round(next_resistance, 4),
                        "next_support": round(next_support, 4),
                        "target": round(target, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": pred_dir,
                        "confidence": 70,
                        "entry_trigger": "Bounce from channel support" if pred_dir == "long" else "Bounce from channel resistance",
                        "invalidation": f"Break below channel at {next_support:.4f}" if pred_dir == "long" else f"Break above channel at {next_resistance:.4f}",
                        "breakout_confirm": current_price > next_resistance or current_price < next_support,
                        "measured_move": round(channel_height, 4),
                        "is_forming": True,
                    })
                    forming.append(patterns[-1])

        # Rectangle Consolidation
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            recent_sh = swing_highs[-2:]
            recent_sl = swing_lows[-2:]
            if len(recent_sh) >= 2 and len(recent_sl) >= 2:
                high_diff = abs(recent_sh[0]["price"] - recent_sh[1]["price"]) / max(recent_sh[0]["price"], recent_sh[1]["price"]) * 100
                low_diff = abs(recent_sl[0]["price"] - recent_sl[1]["price"]) / max(recent_sl[0]["price"], recent_sl[1]["price"]) * 100

                if high_diff < 2 and low_diff < 2:
                    resistance = max(recent_sh[0]["price"], recent_sh[1]["price"])
                    support = min(recent_sl[0]["price"], recent_sl[1]["price"])
                    range_height = resistance - support

                    # Determine likely breakout direction
                    volume_trend = np.mean(volumes[-5:]) > np.mean(volumes[-20:-5]) if len(volumes) >= 20 else False
                    pred_dir = "long" if current_price > (resistance + support) / 2 and volume_trend else \
                               "short" if current_price < (resistance + support) / 2 else "neutral"

                    patterns.append({
                        "name": "Rectangle Consolidation",
                        "type": "neutral",
                        "signal": "consolidation",
                        "strength": "strong",
                        "resistance": round(resistance, 4),
                        "support": round(support, 4),
                        "target_up": round(resistance + range_height, 4),
                        "target_down": round(support - range_height, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": pred_dir,
                        "confidence": 65,
                        "entry_trigger_up": f"Break above {resistance:.4f}",
                        "entry_trigger_down": f"Break below {support:.4f}",
                        "invalidation": "No directional bias in consolidation",
                        "breakout_confirm_up": current_price > resistance,
                        "breakout_confirm_down": current_price < support,
                        "measured_move": round(range_height, 4),
                        "is_forming": current_price > support * 0.98 and current_price < resistance * 1.02,
                    })
                    if patterns[-1]["is_forming"]:
                        forming.append(patterns[-1])

        # Head and Shoulders
        if len(swing_highs) >= 5:
            for i in range(len(swing_highs) - 4):
                shoulder_l = swing_highs[i]
                head = swing_highs[i + 1]
                shoulder_r = swing_highs[i + 2]

                head_pct = abs(head["price"] - shoulder_l["price"]) / shoulder_l["price"] * 100
                shoulder_diff = abs(shoulder_l["price"] - shoulder_r["price"]) / max(shoulder_l["price"], shoulder_r["price"]) * 100

                if head_pct > 3 and shoulder_diff < 3 and head["price"] > shoulder_l["price"] and head["price"] > shoulder_r["price"]:
                    # Find neckline
                    low_between = min(lows[shoulder_l["index"]:head["index"] + 1]) if head["index"] > shoulder_l["index"] else 0
                    low_after = min(lows[head["index"]:shoulder_r["index"] + 1]) if shoulder_r["index"] > head["index"] else 0

                    if low_between > 0 and low_after > 0:
                        neckline = min(low_between, low_after)
                        target = neckline - (head["price"] - neckline)
                        is_hs = True

                        patterns.append({
                            "name": "Head and Shoulders" if is_hs else "Inverse Head and Shoulders",
                            "type": "bearish" if is_hs else "bullish",
                            "signal": "reversal_down" if is_hs else "reversal_up",
                            "strength": "strong",
                            "left_shoulder": round(shoulder_l["price"], 4),
                            "head": round(head["price"], 4),
                            "right_shoulder": round(shoulder_r["price"], 4),
                            "neckline": round(neckline, 4),
                            "target": round(target, 4),
                            "current_price": round(current_price, 4),
                            "projected_direction": "short" if is_hs else "long",
                            "confidence": int(max(70, min(95, 85 - shoulder_diff * 2))),
                            "entry_trigger": f"Break below neckline at {neckline:.4f}" if is_hs else f"Break above neckline at {neckline:.4f}",
                            "invalidation": f"Price closes above {head['price']:.4f}" if is_hs else f"Price closes below {head['price']:.4f}",
                            "breakout_confirm": current_price <= neckline if is_hs else current_price >= neckline,
                            "measured_move": round(head["price"] - neckline, 4),
                            "is_forming": current_price > neckline * 0.98 if is_hs else current_price < neckline * 1.02,
                        })
                        if patterns[-1]["is_forming"]:
                            forming.append(patterns[-1])
                        break

        # Inverse Head and Shoulders
        if len(swing_lows) >= 5:
            for i in range(len(swing_lows) - 4):
                shoulder_l = swing_lows[i]
                head = swing_lows[i + 1]
                shoulder_r = swing_lows[i + 2]

                head_pct = abs(shoulder_l["price"] - head["price"]) / head["price"] * 100
                shoulder_diff = abs(shoulder_l["price"] - shoulder_r["price"]) / max(shoulder_l["price"], shoulder_r["price"]) * 100

                if head_pct > 3 and shoulder_diff < 3 and head["price"] < shoulder_l["price"] and head["price"] < shoulder_r["price"]:
                    high_between = max(highs[shoulder_l["index"]:head["index"] + 1]) if head["index"] > shoulder_l["index"] else 0
                    high_after = max(highs[head["index"]:shoulder_r["index"] + 1]) if shoulder_r["index"] > head["index"] else 0

                    if high_between > 0 and high_after > 0:
                        neckline = max(high_between, high_after)
                        target = neckline + (neckline - head["price"])

                        patterns.append({
                            "name": "Inverse Head and Shoulders",
                            "type": "bullish",
                            "signal": "reversal_up",
                            "strength": "strong",
                            "left_shoulder": round(shoulder_l["price"], 4),
                            "head": round(head["price"], 4),
                            "right_shoulder": round(shoulder_r["price"], 4),
                            "neckline": round(neckline, 4),
                            "target": round(target, 4),
                            "current_price": round(current_price, 4),
                            "projected_direction": "long",
                            "confidence": int(max(70, min(95, 85 - shoulder_diff * 2))),
                            "entry_trigger": f"Break above neckline at {neckline:.4f}",
                            "invalidation": f"Price closes below {head['price']:.4f}",
                            "breakout_confirm": current_price >= neckline,
                            "measured_move": round(neckline - head["price"], 4),
                            "is_forming": current_price < neckline * 1.02,
                        })
                        if patterns[-1]["is_forming"]:
                            forming.append(patterns[-1])
                        break

        # Triple Top
        if len(swing_highs) >= 6:
            for i in range(len(swing_highs) - 5):
                tops = swing_highs[i:i + 3]
                if len(tops) < 3:
                    continue
                p0, p1, p2 = tops
                d01 = abs(p0["price"] - p1["price"]) / max(p0["price"], p1["price"]) * 100
                d12 = abs(p1["price"] - p2["price"]) / max(p1["price"], p2["price"]) * 100
                if d01 < 2 and d12 < 2:
                    valley1 = min(lows[p0["index"]:p1["index"] + 1]) if p1["index"] > p0["index"] else 0
                    valley2 = min(lows[p1["index"]:p2["index"] + 1]) if p2["index"] > p1["index"] else 0
                    neckline = max(valley1, valley2)
                    target = max(p0["price"], p1["price"], p2["price"]) - (max(p0["price"], p1["price"], p2["price"]) - neckline) * 1.5
                    patterns.append({
                        "name": "Triple Top",
                        "type": "bearish",
                        "signal": "reversal_down",
                        "strength": "strong",
                        "tops": [round(p["price"], 4) for p in tops],
                        "neckline": round(neckline, 4),
                        "target": round(target, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": "short",
                        "confidence": 85,
                        "entry_trigger": f"Break below neckline at {neckline:.4f}",
                        "invalidation": f"Price closes above {max(p0['price'], p1['price'], p2['price']):.4f}",
                        "breakout_confirm": current_price <= neckline,
                        "measured_move": round(max(p0["price"], p1["price"], p2["price"]) - neckline, 4),
                        "is_forming": current_price >= neckline * 0.98,
                    })
                    if patterns[-1]["is_forming"]:
                        forming.append(patterns[-1])
                    break

        # Triple Bottom
        if len(swing_lows) >= 6:
            for i in range(len(swing_lows) - 5):
                bottoms = swing_lows[i:i + 3]
                if len(bottoms) < 3:
                    continue
                p0, p1, p2 = bottoms
                d01 = abs(p0["price"] - p1["price"]) / max(p0["price"], p1["price"]) * 100
                d12 = abs(p1["price"] - p2["price"]) / max(p1["price"], p2["price"]) * 100
                if d01 < 2 and d12 < 2:
                    peak1 = max(highs[p0["index"]:p1["index"] + 1]) if p1["index"] > p0["index"] else 0
                    peak2 = max(highs[p1["index"]:p2["index"] + 1]) if p2["index"] > p1["index"] else 0
                    neckline = min(peak1, peak2)
                    target = neckline + (neckline - min(p0["price"], p1["price"], p2["price"])) * 1.5
                    patterns.append({
                        "name": "Triple Bottom",
                        "type": "bullish",
                        "signal": "reversal_up",
                        "strength": "strong",
                        "bottoms": [round(p["price"], 4) for p in bottoms],
                        "neckline": round(neckline, 4),
                        "target": round(target, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": "long",
                        "confidence": 85,
                        "entry_trigger": f"Break above neckline at {neckline:.4f}",
                        "invalidation": f"Price closes below {min(p0['price'], p1['price'], p2['price']):.4f}",
                        "breakout_confirm": current_price >= neckline,
                        "measured_move": round(neckline - min(p0["price"], p1["price"], p2["price"]), 4),
                        "is_forming": current_price <= neckline * 1.02,
                    })
                    if patterns[-1]["is_forming"]:
                        forming.append(patterns[-1])
                    break

        # Diamond Top (broadening top with converging ends)
        if len(swing_highs) >= 4 and len(swing_lows) >= 4:
            recent_sh = swing_highs[-4:]
            recent_sl = swing_lows[-4:]
            sh_line = fit_line(recent_sh)
            sl_line = fit_line(recent_sl)
            if sh_line and sl_line and sh_line["slope"] < 0 and sl_line["slope"] > 0:
                sh_prices = [p["price"] for p in recent_sh]
                sl_prices = [p["price"] for p in recent_sl]
                if max(sh_prices) > max(sl_prices) and min(sh_prices) < min(sl_prices):
                    height = max(sh_prices) - min(sl_prices)
                    target = current_price - height * 0.5
                    patterns.append({
                        "name": "Diamond Top",
                        "type": "bearish",
                        "signal": "reversal_down",
                        "strength": "moderate",
                        "target": round(target, 4),
                        "current_price": round(current_price, 4),
                        "projected_direction": "short",
                        "confidence": 65,
                        "entry_trigger": "Break below diamond support",
                        "invalidation": "Price closes above diamond resistance",
                        "breakout_confirm": current_price < recent_sl[-1]["price"],
                        "measured_move": round(height, 4),
                        "is_forming": True,
                    })
                    forming.append(patterns[-1])

        # Broadening Formation (expanding range)
        if len(swing_highs) >= 3 and len(swing_lows) >= 3:
            recent_sh = swing_highs[-3:]
            recent_sl = swing_lows[-3:]
            sh_line = fit_line(recent_sh)
            sl_line = fit_line(recent_sl)
            if sh_line and sl_line and sh_line["slope"] > 0.03 and sl_line["slope"] < -0.03:
                height = recent_sh[-1]["price"] - recent_sl[-1]["price"]
                patterns.append({
                    "name": "Broadening Formation",
                    "type": "neutral",
                    "signal": "volatility_expansion",
                    "strength": "moderate",
                    "current_price": round(current_price, 4),
                    "projected_direction": "neutral",
                    "confidence": 50,
                    "entry_trigger": "Wait for range breakout",
                    "invalidation": "Range contraction",
                    "breakout_confirm": False,
                    "measured_move": round(height, 4),
                    "is_forming": True,
                })
                forming.append(patterns[-1])

        # ABCD Pattern (harmonic leg)
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            for i in range(min(len(swing_highs), len(swing_lows)) - 1):
                if i + 1 >= len(swing_highs) or i + 1 >= len(swing_lows):
                    break
                x = swing_lows[i] if swing_lows[i]["index"] < swing_highs[i]["index"] else swing_highs[i]
                a = swing_highs[i] if x == swing_lows[i] else swing_lows[i]
                b = swing_lows[i + 1] if a["type"] == "up" else swing_highs[i + 1]
                if i + 2 < len(swing_highs) and i + 2 < len(swing_lows):
                    c = swing_highs[i + 2] if b["type"] == "up" else swing_lows[i + 2]
                    leg_ab = abs(a["price"] - b["price"])
                    leg_bc = abs(b["price"] - c["price"])
                    if leg_ab > 0 and leg_bc / leg_ab > 0.382 and leg_bc / leg_ab < 0.886:
                        if c["price"] > a["price"]:
                            target = c["price"] + leg_ab
                            direction = "long"
                        else:
                            target = c["price"] - leg_ab
                            direction = "short"
                        patterns.append({
                            "name": "ABCD Pattern",
                            "type": "bullish" if direction == "long" else "bearish",
                            "signal": "harmonic_completion",
                            "strength": "moderate",
                            "point_a": round(a["price"], 4),
                            "point_b": round(b["price"], 4),
                            "point_c": round(c["price"], 4),
                            "target": round(target, 4),
                            "current_price": round(current_price, 4),
                            "projected_direction": direction,
                            "confidence": 70,
                            "entry_trigger": f"Entry at {c['price']:.4f} with AB=CD completion",
                            "invalidation": f"Price breaks beyond {b['price']:.4f}",
                            "breakout_confirm": current_price > c["price"] if direction == "long" else current_price < c["price"],
                            "measured_move": round(leg_ab, 4),
                            "is_forming": True,
                        })
                        forming.append(patterns[-1])
                        break

        # Wolfe Wave
        if len(swing_highs) >= 4 and len(swing_lows) >= 4:
            for i in range(min(len(swing_highs), len(swing_lows)) - 3):
                w = []
                for j in range(4):
                    if i + j % 2 == 0:
                        w.append(swing_lows[i + j] if len(swing_lows) > i + j else None)
                    else:
                        w.append(swing_highs[i + j] if len(swing_highs) > i + j else None)
                w = [x for x in w if x is not None]
                if len(w) >= 4:
                    p0, p1, p2, p3 = w[0], w[1], w[2], w[3]
                    line_1_3 = fit_line([p0, p2]) if p0 and p2 else None
                    line_2_4 = fit_line([p1, p3]) if p1 and p3 else None
                    if line_1_3 and line_2_4:
                        slope1, slope2 = line_1_3["slope"], line_2_4["slope"]
                        if slope1 > 0 and slope2 > 0 and slope2 > slope1:
                            target = p3["price"] + (p2["price"] - p1["price"])
                            patterns.append({
                                "name": "Wolfe Wave",
                                "type": "bullish",
                                "signal": "wave_completion",
                                "strength": "moderate",
                                "target": round(target, 4),
                                "current_price": round(current_price, 4),
                                "projected_direction": "long",
                                "confidence": 70,
                                "entry_trigger": "Wave 4 completion entry",
                                "invalidation": "Price breaks below wave 1",
                                "breakout_confirm": current_price > p3["price"],
                                "measured_move": round(abs(p2["price"] - p1["price"]), 4),
                                "is_forming": True,
                            })
                            forming.append(patterns[-1])
                        elif slope1 < 0 and slope2 < 0 and slope2 < slope1:
                            target = p3["price"] - (p1["price"] - p2["price"])
                            patterns.append({
                                "name": "Wolfe Wave",
                                "type": "bearish",
                                "signal": "wave_completion",
                                "strength": "moderate",
                                "target": round(target, 4),
                                "current_price": round(current_price, 4),
                                "projected_direction": "short",
                                "confidence": 70,
                                "entry_trigger": "Wave 4 completion entry",
                                "invalidation": "Price breaks above wave 1",
                                "breakout_confirm": current_price < p3["price"],
                                "measured_move": round(abs(p1["price"] - p2["price"]), 4),
                                "is_forming": True,
                            })
                            forming.append(patterns[-1])

        return _convert_numpy({
            "patterns": patterns,
            "forming_patterns": forming,
            "count": len(patterns),
            "forming_count": len(forming),
            "current_price": round(current_price, 4),
        })

    def calculate_projection(self, pattern: dict) -> dict:
        if not pattern:
            return {}
        direction = pattern.get("projected_direction", "neutral")
        current_price = pattern.get("current_price", 0)
        target = pattern.get("target", 0)
        invalidation = pattern.get("invalidation", "")
        measured_move = pattern.get("measured_move", 0)

        entry = current_price
        sl = invalidation
        try:
            sl_price = float(invalidation.split("at ")[-1]) if "at " in invalidation else 0
        except (ValueError, IndexError):
            sl_price = 0

        if direction == "long":
            tp1 = entry + measured_move * 0.382
            tp2 = entry + measured_move * 0.618
            tp3 = entry + measured_move * 1.0
        elif direction == "short":
            tp1 = entry - measured_move * 0.382
            tp2 = entry - measured_move * 0.618
            tp3 = entry - measured_move * 1.0
        else:
            return {}

        risk = abs(entry - sl_price) if sl_price > 0 else measured_move * 0.1
        rr1 = abs(tp1 - entry) / risk if risk > 0 else 0
        rr2 = abs(tp2 - entry) / risk if risk > 0 else 0
        rr3 = abs(tp3 - entry) / risk if risk > 0 else 0

        return _convert_numpy({
            "direction": direction,
            "entry_zone": {
                "min": round(entry * 0.998, 4),
                "max": round(entry * 1.002, 4),
                "mid": round(entry, 4),
            },
            "stop_loss": round(sl_price if sl_price > 0 else entry * (0.97 if direction == "long" else 1.03), 4),
            "take_profit_1": round(tp1, 4),
            "take_profit_2": round(tp2, 4),
            "take_profit_3": round(tp3, 4),
            "risk_reward_1": round(rr1, 2),
            "risk_reward_2": round(rr2, 2),
            "risk_reward_3": round(rr3, 2),
            "target": round(target, 4),
            "measured_move": round(measured_move, 4),
            "expected_path": [
                {"level": "Entry", "price": round(entry, 4)},
                {"level": "TP1", "price": round(tp1, 4)},
                {"level": "TP2", "price": round(tp2, 4)},
                {"level": "TP3", "price": round(tp3, 4)},
                {"level": "Target", "price": round(target, 4)},
            ],
            "alternate_scenario": {
                "direction": "short" if direction == "long" else "long",
                "trigger": "Breakout failure and reversal",
            },
        })


chart_pattern_engine = ChartPatternEngine()
