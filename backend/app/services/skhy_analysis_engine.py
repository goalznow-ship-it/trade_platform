import asyncio
import numpy as np
from datetime import datetime, timezone
from app.services.skhy_market_data import skhy_market_data
from app.services.skhy_indicators import skhy_indicators
from app.services.skhy_structure import skhy_structure
from app.core.logging import logger

TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

class SkhyAnalysisEngine:
    async def get_full_analysis(self, timeframe: str | None = None) -> dict:
        active_tf = timeframe or "1h"
        now_iso = datetime.now(timezone.utc).isoformat()
        snapshot = await skhy_market_data.get_snapshot()

        if timeframe:
            tfs = [timeframe]
        else:
            tfs = TIMEFRAMES

        ohlcv_tasks = {tf: skhy_market_data.get_ohlcv(tf, 200, skip_cache=bool(timeframe)) for tf in tfs}
        ohlcv_results = await asyncio.gather(*ohlcv_tasks.values(), return_exceptions=True)
        ohlcv_data = {}
        for tf, result in zip(ohlcv_tasks.keys(), ohlcv_results):
            if isinstance(result, Exception):
                logger.warning(f"OHLCV fetch failed for {tf}: {result}")
                ohlcv_data[tf] = []
            else:
                ohlcv_data[tf] = result

        if timeframe:
            data = ohlcv_data.get(timeframe, [])
            if len(data) < 30:
                return {
                    "symbol": "SKHYUSDT", "exchange": "Binance Futures", "market": "USDT Perpetual",
                    "timestamp": now_iso, "last_updated": now_iso, "active_timeframe": timeframe,
                    "snapshot": snapshot, "timeframes": {timeframe: {"error": f"Insufficient data ({len(data)} candles)", "signal": "WAIT"}},
                    "alignment": {"primary_direction": "neutral", "confidence": 0, "status": "NO_DATA"},
                    "scores": {k: 0 for k in ["trend_score","structure_score","momentum_score","volume_score","liquidity_score","pattern_score","futures_score","orderflow_score","multitimeframe_score","risk_score"]} | {"overall": 0, "status": "NO_DATA_"+timeframe, "long_probability": 50, "short_probability": 50, "signal_confidence": 0},
                    "triggers": {}, "patterns": [], "support_resistance": {}, "support_zone": {}, "resistance_zone": {},
                    "elliott_wave": {"status":"insufficient_data"}, "fibonacci": {"status":"insufficient_data"},
                    "fibonacci_levels": {"status":"insufficient_data"}, "detected_structure": {"status":"insufficient_data"},
                    "channel_lines": {"status":"insufficient_data"}, "breakout_zone": {"status":"insufficient_data"},
                    "scenario_paths": {}, "main_scenario_path": [], "alternative_scenario_path": [], "fakeout_scenario_path": [],
                    "target_hierarchy": {"targets":[]}, "time_estimates": {"status":"insufficient_data"},
                    "activation_conditions": {}, "confidence_breakdown": {},
                    "invalidation_level": 0, "module_errors": {f"{timeframe}_data": f"Insufficient data ({len(data)} candles)"},
                    "data_freshness": snapshot.get("data_freshness", "unknown") if isinstance(snapshot, dict) else "unknown",
                    "explanation_az": f"{timeframe} üçün kifayət qədər məlumat yoxdur ({len(data)} şam).",
                }
            indicators = skhy_indicators.analyze(data)
            structure = skhy_structure.analyze(data)
            tf_analysis = {timeframe: self._analyze_timeframe(data, indicators, structure, timeframe)}
            ohlcv_all = {timeframe: ohlcv_data.get(timeframe, [])}
        else:
            tf_analysis = {}
            for tf in TIMEFRAMES:
                data = ohlcv_data.get(tf, [])
                if len(data) < 30:
                    tf_analysis[tf] = {"error": f"Insufficient data ({len(data)} candles)", "signal": "WAIT"}
                    continue
                indicators = skhy_indicators.analyze(data)
                structure = skhy_structure.analyze(data)
                tf_analysis[tf] = self._analyze_timeframe(data, indicators, structure, tf)
            ohlcv_all = ohlcv_data

        alignment = self._compute_alignment(tf_analysis)
        scores = self._compute_scores(tf_analysis, alignment, snapshot)
        triggers = self._compute_triggers(tf_analysis, alignment, scores, snapshot)
        patterns = self._detect_patterns(ohlcv_all)
        support_resistance = self._compute_support_resistance(ohlcv_all, snapshot)
        elliott_wave = self._detect_elliott_wave(ohlcv_all)
        fibonacci = self._compute_fibonacci_levels(ohlcv_all, snapshot)
        detected_structure = self._detect_dominant_structure(ohlcv_all, snapshot)
        channel_lines = self._detect_channel(ohlcv_all)
        breakout_zone = self._detect_breakout_zone(ohlcv_all, snapshot, tf_analysis)
        scenario_paths = self._compute_scenario_paths(tf_analysis, scores, triggers, snapshot, ohlcv_all, fibonacci, detected_structure)
        target_hierarchy = self._compute_target_hierarchy(ohlcv_all, snapshot, scenario_paths, fibonacci, support_resistance, detected_structure, patterns)
        time_estimates = self._compute_time_estimates(ohlcv_all)
        activation_conditions = self._compute_activation_conditions(triggers, tf_analysis, snapshot)
        confidence_breakdown = self._compute_confidence_breakdown(scores, tf_analysis, patterns, detected_structure, alignment)
        whale_analysis = self._compute_whale_analysis(snapshot)
        time_forecast = self._compute_time_forecast(scores, triggers, snapshot, tf_analysis)
        pattern_conflicts = self._compute_pattern_conflicts(patterns)
        trade_plan = self._compute_trade_plan(scores, triggers, snapshot, tf_analysis, fibonacci, target_hierarchy, patterns)
        module_errors = self._collect_module_errors(ohlcv_all, tf_analysis)
        data_freshness = snapshot.get("data_freshness", "live") if isinstance(snapshot, dict) else "unknown"

        sp_main = scenario_paths.get("main_scenario", {}).get("path_points", [])
        sp_alt = scenario_paths.get("alternative_scenario", {}).get("path_points", [])
        sp_fake = scenario_paths.get("fakeout_scenario", {}).get("path_points", [])
        invalidation_level = triggers.get("bullish_invalidation") or triggers.get("bearish_invalidation") or 0
        sup_zone = {"top": detected_structure.get("support_zone_top"), "bottom": detected_structure.get("support_zone_bottom")}
        res_zone = {"top": detected_structure.get("resistance_zone_top"), "bottom": detected_structure.get("resistance_zone_bottom")}

        return {
            "symbol": "SKHYUSDT", "exchange": "Binance Futures", "market": "USDT Perpetual",
            "timestamp": now_iso, "last_updated": now_iso,
            "active_timeframe": active_tf,
            "snapshot": snapshot, "timeframes": tf_analysis, "alignment": alignment, "scores": scores,
            "triggers": triggers, "patterns": patterns, "support_resistance": support_resistance,
            "support_zone": sup_zone, "resistance_zone": res_zone,
            "elliott_wave": elliott_wave, "fibonacci": fibonacci, "fibonacci_levels": fibonacci,
            "detected_structure": detected_structure, "channel_lines": channel_lines,
            "breakout_zone": breakout_zone, "scenario_paths": scenario_paths,
            "main_scenario_path": sp_main, "alternative_scenario_path": sp_alt, "fakeout_scenario_path": sp_fake,
            "target_hierarchy": target_hierarchy, "time_estimates": time_estimates,
            "activation_conditions": activation_conditions, "confidence_breakdown": confidence_breakdown,
            "whale_analysis": whale_analysis, "time_forecast": time_forecast,
            "active_patterns": [p for p in patterns if p.get("probability", 0) >= 50],
            "pattern_conflicts": pattern_conflicts,
            "pattern_completion": {p["name"]: p.get("completion_pct", p.get("completion", 0)) for p in patterns if p.get("probability", 0) >= 50},
            "pattern_invalidation": {p["name"]: {"price": p.get("invalidation", 0), "condition": p.get("invalidation_condition", "")} for p in patterns if p.get("probability", 0) >= 50},
            "trade_plan": trade_plan,
            "future_path_v2": scenario_paths,
            "hourly_forecast": time_forecast,
            "recalculation_timestamp": now_iso,
            "invalidation_level": round(invalidation_level, 2) if invalidation_level else 0,
            "module_errors": module_errors, "data_freshness": data_freshness,
            "explanation_az": self._generate_explanation(tf_analysis, alignment, scores, triggers, detected_structure, breakout_zone),
        }

    def _analyze_timeframe(self, data, indicators, structure, tf):
        if not data: return {"error": "No data", "signal": "WAIT"}
        close = data[-1]["close"]
        interp = indicators.get("interpretation", {})
        trend = interp.get("trend", {}); momentum = interp.get("momentum", {}); volume_info = interp.get("volume", {})
        overall = interp.get("overall", "neutral")
        bullish_score = bearish_score = 0
        if trend.get("bias") == "bullish": bullish_score += 25
        elif trend.get("bias") == "bearish": bearish_score += 25
        if momentum.get("rsi") in ("bullish", "oversold"): bullish_score += 15
        elif momentum.get("rsi") in ("bearish", "overbought"): bearish_score += 15
        if momentum.get("macd") == "bullish": bullish_score += 10
        elif momentum.get("macd") == "bearish": bearish_score += 10
        if volume_info.get("cmf") == "bullish": bullish_score += 10
        elif volume_info.get("cmf") == "bearish": bearish_score += 10
        if trend.get("supertrend") == "up": bullish_score += 15
        elif trend.get("supertrend") == "down": bearish_score += 15
        ms = structure.get("market_structure", {})
        if ms.get("trend") == "bullish": bullish_score += 15
        elif ms.get("trend") == "bearish": bearish_score += 15
        total = bullish_score + bearish_score
        bullish_pct = round(bullish_score / total * 100) if total > 0 else 50
        bearish_pct = round(bearish_score / total * 100) if total > 0 else 50
        support = self._find_support(data); resistance = self._find_resistance(data)
        signal = "STRONG_LONG" if bullish_pct >= 75 else "LONG" if bullish_pct >= 60 else "STRONG_SHORT" if bearish_pct >= 75 else "SHORT" if bearish_pct >= 60 else "WAIT"
        volatility = round(np.std([d["close"] for d in data[-20:]]) / np.mean([d["close"] for d in data[-20:]]), 4) if len(data) >= 20 else 0
        bos = structure.get("break_of_structure", []); choch = structure.get("change_of_character", [])
        return {
            "signal": signal, "trend": overall, "market_structure": ms.get("trend", "undefined"),
            "bullish_score": bullish_pct, "bearish_score": bearish_pct,
            "momentum": momentum.get("rsi", "neutral"), "volume": volume_info.get("relative_volume", "normal"),
            "volatility": volatility, "support": support, "resistance": resistance,
            "bos": len(bos), "bos_details": bos[-3:] if bos else [], "choch": len(choch),
            "choch_details": choch[-3:] if choch else [], "liquidity": structure.get("liquidity", {}),
            "pattern": self._detect_tf_pattern(data, tf), "close": close,
        }

    def _find_support(self, data):
        if len(data) < 20: return min(d["low"] for d in data) if data else 0
        lows = [d["low"] for d in data[-50:]]
        return sorted(set(round(l, 2) for l in lows))[0] if sorted(set(round(l, 2) for l in lows)) else min(lows)

    def _find_resistance(self, data):
        if len(data) < 20: return max(d["high"] for d in data) if data else 0
        highs = [d["high"] for d in data[-50:]]
        return sorted(set(round(h, 2) for h in highs))[-1] if sorted(set(round(h, 2) for h in highs)) else max(highs)

    def _detect_tf_pattern(self, data, tf):
        if len(data) < 30: return {"name": "none", "status": "insufficient_data"}
        closes = [d["close"] for d in data[-30:]]; highs = [d["high"] for d in data[-30:]]; lows = [d["low"] for d in data[-30:]]
        mid = len(closes) // 2
        first_half = np.mean(closes[:mid]); second_half = np.mean(closes[mid:])
        if second_half > first_half * 1.03 and max(highs[-5:]) > max(highs[-10:-5]): return {"name": "ascending", "status": "forming"}
        if second_half < first_half * 0.97 and min(lows[-5:]) < min(lows[-10:-5]): return {"name": "descending", "status": "forming"}
        return {"name": "ranging", "status": "neutral"}

    def _compute_alignment(self, tf_analysis):
        signals = [v.get("signal", "WAIT") for v in tf_analysis.values() if "signal" in v]
        if not signals: return {"confidence": 0, "status": "NO_DATA"}
        long_count = sum(1 for s in signals if s in ("LONG","STRONG_LONG"))
        short_count = sum(1 for s in signals if s in ("SHORT","STRONG_SHORT"))
        total = len(signals)
        h4 = tf_analysis.get("4h", {}).get("signal", "WAIT"); h1 = tf_analysis.get("1h", {}).get("signal", "WAIT")
        h4_h1_aligned = (h4 in ("LONG","STRONG_LONG") and h1 in ("LONG","STRONG_LONG")) or (h4 in ("SHORT","STRONG_SHORT") and h1 in ("SHORT","STRONG_SHORT"))
        d1 = tf_analysis.get("1d", {}).get("signal", "WAIT")
        conflicts = []
        if h4 in ("LONG","STRONG_LONG") and h1 in ("SHORT","STRONG_SHORT"): conflicts.append("4H bullish but 1H bearish")
        if h4 in ("SHORT","STRONG_SHORT") and h1 in ("LONG","STRONG_LONG"): conflicts.append("4H bearish but 1H bullish")
        if d1 == "WAIT" and h4 != "WAIT": conflicts.append("Daily trend neutral")
        primary_direction = "long" if long_count > short_count else "short" if short_count > long_count else "neutral"
        confidence = round((max(long_count, short_count) / total) * 100) if total > 0 else 0
        return {
            "primary_direction": primary_direction, "confidence": min(confidence, 100),
            "long_timeframes": long_count, "short_timeframes": short_count, "total_timeframes": total,
            "h4_h1_aligned": h4_h1_aligned, "d1_filter": d1, "conflicts": conflicts,
            "status": "ALIGNED" if confidence >= 60 and h4_h1_aligned and not conflicts else "CONFLICTING" if conflicts else "LOW_CONFIDENCE",
        }

    def _compute_scores(self, tf_analysis, alignment, snapshot):
        tf_count = sum(1 for v in tf_analysis.values() if "signal" in v)
        if tf_count == 0: return {"overall": 0, "status": "NO_DATA"}
        trend_score=structure_score=momentum_score=volume_score=liquidity_score=pattern_score=futures_score=orderflow_score=0
        multitimeframe_score = alignment["confidence"]; risk_score = 50
        for v in tf_analysis.values():
            if "trend" not in v: continue
            trend_score += 12 if v.get("trend") == "bullish" else 12 if v.get("trend") == "bearish" else 5
            structure_score += 12 if v.get("market_structure") == "bullish" else 12 if v.get("market_structure") == "bearish" else 5
            mom = v.get("momentum", "neutral")
            momentum_score += 10 if mom in ("bullish","oversold") else 10 if mom in ("bearish","overbought") else 5
            vol = v.get("volume", "normal")
            volume_score += 12 if vol in ("high","above_average") else 5
            liq = v.get("liquidity", {})
            liquidity_score += 10 if liq.get("nearest_above") or liq.get("nearest_below") else 5
            pattern_score += 10 if v.get("bos",0) > 0 or v.get("choch",0) > 0 else 5
        tf_count = max(tf_count, 1)
        trend_score = min(trend_score//tf_count,100); structure_score = min(structure_score//tf_count,100)
        momentum_score = min(momentum_score//tf_count,100); volume_score = min(volume_score//tf_count,100)
        liquidity_score = min(liquidity_score//tf_count,100); pattern_score = min(pattern_score//tf_count,100)
        funding = snapshot.get("funding", {})
        if funding:
            fr = funding.get("funding_rate", 0)
            if fr is not None: futures_score = 50 if abs(fr) < 0.0001 else 60 if fr > 0 else 40
        oi = snapshot.get("open_interest", {})
        if oi.get("open_interest"): futures_score = min(futures_score + 10, 100)
        ls = snapshot.get("long_short_ratio", {})
        lsr = ls.get("long_short_ratio", 1)
        orderflow_score += 30 if lsr > 1.5 else 30 if lsr < 0.7 else 15
        taker = snapshot.get("taker_buy_sell_ratio", {})
        tbr = taker.get("buy_sell_ratio", 1)
        if tbr > 1.2: orderflow_score += 20; futures_score += 10
        elif tbr < 0.8: orderflow_score += 20; futures_score += 10
        else: orderflow_score += 10
        risk_score = risk_score - (10 if alignment.get("conflicts") else 0) + (10 if alignment.get("h4_h1_aligned") else 0)
        overall = round((trend_score*0.15 + structure_score*0.12 + momentum_score*0.12 + volume_score*0.10 +
                         liquidity_score*0.10 + pattern_score*0.08 + futures_score*0.10 + orderflow_score*0.08 +
                         multitimeframe_score*0.10 + risk_score*0.05))
        status = "STRONG_TRADE_READY" if overall >= 80 else "TRADE_READY" if overall >= 70 else "WATCHLIST" if overall >= 50 else "WAIT"
        long_prob = round(trend_score*0.3 + momentum_score*0.2 + volume_score*0.1 + (100-structure_score)*0.1 + multitimeframe_score*0.3)
        short_prob = 100 - long_prob
        return {
            "trend_score": trend_score, "structure_score": structure_score, "momentum_score": momentum_score,
            "volume_score": volume_score, "liquidity_score": liquidity_score, "pattern_score": pattern_score,
            "futures_score": futures_score, "orderflow_score": orderflow_score,
            "multitimeframe_score": multitimeframe_score, "risk_score": risk_score,
            "overall": overall, "status": status, "long_probability": min(max(long_prob,0),100),
            "short_probability": min(max(short_prob,0),100), "signal_confidence": overall,
        }

    def _compute_triggers(self, tf_analysis, alignment, scores, snapshot):
        h4 = tf_analysis.get("4h", {}); h1 = tf_analysis.get("1h", {}); m15 = tf_analysis.get("15m", {})
        close_4h = h4.get("close",0); close_1h = h1.get("close",0)
        res_1h = h1.get("resistance",0); sup_1h = h1.get("support",0)
        h4_trend = h4.get("trend","neutral"); h1_trend = h1.get("trend","neutral")
        long_trigger_price = round(res_1h*1.005,2) if res_1h else round(close_1h*1.02,2)
        short_trigger_price = round(sup_1h*0.995,2) if sup_1h else round(close_1h*0.98,2)
        long_conditions = []; short_conditions = []
        if h4_trend in ("bullish","neutral"): long_conditions.append("4H strukturu alışı dəstəkləyir")
        else: long_conditions.append("4H trendi aşağı - təsdiq üçün GÖZLƏ")
        if h1_trend in ("bullish","neutral"): long_conditions.append("1H momentum alışı dəstəkləyir")
        else: long_conditions.append("1H aşağı trenddə - dönüş gözlənilir")
        if res_1h: long_conditions.append(f"1H şamı ${long_trigger_price} üzərində bağlanmalı")
        long_conditions.append("Partlayış şamında həcm 1.5x ortalamadan yuxarı")
        long_conditions.append("Partlayışda OI artmalı")
        taker = snapshot.get("taker_buy_sell_ratio", {})
        if taker.get("buy_sell_ratio",1) < 1.0: long_conditions.append("Taker alış nisbəti 1.0 üzərində güclənməlidir")
        if h4_trend in ("bearish","neutral"): short_conditions.append("4H strukturu satışı dəstəkləyir")
        else: short_conditions.append("4H trendi yuxarı - dönüş üçün GÖZLƏ")
        if h1_trend in ("bearish","neutral"): short_conditions.append("1H momentum satışı dəstəkləyir")
        else: short_conditions.append("1H yuxarı trenddə - dönüş gözlənilir")
        if sup_1h: short_conditions.append(f"1H şamı ${short_trigger_price} altında bağlanmalı")
        short_conditions.append("Qırılma şamında həcm 1.5x ortalamadan yuxarı")
        short_conditions.append("Qırılmada OI artmalı")
        if taker.get("buy_sell_ratio",1) > 1.0: short_conditions.append("Taker satış nisbəti 1.0 üzərində güclənməlidir")
        bullish_invalidation = round(close_1h*0.98,2) if close_1h else 0
        bearish_invalidation = round(close_1h*1.02,2) if close_1h else 0
        if h4_trend == "bullish":
            bullish_invalidation = round(h4.get("support", close_4h*0.95),2)
            bearish_invalidation = round(h4.get("resistance", close_4h*1.05),2)
        return {
            "long_trigger_price": long_trigger_price, "long_trigger_conditions": long_conditions,
            "short_trigger_price": short_trigger_price, "short_trigger_conditions": short_conditions,
            "bullish_invalidation": bullish_invalidation, "bearish_invalidation": bearish_invalidation,
            "entry_ready": scores["overall"] >= 70 and alignment["h4_h1_aligned"],
        }

    # ─── PATTERN DETECTION ───
    def _detect_patterns(self, ohlcv_data):
        patterns = []
        for tf in TIMEFRAMES:
            data = ohlcv_data.get(tf, [])
            if len(data) < 50: continue
            recent = data[-30:]
            for check in [self._check_bull_flag, self._check_bear_flag, self._check_double_top,
                          self._check_double_bottom, self._check_triangle, self._check_abcd,
                          self._check_rectangle, self._check_wedge, self._check_head_shoulders,
                          self._check_cup_handle]:
                p = check(recent, tf)
                if p: patterns.append(p)
        return patterns

    def _check_bull_flag(self, data, tf):
        if len(data) < 15: return None
        pole = data[:8]; flag = data[8:]
        pole_rise = pole[-1]["close"] - pole[0]["close"]
        if pole_rise > 0 and pole_rise / pole[0]["close"] > 0.03:
            flag_highs = [d["high"] for d in flag]; flag_lows = [d["low"] for d in flag]
            if max(flag_highs) - min(flag_lows) < (max(d["high"] for d in pole) - min(d["low"] for d in pole)) * 0.5:
                flag_price = data[-1]["close"]
                near_breakout = flag_price >= max(flag_highs) * 0.98
                return {"name":"Bull Flag","timeframe":tf,"status":"DETECTED","completion":70,
                        "breakout_level":max(flag_highs),"measured_target":round(flag[-1]["close"]+pole_rise,2),
                        "invalidation":min(flag_lows),"probability":60,"reliability":"medium",
                        "detection_reason":"Güclü yüksəlişdən sonra üfüqi konsolidasiya (bayraq forması)",
                        "invalidation_condition":f"Qiymət ${min(flag_lows)} altında bağlanarsa",
                        "completion_pct":90 if near_breakout else 70,
                        "neckline":round(max(flag_highs),2),
                        "retest_zone_low":round(min(flag_lows),2),"retest_zone_high":round(max(flag_highs),2)}
        return None

    def _check_bear_flag(self, data, tf):
        if len(data) < 15: return None
        pole = data[:8]; flag = data[8:]
        pole_drop = pole[0]["close"] - pole[-1]["close"]
        if pole_drop > 0 and pole_drop / pole[0]["close"] > 0.03:
            flag_highs = [d["high"] for d in flag]; flag_lows = [d["low"] for d in flag]
            if max(flag_highs) - min(flag_lows) < (max(d["high"] for d in pole) - min(d["low"] for d in pole)) * 0.5:
                flag_price = data[-1]["close"]
                near_breakdown = flag_price <= min(flag_lows) * 1.02
                return {"name":"Bear Flag","timeframe":tf,"status":"DETECTED","completion":70,
                        "breakout_level":min(flag_lows),"measured_target":round(flag[-1]["close"]-pole_drop,2),
                        "invalidation":max(flag_highs),"probability":60,"reliability":"medium",
                        "detection_reason":"Güclü enişdən sonra üfüqi konsolidasiya (bayraq forması)",
                        "invalidation_condition":f"Qiymət ${max(flag_highs)} üzərində bağlanarsa",
                        "completion_pct":90 if near_breakdown else 70,
                        "neckline":round(min(flag_lows),2),
                        "retest_zone_low":round(min(flag_lows),2),"retest_zone_high":round(max(flag_highs),2)}
        return None

    def _check_double_top(self, data, tf):
        if len(data) < 20: return None
        highs = [d["high"] for d in data]; mid = len(highs)//2
        left = max(highs[:mid]); right = max(highs[mid:])
        if abs(left-right)/left < 0.015:
            neckline = min(d["low"] for d in data)
            dt_price = data[-1]["close"]
            dt_range = left - neckline
            dt_dist = abs(dt_price - neckline)
            dt_completion = min(95, max(30, int(50 + 40 * (1 - dt_dist / max(dt_range, 0.01)))) if dt_range > 0 else 50)
            return {"name":"Double Top","timeframe":tf,"status":"DETECTED","completion":50,
                    "breakdown_level":neckline,"measured_target":round(neckline-(left-neckline),2),
                    "invalidation":max(left,right)*1.01,"probability":55,"reliability":"medium",
                    "detection_reason":"Eyni səviyyədə iki yüksək zirvə — dönüş patterni",
                    "invalidation_condition":f"Qiymət ${max(left,right)*1.01} üzərində bağlanarsa",
                    "completion_pct":dt_completion,
                    "neckline":round(neckline,2),
                    "retest_zone_low":round(neckline,2),"retest_zone_high":round(neckline+(left-neckline)*0.3,2)}
        return None

    def _check_double_bottom(self, data, tf):
        if len(data) < 20: return None
        lows = [d["low"] for d in data]; mid = len(lows)//2
        left = min(lows[:mid]); right = min(lows[mid:])
        if abs(left-right)/left < 0.015:
            neckline = max(d["high"] for d in data)
            db_price = data[-1]["close"]
            db_range = neckline - left
            db_dist = abs(db_price - neckline)
            db_completion = min(95, max(30, int(50 + 40 * (1 - db_dist / max(db_range, 0.01)))) if db_range > 0 else 50)
            return {"name":"Double Bottom","timeframe":tf,"status":"DETECTED","completion":50,
                    "breakout_level":neckline,"measured_target":round(neckline+(neckline-left),2),
                    "invalidation":min(left,right)*0.99,"probability":55,"reliability":"medium",
                    "detection_reason":"Eyni səviyyədə iki aşağı dib — dönüş patterni",
                    "invalidation_condition":f"Qiymət ${min(left,right)*0.99} altında bağlanarsa",
                    "completion_pct":db_completion,
                    "neckline":round(neckline,2),
                    "retest_zone_low":round(neckline-(neckline-left)*0.3,2),"retest_zone_high":round(neckline,2)}
        return None

    def _check_triangle(self, data, tf):
        if len(data) < 15: return None
        highs = [d["high"] for d in data[-15:]]; lows = [d["low"] for d in data[-15:]]
        h_slope = (highs[-1]-highs[0])/len(highs); l_slope = (lows[-1]-lows[0])/len(lows)
        tr_price = data[-1]["close"]
        tr_range = max(highs) - min(lows)
        initial_range = max(highs[:5]) - min(lows[:5])
        tri_convergence = min(95, max(20, int(100 * (1 - tr_range / max(initial_range, 0.01)))) if initial_range > 0 else 50)
        if abs(h_slope) < 0.001 and l_slope > 0:
            return {"name":"Ascending Triangle","timeframe":tf,"status":"FORMING","breakout_level":max(highs),
                    "measured_target":round(max(highs)+(max(highs)-min(lows)),2),"invalidation":min(lows)*0.99,"probability":50,"reliability":"medium",
                    "detection_reason":"Yuxarı müqavimət xətti, yüksələn dəstək — yüksəlişə hazırlıq",
                    "invalidation_condition":f"Qiymət ${min(lows)*0.99} altında bağlanarsa",
                    "completion_pct":tri_convergence,
                    "neckline":round(max(highs),2),
                    "retest_zone_low":round(min(lows),2),"retest_zone_high":round(max(highs),2)}
        if h_slope < 0 and abs(l_slope) < 0.001:
            return {"name":"Descending Triangle","timeframe":tf,"status":"FORMING","breakdown_level":min(lows),
                    "measured_target":round(min(lows)-(max(highs)-min(lows)),2),"invalidation":max(highs)*1.01,"probability":50,"reliability":"medium",
                    "detection_reason":"Aşağı dəstək xətti, enən müqavimət — enişə hazırlıq",
                    "invalidation_condition":f"Qiymət ${max(highs)*1.01} üzərində bağlanarsa",
                    "completion_pct":tri_convergence,
                    "neckline":round(min(lows),2),
                    "retest_zone_low":round(min(lows),2),"retest_zone_high":round(max(highs),2)}
        if h_slope < 0 and l_slope > 0:
            sym_inval = max(highs) if abs(max(highs)-tr_price) < abs(min(lows)-tr_price) else min(lows)
            return {"name":"Symmetrical Triangle","timeframe":tf,"status":"FORMING","probability":45,"reliability":"medium",
                    "invalidation":sym_inval,
                    "detection_reason":"Yaxınlaşan müqavimət və dəstək xətləri — sıxılma",
                    "invalidation_condition":f"Qiymət ${sym_inval} səviyyəsindən kənara çıxarsa",
                    "completion_pct":tri_convergence,
                    "neckline":round(tr_price,2),
                    "retest_zone_low":round(min(lows),2),"retest_zone_high":round(max(highs),2)}
        return None

    def _check_abcd(self, data, tf):
        if len(data) < 20: return None
        closes = [d["close"] for d in data[-20:]]
        if len(closes) < 10: return None
        a,b,c,dv = closes[0],closes[5],closes[10],closes[-1]
        ab = abs(b-a); bc = abs(c-b)
        if ab > 0 and bc/ab > 0.6 and bc/ab < 0.9:
            target = dv + (ab-bc)*(1 if b>a else -1)
            cd_len = abs(closes[-1] - c)
            expected_cd = abs(b - a) * 0.786
            abcd_completion = min(95, max(20, int(cd_len / max(expected_cd, 0.01) * 100)))
            return {"name":"ABCD Pattern","timeframe":tf,"status":"FORMING","completion":80,
                    "measured_target":round(target,2),"probability":50,"reliability":"low",
                    "detection_reason":"Harmonik ABCD formalaşması — ardıcıl impuls və korreksiya",
                    "invalidation_condition":f"Qiymət {c} səviyyəsindən geri dönərsə",
                    "completion_pct":abcd_completion,
                    "neckline":round(c,2),
                    "retest_zone_low":round(min(c, dv),2),"retest_zone_high":round(max(c, dv),2)}
        return None

    def _check_rectangle(self, data, tf):
        if len(data) < 15: return None
        highs = [d["high"] for d in data[-15:]]; lows = [d["low"] for d in data[-15:]]
        top = max(highs); bottom = min(lows)
        if abs(top-np.mean(highs[-5:]))/top < 0.01 and abs(bottom-np.mean(lows[-5:]))/bottom < 0.01:
            rect_price = data[-1]["close"]
            rect_dist = min(abs(rect_price - top), abs(rect_price - bottom)) / max(top - bottom, 0.01)
            rect_completion = min(95, max(30, int(100 * (1 - rect_dist))))
            return {"name":"Rectangle","timeframe":tf,"status":"FORMING","breakout_level":top,"breakdown_level":bottom,
                    "measured_target":round(top+(top-bottom),2),"probability":45,"reliability":"low",
                    "detection_reason":"Üfüqi müqavimət və dəstək arasında konsolidasiya",
                    "invalidation_condition":f"Qiymət ${bottom} altında və ya ${top} üzərində bağlanarsa",
                    "completion_pct":rect_completion,
                    "neckline":round(top,2),
                    "retest_zone_low":round(bottom,2),"retest_zone_high":round(top,2)}
        return None

    def _check_wedge(self, data, tf):
        if len(data) < 15: return None
        highs = [d["high"] for d in data[-15:]]; lows = [d["low"] for d in data[-15:]]
        h_slope = (highs[-1]-highs[0])/len(highs) if len(highs)>1 else 0
        l_slope = (lows[-1]-lows[0])/len(lows) if len(lows)>1 else 0
        wedge_initial = max(highs[:5]) - min(lows[:5])
        wedge_current = max(highs[-5:]) - min(lows[-5:])
        wedge_convergence = min(95, max(30, int(100 * (1 - wedge_current / max(wedge_initial, 0.01)))) if wedge_initial > 0 else 50)
        if h_slope < 0 and l_slope < 0 and h_slope > l_slope:
            return {"name":"Falling Wedge","timeframe":tf,"status":"FORMING","breakout_level":max(highs),
                    "measured_target":round(max(highs)+(max(highs)-min(lows))*0.5,2),"invalidation":min(lows)*0.99,"probability":50,"reliability":"medium",
                    "detection_reason":"Enən müqavimət və dəstək xətləri — daralma və potensial yuxarı breakout",
                    "invalidation_condition":f"Qiymət ${min(lows)*0.99} altında bağlanarsa",
                    "completion_pct":wedge_convergence,
                    "neckline":round(max(highs),2),
                    "retest_zone_low":round(min(lows),2),"retest_zone_high":round(max(highs),2)}
        if h_slope > 0 and l_slope > 0 and h_slope > l_slope:
            return {"name":"Rising Wedge","timeframe":tf,"status":"FORMING","breakdown_level":min(lows),
                    "measured_target":round(min(lows)-(max(highs)-min(lows))*0.5,2),"invalidation":max(highs)*1.01,"probability":50,"reliability":"medium",
                    "detection_reason":"Yüksələn müqavimət və dəstək xətləri — daralma və potensial aşağı breakdown",
                    "invalidation_condition":f"Qiymət ${max(highs)*1.01} üzərində bağlanarsa",
                    "completion_pct":wedge_convergence,
                    "neckline":round(min(lows),2),
                    "retest_zone_low":round(min(lows),2),"retest_zone_high":round(max(highs),2)}
        return None

    def _check_cup_handle(self, data, tf):
        if len(data) < 30: return None
        closes = [d["close"] for d in data[-30:]]; highs = [d["high"] for d in data[-30:]]; lows = [d["low"] for d in data[-30:]]
        mid = len(closes)//2; cup_start = closes[0]; cup_bottom = min(closes[:mid])
        cup_rnd = closes[:mid]; handle_rnd = closes[mid:]
        cup_depth = (cup_start - cup_bottom) / cup_start
        if 0.05 <= cup_depth <= 0.35:
            handle_high = max(handle_rnd[:len(handle_rnd)//2]) if handle_rnd else 0
            handle_low = min(handle_rnd) if handle_rnd else 0
            handle_retrace = (handle_high - handle_low) / (cup_start - cup_bottom) if (cup_start-cup_bottom) > 0 else 0
            if 0.1 <= handle_retrace <= 0.5:
                breakout = max(highs[-5:])
                target = round(breakout + (cup_start - cup_bottom), 2)
                cup_handle_progress = len(handle_rnd) / 15.0
                cup_completion = min(95, max(40, int(60 + cup_handle_progress * 30)))
                return {"name":"Cup and Handle","timeframe":tf,"status":"DETECTED","completion":80,
                        "breakout_level":breakout,"measured_target":target,
                        "cup_bottom":round(cup_bottom,2),"cup_rim":round(cup_start,2),
                        "handle_low":round(handle_low,2),"invalidation":round(min(handle_low,cup_bottom)*0.99,2),
                        "probability":60,"reliability":"medium",
                        "detection_reason":"Kubok formalaşması (yuvarlaqlı dib) + sap (konsolidasiya) — qalxma patterni",
                        "invalidation_condition":f"Qiymət ${round(min(handle_low,cup_bottom)*0.99,2)} altında bağlanarsa",
                        "completion_pct":cup_completion,
                        "neckline":round(breakout,2),
                        "retest_zone_low":round(handle_low,2),"retest_zone_high":round(breakout,2)}
        return None

    def _check_head_shoulders(self, data, tf):
        if len(data) < 20: return None
        highs = [d["high"] for d in data[-20:]]; mid = len(highs)//2
        ls = max(highs[:mid//2]) if highs[:mid//2] else 0
        hd = max(highs[mid//2:mid+mid//2]) if highs[mid//2:mid+mid//2] else 0
        rs = max(highs[mid+mid//2:]) if highs[mid+mid//2:] else 0
        if hd > ls and hd > rs and abs(ls-rs)/hd < 0.05:
            neckline = min(d["low"] for d in data[-20:])
            hs_completion = 70 if rs > hd * 0.8 else 50
            return {"name":"Head and Shoulders","timeframe":tf,"status":"DETECTED","breakdown_level":neckline,
                    "measured_target":round(neckline-(hd-neckline),2),"invalidation":hd*1.01,"probability":55,"reliability":"medium",
                    "detection_reason":"Üç zirvə: sol çiyin, baş, sağ çiyin — trend dönüşü",
                    "invalidation_condition":f"Qiymət ${hd*1.01} üzərində bağlanarsa",
                    "completion_pct":hs_completion,
                    "neckline":round(neckline,2),
                    "retest_zone_low":round(neckline,2),"retest_zone_high":round(neckline+(hd-neckline)*0.3,2)}
        if ls > 0 and hd > 0 and rs > 0 and ls < hd and rs < hd and abs(ls-rs)/hd < 0.05:
            neckline = max(d["high"] for d in data[-20:])
            ihs_completion = 70 if rs > hd * 0.8 else 50
            return {"name":"Inverse Head and Shoulders","timeframe":tf,"status":"DETECTED","breakout_level":neckline,
                    "measured_target":round(neckline+(neckline-min(d["low"] for d in data[-20:])),2),"invalidation":min(highs)*0.99,"probability":55,"reliability":"medium",
                    "detection_reason":"Ters çevrilmiş baş-çiyin — eniş trendinin sonu",
                    "invalidation_condition":f"Qiymət ${min(highs)*0.99} altında bağlanarsa",
                    "completion_pct":ihs_completion,
                    "neckline":round(neckline,2),
                    "retest_zone_low":round(neckline-(neckline-min(highs))*0.3,2),"retest_zone_high":round(neckline,2)}
        return None

    def _compute_pattern_conflicts(self, patterns):
        if not patterns or len(patterns) < 2:
            return {"conflicts": [], "dominant_pattern": None, "has_conflict": False}

        conflicts = []
        directions = []
        for p in patterns:
            name = p.get("name", "")
            if any(x in name for x in ["Bull", "Ascending", "Cup", "Bottom", "Inverse", "Bullish"]):
                directions.append("bullish")
            elif any(x in name for x in ["Bear", "Descending", "Top", "Head", "Rising"]):
                directions.append("bearish")
            else:
                directions.append("neutral")

        bullish_count = sum(1 for d in directions if d == "bullish")
        bearish_count = sum(1 for d in directions if d == "bearish")

        if bullish_count > 0 and bearish_count > 0:
            conflicts.append({
                "type": "direction_conflict",
                "description_az": "Patternlər ziddiyyət təşkil edir: həm yüksəliş, həm eniş patternləri aşkarlandı",
                "bullish_patterns": [p["name"] for i, p in enumerate(patterns) if directions[i] == "bullish"],
                "bearish_patterns": [p["name"] for i, p in enumerate(patterns) if directions[i] == "bearish"],
            })

        dominant = max(patterns, key=lambda p: p.get("probability", 0)) if patterns else None

        return {
            "has_conflict": len(conflicts) > 0,
            "conflicts": conflicts,
            "dominant_pattern": dominant.get("name") if dominant else None,
            "dominant_direction": max(set(directions), key=directions.count) if directions else "neutral",
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "conflict_level": "high" if len(conflicts) > 0 and abs(bullish_count - bearish_count) <= 1 else "low",
        }

    # ─── SUPPORT / RESISTANCE ───
    def _compute_support_resistance(self, ohlcv_data, snapshot):
        all_lows = []; all_highs = []
        for data in ohlcv_data.values():
            if len(data) < 20: continue
            all_lows.extend(d["low"] for d in data[-50:])
            all_highs.extend(d["high"] for d in data[-50:])
        if not all_lows or not all_highs: return {"error":"Insufficient data"}
        price = snapshot.get("ticker",{}).get("price",0) or all_highs[-1] if all_highs else 0
        nearest_support = max([l for l in all_lows if l < price], default=min(all_lows)) if all_lows else 0
        strongest_support = min(all_lows) if all_lows else 0
        nearest_resistance = min([h for h in all_highs if h > price], default=max(all_highs)) if all_highs else 0
        strongest_resistance = max(all_highs) if all_highs else 0
        return {
            "nearest_support":round(nearest_support,2),"strongest_support":round(strongest_support,2),
            "nearest_resistance":round(nearest_resistance,2),"strongest_resistance":round(strongest_resistance,2),
            "distance_to_support":round(price-nearest_support,2) if price else 0,
            "distance_to_resistance":round(nearest_resistance-price,2) if price else 0,
            "liquidity_above":[{"price":round(h,2),"strength":2} for h in sorted(set(round(h,1) for h in all_highs[-10:]),reverse=True)[:5]],
            "liquidity_below":[{"price":round(l,2),"strength":2} for l in sorted(set(round(l,1) for l in all_lows[-10:]))[:5]],
        }

    # ─── ELLIOTT WAVE ───
    def _detect_elliott_wave(self, ohlcv_data):
        data_1h = ohlcv_data.get("1h", [])
        if len(data_1h) < 100: return {"status":"insufficient_data","waves":[]}
        highs = [d["high"] for d in data_1h]; lows = [d["low"] for d in data_1h]
        waves = []; i = 0
        while i < len(highs)-20:
            i += 10
            local_h = max(highs[max(0,i-10):i+10]); local_l = min(lows[max(0,i-10):i+10])
            hi = highs.index(local_h) if local_h in highs else i
            li = lows.index(local_l) if local_l in lows else i
            waves.append({"type":"wave_up" if hi > li else "wave_down","start":local_l if hi > li else local_h,
                          "end":local_h if hi > li else local_l,"index":hi if hi > li else li})
            if len(waves) >= 8: break
        impulse = sum(1 for w in waves if abs(w["end"]-w["start"])/w["start"] > 0.03)
        corrective = len(waves) - impulse
        direction = "impulsive_up" if impulse > corrective*1.5 else "impulsive_down" if corrective > impulse*1.5 else "corrective"
        return {
            "status":"detected" if len(waves)>=5 else "forming","waves":waves[-8:],
            "impulse_count":impulse,"corrective_count":corrective,"wave_direction":direction,
            "completion":min(impulse*12.5,100) if waves else 0,
            "description_az":"Yüksələn impuls dalğası" if direction=="impulsive_up" else "Enən impuls dalğası" if direction=="impulsive_down" else "Korrektiv hərəkət",
        }

    # ─── FIBONACCI ───
    def _compute_fibonacci_levels(self, ohlcv_data, snapshot):
        data_1h = ohlcv_data.get("1h", [])
        if len(data_1h) < 30: return {"status":"insufficient_data"}
        recent = data_1h[-50:]
        high = max(d["high"] for d in recent); low = min(d["low"] for d in recent)
        rg = high - low
        if rg <= 0: return {"status":"insufficient_range"}
        price = snapshot.get("ticker",{}).get("price",0) or recent[-1]["close"]
        levels = {}
        for lev in [0,0.236,0.382,0.5,0.618,0.786,1,1.272,1.414,1.618,2.0,2.272,2.618,3.618]:
            levels[str(lev)] = round(high - rg*lev, 2)
        ext_up = {}
        for e in [0.382,0.618,1.0,1.272,1.414,1.618,2.0,2.272,2.618,3.618]:
            ext_up[str(e)] = round(high + rg*e, 2)
        ext_down = {}
        for e in [0.382,0.618,1.0,1.272,1.414,1.618,2.0,2.272,2.618,3.618]:
            ext_down[str(e)] = round(low - rg*e, 2)
        nearest_support_fib = max(v for v in levels.values() if v < price) if any(v < price for v in levels.values()) else low
        nearest_resistance_fib = min(v for v in levels.values() if v > price) if any(v > price for v in levels.values()) else high
        return {
            "status":"calculated","high":round(high,2),"low":round(low,2),"range":round(rg,2),
            "retracement_levels":levels,"extension_up":ext_up,"extension_down":ext_down,
            "nearest_support_fib":round(nearest_support_fib,2),"nearest_resistance_fib":round(nearest_resistance_fib,2),
            "current_price_zone":"oversold_fib" if price <= low+rg*0.236 else "overbought_fib" if price >= high-rg*0.236 else "middle_fib",
            "description_az":"Qiymət Fib 0.618-ə yaxınlaşır alış zonası" if price <= low+rg*0.382 else "Qiymət Fib 0.618-dən yuxarı satış zonası" if price >= high-rg*0.382 else "Qiymət Fib orta zonasında",
        }

    # ─── STRUCTURE DETECTION ───
    def _detect_dominant_structure(self, ohlcv_data, snapshot):
        data_1h = ohlcv_data.get("1h", [])
        data_4h = ohlcv_data.get("4h", [])
        data_15m = ohlcv_data.get("15m", [])
        primary = data_4h if len(data_4h)>=50 else data_1h
        if len(primary) < 50: return {"status":"insufficient_data","type":"none"}
        highs = [d["high"] for d in primary[-60:]]; lows = [d["low"] for d in primary[-60:]]
        closes = [d["close"] for d in primary[-60:]]

        swing_highs = []; swing_lows = []
        for i in range(2, len(highs)-2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append({"price":highs[i],"index":i})
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append({"price":lows[i],"index":i})

        if len(swing_highs) < 3 or len(swing_lows) < 3:
            return {"status":"partial","type":"insufficient_swings"}

        h_prices = [s["price"] for s in swing_highs[:6]]
        l_prices = [s["price"] for s in swing_lows[:6]]
        h_slope = (h_prices[-1]-h_prices[0])/len(h_prices) if len(h_prices)>1 else 0
        l_slope = (l_prices[-1]-l_prices[0])/len(l_prices) if len(l_prices)>1 else 0

        structure_type = "neutral"
        structure_label_az = "Neytral"

        if h_slope < -0.01 and l_slope < -0.01:
            structure_type = "descending_channel"
            structure_label_az = "Enən kanal"
        elif h_slope > 0.01 and l_slope > 0.01:
            structure_type = "ascending_channel"
            structure_label_az = "Yüksələn kanal"
        elif h_slope < -0.005 and l_slope > 0.005:
            structure_type = "symmetrical_triangle"
            structure_label_az = "Simmetrik üçbucaq"
        elif abs(h_slope) < 0.005 and l_slope > 0.005:
            structure_type = "ascending_triangle"
            structure_label_az = "Yüksələn üçbucaq"
        elif h_slope < -0.005 and abs(l_slope) < 0.005:
            structure_type = "descending_triangle"
            structure_label_az = "Enən üçbucaq"
        elif len(swing_highs) >= 4 and len(swing_lows) >= 4:
            h_recent = swing_highs[-4:]; l_recent = swing_lows[-4:]
            h_bias = sum(1 for i in range(1,len(h_recent)) if h_recent[i]["price"] < h_recent[i-1]["price"])
            l_bias = sum(1 for i in range(1,len(l_recent)) if l_recent[i]["price"] < l_recent[i-1]["price"])
            if h_bias >= 3 and l_bias >= 3:
                structure_type = "descending_channel"
                structure_label_az = "Enən kanal"
            elif h_bias <= 1 and l_bias <= 1:
                structure_type = "ascending_channel"
                structure_label_az = "Yüksələn kanal"

        bull_flag = None; bear_flag = None
        for tf_check in ["15m","1h","4h"]:
            d = ohlcv_data.get(tf_check, [])
            if len(d) < 30: continue
            pole = d[:10]; flag = d[10:25]
            pole_rise = pole[-1]["close"] - pole[0]["close"]
            pole_drop = pole[0]["close"] - pole[-1]["close"]
            if len(flag) >= 5:
                flag_highs = [x["high"] for x in flag]; flag_lows = [x["low"] for x in flag]
                flag_narrow = (max(flag_highs)-min(flag_lows)) < (max(x["high"] for x in pole)-min(x["low"] for x in pole))*0.5
                if pole_rise > 0 and pole_rise/pole[0]["close"] > 0.02 and flag_narrow:
                    bull_flag = {"timeframe":tf_check,"breakout_level":max(flag_highs),"flag_low":min(flag_lows),"pole_height":pole_rise}
                if pole_drop > 0 and pole_drop/pole[0]["close"] > 0.02 and flag_narrow:
                    bear_flag = {"timeframe":tf_check,"breakdown_level":min(flag_lows),"flag_high":max(flag_highs),"pole_height":pole_drop}
            if bull_flag and bear_flag: break
        if bull_flag and not structure_type.startswith("ascending") and not structure_type.startswith("descending"):
            structure_type = "bull_flag"
            structure_label_az = "Yüksələn bayraq"
        if bear_flag and not structure_type.startswith("ascending") and not structure_type.startswith("descending"):
            structure_type = "bear_flag"
            structure_label_az = "Enən bayraq"

        ch_top = max(h_prices); ch_bottom = min(l_prices)
        price = snapshot.get("ticker",{}).get("price",0) or closes[-1]

        breakout_status = "daxilində"
        if price > ch_top * 1.01: breakout_status = "yuxarı breakout"
        elif price < ch_bottom * 0.99: breakout_status = "aşağı breakout"

        obs = 0
        for i in range(1, len(closes)):
            vol_mean = np.mean([d.get("volume",0) for d in primary[max(0,i-20):i+1]])
            if closes[i] > closes[i-1] and primary[i].get("volume",0) > vol_mean:
                obs += 1
            elif closes[i] < closes[i-1] and primary[i].get("volume",0) > vol_mean:
                obs -= 1
        accum = obs > 5
        distrib = obs < -5

        support_zone_top = round(ch_bottom * 1.01, 2) if ch_bottom else 0
        support_zone_bottom = round(ch_bottom * 0.97, 2) if ch_bottom else 0
        resistance_zone_top = round(ch_top * 1.03, 2) if ch_top else 0
        resistance_zone_bottom = round(ch_top * 0.99, 2) if ch_top else 0

        return {
            "status":"detected","type":structure_type,"label_az":structure_label_az,
            "swing_highs":swing_highs[-6:],"swing_lows":swing_lows[-6:],
            "channel_top":round(ch_top,2),"channel_bottom":round(ch_bottom,2),
            "channel_mid":round((ch_top+ch_bottom)/2,2),
            "support_zone_top":support_zone_top,"support_zone_bottom":support_zone_bottom,
            "resistance_zone_top":resistance_zone_top,"resistance_zone_bottom":resistance_zone_bottom,
            "breakout_status":breakout_status,
            "accumulation_zone":accum,"distribution_zone":distrib,
            "bull_flag":bull_flag,"bear_flag":bear_flag,
            "swing_count":len(swing_highs)+len(swing_lows),
            "description_az":f"{structure_label_az} - Qiymət kanal {breakout_status}. {'Yığım zonası müşahidə olunur.' if accum else 'Paylanma zonası müşahidə olunur.' if distrib else 'Neytral zona.'}",
        }

    # ─── CHANNEL LINES ───
    def _detect_channel(self, ohlcv_data):
        data_4h = ohlcv_data.get("4h", [])
        data_1h = ohlcv_data.get("1h", [])
        primary = data_4h if len(data_4h) >= 60 else data_1h
        if len(primary) < 50: return {"status":"insufficient_data","upper":[],"lower":[],"mid":[]}
        highs = [d["high"] for d in primary[-60:]]; lows = [d["low"] for d in primary[-60:]]

        swing_highs = []; swing_lows = []
        for i in range(2, len(highs)-2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append({"price":highs[i],"time":primary[i]["time"],"index":i})
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append({"price":lows[i],"time":primary[i]["time"],"index":i})

        if len(swing_highs) < 3 or len(swing_lows) < 3:
            return {"status":"partial","upper":[],"lower":[],"mid":[]}

        sh = swing_highs[:5]; sl = swing_lows[:5]
        x_h = np.array([s["index"] for s in sh])
        y_h = np.array([s["price"] for s in sh])
        x_l = np.array([s["index"] for s in sl])
        y_l = np.array([s["price"] for s in sl])

        try:
            h_slope, h_intercept = np.polyfit(x_h, y_h, 1)
            l_slope, l_intercept = np.polyfit(x_l, y_l, 1)
            mid_slope = (h_slope + l_slope) / 2
            mid_intercept = (h_intercept + l_intercept) / 2
        except:
            return {"status":"error","upper":[],"lower":[],"mid":[]}

        def project(slope, intercept, idx):
            return slope * idx + intercept

        up_line = [{"time":primary[i]["time"],"value":round(project(h_slope, h_intercept, i),2),
                    "index":i} for i in range(len(primary)) if 0 <= i < len(primary)]
        low_line = [{"time":primary[i]["time"],"value":round(project(l_slope, l_intercept, i),2),
                     "index":i} for i in range(len(primary)) if 0 <= i < len(primary)]
        mid_line = [{"time":primary[i]["time"],"value":round(project(mid_slope, mid_intercept, i),2),
                     "index":i} for i in range(len(primary)) if 0 <= i < len(primary)]

        return {
            "status":"calculated","upper":up_line[-40:],"lower":low_line[-40:],"mid":mid_line[-40:],
            "upper_slope":round(h_slope,6),"lower_slope":round(l_slope,6),
            "swing_highs":[{"time":primary[s["index"]]["time"],"price":s["price"],"index":s["index"]} for s in swing_highs[:6]],
            "swing_lows":[{"time":primary[s["index"]]["time"],"price":s["price"],"index":s["index"]} for s in swing_lows[:6]],
        }

    # ─── BREAKOUT ZONE ───
    def _detect_breakout_zone(self, ohlcv_data, snapshot, tf_analysis):
        h1 = ohlcv_data.get("1h", [])
        h4 = ohlcv_data.get("4h", [])
        primary = h4 if len(h4) >= 50 else h1
        if len(primary) < 40: return {"status":"insufficient_data"}
        price = snapshot.get("ticker",{}).get("price",0) or primary[-1]["close"]
        highs = [d["high"] for d in primary[-40:]]; lows = [d["low"] for d in primary[-40:]]
        res = max(highs[:20]); sup = min(lows[:20])
        zone_top = round(res*1.005,2); zone_bottom = round(sup*0.995,2)
        test_count = sum(1 for d in primary[-40:] if d["high"] >= res*0.995 and d["high"] <= res*1.005) + \
                     sum(1 for d in primary[-40:] if d["low"] <= sup*1.005 and d["low"] >= sup*0.995)
        h1_signal = tf_analysis.get("1h",{}).get("signal","WAIT")
        h4_signal = tf_analysis.get("4h",{}).get("signal","WAIT")
        is_bullish_breakout_ready = price >= zone_bottom * 0.995 and h4_signal in ("LONG","STRONG_LONG","WAIT")
        is_bearish_breakout_ready = price <= zone_top * 1.005 and h4_signal in ("SHORT","STRONG_SHORT","WAIT")
        return {
            "status":"calculated","zone_top":zone_top,"zone_bottom":zone_bottom,
            "zone_mid":round((zone_top+zone_bottom)/2,2),"test_count":test_count,
            "current_price_zone":"inside_zone" if zone_bottom <= price <= zone_top else "above_zone" if price > zone_top else "below_zone",
            "bullish_breakout_ready":is_bullish_breakout_ready,"bearish_breakout_ready":is_bearish_breakout_ready,
            "bullish_breakout_conditions":[
                f"1H şamı ${zone_top} üzərində bağlanmalı",
                "Həcm 1.5x ortalamadan yuxarı olmalı",
                "OI artımı müşahidə olunmalı",
                "Retest uğurlu olmalı (geridönüb zone top-u test etməli)",
            ],
            "bearish_breakout_conditions":[
                f"1H şamı ${zone_bottom} altında bağlanmalı",
                "Satış həcmi 1.5x ortalamadan yuxarı",
                "OI artımı müşahidə olunmalı",
                "Retest uğurlu olmalı (geridönüb zone bottom-u test etməli)",
            ],
            "description_az":f"Breakout zonası ${zone_bottom}-${zone_top}. {test_count} dəfə test edilib. {'Bullish breakout hazırdır.' if is_bullish_breakout_ready else ''} {'Bearish breakout hazırdır.' if is_bearish_breakout_ready else ''}",
        }

    def _compute_trade_plan(self, scores, triggers, snapshot, tf_analysis, fibonacci, target_hierarchy, patterns):
        confidence = scores.get("signal_confidence", 0)
        price = snapshot.get("ticker", {}).get("price", 0) or 155
        long_prob = scores.get("long_probability", 50)
        short_prob = scores.get("short_probability", 50)
        direction = "LONG" if long_prob >= short_prob else "SHORT"

        if confidence < 70:
            return {
                "status": "gözləmə",
                "status_az": "Təsdiq gözlənilir — inam yetərsiz",
                "direction": direction,
                "confidence": confidence,
                "trade_ready": False,
                "message_az": f"İnam səviyyəsi {confidence}% — trade plan üçün minimum 70% tələb olunur. Hazırda yalnız trigger səviyyələrini izləyin.",
                "long_trigger": triggers.get("long_trigger_price", 0),
                "short_trigger": triggers.get("short_trigger_price", 0),
                "bullish_invalidation": triggers.get("bullish_invalidation", 0),
                "bearish_invalidation": triggers.get("bearish_invalidation", 0),
            }

        entry_price = price
        fib_up = fibonacci.get("extension_up", {}) if isinstance(fibonacci.get("extension_up"), dict) else {}
        fib_down = fibonacci.get("extension_down", {}) if isinstance(fibonacci.get("extension_down"), dict) else {}
        atr = tf_analysis.get("1h", {}).get("volatility", 0.02) or 0.02

        if direction == "LONG":
            sl_raw = triggers.get("bullish_invalidation", price * 0.97)
            sl = round(sl_raw, 2)
            tp1 = round(price * (1 + atr * 1.5), 2)
            tp2 = round(price * (1 + atr * 3.0), 2)
            tp3 = round(price * (1 + atr * 5.0), 2)
            tp4 = round(price * (1 + atr * 7.5), 2)
            tp5 = round(price * (1 + atr * 10.0), 2)
            if fib_up.get("1.272"): tp1 = round(fib_up["1.272"], 2)
            if fib_up.get("1.618"): tp2 = round(fib_up["1.618"], 2)
            if fib_up.get("2.618"): tp3 = round(fib_up["2.618"], 2)
            if fib_up.get("3.618"): tp4 = round(fib_up["3.618"], 2)
            risk = abs(entry_price - sl)
            entry_zone_min = round(price * 0.995, 2)
            entry_zone_max = round(price * 1.005, 2)
        else:
            sl_raw = triggers.get("bearish_invalidation", price * 1.03)
            sl = round(sl_raw, 2)
            tp1 = round(price * (1 - atr * 1.5), 2)
            tp2 = round(price * (1 - atr * 3.0), 2)
            tp3 = round(price * (1 - atr * 5.0), 2)
            tp4 = round(price * (1 - atr * 7.5), 2)
            tp5 = round(price * (1 - atr * 10.0), 2)
            if fib_down.get("1.272"): tp1 = round(fib_down["1.272"], 2)
            if fib_down.get("1.618"): tp2 = round(fib_down["1.618"], 2)
            if fib_down.get("2.618"): tp3 = round(fib_down["2.618"], 2)
            if fib_down.get("3.618"): tp4 = round(fib_down["3.618"], 2)
            risk = abs(entry_price - sl)
            entry_zone_min = round(price * 0.995, 2)
            entry_zone_max = round(price * 1.005, 2)

        rr1 = round(abs(tp1 - entry_price) / risk, 2) if risk > 0 else 0
        rr2 = round(abs(tp2 - entry_price) / risk, 2) if risk > 0 else 0
        rr3 = round(abs(tp3 - entry_price) / risk, 2) if risk > 0 else 0
        rr4 = round(abs(tp4 - entry_price) / risk, 2) if risk > 0 else 0
        rr5 = round(abs(tp5 - entry_price) / risk, 2) if risk > 0 else 0

        hold_time = "4-8 saat"
        if tf_analysis.get("4h", {}).get("signal", "") in ("STRONG_LONG", "STRONG_SHORT"):
            hold_time = "8-24 saat"
        elif tf_analysis.get("1d", {}).get("signal", "") in ("STRONG_LONG", "STRONG_SHORT"):
            hold_time = "24-72 saat"

        targets = [
            {"level": "TP1", "price": tp1, "risk_reward": rr1, "probability": 75, "source": "Fibonacci 1.272" if fib_up.get("1.272") and direction == "LONG" else "ATR based"},
            {"level": "TP2", "price": tp2, "risk_reward": rr2, "probability": 60, "source": "Fibonacci 1.618" if fib_up.get("1.618") and direction == "LONG" else "ATR based"},
            {"level": "TP3", "price": tp3, "risk_reward": rr3, "probability": 40, "source": "Fibonacci 2.618" if fib_up.get("2.618") and direction == "LONG" else "ATR based"},
            {"level": "TP4", "price": tp4, "risk_reward": rr4, "probability": 25, "source": "Extension"},
            {"level": "TP5", "price": tp5, "risk_reward": rr5, "probability": 15, "source": "Maximum extension"},
        ]

        return {
            "status": "hazırdır",
            "status_az": "Trade plan hazırdır",
            "trade_ready": True,
            "direction": direction,
            "direction_az": "ALIŞ" if direction == "LONG" else "SATIŞ",
            "confidence": confidence,
            "entry_zone": {
                "min": entry_zone_min,
                "max": entry_zone_max,
                "mid": round(price, 2),
            },
            "stop_loss": sl,
            "take_profits": targets,
            "risk_reward": rr3,
            "max_acceptable_entry": entry_zone_max,
            "invalidation": sl,
            "expected_holding_time": hold_time,
            "position_sizing_hint": f"Risk {round(risk/entry_price*100, 1)}%, 1% capital riski üçün {round(0.01/risk*entry_price, 2)} vahid",
            "message_az": f"{direction} istiqamətində trade plan hazırdır. Giriş zonası: ${entry_zone_min}-${entry_zone_max}, SL: ${sl}, TP1: ${tp1} (R:{rr1})",
            "pattern_based": any(p.get("probability", 0) >= 60 for p in (patterns or [])),
        }

    # ─── SCENARIO PATHS ───
    def _compute_scenario_paths(self, tf_analysis, scores, triggers, snapshot, ohlcv_data, fibonacci, detected_structure):
        price = snapshot.get("ticker",{}).get("price",0) or 155
        h4_trend = tf_analysis.get("4h",{}).get("trend","neutral")
        h1_trend = tf_analysis.get("1h",{}).get("trend","neutral")
        long_prob = scores.get("long_probability",50)
        short_prob = scores.get("short_probability",50)
        signal_conf = scores.get("signal_confidence",0)
        fib = fibonacci
        fib_up = fib.get("extension_up",{}) if isinstance(fib.get("extension_up"), dict) else {}
        fib_down = fib.get("extension_down",{}) if isinstance(fib.get("extension_down"), dict) else {}
        lt_price = triggers.get("long_trigger_price",0)
        st_price = triggers.get("short_trigger_price",0)
        inval_bull = triggers.get("bullish_invalidation",0)
        inval_bear = triggers.get("bearish_invalidation",0)
        active_tf_analysis = next(iter(tf_analysis.values()), {})
        volatility = float(active_tf_analysis.get("volatility", 0.015) or 0.015)
        volatility = min(max(volatility, 0.008), 0.035)
        projected_move = price * volatility
        max_projection_distance = price * 0.15

        def bounded_projection(value):
            return round(
                min(max(value, price - max_projection_distance), price + max_projection_distance),
                2,
            )

        fib_1_272_up = fib_up.get("1.272", price*1.02) if (isinstance(fib_up, dict) and "1.272" in fib_up) else price*1.02
        fib_1_618_up = fib_up.get("1.618", price*1.04) if (isinstance(fib_up, dict) and "1.618" in fib_up) else price*1.04
        fib_2_618_up = fib_up.get("2.618", price*1.08) if (isinstance(fib_up, dict) and "2.618" in fib_up) else price*1.08
        fib_1_272_dn = fib_down.get("1.272", price*0.98) if (isinstance(fib_down, dict) and "1.272" in fib_down) else price*0.98
        fib_1_618_dn = fib_down.get("1.618", price*0.96) if (isinstance(fib_down, dict) and "1.618" in fib_down) else price*0.96
        fib_2_618_dn = fib_down.get("2.618", price*0.92) if (isinstance(fib_down, dict) and "2.618" in fib_down) else price*0.92

        def path_points(start_price, direction):
            pts = [{"time_offset": 0, "price": start_price, "label": "Başlanğıc", "phase": "start", "probability": 100, "reason": "Cari qiymət"}]
            if direction == "up":
                b = bounded_projection(max(lt_price or start_price * 1.01, start_price + projected_move * 0.35))
                r = bounded_projection(max(start_price, b - projected_move * 0.45))
                i1 = bounded_projection(b + projected_move * 1.25)
                pb = bounded_projection(i1 - projected_move * 0.55)
                t1 = bounded_projection(b + projected_move * 2.0)
                t2 = bounded_projection(b + projected_move * 3.25)
                ext = bounded_projection(b + projected_move * 4.5)
                pts.append({"time_offset": 1, "price": b, "label": "Trigger/Breakout", "phase": "trigger", "probability": 75, "reason": f"Qiymət ${b} üzərində bağlanarsa"})
                pts.append({"time_offset": 2, "price": round((b+r)/2, 2), "label": "Retest", "phase": "retest", "probability": 68, "reason": "Breakout sonrası geri dönüş testi"})
                pts.append({"time_offset": 3, "price": i1, "label": "İlk impuls", "phase": "impulse", "probability": 60, "reason": "Yüksələn impuls 1.272 Fib"})
                pts.append({"time_offset": 4, "price": pb, "label": "Geri çəkilmə", "phase": "pullback", "probability": 50, "reason": "TP1 öncəsi korreksiya"})
                pts.append({"time_offset": 5, "price": t1, "label": "Davam", "phase": "continuation", "probability": 45, "reason": "Əsas hədəfə doğru davam"})
                pts.append({"time_offset": 6, "price": round((t1+t2)/2, 2), "label": "TP1", "phase": "tp1", "probability": 40, "reason": "İlk mənfəət hədəfi Fib 1.618"})
                pts.append({"time_offset": 9, "price": t2, "label": "TP2", "phase": "tp2", "probability": 30, "reason": "İkinci mənfəət hədəfi Fib 2.618"})
                pts.append({"time_offset": 14, "price": ext, "label": "Uzadılma", "phase": "extension", "probability": 20, "reason": "Maksimum uzadılma hədəfi"})
            else:
                b = bounded_projection(min(st_price or start_price * 0.99, start_price - projected_move * 0.35))
                r = bounded_projection(min(start_price, b + projected_move * 0.45))
                i1 = bounded_projection(b - projected_move * 1.25)
                pb = bounded_projection(i1 + projected_move * 0.55)
                t1 = bounded_projection(b - projected_move * 2.0)
                t2 = bounded_projection(b - projected_move * 3.25)
                ext = bounded_projection(b - projected_move * 4.5)
                pts.append({"time_offset": 1, "price": b, "label": "Trigger/Breakdown", "phase": "trigger", "probability": 75, "reason": f"Qiymət ${b} altında bağlanarsa"})
                pts.append({"time_offset": 2, "price": round((b+r)/2, 2), "label": "Retest", "phase": "retest", "probability": 68, "reason": "Breakdown sonrası geri dönüş testi"})
                pts.append({"time_offset": 3, "price": i1, "label": "İlk impuls", "phase": "impulse", "probability": 60, "reason": "Enən impuls 1.272 Fib"})
                pts.append({"time_offset": 4, "price": pb, "label": "Geri çəkilmə", "phase": "pullback", "probability": 50, "reason": "TP1 öncəsi korreksiya"})
                pts.append({"time_offset": 5, "price": t1, "label": "Davam", "phase": "continuation", "probability": 45, "reason": "Əsas hədəfə doğru davam"})
                pts.append({"time_offset": 6, "price": round((t1+t2)/2, 2), "label": "TP1", "phase": "tp1", "probability": 40, "reason": "İlk mənfəət hədəfi"})
                pts.append({"time_offset": 9, "price": t2, "label": "TP2", "phase": "tp2", "probability": 30, "reason": "İkinci mənfəət hədəfi"})
                pts.append({"time_offset": 14, "price": ext, "label": "Uzadılma", "phase": "extension", "probability": 20, "reason": "Maksimum uzadılma"})
            return pts

        def fakeout_path(start_price, direction):
            pts = [{"time_offset":0,"price":start_price,"label":"Başlanğıc","phase":"start"}]
            if direction == "up":
                fake_high = round(lt_price or start_price*1.02, 2)
                pivot = round(start_price*0.975, 2)
                cont = round(start_price*0.95, 2)
                pts.append({"time_offset":1,"price":fake_high,"label":"Yalançı breakout","phase":"fake_breakout"})
                pts.append({"time_offset":2,"price":round((fake_high+pivot)/2,2),"label":"Dönüş","phase":"reversal"})
                pts.append({"time_offset":3,"price":pivot,"label":"Tələ","phase":"trap"})
                pts.append({"time_offset":5,"price":cont,"label":"Aşağı davam","phase":"continuation"})
            else:
                fake_low = round(st_price or start_price*0.98, 2)
                pivot = round(start_price*1.025, 2)
                cont = round(start_price*1.05, 2)
                pts.append({"time_offset":1,"price":fake_low,"label":"Yalançı breakdown","phase":"fake_breakout"})
                pts.append({"time_offset":2,"price":round((fake_low+pivot)/2,2),"label":"Dönüş","phase":"reversal"})
                pts.append({"time_offset":3,"price":pivot,"label":"Tələ","phase":"trap"})
                pts.append({"time_offset":5,"price":cont,"label":"Yuxarı davam","phase":"continuation"})
            return pts

        main_dir = "up" if long_prob >= short_prob else "down"
        main_label = "LONG" if main_dir == "up" else "SHORT"
        alt_dir = "down" if main_dir == "up" else "up"
        alt_label = "SHORT" if alt_dir == "down" else "LONG"

        main_path = path_points(price, main_dir)
        alt_path = path_points(price, alt_dir)
        fake_path = fakeout_path(price, main_dir)

        main_targets = [p for p in main_path if p["phase"] in ("tp1","tp2","extension")]
        alt_targets = [p for p in alt_path if p["phase"] in ("tp1","tp2","extension")]

        h4_sig = tf_analysis.get("4h",{}).get("signal","WAIT")
        h1_sig = tf_analysis.get("1h",{}).get("signal","WAIT")

        main_activation = f"{main_label} trigger: ${lt_price if main_dir=='up' else st_price} üzərində/qırılır + həcm təsdiqi"
        alt_activation = f"{alt_label} trigger: ${st_price if alt_dir=='down' else lt_price} altında/qırılır + həcm təsdiqi"

        main_reasons = [
            f"{'4H' if h4_sig else 'H4'} siqnalı {main_label} istiqamətində" if h4_sig in ("LONG","STRONG_LONG","SHORT","STRONG_SHORT") else "Neytral 4H bazası",
            f"1H {h1_trend} trend",
            f"Ehtimal: {max(long_prob,short_prob)}%",
        ]
        alt_reasons = [
            "Əsas ssenarinin əksi - alternativ hədəf",
            f"1H {h1_trend} trend dəyişərsə aktivləşər",
            f"Ehtimal: {min(long_prob,short_prob)}%",
        ]

        return {
            "main_scenario":{
                "direction":main_label,"direction_az":"ALIŞ" if main_label=="LONG" else "SATIŞ",
                "probability":max(long_prob,short_prob),
                "confidence":signal_conf,
                "activation_trigger":main_activation,
                "path_points":main_path,
                "targets":[{"level":f"TP{i+1}","price":t["price"]} for i,t in enumerate(main_targets)],
                "target_zones":[f"${t['price']}" for t in main_targets],
                "invalidation":f"${inval_bull if main_dir=='up' else inval_bear}",
                "expected_duration":"4-8 saat",
                "supporting_reasons":main_reasons,
                "risks":["Fakeout riski", "Həcm təsdiqi olmazsa uğursuz ola bilər", "4H trendi dəyişərsə etibarsız"],
                "description_az":f"Əsas ehtimal olunan ssenari: {main_label}. Hədəf: ${main_path[-1]['price']}",
            },
            "alternative_scenario":{
                "direction":alt_label,"direction_az":"SATIŞ" if alt_label=="SHORT" else "ALIŞ",
                "probability":min(long_prob,short_prob),
                "confidence":max(10, signal_conf-20),
                "activation_trigger":alt_activation,
                "path_points":alt_path,
                "targets":[{"level":f"TP{i+1}","price":t["price"]} for i,t in enumerate(alt_targets)],
                "target_zones":[f"${t['price']}" for t in alt_targets],
                "invalidation":f"${inval_bear if alt_dir=='down' else inval_bull}",
                "expected_duration":"6-12 saat",
                "supporting_reasons":alt_reasons,
                "risks":["Fakeout riski", "Trend güclü olduqda alternativ uğursuz ola bilər"],
                "description_az":f"Alternativ ssenari: {alt_label}. Hədəf: ${alt_path[-1]['price']}",
            },
            "fakeout_scenario":{
                "direction":f"FAKEOUT - {main_label}","direction_az":f"YALANÇI - {main_label}",
                "probability":20,
                "confidence":min(40, signal_conf-30),
                "activation_trigger":"Qiymət breakout edib geri dönərsə",
                "path_points":fake_path,
                "targets":[],
                "target_zones":[],
                "invalidation":f"${price} (başlanğıca qayıdış)",
                "expected_duration":"2-4 saat",
                "supporting_reasons":["Aşağı həcmli breakout", "OI artımı yoxdursa fakeout riski", "Double top/bottom formalaşması"],
                "risks":["Fakeout ssenarisi baş tutarsa sürətli itki"],
                "description_az":f"Yalançı breakout riski: qiymət əvvəl {main_dir.upper()} istiqamətdə çıxıb geri dönər.",
            },
        }

    # ─── TARGET HIERARCHY ───
    def _compute_target_hierarchy(self, ohlcv_data, snapshot, scenario_paths, fibonacci, sr, detected_structure, patterns=None):
        price = snapshot.get("ticker",{}).get("price",0) or 155
        fib_ret = fibonacci.get("retracement_levels",{}) if isinstance(fibonacci.get("retracement_levels"), dict) else {}
        fib_up = fibonacci.get("extension_up",{}) if isinstance(fibonacci.get("extension_up"), dict) else {}
        fib_down = fibonacci.get("extension_down",{}) if isinstance(fibonacci.get("extension_down"), dict) else {}
        sr_high = sr.get("strongest_resistance", price*1.1); sr_low = sr.get("strongest_support", price*0.9)
        main = scenario_paths.get("main_scenario",{})
        main_dir = "up" if main.get("direction") == "LONG" else "down"
        ch_top = detected_structure.get("channel_top",0)
        ch_bottom = detected_structure.get("channel_bottom",0)
        ch_mid = detected_structure.get("channel_mid",0)

        targets = []
        retrace_targets = ["0.382","0.5","0.618","0.786","1.0"]
        for k in retrace_targets:
            v = fib_ret.get(k)
            if v and ((main_dir == "up" and v > price) or (main_dir == "down" and v < price)):
                continue
            if v:
                targets.append({
                    "level":f"Fib {k}","price":round(v,2),"type":f"Retracement {k}",
                    "distance_pct":round(abs(v-price)/price*100,1) if price else 0,
                    "probability":round(max(30,60-abs(0.5-float(k))*40)),
                    "source":"Fibonacci retracement",
                    "time_estimate":"2-4 saat",
                    "invalidation":round(price*0.97 if main_dir=="up" else price*1.03,2),
                })

        if main_dir == "up":
            fib_ext_keys = ["1.272","1.618","2.0","2.618","3.618"]
            fib_vals = []
            for k in fib_ext_keys:
                v = fib_up.get(k)
                if v and v > price: fib_vals.append((k, v))
            for i, (k, v) in enumerate(fib_vals[:5]):
                targets.append({
                    "level":f"TP{i+1}","price":round(v,2),"type":f"Fib {k}",
                    "distance_pct":round((v-price)/price*100,1) if price else 0,
                    "probability":max(25, 85 - i*15),"source":"Fibonacci extension",
                    "time_estimate":"4-8 saat" if i==0 else "1-2 gün" if i<=2 else "3-7 gün",
                    "invalidation":round(price*0.97 if i==0 else price*0.95 if i<=2 else price*0.93,2),
                })
        else:
            fib_ext_keys = ["1.272","1.618","2.0","2.618","3.618"]
            fib_vals = []
            for k in fib_ext_keys:
                v = fib_down.get(k)
                if v and v < price: fib_vals.append((k, v))
            for i, (k, v) in enumerate(fib_vals[:5]):
                targets.append({
                    "level":f"TP{i+1}","price":round(v,2),"type":f"Fib {k}",
                    "distance_pct":round((price-v)/price*100,1) if price else 0,
                    "probability":max(25, 85 - i*15),"source":"Fibonacci extension",
                    "time_estimate":"4-8 saat" if i==0 else "1-2 gün" if i<=2 else "3-7 gün",
                    "invalidation":round(price*1.03 if i==0 else price*1.05 if i<=2 else price*1.07,2),
                })

        if main_dir == "up":
            sr_target = {"level":"TP-SR","price":round(sr_high,2),"type":"Müqavimət","distance_pct":round((sr_high-price)/price*100,1) if price else 0,"probability":50,"source":"Support/Resistance","time_estimate":"1-2 gün","invalidation":round(price*0.95,2)}
        else:
            sr_target = {"level":"TP-SR","price":round(sr_low,2),"type":"Dəstək","distance_pct":round((price-sr_low)/price*100,1) if price else 0,"probability":50,"source":"Support/Resistance","time_estimate":"1-2 gün","invalidation":round(price*1.05,2)}
        targets.append(sr_target)

        if ch_top and ch_bottom:
            targets.append({"level":"Kanal Top","price":round(ch_top,2),"type":"Kanal yuxarı","distance_pct":round((ch_top-price)/price*100,1) if price else 0,"probability":45,"source":"Channel","time_estimate":"1-4 saat","invalidation":round(price*0.96,2)})
            targets.append({"level":"Kanal Bottom","price":round(ch_bottom,2),"type":"Kanal aşağı","distance_pct":round((price-ch_bottom)/price*100,1) if price else 0,"probability":45,"source":"Channel","time_estimate":"1-4 saat","invalidation":round(price*1.04,2)})

        if patterns:
            for p in patterns[:3]:
                mm = p.get("measured_target", 0)
                if mm and ((main_dir == "up" and mm > price) or (main_dir == "down" and mm < price)):
                    targets.append({
                        "level": f"Pattern-{p.get('name','')[:10]}",
                        "price": round(mm, 2),
                        "type": f"Pattern measured move ({p.get('name','')})",
                        "distance_pct": round(abs(mm-price)/price*100, 1) if price else 0,
                        "probability": min(p.get("probability", 50) + 10, 90),
                        "source": "pattern measured move",
                        "time_estimate": "2-6 saat",
                        "invalidation": round(price * (0.97 if main_dir == "up" else 1.03), 2),
                    })

        targets.sort(key=lambda t: t["distance_pct"] if t["distance_pct"] else 0)

        return {
            "targets":targets,
            "primary_direction":main_dir,
            "description_az":"{} hədəflər: {}".format("Yuxarı" if main_dir=="up" else "Aşağı", ", ".join("${}({})".format(t["price"], t["type"]) for t in targets[:5])),
        }

    # ─── TIME ESTIMATES ───
    def _compute_time_estimates(self, ohlcv_data):
        h1 = ohlcv_data.get("1h", [])
        if len(h1) < 50: return {"status":"insufficient_data"}
        closes = [d["close"] for d in h1[-100:]]
        daily_volatility = np.std(closes) / np.mean(closes) if closes else 0.02
        avg_range = np.mean([d["high"]-d["low"] for d in h1[-50:]]) if len(h1)>=50 else 0.1
        atr = avg_range
        price = closes[-1] if closes else 155
        pct_per_candle = atr / price * 100 if price else 0.1
        candles_per_tp1 = max(4, int(2.0 / max(pct_per_candle, 0.05)))
        candles_per_tp2 = max(8, int(4.0 / max(pct_per_candle, 0.05)))
        candles_per_tp3 = max(16, int(8.0 / max(pct_per_candle, 0.05)))
        return {
            "status":"calculated","avg_candle_range":round(avg_range,2),"daily_volatility":round(daily_volatility,4),
            "tp1_estimate_hours":max(1, round(candles_per_tp1*1.5)),"tp2_estimate_hours":max(2, round(candles_per_tp2*1.5)),
            "tp3_estimate_hours":max(4, round(candles_per_tp3*1.5)),
            "avg_hourly_speed_pct":round(pct_per_candle,3),
            "description_az":f"TP1: ~{max(1, round(candles_per_tp1*1.5))} saat, TP2: ~{max(2, round(candles_per_tp2*1.5))} saat, TP3: ~{max(4, round(candles_per_tp3*1.5))} saat",
        }

    # ─── ACTIVATION CONDITIONS ───
    def _compute_activation_conditions(self, triggers, tf_analysis, snapshot):
        h4 = tf_analysis.get("4h",{}); h1 = tf_analysis.get("1h",{})
        price = snapshot.get("ticker",{}).get("price",0) or 155
        taker = snapshot.get("taker_buy_sell_ratio",{})
        lt = triggers.get("long_trigger_price",0); st = triggers.get("short_trigger_price",0)
        vol = h1.get("volume","normal")
        return {
            "bullish":{
                "conditions":[
                    {"name":"Qiymət səviyyəsi","check":f"1H close > ${lt}","met":price > lt if lt else False,"required":True},
                    {"name":"Həcm təsdiqi","check":"Volume > 1.5x SMA","met":vol in ("high","above_average"),"required":True},
                    {"name":"OI artımı","check":"OI breakout zamanı artır","met":False,"required":True},
                    {"name":"Taker alış","check":"Taker buy/sell > 1.0","met":taker.get("buy_sell_ratio",0) > 1.0,"required":False},
                ],
                "all_required_met":price > lt if lt else False,
                "status":"hazırdır" if (price > lt if lt else False) else "gözlənilir",
            },
            "bearish":{
                "conditions":[
                    {"name":"Qiymət səviyyəsi","check":f"1H close < ${st}","met":price < st if st else False,"required":True},
                    {"name":"Həcm təsdiqi","check":"Sell volume > 1.5x SMA","met":vol in ("high","above_average"),"required":True},
                    {"name":"OI artımı","check":"OI qırılma zamanı artır","met":False,"required":True},
                    {"name":"Taker satış","check":"Taker sell/buy > 1.0","met":taker.get("buy_sell_ratio",0) < 1.0,"required":False},
                ],
                "all_required_met":price < st if st else False,
                "status":"hazırdır" if (price < st if st else False) else "gözlənilir",
            },
        }

    def _collect_module_errors(self, ohlcv_data, tf_analysis):
        errors = {}
        for tf, v in tf_analysis.items():
            if isinstance(v, dict) and v.get("error"):
                errors[f"{tf}_data"] = v["error"]
        for tf, data in ohlcv_data.items():
            if not data:
                errors[f"{tf}_ohlcv"] = "No OHLCV data"
        return errors if errors else {}

    # ─── CONFIDENCE BREAKDOWN ───
    def _compute_confidence_breakdown(self, scores, tf_analysis, patterns, detected_structure, alignment):
        signal_conf = scores.get("signal_confidence",0)
        pattern_conf = 0
        if patterns:
            pattern_conf = min(int(np.mean([p.get("probability",50) for p in patterns])), 100)
        structure_conf = scores.get("structure_score",0)
        breakout_conf = 0
        if detected_structure.get("status") == "detected":
            breakout_conf = min(50 + len(patterns)*5, 100)
        direction_conf = max(scores.get("long_probability",0), scores.get("short_probability",0))
        target_conf = min(30 + signal_conf//2, 100)
        trend_conf = scores.get("trend_score",0)
        momentum_conf = scores.get("momentum_score",0)
        volume_conf = scores.get("volume_score",0)
        futures_conf = scores.get("futures_score",0)
        liquidity_conf = scores.get("liquidity_score",0)
        mtf_conf = alignment.get("confidence",0)
        risk_conf = scores.get("risk_score",0)
        return {
            "signal_confidence":signal_conf,
            "direction_probability":direction_conf,
            "trend_confidence":trend_conf,
            "structure_confidence":structure_conf,
            "momentum_confidence":momentum_conf,
            "volume_confidence":volume_conf,
            "futures_confidence":futures_conf,
            "liquidity_confidence":liquidity_conf,
            "pattern_confidence":pattern_conf,
            "breakout_confidence":breakout_conf,
            "target_confidence":target_conf,
            "multitimeframe_confidence":mtf_conf,
            "risk_confidence":risk_conf,
            "overall_assessment":"yüksək" if signal_conf >= 70 else "orta" if signal_conf >= 50 else "aşağı",
        }

    # ─── WHALE / SMART MONEY ANALYSIS ───
    def _compute_whale_analysis(self, snapshot):
        taker = snapshot.get("taker_buy_sell_ratio", {}) or {}
        ls = snapshot.get("long_short_ratio", {}) or {}
        ob = snapshot.get("orderbook", {}) or {}
        funding = snapshot.get("funding", {}) or {}
        oi = snapshot.get("open_interest", {}) or {}
        bid = ob.get("bids", [])
        ask = ob.get("asks", [])
        bid_vol = sum(b[1] for b in bid[:5]) if bid else 0
        ask_vol = sum(a[1] for a in ask[:5]) if ask else 0
        taker_ratio = taker.get("buy_sell_ratio", 1.0) or 1.0
        ls_ratio = ls.get("long_short_ratio", 1.0) or 1.0
        fr = funding.get("funding_rate", 0) or 0
        oi_change = oi.get("change_24h", 0) or 0
        oi_value = oi.get("open_interest", 0) or 0

        whale_bias = "neutral"
        whale_direction = "neutral"
        whale_desc = "Böyük oyunçular neytral mövqedədir."
        signals = []

        if taker_ratio > 1.2:
            signals.append(f"Taker alışları dominantdır (nisbət: {taker_ratio:.2f}) — alış təzyiqi")
            whale_bias = "bullish"; whale_direction = "bullish"
            whale_desc = "Böyük oyunçular alış tərəfdədir"
        elif taker_ratio < 0.8:
            signals.append(f"Taker satışları dominantdır (nisbət: {taker_ratio:.2f}) — satış təzyiqi")
            whale_bias = "bearish"; whale_direction = "bearish"
            whale_desc = "Böyük oyunçular satış tərəfdədir"
        else:
            signals.append(f"Taker alış/satış balanslıdır ({taker_ratio:.2f})")

        if bid_vol > ask_vol * 2 and bid_vol > 0 and ask_vol > 0:
            signals.append(f"Order book-da alış tərəfi güclüdür (bid:{bid_vol:.0f} > ask:{ask_vol:.0f})")
            if whale_bias == "neutral": whale_bias = "bullish"; whale_direction = "bullish"
        elif ask_vol > bid_vol * 2 and bid_vol > 0 and ask_vol > 0:
            signals.append(f"Order book-da satış tərəfi güclüdür (ask:{ask_vol:.0f} > bid:{bid_vol:.0f})")
            if whale_bias == "neutral": whale_bias = "bearish"; whale_direction = "bearish"
        else:
            signals.append("Order book balanslıdır")

        if ls_ratio > 1.5:
            signals.append(f"Long/Short nisbəti {ls_ratio:.1f} — bazarda alış üstünlüyü (retail long)")
            if whale_bias == "neutral": whale_bias = "bearish"
        elif ls_ratio < 0.7:
            signals.append(f"Long/Short nisbəti {ls_ratio:.1f} — bazarda satış üstünlüyü (retail short)")
            if whale_bias == "neutral": whale_bias = "bullish"

        if fr > 0.001:
            signals.append(f"Funding rate yüksək ({fr*100:.4f}%) — long tərəf bahalıdır, sıxışdırma riski")
        elif fr < -0.001:
            signals.append(f"Funding rate mənfi ({fr*100:.4f}%) — short tərəf bahalıdır, sıxışdırma riski")
        else:
            signals.append(f"Funding rate neytraldır ({fr*100:.4f}%)")

        if oi_value:
            if oi_change > 10:
                signals.append(f"OI {oi_change:.0f}% artıb — yeni pul bazara daxil olur")
            elif oi_change < -10:
                signals.append(f"OI {oi_change:.0f}% azalıb — pul bazardan çıxır")
            else:
                signals.append(f"OI dəyişməyib ({oi_change:.0f}%)")

        accum = whale_direction == "bullish" and ls_ratio > 1.3
        distrib = whale_direction == "bearish" and ls_ratio < 0.7

        return {
            "whale_bias": whale_bias,
            "whale_direction": whale_direction,
            "whale_description_az": whale_desc,
            "signals": signals,
            "taker_buy_sell_ratio": round(taker_ratio, 2),
            "long_short_ratio": round(ls_ratio, 2),
            "bid_wall_volume": round(bid_vol, 2),
            "ask_wall_volume": round(ask_vol, 2),
            "funding_rate": round(fr, 6),
            "bid_ask_imbalance": round((bid_vol - ask_vol) / max(bid_vol + ask_vol, 1), 4),
            "retail_sentiment": "həddindən artıq long" if ls_ratio > 2 else "long üstünlük" if ls_ratio > 1.2 else "balanslı" if ls_ratio > 0.8 else "short üstünlük" if ls_ratio > 0.5 else "həddindən artıq short",
            "oi_change_24h_pct": round(oi_change, 1),
            "oi_value": round(oi_value, 2),
            "accumulation_zone": accum,
            "distribution_zone": distrib,
            "whale_verdict_az": "Böyük oyunçular alır (accumulation)" if accum else "Böyük oyunçular satır (distribution)" if distrib else "Böyük oyunçular neytraldır",
        }

    # ─── TIME-BASED FORECAST ───
    def _compute_time_forecast(self, scores, triggers, snapshot, tf_analysis):
        h4 = tf_analysis.get("4h", {})
        h1 = tf_analysis.get("1h", {})
        price = snapshot.get("ticker", {}).get("price", 0) or 155
        lt = triggers.get("long_trigger_price", 0)
        st = triggers.get("short_trigger_price", 0)
        long_prob = scores.get("long_probability", 50)
        short_prob = scores.get("short_probability", 50)
        signal_conf = scores.get("signal_confidence", 0)
        vol = h1.get("volatility", 0.02) or 0.02
        h1_range = price * vol

        def period_forecast(hours, base_prob, volatility_decay):
            bull = max(min(int(base_prob * (1 - hours * 0.05)), 95), 5)
            bear = 100 - bull
            expected_range = round(price * volatility_decay * np.sqrt(hours) * 0.01, 2)
            lower = round(price - expected_range, 2)
            upper = round(price + expected_range, 2)
            direction = "LONG" if bull >= bear else "SHORT"
            trig = lt if direction == "LONG" else st
            inv = triggers.get("bullish_invalidation" if direction == "LONG" else "bearish_invalidation", 0)
            risk_desc = "Triggerə yaxınlaşma" if trig and abs(price - trig) / trig < 0.03 else "Gözlənilən breakout" if signal_conf >= 60 else "Qeyri-müəyyən hərəkət"
            return {
                "period": f"{hours} saat",
                "direction": direction,
                "direction_az": "ALIŞ" if direction == "LONG" else "SATIŞ",
                "bullish_prob": bull,
                "bearish_prob": bear,
                "expected_range_low": lower,
                "expected_range_high": upper,
                "expected_range_pct": round(expected_range / price * 100, 1),
                "volatility": round(vol * 100, 2),
                "trigger": trig,
                "invalidation": inv,
                "main_risk": risk_desc,
                "confidence": max(min(signal_conf - hours * 5, 90), 5),
            }

        forecasts = [period_forecast(h, long_prob if long_prob >= short_prob else short_prob, vol * 100) for h in [1, 2, 4, 12]]

        return {
            "forecasts": forecasts,
            "best_period": "1h" if signal_conf >= 70 else "2h" if signal_conf >= 50 else "4h",
            "description_az": f"Ən güclü ehtimal {forecasts[0]['period']} vaxtında. {max(forecasts[0]['bullish_prob'], forecasts[0]['bearish_prob'])}% ehtimal.",
            "overall_bias": "bullish" if long_prob > 55 else "bearish" if short_prob > 55 else "neutral",
            "average_volatility": round(vol * 100, 2),
        }

    # ─── EXPLANATION ───
    def _generate_explanation(self, tf_analysis, alignment, scores, triggers, detected_structure, breakout_zone):
        h4 = tf_analysis.get("4h",{}); h1 = tf_analysis.get("1h",{}); d1 = tf_analysis.get("1d",{})
        h4_trend = h4.get("trend","məlum deyil"); h1_trend = h1.get("trend","məlum deyil"); d1_trend = d1.get("trend","məlum deyil")
        lines = [f"SKHYUSDT analizi:"]
        struct_label = detected_structure.get("label_az","")
        if struct_label: lines.append(f"Aşkarlanan struktur: {struct_label}.")
        if d1_trend != "neutral": lines.append(f"Günlük trend {d1_trend}-dir.")
        if h4_trend != "neutral": lines.append(f"4H {h4_trend} struktur.")
        h1_dir = "yüksələn" if h1_trend=="bullish" else "enən" if h1_trend=="bearish" else "neytral"
        lines.append(f"1H {h1_dir}.")
        bz = breakout_zone
        if bz.get("status")=="calculated":
            lines.append(f"Breakout zonası: ${bz['zone_bottom']}-${bz['zone_top']}, {bz['test_count']} dəfə test edilib.")
        lt = triggers.get("long_trigger_price",0); st = triggers.get("short_trigger_price",0)
        if lt and alignment.get("primary_direction") != "short":
            lines.append(f"${lt} üzərində 1H bağlanış və artan həcm gəlmədən ALIŞ təsdiqlənmir.")
        if st and alignment.get("primary_direction") != "long":
            lines.append(f"${st} aşağı qırılarsa və OI artarsa SATIŞ ssenarisi güclənəcək.")
        if scores.get("status")=="WAIT": lines.append("Gözləmə tövsiyə olunur - təsdiq gözlənilir.")
        elif scores.get("status")=="WATCHLIST": lines.append("İzləmə siyahısı - trigger yaxınlaşdıqda dəyərləndir.")
        if alignment.get("conflicts"): lines.append(f"Ziddiyyət: {'; '.join(alignment['conflicts'])}")
        return "\n".join(lines) if lines else "Məlumat yoxdur."

    # ─── SCENARIOS ENDPOINT ───
    async def get_scenarios(self, timeframe: str | None = None) -> dict:
        analysis = await self.get_full_analysis(timeframe)
        return {
            "main_scenario": analysis.get("scenario_paths",{}).get("main_scenario",{}),
            "alternative_scenario": analysis.get("scenario_paths",{}).get("alternative_scenario",{}),
            "risk_fakeout_scenario": analysis.get("scenario_paths",{}).get("fakeout_scenario",{}),
            "target_hierarchy": analysis.get("target_hierarchy",{}),
            "time_estimates": analysis.get("time_estimates",{}),
            "activation_conditions": analysis.get("activation_conditions",{}),
            "confidence_breakdown": analysis.get("confidence_breakdown",{}),
        }


skhy_analysis = SkhyAnalysisEngine()
