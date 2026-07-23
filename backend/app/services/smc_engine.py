"""
Complete SMC/ICT Engine

Smart Money Concepts implementation:
- Market Structure (BOS, CHoCH)
- Liquidity Sweep / Liquidity Pools
- Order Blocks, Breaker Blocks, Mitigation Blocks
- Fair Value Gaps
- Premium / Discount Zones
- Equal Highs / Lows
- Displacement / Inducement
- Internal / External Structure
- Session Range
"""
import numpy as np
from typing import Optional


class SMCEngine:
    def analyze(self, data: list) -> dict:
        if len(data) < 30:
            return {"error": "insufficient_data"}

        highs = np.array([d["high"] for d in data])
        lows = np.array([d["low"] for d in data])
        closes = np.array([d["close"] for d in data])
        opens = np.array([d["open"] for d in data])
        current_price = closes[-1]

        structure = self._market_structure(highs, lows, closes)
        bos_events = self._break_of_structure(highs, lows, closes)
        choch_events = self._change_of_character(highs, lows, closes, opens)
        fvg = self._fair_value_gaps(highs, lows)
        order_blocks = self._order_blocks(opens, closes, highs, lows)
        breaker_blocks = self._breaker_blocks(opens, closes, highs, lows)
        mitigation_blocks = self._mitigation_blocks(opens, closes, highs, lows)
        liquidity_pools = self._liquidity_pools(highs, lows, closes)
        liquidity_sweep = self._liquidity_sweep(highs, lows, closes)
        premium_discount = self._premium_discount_zones(highs, lows, closes)
        equal_highs_lows = self._equal_highs_lows(highs, lows, closes)
        displacement = self._displacement(data)
        inducement = self._inducement(highs, lows, closes, opens)
        internal_structure = self._internal_structure(highs, lows, closes)
        external_structure = self._external_structure(highs, lows, closes, opens)
        session_range = self._session_range(highs, lows, closes)

        net_bos = sum(1 for b in bos_events if b["type"] == "bullish_bos") - sum(1 for b in bos_events if b["type"] == "bearish_bos")
        net_choch = sum(1 for c in choch_events if c["type"] == "bullish_choch") - sum(1 for c in choch_events if c["type"] == "bearish_choch")

        return {
            "structure": structure,
            "trend": structure["trend"],
            "bos_events": bos_events[-8:],
            "choch_events": choch_events[-5:],
            "bos_count": len(bos_events),
            "choch_count": len(choch_events),
            "net_bos": net_bos,
            "net_choch": net_choch,
            "fair_value_gaps": fvg[-8:],
            "order_blocks": order_blocks[-5:],
            "breaker_blocks": breaker_blocks[-5:],
            "mitigation_blocks": mitigation_blocks[-5:],
            "liquidity_pools": liquidity_pools[-5:],
            "liquidity_sweep": liquidity_sweep,
            "premium_discount": premium_discount,
            "equal_highs": equal_highs_lows["equal_highs"][-3:],
            "equal_lows": equal_highs_lows["equal_lows"][-3:],
            "displacement": displacement,
            "inducement": inducement,
            "internal_structure": internal_structure,
            "external_structure": external_structure,
            "session_range": session_range,
            "current_price": current_price,
        }

    def _market_structure(self, highs, lows, closes) -> dict:
        recent_highs = highs[-25:]
        recent_lows = lows[-25:]

        hh = recent_highs[-1] > max(recent_highs[:-1]) if len(recent_highs) > 1 else False
        ll = recent_lows[-1] < min(recent_lows[:-1]) if len(recent_lows) > 1 else False
        lh = recent_highs[-1] < max(recent_highs[:-1]) if len(recent_highs) > 1 else False
        hl = recent_lows[-1] > min(recent_lows[:-1]) if len(recent_lows) > 1 else False

        if hh and hl:
            trend = "uptrend"
        elif ll and lh:
            trend = "downtrend"
        elif hh and ll:
            trend = "expansion"
        elif lh and hl:
            trend = "contraction"
        else:
            trend = "ranging"

        return {
            "trend": trend,
            "higher_high": bool(hh),
            "lower_low": bool(ll),
            "lower_high": bool(lh),
            "higher_low": bool(hl),
            "structure_type": "bullish" if trend in ("uptrend", "expansion") else "bearish" if trend in ("downtrend", "contraction") else "neutral",
        }

    def _break_of_structure(self, highs, lows, closes) -> list:
        events = []
        for i in range(8, len(highs) - 1):
            prev_highs = highs[max(0, i - 8):i]
            prev_lows = lows[max(0, i - 8):i]
            if prev_highs.size > 0 and highs[i] > max(prev_highs) and closes[i] > closes[i - 1]:
                events.append({"index": i, "type": "bullish_bos", "price": float(highs[i])})
            if prev_lows.size > 0 and lows[i] < min(prev_lows) and closes[i] < closes[i - 1]:
                events.append({"index": i, "type": "bearish_bos", "price": float(lows[i])})
        return events

    def _change_of_character(self, highs, lows, closes, opens) -> list:
        events = []
        for i in range(12, len(highs) - 1):
            prev_highs = highs[i - 8:i]
            prev_lows = lows[i - 8:i]
            if prev_highs.size > 0 and prev_lows.size > 0:
                if highs[i] > max(prev_highs) and closes[i] < opens[i] and closes[i] < closes[i - 1]:
                    events.append({"index": i, "type": "bearish_choch", "price": float(highs[i])})
                if lows[i] < min(prev_lows) and closes[i] > opens[i] and closes[i] > closes[i - 1]:
                    events.append({"index": i, "type": "bullish_choch", "price": float(lows[i])})
        return events

    def _fair_value_gaps(self, highs, lows) -> list:
        gaps = []
        for i in range(2, len(highs)):
            if lows[i] > highs[i - 2]:
                gaps.append({
                    "type": "bullish_fvg",
                    "low": float(highs[i - 2]),
                    "high": float(lows[i]),
                    "gap_size": float(lows[i] - highs[i - 2]),
                    "mitigated": False,
                })
            if highs[i] < lows[i - 2]:
                gaps.append({
                    "type": "bearish_fvg",
                    "low": float(highs[i]),
                    "high": float(lows[i - 2]),
                    "gap_size": float(lows[i - 2] - highs[i]),
                    "mitigated": False,
                })

        for gap in gaps:
            gap_low, gap_high = (gap["low"], gap["high"]) if gap["type"] == "bullish_fvg" else (gap["high"], gap["low"])
            for j in range(1, min(20, len(highs))):
                idx = -j
                if gap_low <= highs[idx] <= gap_high or gap_low <= lows[idx] <= gap_high:
                    gap["mitigated"] = True
                    break

        return gaps

    def _order_blocks(self, opens, closes, highs, lows) -> list:
        blocks = []
        for i in range(10, len(opens) - 1):
            if closes[i] > opens[i] and closes[i - 1] < opens[i - 1]:
                bull_low = float(min(opens[i], closes[i - 1]))
                bull_high = float(max(opens[i], closes[i - 1]))
                blocks.append({
                    "type": "bullish",
                    "price_low": bull_low,
                    "price_high": bull_high,
                    "strength": "strong" if (closes[i] - opens[i]) > (closes[i - 1] - opens[i - 1]) * 1.5 else "moderate",
                    "time_index": i,
                })
            if closes[i] < opens[i] and closes[i - 1] > opens[i - 1]:
                bear_low = float(min(closes[i], opens[i - 1]))
                bear_high = float(max(closes[i], opens[i - 1]))
                blocks.append({
                    "type": "bearish",
                    "price_low": bear_low,
                    "price_high": bear_high,
                    "strength": "strong" if (opens[i] - closes[i]) > (opens[i - 1] - closes[i - 1]) * 1.5 else "moderate",
                    "time_index": i,
                })
        return blocks

    def _breaker_blocks(self, opens, closes, highs, lows) -> list:
        blocks = []
        order_blocks = self._order_blocks(opens, closes, highs, lows)

        for ob in order_blocks:
            for i in range(ob.get("time_index", 0) + 1, min(ob.get("time_index", 0) + 20, len(closes))):
                if ob["type"] == "bullish":
                    if lows[i] < ob["price_low"] and closes[i] > ob["price_low"]:
                        blocks.append({
                            "type": "bullish_breaker",
                            "price_low": ob["price_low"],
                            "price_high": ob["price_high"],
                            "strength": "strong",
                        })
                        break
                elif ob["type"] == "bearish":
                    if highs[i] > ob["price_high"] and closes[i] < ob["price_high"]:
                        blocks.append({
                            "type": "bearish_breaker",
                            "price_low": ob["price_low"],
                            "price_high": ob["price_high"],
                            "strength": "strong",
                        })
                        break
        return blocks

    def _mitigation_blocks(self, opens, closes, highs, lows) -> list:
        blocks = []
        fvg_entries = self._fair_value_gaps(highs, lows)
        for fvg in fvg_entries[-10:]:
            if fvg["mitigated"]:
                for i in range(2, min(15, len(closes))):
                    if fvg["type"] == "bullish_fvg" and closes[-i] > fvg["high"]:
                        blocks.append({
                            "type": "bullish_mitigation",
                            "zone_low": fvg["low"],
                            "zone_high": fvg["high"],
                        })
                        break
                    elif fvg["type"] == "bearish_fvg" and closes[-i] < fvg["low"]:
                        blocks.append({
                            "type": "bearish_mitigation",
                            "zone_low": fvg["low"],
                            "zone_high": fvg["high"],
                        })
                        break
        return blocks

    def _liquidity_pools(self, highs, lows, closes) -> list:
        pools = []
        for i in range(15, len(highs) - 1):
            chunk_highs = highs[i - 10:i + 5]
            chunk_lows = lows[i - 10:i + 5]
            if chunk_highs.size > 0:
                local_high = float(max(chunk_highs))
                local_low = float(min(chunk_lows))
                if highs[i] == local_high and highs[i] > highs[i - 1] and closes[i] < local_high:
                    pools.append({"type": "sell_side", "price": local_high,
                                  "strength": "strong" if highs[i] > max(highs[max(0, i - 15):i + 10]) else "moderate"})
                if lows[i] == local_low and lows[i] < lows[i - 1] and closes[i] > local_low:
                    pools.append({"type": "buy_side", "price": local_low,
                                  "strength": "strong" if lows[i] < min(lows[max(0, i - 15):i + 10]) else "moderate"})
        return pools

    def _liquidity_sweep(self, highs, lows, closes) -> Optional[dict]:
        if len(highs) < 20:
            return None

        recent_high = max(highs[-15:-1]) if len(highs) > 15 else 0
        recent_low = min(lows[-15:-1]) if len(lows) > 15 else 0

        if closes[-1] and recent_high and len(closes) > 2:
            if highs[-1] > recent_high * 1.001 and closes[-1] < closes[-2]:
                return {"type": "sell_side_sweep", "swept_level": float(recent_high), "current_price": float(closes[-1])}
            if lows[-1] < recent_low * 0.999 and closes[-1] > closes[-2]:
                return {"type": "buy_side_sweep", "swept_level": float(recent_low), "current_price": float(closes[-1])}

        return None

    def _premium_discount_zones(self, highs, lows, closes) -> dict:
        if len(highs) < 20:
            return {"zone": "unknown", "position": 0.5}

        swing_high = max(highs[-30:])
        swing_low = min(lows[-30:])
        range_val = swing_high - swing_low if swing_high > swing_low else 1

        fair_value_low = swing_low + range_val * 0.25
        fair_value_high = swing_high - range_val * 0.25
        current = float(closes[-1])

        if current >= swing_high:
            zone = "premium_high"
        elif current >= fair_value_high:
            zone = "premium"
        elif current >= fair_value_low:
            zone = "fair_value"
        elif current >= swing_low:
            zone = "discount"
        else:
            zone = "deep_discount"

        position = (current - swing_low) / range_val if range_val > 0 else 0.5

        return {
            "zone": zone,
            "swing_high": float(swing_high),
            "swing_low": float(swing_low),
            "fair_value_low": float(fair_value_low),
            "fair_value_high": float(fair_value_high),
            "current_position": round(float(position), 2),
            "in_discount": position < 0.25,
            "in_premium": position > 0.75,
        }

    def _equal_highs_lows(self, highs, lows, closes) -> dict:
        equal_highs = []
        equal_lows = []
        tolerance = 0.001

        for i in range(5, len(highs) - 1):
            for j in range(max(0, i - 20), i):
                if abs(highs[i] / highs[j] - 1) < tolerance and highs[i] > highs[i - 1] and closes[i] < highs[i]:
                    equal_highs.append({"index": i, "price": float(highs[i]),
                                        "type": "rejection" if closes[i] < highs[i] else "breakout"})
                if abs(lows[i] / lows[j] - 1) < tolerance and lows[i] < lows[i - 1] and closes[i] > lows[i]:
                    equal_lows.append({"index": i, "price": float(lows[i]),
                                       "type": "rejection" if closes[i] > lows[i] else "breakout"})

        return {"equal_highs": equal_highs[-5:], "equal_lows": equal_lows[-5:]}

    def _displacement(self, data: list) -> Optional[dict]:
        if len(data) < 10:
            return None

        closes = [d["close"] for d in data]
        volumes = [d["volume"] for d in data]

        for i in range(1, min(10, len(data))):
            move_pct = abs(closes[-i] / closes[-(i + 1)] - 1) * 100
            avg_vol = np.mean(volumes[-(i + 10):-(i + 1)]) if len(volumes) > i + 10 else 0
            current_vol = volumes[-i] if i <= len(volumes) else 0

            if move_pct > 2 and current_vol > avg_vol * 1.5:
                return {
                    "detected": True,
                    "direction": "up" if closes[-i] > closes[-(i + 1)] else "down",
                    "move_percent": round(move_pct, 2),
                    "volume_ratio": round(current_vol / avg_vol, 2) if avg_vol > 0 else 0,
                    "index": -i,
                }

        return {"detected": False}

    def _inducement(self, highs, lows, closes, opens) -> Optional[dict]:
        if len(highs) < 20:
            return None

        for i in range(-5, -1):
            if i + 1 >= len(highs):
                continue
            if highs[i] > highs[i + 1] and lows[i] > lows[i + 1] and closes[i] < opens[i]:
                return {
                    "type": "bearish_inducement",
                    "high": float(highs[i]),
                    "low": float(lows[i]),
                    "index": i,
                }
            if highs[i] < highs[i + 1] and lows[i] < lows[i + 1] and closes[i] > opens[i]:
                return {
                    "type": "bullish_inducement",
                    "high": float(highs[i]),
                    "low": float(lows[i]),
                    "index": i,
                }

        return None

    def _internal_structure(self, highs, lows, closes) -> dict:
        if len(highs) < 10:
            return {"type": "unknown"}

        short_highs = highs[-6:]
        short_lows = lows[-6:]
        mid_highs = highs[-15:-6] if len(highs) >= 15 else highs[:max(1, len(highs) - 6)]
        mid_lows = lows[-15:-6] if len(lows) >= 15 else lows[:max(1, len(lows) - 6)]

        short_bullish = len(short_highs) > 0 and len(short_lows) > 0 and short_highs[-1] > max(short_highs[:-1]) and short_lows[-1] > min(short_lows[:-1]) if len(short_highs) > 1 else False
        short_bearish = len(short_highs) > 0 and len(short_lows) > 0 and short_highs[-1] < max(short_highs[:-1]) and short_lows[-1] < min(short_lows[:-1]) if len(short_highs) > 1 else False
        mid_bullish = len(mid_highs) > 0 and len(mid_lows) > 0 and mid_highs[-1] > max(mid_highs[:-1]) and mid_lows[-1] > min(mid_lows[:-1]) if len(mid_highs) > 1 else False
        mid_bearish = len(mid_highs) > 0 and len(mid_lows) > 0 and mid_highs[-1] < max(mid_highs[:-1]) and mid_lows[-1] < min(mid_lows[:-1]) if len(mid_highs) > 1 else False

        if short_bullish and mid_bullish:
            return {"type": "bullish_aligned", "short_term": "bullish", "mid_term": "bullish"}
        elif short_bearish and mid_bearish:
            return {"type": "bearish_aligned", "short_term": "bearish", "mid_term": "bearish"}
        elif short_bullish and mid_bearish:
            return {"type": "potential_reversal", "short_term": "bullish", "mid_term": "bearish"}
        elif short_bearish and mid_bullish:
            return {"type": "pullback", "short_term": "bearish", "mid_term": "bullish"}
        return {"type": "mixed", "short_term": "neutral", "mid_term": "neutral"}

    def _external_structure(self, highs, lows, closes, opens) -> dict:
        if len(highs) < 30:
            return {"type": "unknown"}

        major_highs = highs[-30:]
        major_lows = lows[-30:]

        hh = major_highs[-1] > max(major_highs[:-1]) if len(major_highs) > 1 else False
        ll = major_lows[-1] < min(major_lows[:-1]) if len(major_lows) > 1 else False
        lh = major_highs[-1] < max(major_highs[:-1]) if len(major_highs) > 1 else False
        hl = major_lows[-1] > min(major_lows[:-1]) if len(major_lows) > 1 else False

        if hh and hl:
            return {"type": "bullish_macro", "structure": "uptrend", "continuation": True}
        elif ll and lh:
            return {"type": "bearish_macro", "structure": "downtrend", "continuation": True}
        elif hh and ll:
            return {"type": "expansion", "structure": "volatile", "continuation": False}
        elif lh and hl:
            return {"type": "contraction", "structure": "consolidation", "continuation": True}
        return {"type": "neutral", "structure": "ranging", "continuation": False}

    def _session_range(self, highs, lows, closes) -> dict:
        if len(highs) < 5:
            return {"error": "insufficient_data"}

        session_high = float(max(highs[-5:]))
        session_low = float(min(lows[-5:]))
        session_range_pct = (session_high - session_low) / session_low * 100 if session_low > 0 else 0
        current = float(closes[-1])
        position = (current - session_low) / (session_high - session_low) if session_high > session_low else 0.5

        return {
            "high": session_high,
            "low": session_low,
            "range_percent": round(session_range_pct, 2),
            "current_position": round(position, 2),
            "position_label": "premium" if position > 0.75 else "discount" if position < 0.25 else "middle",
        }


smc_engine = SMCEngine()
