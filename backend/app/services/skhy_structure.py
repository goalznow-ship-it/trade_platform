import numpy as np
from typing import List, Tuple, Optional
from app.core.logging import logger

class SkhyStructureEngine:
    def analyze(self, data: list) -> dict:
        if len(data) < 20:
            return {"error": "Insufficient data", "structures": [], "market_structure": {}}

        closes = [d["close"] for d in data]
        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]
        opens = [d["open"] for d in data]
        volumes = [d["volume"] for d in data]

        swings = self._find_swing_points(highs, lows)
        structure = self._market_structure(swings)
        bos = self._detect_bos(swings, highs, lows)
        choch = self._detect_choch(swings, highs, lows)
        fvg = self._detect_fvg(data)
        inv_fvg = self._detect_inverse_fvg(data)
        order_blocks = self._detect_order_blocks(data)
        breaker_blocks = self._detect_breaker_blocks(data)
        mitigation_blocks = self._detect_mitigation_blocks(order_blocks)
        liquidity = self._detect_liquidity(highs, lows, swings)
        eq_highs, eq_lows = self._detect_equal_highs_lows(highs, lows)
        premium_discount = self._premium_discount_zones(highs, lows, closes)
        inducement = self._detect_inducement(data)

        return {
            "swing_highs": [{"price": s["price"], "index": s["index"], "strength": s.get("strength", 1)} for s in swings if s["type"] == "high"],
            "swing_lows": [{"price": s["price"], "index": s["index"], "strength": s.get("strength", 1)} for s in swings if s["type"] == "low"],
            "market_structure": structure,
            "break_of_structure": bos,
            "change_of_character": choch,
            "fair_value_gaps": fvg,
            "inverse_fair_value_gaps": inv_fvg,
            "order_blocks": order_blocks,
            "breaker_blocks": breaker_blocks,
            "mitigation_blocks": mitigation_blocks,
            "liquidity": liquidity,
            "equal_highs": eq_highs,
            "equal_lows": eq_lows,
            "premium_discount": premium_discount,
            "inducement": inducement,
            "all_structures": self._collect_all(swings, bos, choch, fvg, inv_fvg, order_blocks, breaker_blocks, mitigation_blocks, liquidity, eq_highs, eq_lows, inducement),
        }

    def _find_swing_points(self, highs: list, lows: list, left: int = 5, right: int = 5) -> list:
        swings = []
        for i in range(left, len(highs) - right):
            is_high = all(highs[i] >= highs[i - j] for j in range(1, left + 1)) and all(highs[i] >= highs[i + j] for j in range(1, right + 1))
            is_low = all(lows[i] <= lows[i - j] for j in range(1, left + 1)) and all(lows[i] <= lows[i + j] for j in range(1, right + 1))
            if is_high:
                strength = min(3, sum(1 for j in range(1, left + 1) if highs[i] > highs[i - j] * 1.01) + sum(1 for j in range(1, right + 1) if highs[i] > highs[i + j] * 1.01))
                swings.append({"type": "high", "price": highs[i], "index": i, "strength": strength})
            if is_low:
                strength = min(3, sum(1 for j in range(1, left + 1) if lows[i] < lows[i - j] * 0.99) + sum(1 for j in range(1, right + 1) if lows[i] < lows[i + j] * 0.99))
                swings.append({"type": "low", "price": lows[i], "index": i, "strength": strength})
        return swings

    def _market_structure(self, swings: list) -> dict:
        if len(swings) < 4:
            return {"trend": "undefined", "hh_hl": False, "lh_ll": False}
        recent = swings[-6:]
        highs = [s for s in recent if s["type"] == "high"]
        lows = [s for s in recent if s["type"] == "low"]

        hh = len(highs) >= 2 and highs[-1]["price"] > highs[-2]["price"]
        hl = len(lows) >= 2 and lows[-1]["price"] > lows[-2]["price"]
        lh = len(highs) >= 2 and highs[-1]["price"] < highs[-2]["price"]
        ll = len(lows) >= 2 and lows[-1]["price"] < lows[-2]["price"]

        trend = "bullish" if hh and hl else "bearish" if lh and ll else "ranging" if (hh and ll) or (lh and hl) else "undefined"
        return {"trend": trend, "hh": bool(hh), "hl": bool(hl), "lh": bool(lh), "ll": bool(ll)}

    def _detect_bos(self, swings: list, highs: list, lows: list) -> list:
        bos_list = []
        if len(swings) < 3:
            return bos_list
        for i in range(2, len(swings)):
            s0, s1, s2 = swings[i - 2], swings[i - 1], swings[i]
            if s0["type"] == "low" and s1["type"] == "high" and s2["type"] == "low":
                if s2["price"] < s0["price"]:
                    bos_list.append({"type": "bearish_bos", "break_price": s0["price"], "index": s2["index"], "strength": s0.get("strength", 1)})
            elif s0["type"] == "high" and s1["type"] == "low" and s2["type"] == "high":
                if s2["price"] > s0["price"]:
                    bos_list.append({"type": "bullish_bos", "break_price": s0["price"], "index": s2["index"], "strength": s0.get("strength", 1)})
        return bos_list

    def _detect_choch(self, swings: list, highs: list, lows: list) -> list:
        choch_list = []
        if len(swings) < 4:
            return choch_list
        for i in range(3, len(swings)):
            s0, s1, s2, s3 = swings[i - 3], swings[i - 2], swings[i - 1], swings[i]
            if s0["type"] == "high" and s1["type"] == "low" and s2["type"] == "high" and s3["type"] == "low":
                if s2["price"] > s0["price"] and s3["price"] > s1["price"]:
                    choch_list.append({"type": "bullish_choch", "index": s3["index"], "strength": 2})
            elif s0["type"] == "low" and s1["type"] == "high" and s2["type"] == "low" and s3["type"] == "high":
                if s2["price"] < s0["price"] and s3["price"] < s1["price"]:
                    choch_list.append({"type": "bearish_choch", "index": s3["index"], "strength": 2})
        return choch_list

    def _detect_fvg(self, data: list) -> list:
        fvg_list = []
        for i in range(2, len(data)):
            if data[i]["low"] > data[i - 2]["high"]:
                fvg_list.append({
                    "type": "bullish_fvg",
                    "gap_high": data[i]["low"],
                    "gap_low": data[i - 2]["high"],
                    "index": i,
                    "strength": min(3, int((data[i]["low"] - data[i - 2]["high"]) / (data[i]["high"] - data[i]["low"]) * 3)) if data[i]["high"] != data[i]["low"] else 1,
                })
            elif data[i]["high"] < data[i - 2]["low"]:
                fvg_list.append({
                    "type": "bearish_fvg",
                    "gap_high": data[i - 2]["low"],
                    "gap_low": data[i]["high"],
                    "index": i,
                    "strength": min(3, int((data[i - 2]["low"] - data[i]["high"]) / (data[i]["high"] - data[i]["low"]) * 3)) if data[i]["high"] != data[i]["low"] else 1,
                })
        return fvg_list

    def _detect_inverse_fvg(self, data: list) -> list:
        inv_fvg_list = []
        for i in range(2, len(data)):
            if data[i - 1]["high"] < data[i - 2]["low"] and data[i]["close"] > data[i - 2]["low"]:
                inv_fvg_list.append({"type": "bullish_ifvg", "index": i, "strength": 1})
            elif data[i - 1]["low"] > data[i - 2]["high"] and data[i]["close"] < data[i - 2]["high"]:
                inv_fvg_list.append({"type": "bearish_ifvg", "index": i, "strength": 1})
        return inv_fvg_list

    def _detect_order_blocks(self, data: list) -> list:
        obs = []
        for i in range(3, len(data) - 1):
            if data[i]["close"] < data[i]["open"] and data[i + 1]["close"] > data[i]["open"]:
                obs.append({
                    "type": "bullish_ob",
                    "price_high": data[i]["open"],
                    "price_low": data[i]["close"],
                    "index": i,
                    "strength": min(3, int(data[i]["volume"] / np.mean([d["volume"] for d in data[max(0, i - 10):i + 1]]) * 2)) if i > 0 else 1,
                    "volume": data[i]["volume"],
                })
            elif data[i]["close"] > data[i]["open"] and data[i + 1]["close"] < data[i]["open"]:
                obs.append({
                    "type": "bearish_ob",
                    "price_high": data[i]["close"],
                    "price_low": data[i]["open"],
                    "index": i,
                    "strength": min(3, int(data[i]["volume"] / np.mean([d["volume"] for d in data[max(0, i - 10):i + 1]]) * 2)) if i > 0 else 1,
                    "volume": data[i]["volume"],
                })
        return obs

    def _detect_breaker_blocks(self, data: list) -> list:
        return [ob for ob in self._detect_order_blocks(data) if ob["strength"] >= 2][-5:]

    def _detect_mitigation_blocks(self, order_blocks: list) -> list:
        return [{"type": f"mitigation_{ob['type']}", "price": (ob["price_high"] + ob["price_low"]) / 2, "strength": ob["strength"]} for ob in order_blocks[-3:]]

    def _detect_liquidity(self, highs: list, lows: list, swings: list) -> dict:
        eq_highs = self._find_eq_levels(highs)
        eq_lows = self._find_eq_levels(lows)
        recent_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
        recent_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)

        liquidity_above = []
        for i, eh in enumerate(eq_highs):
            liquidity_above.append({"price": eh, "type": "equal_highs", "strength": min(3, eq_highs.count(eh))})
        liquidity_above.append({"price": max(highs[-50:]) if len(highs) >= 50 else max(highs), "type": "swing_high", "strength": 2})

        liquidity_below = []
        for el in eq_lows:
            liquidity_below.append({"price": el, "type": "equal_lows", "strength": min(3, eq_lows.count(el))})
        liquidity_below.append({"price": min(lows[-50:]) if len(lows) >= 50 else min(lows), "type": "swing_low", "strength": 2})

        return {
            "above": [l for l in liquidity_above if l["price"] > highs[-1]],
            "below": [l for l in liquidity_below if l["price"] < lows[-1]],
            "nearest_above": min([l for l in liquidity_above if l["price"] > highs[-1]], key=lambda x: x["price"] - highs[-1]) if any(l["price"] > highs[-1] for l in liquidity_above) else None,
            "nearest_below": max([l for l in liquidity_below if l["price"] < lows[-1]], key=lambda x: x["price"]) if any(l["price"] < lows[-1] for l in liquidity_below) else None,
        }

    def _find_eq_levels(self, values: list, tolerance: float = 0.002) -> list:
        levels = []
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                if abs(values[j] - values[i]) / values[i] < tolerance:
                    levels.append(round((values[i] + values[j]) / 2, 2))
        return levels

    def _detect_equal_highs_lows(self, highs: list, lows: list) -> Tuple[list, list]:
        return self._find_eq_levels(highs), self._find_eq_levels(lows)

    def _premium_discount_zones(self, highs: list, lows: list, closes: list) -> dict:
        if not highs or not lows:
            return {}
        period_high = max(highs[-50:]) if len(highs) >= 50 else max(highs)
        period_low = min(lows[-50:]) if len(lows) >= 50 else min(lows)
        midpoint = (period_high + period_low) / 2
        current = closes[-1] if closes else 0
        zone = "premium" if current > midpoint else "discount"
        ratio = (current - period_low) / (period_high - period_low) * 100 if period_high != period_low else 50
        return {
            "high": period_high,
            "low": period_low,
            "midpoint": midpoint,
            "current_zone": zone,
            "current_ratio": round(ratio, 1),
            "equilibrium": midpoint,
        }

    def _detect_inducement(self, data: list) -> list:
        inducements = []
        for i in range(3, len(data) - 1):
            body1 = abs(data[i - 1]["close"] - data[i - 1]["open"])
            body2 = abs(data[i]["close"] - data[i]["open"])
            if body1 > 0 and body2 / body1 > 1.5:
                if data[i]["close"] > data[i]["open"] and data[i - 1]["close"] < data[i - 1]["open"]:
                    inducements.append({"type": "bullish_inducement", "index": i, "strength": 2})
                elif data[i]["close"] < data[i]["open"] and data[i - 1]["close"] > data[i - 1]["open"]:
                    inducements.append({"type": "bearish_inducement", "index": i, "strength": 2})
        return inducements

    def _collect_all(self, swings, bos, choch, fvg, inv_fvg, obs, breakers, mitigation, liquidity, eq_highs, eq_lows, inducement) -> list:
        all_s = []
        for s in swings:
            all_s.append({"type": s["type"], "price": s["price"], "index": s["index"], "strength": s.get("strength", 1), "category": "swing", "status": "active"})
        for b in bos:
            all_s.append({"type": b["type"], "price": b["break_price"], "index": b["index"], "strength": b.get("strength", 1), "category": "bos", "status": "active"})
        for c in choch:
            all_s.append({"type": c["type"], "index": c["index"], "strength": c.get("strength", 1), "category": "choch", "status": "active"})
        for f in fvg:
            all_s.append({"type": f["type"], "gap_high": f["gap_high"], "gap_low": f["gap_low"], "index": f["index"], "strength": f.get("strength", 1), "category": "fvg", "status": "active"})
        for ob in obs:
            all_s.append({"type": ob["type"], "price": (ob["price_high"] + ob["price_low"]) / 2, "high": ob["price_high"], "low": ob["price_low"], "index": ob["index"], "strength": ob.get("strength", 1), "category": "order_block", "status": "active"})
        return all_s

skhy_structure = SkhyStructureEngine()
