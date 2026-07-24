import asyncio
import numpy as np
from datetime import datetime, timezone
from app.services.skhy_market_data import skhy_market_data
from app.services.skhy_indicators import skhy_indicators
from app.services.skhy_structure import skhy_structure
from app.core.logging import logger

TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

class SkhyAnalysisEngine:
    async def get_full_analysis(self) -> dict:
        ohlcv_tasks = {tf: skhy_market_data.get_ohlcv(tf, 200) for tf in TIMEFRAMES}
        ohlcv_results = await asyncio.gather(*ohlcv_tasks.values())
        ohlcv_data = dict(zip(ohlcv_tasks.keys(), ohlcv_results))

        snapshot = await skhy_market_data.get_snapshot()

        tf_analysis = {}
        for tf in TIMEFRAMES:
            data = ohlcv_data.get(tf, [])
            if len(data) < 30:
                tf_analysis[tf] = {"error": f"Insufficient data ({len(data)} candles)", "signal": "WAIT"}
                continue
            indicators = skhy_indicators.analyze(data)
            structure = skhy_structure.analyze(data)
            tf_result = self._analyze_timeframe(data, indicators, structure, tf)
            tf_analysis[tf] = tf_result

        alignment = self._compute_alignment(tf_analysis)
        scores = self._compute_scores(tf_analysis, alignment, snapshot)
        triggers = self._compute_triggers(tf_analysis, alignment, scores, snapshot)
        patterns = self._detect_patterns(ohlcv_data)
        support_resistance = self._compute_support_resistance(ohlcv_data, snapshot)

        return {
            "symbol": "SKHYUSDT",
            "exchange": "Binance Futures",
            "market": "USDT Perpetual",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "snapshot": snapshot,
            "timeframes": tf_analysis,
            "alignment": alignment,
            "scores": scores,
            "triggers": triggers,
            "patterns": patterns,
            "support_resistance": support_resistance,
            "explanation_az": self._generate_explanation(tf_analysis, alignment, scores, triggers),
        }

    def _analyze_timeframe(self, data: list, indicators: dict, structure: dict, tf: str) -> dict:
        if not data:
            return {"error": "No data", "signal": "WAIT"}
        close = data[-1]["close"] if data else 0
        interp = indicators.get("interpretation", {})

        trend = interp.get("trend", {})
        momentum = interp.get("momentum", {})
        volume_info = interp.get("volume", {})
        overall = interp.get("overall", "neutral")

        bullish_score = 0
        bearish_score = 0

        if trend.get("bias") == "bullish":
            bullish_score += 25
        elif trend.get("bias") == "bearish":
            bearish_score += 25
        if momentum.get("rsi") in ("bullish", "oversold"):
            bullish_score += 15
        elif momentum.get("rsi") in ("bearish", "overbought"):
            bearish_score += 15
        if momentum.get("macd") == "bullish":
            bullish_score += 10
        elif momentum.get("macd") == "bearish":
            bearish_score += 10
        if volume_info.get("cmf") == "bullish":
            bullish_score += 10
        elif volume_info.get("cmf") == "bearish":
            bearish_score += 10
        if trend.get("supertrend") == "up":
            bullish_score += 15
        elif trend.get("supertrend") == "down":
            bearish_score += 15

        ms = structure.get("market_structure", {})
        if ms.get("trend") == "bullish":
            bullish_score += 15
        elif ms.get("trend") == "bearish":
            bearish_score += 15

        total = bullish_score + bearish_score
        bullish_pct = round(bullish_score / total * 100) if total > 0 else 50
        bearish_pct = round(bearish_score / total * 100) if total > 0 else 50

        support = self._find_support(data)
        resistance = self._find_resistance(data)

        signal = "STRONG_LONG" if bullish_pct >= 75 else "LONG" if bullish_pct >= 60 else "STRONG_SHORT" if bearish_pct >= 75 else "SHORT" if bearish_pct >= 60 else "WAIT"

        volatility = round(np.std([d["close"] for d in data[-20:]]) / np.mean([d["close"] for d in data[-20:]]), 4) if len(data) >= 20 else 0

        momentum_val = momentum.get("rsi", "neutral")
        volume_val = volume_info.get("relative_volume", "normal")

        bos = structure.get("break_of_structure", [])
        choch = structure.get("change_of_character", [])

        return {
            "signal": signal,
            "trend": overall,
            "market_structure": ms.get("trend", "undefined"),
            "bullish_score": bullish_pct,
            "bearish_score": bearish_pct,
            "momentum": momentum_val,
            "volume": volume_val,
            "volatility": volatility,
            "support": support,
            "resistance": resistance,
            "bos": len(bos),
            "bos_details": bos[-3:] if bos else [],
            "choch": len(choch),
            "choch_details": choch[-3:] if choch else [],
            "liquidity": structure.get("liquidity", {}),
            "pattern": self._detect_tf_pattern(data, tf),
            "close": close,
        }

    def _find_support(self, data: list) -> float:
        if len(data) < 20:
            return min(d["low"] for d in data) if data else 0
        lows = [d["low"] for d in data[-50:]]
        return sorted(set(round(l, 2) for l in lows))[0] if sorted(set(round(l, 2) for l in lows)) else min(lows)

    def _find_resistance(self, data: list) -> float:
        if len(data) < 20:
            return max(d["high"] for d in data) if data else 0
        highs = [d["high"] for d in data[-50:]]
        return sorted(set(round(h, 2) for h in highs))[-1] if sorted(set(round(h, 2) for h in highs)) else max(highs)

    def _detect_tf_pattern(self, data: list, tf: str) -> dict:
        if len(data) < 30:
            return {"name": "none", "status": "insufficient_data"}
        closes = [d["close"] for d in data[-30:]]
        highs = [d["high"] for d in data[-30:]]
        lows = [d["low"] for d in data[-30:]]
        mid = len(closes) // 2
        first_half = np.mean(closes[:mid])
        second_half = np.mean(closes[mid:])
        if second_half > first_half * 1.03 and max(highs[-5:]) > max(highs[-10:-5]):
            return {"name": "ascending", "status": "forming"}
        if second_half < first_half * 0.97 and min(lows[-5:]) < min(lows[-10:-5]):
            return {"name": "descending", "status": "forming"}
        return {"name": "ranging", "status": "neutral"}

    def _compute_alignment(self, tf_analysis: dict) -> dict:
        signals = [v.get("signal", "WAIT") for v in tf_analysis.values() if "signal" in v]
        if not signals:
            return {"confidence": 0, "status": "NO_DATA"}

        long_count = sum(1 for s in signals if s in ("LONG", "STRONG_LONG"))
        short_count = sum(1 for s in signals if s in ("SHORT", "STRONG_SHORT"))
        wait_count = sum(1 for s in signals if s == "WAIT")
        total = len(signals)

        h4 = tf_analysis.get("4h", {}).get("signal", "WAIT")
        h1 = tf_analysis.get("1h", {}).get("signal", "WAIT")
        h4_h1_aligned = (h4 in ("LONG", "STRONG_LONG") and h1 in ("LONG", "STRONG_LONG")) or \
                         (h4 in ("SHORT", "STRONG_SHORT") and h1 in ("SHORT", "STRONG_SHORT"))
        d1 = tf_analysis.get("1d", {}).get("signal", "WAIT")
        conflicts = []

        if h4 not in ("LONG", "STRONG_LONG", "SHORT", "STRONG_SHORT", "WAIT"):
            conflicts.append("4H trend unclear")
        if h4 in ("LONG", "STRONG_LONG") and h1 in ("SHORT", "STRONG_SHORT"):
            conflicts.append("4H bullish but 1H bearish")
        if h4 in ("SHORT", "STRONG_SHORT") and h1 in ("LONG", "STRONG_LONG"):
            conflicts.append("4H bearish but 1H bullish")
        if d1 == "WAIT" and h4 != "WAIT":
            conflicts.append("Daily trend neutral")

        primary_direction = "long" if long_count > short_count else "short" if short_count > long_count else "neutral"
        confidence = round((max(long_count, short_count) / total) * 100) if total > 0 else 0

        return {
            "primary_direction": primary_direction,
            "confidence": min(confidence, 100),
            "long_timeframes": long_count,
            "short_timeframes": short_count,
            "wait_timeframes": wait_count,
            "total_timeframes": total,
            "h4_h1_aligned": h4_h1_aligned,
            "d1_filter": d1,
            "conflicts": conflicts,
            "status": "ALIGNED" if confidence >= 60 and h4_h1_aligned and not conflicts else "CONFLICTING" if conflicts else "LOW_CONFIDENCE",
        }

    def _compute_scores(self, tf_analysis: dict, alignment: dict, snapshot: dict) -> dict:
        tf_count = sum(1 for v in tf_analysis.values() if "signal" in v)
        if tf_count == 0:
            return {"overall": 0, "status": "NO_DATA"}

        trend_score = 0
        structure_score = 0
        momentum_score = 0
        volume_score = 0
        liquidity_score = 0
        pattern_score = 0
        futures_score = 0
        orderflow_score = 0
        multitimeframe_score = alignment["confidence"]
        risk_score = 50

        for tf, v in tf_analysis.items():
            if "trend" not in v:
                continue
            if v.get("trend") == "bullish":
                trend_score += 12
            elif v.get("trend") == "bearish":
                trend_score += 12
            else:
                trend_score += 5
            if v.get("market_structure") == "bullish":
                structure_score += 12
            elif v.get("market_structure") == "bearish":
                structure_score += 12
            else:
                structure_score += 5
            mom = v.get("momentum", "neutral")
            if mom in ("bullish", "oversold"):
                momentum_score += 10
            elif mom in ("bearish", "overbought"):
                momentum_score += 10
            else:
                momentum_score += 5
            vol = v.get("volume", "normal")
            if vol in ("high", "above_average"):
                volume_score += 12
            else:
                volume_score += 5
            liq = v.get("liquidity", {})
            if liq.get("nearest_above") or liq.get("nearest_below"):
                liquidity_score += 10
            else:
                liquidity_score += 5
            if v.get("bos", 0) > 0 or v.get("choch", 0) > 0:
                pattern_score += 10
            else:
                pattern_score += 5

        tf_count = max(tf_count, 1)
        trend_score = min(trend_score // tf_count, 100)
        structure_score = min(structure_score // tf_count, 100)
        momentum_score = min(momentum_score // tf_count, 100)
        volume_score = min(volume_score // tf_count, 100)
        liquidity_score = min(liquidity_score // tf_count, 100)
        pattern_score = min(pattern_score // tf_count, 100)

        funding = snapshot.get("funding", {})
        if funding:
            fr = funding.get("funding_rate", 0)
            if fr is not None:
                if abs(fr) < 0.0001:
                    futures_score = 50
                elif fr > 0:
                    futures_score = 60
                else:
                    futures_score = 40

        oi = snapshot.get("open_interest", {})
        oi_val = oi.get("open_interest")
        if oi_val:
            futures_score = min(futures_score + 10, 100)

        ls = snapshot.get("long_short_ratio", {})
        lsr = ls.get("long_short_ratio", 1)
        if lsr > 1.5:
            orderflow_score += 30
        elif lsr < 0.7:
            orderflow_score += 30
        else:
            orderflow_score += 15
        taker = snapshot.get("taker_buy_sell_ratio", {})
        if taker.get("buy_sell_ratio", 1) > 1.2:
            orderflow_score += 20
            futures_score += 10
        elif taker.get("buy_sell_ratio", 0) < 0.8:
            orderflow_score += 20
            futures_score += 10
        else:
            orderflow_score += 10

        risk_score = risk_score - (10 if alignment.get("conflicts") else 0) + (10 if alignment.get("h4_h1_aligned") else 0)

        overall = round((trend_score * 0.15 + structure_score * 0.12 + momentum_score * 0.12 +
                         volume_score * 0.10 + liquidity_score * 0.10 + pattern_score * 0.08 +
                         futures_score * 0.10 + orderflow_score * 0.08 + multitimeframe_score * 0.10 +
                         risk_score * 0.05))

        status = "STRONG_TRADE_READY" if overall >= 80 else "TRADE_READY" if overall >= 70 else "WATCHLIST" if overall >= 50 else "WAIT"

        long_prob = round(trend_score * 0.3 + momentum_score * 0.2 + volume_score * 0.1 + (100 - structure_score) * 0.1 + multitimeframe_score * 0.3)
        short_prob = 100 - long_prob

        return {
            "trend_score": trend_score,
            "structure_score": structure_score,
            "momentum_score": momentum_score,
            "volume_score": volume_score,
            "liquidity_score": liquidity_score,
            "pattern_score": pattern_score,
            "futures_score": futures_score,
            "orderflow_score": orderflow_score,
            "multitimeframe_score": multitimeframe_score,
            "risk_score": risk_score,
            "overall": overall,
            "status": status,
            "long_probability": min(max(long_prob, 0), 100),
            "short_probability": min(max(short_prob, 0), 100),
            "signal_confidence": overall,
        }

    def _compute_triggers(self, tf_analysis: dict, alignment: dict, scores: dict, snapshot: dict) -> dict:
        h4 = tf_analysis.get("4h", {})
        h1 = tf_analysis.get("1h", {})
        m15 = tf_analysis.get("15m", {})
        d1 = tf_analysis.get("1d", {})

        close_4h = h4.get("close", 0)
        close_1h = h1.get("close", 0)
        res_1h = h1.get("resistance", 0)
        sup_1h = h1.get("support", 0)
        res_4h = h4.get("resistance", 0)
        sup_4h = h4.get("support", 0)

        h4_trend = h4.get("trend", "neutral")
        h1_trend = h1.get("trend", "neutral")
        h4_structure = h4.get("market_structure", "undefined")
        h1_structure = h1.get("market_structure", "undefined")

        long_trigger_price = round(res_1h * 1.005, 2) if res_1h else round(close_1h * 1.02, 2)
        short_trigger_price = round(sup_1h * 0.995, 2) if sup_1h else round(close_1h * 0.98, 2)

        long_conditions = []
        short_conditions = []

        if h4_trend in ("bullish", "neutral"):
            long_conditions.append("4H structure supports longs")
        else:
            long_conditions.append("4H trend bearish - WAIT for reversal confirmation")

        if h1_trend in ("bullish", "neutral"):
            long_conditions.append("1H momentum favors longs")
        else:
            long_conditions.append("1H bearish - need flip")

        if res_1h:
            long_conditions.append(f"1H candle close above ${long_trigger_price}")
        long_conditions.append("Volume 1.5x above average on breakout candle")
        long_conditions.append("OI increases on breakout")
        taker = snapshot.get("taker_buy_sell_ratio", {})
        if taker.get("buy_sell_ratio", 1) < 1.0:
            long_conditions.append("Taker buy ratio strengthens above 1.0")

        if h4_trend in ("bearish", "neutral"):
            short_conditions.append("4H structure supports shorts")
        else:
            short_conditions.append("4H trend bullish - WAIT for reversal")

        if h1_trend in ("bearish", "neutral"):
            short_conditions.append("1H momentum favors shorts")
        else:
            short_conditions.append("1H bullish - need flip")

        if sup_1h:
            short_conditions.append(f"1H candle close below ${short_trigger_price}")
        short_conditions.append("Volume 1.5x above average on breakdown candle")
        short_conditions.append("OI increases on breakdown")
        if taker.get("buy_sell_ratio", 1) > 1.0:
            short_conditions.append("Taker sell ratio strengthens above 1.0")

        bullish_invalidation = round(close_1h * 0.98, 2) if close_1h else 0
        bearish_invalidation = round(close_1h * 1.02, 2) if close_1h else 0

        if h4_trend == "bullish":
            bullish_invalidation = round(h4.get("support", close_4h * 0.95), 2)
            bearish_invalidation = round(h4.get("resistance", close_4h * 1.05), 2)

        return {
            "long_trigger_price": long_trigger_price,
            "long_trigger_conditions": long_conditions,
            "short_trigger_price": short_trigger_price,
            "short_trigger_conditions": short_conditions,
            "bullish_invalidation": bullish_invalidation,
            "bearish_invalidation": bearish_invalidation,
            "entry_ready": scores["overall"] >= 70 and alignment["h4_h1_aligned"],
        }

    def _detect_patterns(self, ohlcv_data: dict) -> list:
        patterns = []
        for tf in TIMEFRAMES:
            data = ohlcv_data.get(tf, [])
            if len(data) < 50:
                continue
            closes = [d["close"] for d in data]
            highs = [d["high"] for d in data]
            lows = [d["low"] for d in data]
            volumes = [d["volume"] for d in data]
            recent = data[-30:]

            p = self._check_bull_flag(recent, tf)
            if p:
                patterns.append(p)
            p = self._check_bear_flag(recent, tf)
            if p:
                patterns.append(p)
            p = self._check_double_top(recent, tf)
            if p:
                patterns.append(p)
            p = self._check_double_bottom(recent, tf)
            if p:
                patterns.append(p)
            p = self._check_triangle(recent, tf)
            if p:
                patterns.append(p)
            p = self._check_abcd(recent, tf)
            if p:
                patterns.append(p)
            p = self._check_rectangle(recent, tf)
            if p:
                patterns.append(p)
            p = self._check_wedge(recent, tf)
            if p:
                patterns.append(p)
            p = self._check_head_shoulders(recent, tf)
            if p:
                patterns.append(p)
        return patterns

    def _check_bull_flag(self, data: list, tf: str) -> dict:
        if len(data) < 15:
            return None
        pole = data[:8]
        flag = data[8:]
        pole_rise = pole[-1]["close"] - pole[0]["close"]
        if pole_rise > 0 and pole_rise / pole[0]["close"] > 0.03:
            flag_highs = [d["high"] for d in flag]
            flag_lows = [d["low"] for d in flag]
            if max(flag_highs) - min(flag_lows) < (max(d["high"] for d in pole) - min(d["low"] for d in pole)) * 0.5:
                return {
                    "name": "Bull Flag", "timeframe": tf, "status": "DETECTED",
                    "completion": 70, "breakout_level": max(flag_highs),
                    "breakdown_level": min(flag_lows), "measured_target": round(flag[-1]["close"] + pole_rise, 2),
                    "invalidation": min(flag_lows), "probability": 60, "reliability": "medium",
                }
        return None

    def _check_bear_flag(self, data: list, tf: str) -> dict:
        if len(data) < 15:
            return None
        pole = data[:8]
        flag = data[8:]
        pole_drop = pole[0]["close"] - pole[-1]["close"]
        if pole_drop > 0 and pole_drop / pole[0]["close"] > 0.03:
            flag_highs = [d["high"] for d in flag]
            flag_lows = [d["low"] for d in flag]
            if max(flag_highs) - min(flag_lows) < (max(d["high"] for d in pole) - min(d["low"] for d in pole)) * 0.5:
                return {
                    "name": "Bear Flag", "timeframe": tf, "status": "DETECTED",
                    "completion": 70, "breakout_level": min(flag_lows),
                    "breakdown_level": max(flag_highs), "measured_target": round(flag[-1]["close"] - pole_drop, 2),
                    "invalidation": max(flag_highs), "probability": 60, "reliability": "medium",
                }
        return None

    def _check_double_top(self, data: list, tf: str) -> dict:
        if len(data) < 20:
            return None
        highs = [d["high"] for d in data]
        mid = len(highs) // 2
        left_high = max(highs[:mid])
        right_high = max(highs[mid:])
        if abs(left_high - right_high) / left_high < 0.015:
            neckline = min(d["low"] for d in data)
            return {
                "name": "Double Top", "timeframe": tf, "status": "DETECTED",
                "completion": 50, "breakdown_level": neckline,
                "measured_target": round(neckline - (left_high - neckline), 2),
                "invalidation": max(left_high, right_high) * 1.01, "probability": 55, "reliability": "medium",
            }
        return None

    def _check_double_bottom(self, data: list, tf: str) -> dict:
        if len(data) < 20:
            return None
        lows_list = [d["low"] for d in data]
        mid = len(lows_list) // 2
        left_low = min(lows_list[:mid])
        right_low = min(lows_list[mid:])
        if abs(left_low - right_low) / left_low < 0.015:
            neckline = max(d["high"] for d in data)
            return {
                "name": "Double Bottom", "timeframe": tf, "status": "DETECTED",
                "completion": 50, "breakout_level": neckline,
                "measured_target": round(neckline + (neckline - left_low), 2),
                "invalidation": min(left_low, right_low) * 0.99, "probability": 55, "reliability": "medium",
            }
        return None

    def _check_triangle(self, data: list, tf: str) -> dict:
        if len(data) < 15:
            return None
        highs = [d["high"] for d in data[-15:]]
        lows = [d["low"] for d in data[-15:]]
        h_slope = (highs[-1] - highs[0]) / len(highs)
        l_slope = (lows[-1] - lows[0]) / len(lows)
        if abs(h_slope) < 0.001 and l_slope > 0:
            return {"name": "Ascending Triangle", "timeframe": tf, "status": "FORMING",
                    "breakout_level": max(highs), "probability": 50, "reliability": "medium",
                    "measured_target": round(max(highs) + (max(highs) - min(lows)), 2), "invalidation": min(lows) * 0.99}
        if h_slope < 0 and abs(l_slope) < 0.001:
            return {"name": "Descending Triangle", "timeframe": tf, "status": "FORMING",
                    "breakdown_level": min(lows), "probability": 50, "reliability": "medium",
                    "measured_target": round(min(lows) - (max(highs) - min(lows)), 2), "invalidation": max(highs) * 1.01}
        if h_slope < 0 and l_slope > 0:
            return {"name": "Symmetrical Triangle", "timeframe": tf, "status": "FORMING",
                    "probability": 45, "reliability": "medium",
                    "invalidation": max(highs) if abs(max(highs) - data[-1]["close"]) < abs(min(lows) - data[-1]["close"]) else min(lows)}
        return None

    def _check_abcd(self, data: list, tf: str) -> dict:
        if len(data) < 20:
            return None
        closes = [d["close"] for d in data[-20:]]
        if len(closes) < 10:
            return None
        a, b, c, d_val = closes[0], closes[5], closes[10], closes[-1]
        ab_move = abs(b - a)
        bc_move = abs(c - b)
        if ab_move > 0 and bc_move / ab_move > 0.6 and bc_move / ab_move < 0.9:
            target = d_val + (ab_move - bc_move) * (1 if b > a else -1)
            return {"name": "ABCD Pattern", "timeframe": tf, "status": "FORMING",
                    "completion": 80, "measured_target": round(target, 2), "probability": 50, "reliability": "low"}
        return None

    def _check_rectangle(self, data: list, tf: str) -> dict:
        if len(data) < 15:
            return None
        highs = [d["high"] for d in data[-15:]]
        lows = [d["low"] for d in data[-15:]]
        top = max(highs)
        bottom = min(lows)
        h_range = max(highs) - min(highs)
        l_range = max(lows) - min(lows)
        if abs(top - np.mean(highs[-5:])) / top < 0.01 and abs(bottom - np.mean(lows[-5:])) / bottom < 0.01:
            return {"name": "Rectangle", "timeframe": tf, "status": "FORMING",
                    "breakout_level": top, "breakdown_level": bottom,
                    "measured_target": round(top + (top - bottom), 2), "probability": 45, "reliability": "low"}
        return None

    def _check_wedge(self, data: list, tf: str) -> dict:
        if len(data) < 15:
            return None
        highs = [d["high"] for d in data[-15:]]
        lows = [d["low"] for d in data[-15:]]
        h_slope = (highs[-1] - highs[0]) / len(highs) if len(highs) > 1 else 0
        l_slope = (lows[-1] - lows[0]) / len(lows) if len(lows) > 1 else 0
        if h_slope < 0 and l_slope < 0 and h_slope > l_slope:
            return {"name": "Falling Wedge", "timeframe": tf, "status": "FORMING",
                    "breakout_level": max(highs), "probability": 50, "reliability": "medium",
                    "measured_target": round(max(highs) + (max(highs) - min(lows)) * 0.5, 2), "invalidation": min(lows) * 0.99}
        if h_slope > 0 and l_slope > 0 and h_slope > l_slope:
            return {"name": "Rising Wedge", "timeframe": tf, "status": "FORMING",
                    "breakdown_level": min(lows), "probability": 50, "reliability": "medium",
                    "measured_target": round(min(lows) - (max(highs) - min(lows)) * 0.5, 2), "invalidation": max(highs) * 1.01}
        return None

    def _check_head_shoulders(self, data: list, tf: str) -> dict:
        if len(data) < 20:
            return None
        highs = [d["high"] for d in data[-20:]]
        mid = len(highs) // 2
        left_shoulder = max(highs[:mid // 2]) if highs[:mid // 2] else 0
        head = max(highs[mid // 2:mid + mid // 2]) if highs[mid // 2:mid + mid // 2] else 0
        right_shoulder = max(highs[mid + mid // 2:]) if highs[mid + mid // 2:] else 0
        if head > left_shoulder and head > right_shoulder and abs(left_shoulder - right_shoulder) / head < 0.05:
            neckline = min(d["low"] for d in data[-20:])
            return {"name": "Head and Shoulders", "timeframe": tf, "status": "DETECTED",
                    "breakdown_level": neckline, "probability": 55, "reliability": "medium",
                    "measured_target": round(neckline - (head - neckline), 2), "invalidation": head * 1.01}
        if left_shoulder > 0 and head > 0 and right_shoulder > 0:
            inv_left = min(d["low"] for d in data[-20:])
            if left_shoulder < head and right_shoulder < head and abs(left_shoulder - right_shoulder) / head < 0.05:
                neckline = max(d["high"] for d in data[-20:])
                return {"name": "Inverse Head and Shoulders", "timeframe": tf, "status": "DETECTED",
                        "breakout_level": neckline, "probability": 55, "reliability": "medium",
                        "measured_target": round(neckline + (neckline - inv_left), 2), "invalidation": min(highs) * 0.99}
        return None

    def _compute_support_resistance(self, ohlcv_data: dict, snapshot: dict) -> dict:
        all_lows = []
        all_highs = []
        for tf, data in ohlcv_data.items():
            if len(data) < 20:
                continue
            all_lows.extend([d["low"] for d in data[-50:]])
            all_highs.extend([d["high"] for d in data[-50:]])

        if not all_lows or not all_highs:
            return {"error": "Insufficient data"}

        price = snapshot.get("ticker", {}).get("price", 0) or all_highs[-1] if all_highs else 0

        nearest_support = max([l for l in all_lows if l < price], default=min(all_lows)) if all_lows else 0
        strongest_support = min(all_lows) if all_lows else 0
        nearest_resistance = min([h for h in all_highs if h > price], default=max(all_highs)) if all_highs else 0
        strongest_resistance = max(all_highs) if all_highs else 0

        return {
            "nearest_support": round(nearest_support, 2),
            "strongest_support": round(strongest_support, 2),
            "nearest_resistance": round(nearest_resistance, 2),
            "strongest_resistance": round(strongest_resistance, 2),
            "distance_to_support": round(price - nearest_support, 2) if price else 0,
            "distance_to_resistance": round(nearest_resistance - price, 2) if price else 0,
            "liquidity_above": [{"price": round(h, 2), "strength": 2} for h in sorted(set(round(h, 1) for h in all_highs[-10:]), reverse=True)[:5]],
            "liquidity_below": [{"price": round(l, 2), "strength": 2} for l in sorted(set(round(l, 1) for l in all_lows[-10:]))[:5]],
        }

    def _generate_explanation(self, tf_analysis: dict, alignment: dict, scores: dict, triggers: dict) -> str:
        h4 = tf_analysis.get("4h", {})
        h1 = tf_analysis.get("1h", {})
        d1 = tf_analysis.get("1d", {})
        m15 = tf_analysis.get("15m", {})

        h4_trend = h4.get("trend", "məlum deyil")
        h1_trend = h1.get("trend", "məlum deyil")
        d1_trend = d1.get("trend", "məlum deyil")

        lines = [f"SKHYUSDT analizi:"]

        if d1_trend != "neutral":
            lines.append(f"Günlük trend {d1_trend}-dir.")
        if h4_trend != "neutral":
            lines.append(f"4H {h4_trend} struktur.")

        h1_dir = "yüksələn" if h1_trend == "bullish" else "enən" if h1_trend == "bearish" else "neytral"
        lines.append(f"1H {h1_dir}. Qiymət EMA göstəricilərinə nəzərən {'yuxarı' if h1.get('trend') == 'bullish' else 'aşağı'}.")

        m15_mom = m15.get("momentum", "neytral")
        if m15_mom in ("bearish", "overbought"):
            lines.append("15M-də satış momentumu zəifləyir." if m15_mom == "bearish" else "15M-də həddən artıq satış zonası.")
        elif m15_mom in ("bullish", "oversold"):
            lines.append("15M-də alış momentumu var." if m15_mom == "bullish" else "15M-də həddən artıq alış zonası.")

        lt = triggers.get("long_trigger_price", 0)
        st = triggers.get("short_trigger_price", 0)
        if lt and alignment.get("primary_direction") != "short":
            lines.append(f"${lt} üzərində 1H bağlanış və artan həcm gəlmədən LONG təsdiqlənmir.")
        if st and alignment.get("primary_direction") != "long":
            lines.append(f"${st} aşağı qırılarsa və OI artarsa SHORT ssenarisi güclənəcək.")

        if scores.get("status") == "WAIT":
            lines.append("Gözləmə tövsiyə olunur - təsdiq gözlənilir.")
        elif scores.get("status") == "WATCHLIST":
            lines.append("İzləmə siyahısı - trigger yaxınlaşdıqda dəyərləndir.")

        if alignment.get("conflicts"):
            lines.append(f"Ziddiyyət: {'; '.join(alignment['conflicts'])}")

        return "\n".join(lines) if lines else "Məlumat yoxdur."

    async def get_scenarios(self) -> dict:
        analysis = await self.get_full_analysis()
        tf = analysis.get("timeframes", {})
        triggers = analysis.get("triggers", {})
        scores = analysis.get("scores", {})
        sr = analysis.get("support_resistance", {})
        snapshot = analysis.get("snapshot", {})
        price = snapshot.get("ticker", {}).get("price", 0)
        h4 = tf.get("4h", {})
        h1 = tf.get("1h", {})

        h4_vol = h4.get("volatility", 0.02) or 0.02
        atr_val = price * h4_vol if price else 0

        main_scenario = self._build_main_scenario(tf, triggers, scores, price, atr_val, sr)
        alt_scenario = self._build_alt_scenario(tf, triggers, scores, price, atr_val, sr, main_scenario)
        risk_scenario = self._build_risk_scenario(tf, triggers, scores, price, atr_val, sr, main_scenario)

        return {
            "main_scenario": main_scenario,
            "alternative_scenario": alt_scenario,
            "risk_fakeout_scenario": risk_scenario,
        }

    def _build_main_scenario(self, tf, triggers, scores, price, atr, sr) -> dict:
        h4_trend = tf.get("4h", {}).get("trend", "neutral")
        h1_trend = tf.get("1h", {}).get("trend", "neutral")
        primary = scores.get("long_probability", 50) >= 50 and "long" or "short"
        long_bias = scores.get("long_probability", 50) >= 50
        dir_label = "LONG" if long_bias else "SHORT"
        direction = "up" if long_bias else "down"

        if long_bias:
            activation = f"1H close above ${triggers.get('long_trigger_price', 0)} with volume confirmation"
            targets = [
                f"TP1: ${round(price + atr * 1.5, 2) if price else 0}",
                f"TP2: ${round(price + atr * 3.0, 2) if price else 0}",
                f"TP3: ${round(price + atr * 5.0, 2) if price else 0}",
            ]
            invalidation = f"Below ${triggers.get('bullish_invalidation', 0)}"
            reasons = ["Higher timeframe structure supports", "Momentum favoring buyers", "Volume confirmation expected"]
            risks = ["Resistance overhead", "Funding may flip negative"]
        else:
            activation = f"1H close below ${triggers.get('short_trigger_price', 0)} with volume confirmation"
            targets = [
                f"TP1: ${round(price - atr * 1.5, 2) if price else 0}",
                f"TP2: ${round(price - atr * 3.0, 2) if price else 0}",
                f"TP3: ${round(price - atr * 5.0, 2) if price else 0}",
            ]
            invalidation = f"Above ${triggers.get('bearish_invalidation', 0)}"
            reasons = ["Higher timeframe structure bearish", "Momentum favoring sellers", "Breakdown with volume"]
            risks = ["Support below", "Short squeeze potential"]

        return {
            "direction": dir_label,
            "activation_trigger": activation,
            "probability": max(scores.get("long_probability", 50), scores.get("short_probability", 50)) if long_bias else max(scores.get("short_probability", 50), scores.get("long_probability", 50)),
            "projected_path": f"Price moves {direction} over next 10-20 candles, targeting {targets[0]} initially",
            "target_zones": targets,
            "invalidation": invalidation,
            "expected_duration": "1-2 days" if direction == "up" else "1-2 days",
            "supporting_reasons": reasons,
            "opposing_risks": risks,
        }

    def _build_alt_scenario(self, tf, triggers, scores, price, atr, sr, main) -> dict:
        opposite_dir = "SHORT" if main["direction"] == "LONG" else "LONG"
        opposite_prob = scores.get("short_probability", 50) if main["direction"] == "LONG" else scores.get("long_probability", 50)
        return {
            "direction": opposite_dir,
            "activation_trigger": f"Failure at trigger level, reversal to {opposite_dir.lower()} side",
            "probability": opposite_prob,
            "projected_path": f"Rejection at key level drives price in opposite direction over 5-10 candles",
            "target_zones": [f"~${round(price * (0.95 if opposite_dir == 'LONG' else 1.05), 2)}"],
            "invalidation": main["invalidation"],
            "expected_duration": "12-24 hours",
            "supporting_reasons": ["Failure at key level", "Divergence signal", "Order flow shift"],
            "opposing_risks": ["Main scenario still valid", "Low volume reversal"],
        }

    def _build_risk_scenario(self, tf, triggers, scores, price, atr, sr, main) -> dict:
        return {
            "direction": f"FAKEOUT - {main['direction']} TRAP",
            "activation_trigger": f"Initial {main['direction'].lower()} breakout, then immediate reversal below/above trigger",
            "probability": 20,
            "projected_path": f"Liquidity sweep + fake breakout, trapping {main['direction'].lower()} traders, then sharp reversal",
            "target_zones": [f"Stop hunt +50% beyond invalidation"],
            "invalidation": "Holding above/below main trigger level",
            "expected_duration": "4-8 hours",
            "supporting_reasons": ["Large position buildup", "Spoofing detection", "Liquidity grab"],
            "opposing_risks": ["Majority wrong", "Low probability"],
        }


skhy_analysis = SkhyAnalysisEngine()
