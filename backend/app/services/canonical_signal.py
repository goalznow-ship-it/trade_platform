"""
Canonical Signal Engine

Unified signal format consumed by all frontend pages:
- AI Terminal
- Dashboard
- Scanner
- Futures Intel
- AI Signals

Ensures the same symbol+timeframe produces identical data everywhere.
"""
from datetime import datetime, timezone
from typing import Optional


class CanonicalSignalEngine:

    def build(self,
              symbol: str,
              exchange: str = "Binance",
              timeframe: str = "1h",
              signal_data: Optional[dict] = None,
              scoring_data: Optional[dict] = None,
              pattern_data: Optional[dict] = None,
              mtf_data: Optional[dict] = None,
              futures_data: Optional[dict] = None,
              risk_data: Optional[dict] = None) -> dict:
        now_iso = datetime.now(timezone.utc).isoformat()

        direction = signal_data.get("direction", "neutral") if signal_data else "neutral"
        confidence = signal_data.get("confidence", 0) if signal_data else 0
        current_price = signal_data.get("current_price", 0) if signal_data else 0

        entry_zone = (signal_data or {}).get("entry_zone", {})
        stop_loss = (signal_data or {}).get("stop_loss")
        tp1 = (signal_data or {}).get("take_profit_1")
        tp2 = (signal_data or {}).get("take_profit_2")
        tp3 = (signal_data or {}).get("take_profit_3")
        rr1 = (signal_data or {}).get("risk_reward_1", 0)

        inst_score = (signal_data or {}).get("institutional_score", {}) or (scoring_data or {})
        scores = inst_score.get("scores", {})
        details = inst_score.get("details", {})

        # Pattern info
        chart_patterns = (pattern_data or {}).get("components", {}).get("chart_patterns", {})
        forming_patterns = chart_patterns.get("forming_patterns", [])
        all_patterns = chart_patterns.get("patterns", [])
        active_pattern = forming_patterns[0] if forming_patterns else (all_patterns[0] if all_patterns else None)

        projection = (pattern_data or {}).get("projection", {})

        # Multi-timeframe alignment
        mtf_alignment = (mtf_data or {}).get("alignment", {})
        mtf_aggregated = (mtf_data or {}).get("aggregated", {})
        major_aligned = mtf_alignment.get("major_aligned", False) if mtf_alignment else False

        # Futures data
        funding_rate = (futures_data or {}).get("funding_rate", 0)
        oi = (futures_data or {}).get("open_interest", 0)
        ls_ratio = (futures_data or {}).get("long_short_ratio")
        funding_pressure = (futures_data or {}).get("funding_pressure", "neutral")

        # Factor scores normalized to -100/+100
        normalized_scores = {}
        weights = inst_score.get("weights", {})
        for key in ["trend", "momentum", "volume", "liquidity", "smc", "risk"]:
            raw = scores.get(key, 0)
            weight = weights.get(key, 20 if key in ("trend", "smc") else 15)
            normalized_scores[key] = round(raw / max(weight, 1) * 100, 1) if raw != 0 else 0

        # Extended factors
        normalized_scores["volatility"] = round(
            max(-100, min(100, 50 - ((details.get("atr", 0) or 0) / max(current_price, 1)) * 5000)), 1
        ) if details.get("atr") and current_price else 0
        normalized_scores["structure"] = round(abs(normalized_scores.get("smc", 0)), 1)
        normalized_scores["funding"] = round(
            max(-100, min(100, -(funding_rate or 0) * 10000)), 1
        ) if funding_rate else 0
        normalized_scores["open_interest"] = round(
            max(-100, min(100, min(100, (futures_data or {}).get("oi_change_percent", 0) * 5))), 1
        ) if futures_data else 0
        normalized_scores["liquidation"] = round(
            normalized_scores.get("risk", 0) * -1 if normalized_scores.get("risk", 0) < 0 else normalized_scores.get("risk", 0), 1
        )
        normalized_scores["pattern_quality"] = round(
            active_pattern.get("confidence", 0) * 2 - 100 if active_pattern else 0, 1
        ) if active_pattern else 0
        normalized_scores["breakout"] = 100 if active_pattern and active_pattern.get("breakout_confirm") else (
            -50 if active_pattern and not active_pattern.get("breakout_confirm") else 0
        )
        normalized_scores["retest"] = 0
        normalized_scores["timeframe_alignment"] = round(
            max(-100, min(100, (mtf_aggregated.get("timeframe_count", 0) if mtf_aggregated else 0) * 20 - 20)), 1
        ) if mtf_aggregated else 0

        # Data freshness check
        data_sources = ["Binance"]
        if exchange and exchange != "Binance":
            data_sources.append(exchange)

        # Determine long/short scores
        long_score = max(0, min(100, 50 + (confidence if direction == "long" else -confidence) * 0.5))
        short_score = 100 - long_score

        # Risk profile
        risk_level = inst_score.get("risk_level", "medium")
        if risk_data:
            validation = risk_data.get("validation", {}) if isinstance(risk_data, dict) else {}
        else:
            validation = (signal_data or {}).get("validation", {})

        # Support/resistance from trend lines or pattern
        support = None
        resistance = None
        if active_pattern:
            support = active_pattern.get("consolidation_low") or active_pattern.get("support") or active_pattern.get("neckline")
            resistance = active_pattern.get("consolidation_high") or active_pattern.get("resistance")
        if not support:
            trend_lines = (pattern_data or {}).get("components", {}).get("trend_lines", {})
            closest_support = trend_lines.get("closest_support", {})
            if closest_support:
                support = closest_support.get("end_price")
        if not resistance:
            trend_lines = (pattern_data or {}).get("components", {}).get("trend_lines", {})
            closest_resistance = trend_lines.get("closest_resistance", {})
            if closest_resistance:
                resistance = closest_resistance.get("end_price")

        # Volume info
        volume_info = {
            "current": details.get("volume_ratio", None),
            "status": "high" if (details.get("volume_ratio") or 0) > 1.5 else
                      "low" if (details.get("volume_ratio") or 0) < 0.5 else "normal",
        }

        # Reasons with context
        reasons = (signal_data or {}).get("reasons", [])
        risks = []
        if risk_level == "high":
            risks.append("High risk level - caution advised")
        if confidence < 70:
            risks.append("Low confidence signal")
        if not major_aligned:
            risks.append("Major timeframes not aligned")
        risks.extend((signal_data or {}).get("execution", {}).get("rejection_reasons", []))

        classification = "institutional_grade" if confidence >= 95 else \
                         "excellent" if confidence >= 90 else \
                         "very_strong" if confidence >= 85 else \
                         "strong" if confidence >= 80 else \
                         "watchlist" if confidence >= 70 else "reject"

        signal_status = "active" if confidence >= 70 and direction != "neutral" else \
                        "watchlist" if confidence >= 50 else "reject"

        return {
            "symbol": symbol,
            "exchange": exchange,
            "timeframe": timeframe,
            "snapshot_timestamp": now_iso,
            "live_price": round(current_price, 4) if current_price else None,
            "direction": direction,
            "status": signal_status,
            "classification": classification,
            "confidence": round(confidence, 1),
            "long_score": round(long_score, 1),
            "short_score": round(short_score, 1),
            "pattern": {
                "name": active_pattern.get("name") if active_pattern else None,
                "type": active_pattern.get("type") if active_pattern else None,
                "status": "forming" if active_pattern and active_pattern.get("is_forming") else
                          "confirmed" if active_pattern else None,
                "confidence": active_pattern.get("confidence") if active_pattern else None,
                "breakout_confirmed": active_pattern.get("breakout_confirm", False) if active_pattern else False,
            },
            "projected_path": projection.get("expected_path", []),
            "entry_trigger": projection.get("entry_trigger", "") or
                             (active_pattern.get("entry_trigger") if active_pattern else ""),
            "stop_loss": round(projection.get("stop_loss", stop_loss or 0), 4) if (projection.get("stop_loss") or stop_loss) else None,
            "tp1": round(projection.get("take_profit_1", tp1 or 0), 4) if (projection.get("take_profit_1") or tp1) else None,
            "tp2": round(projection.get("take_profit_2", tp2 or 0), 4) if (projection.get("take_profit_2") or tp2) else None,
            "tp3": round(projection.get("take_profit_3", tp3 or 0), 4) if (projection.get("take_profit_3") or tp3) else None,
            "risk_reward": round(rr1, 1),
            "reasons": reasons[:5],
            "risks": risks[:3],
            "factor_scores": normalized_scores,
            "support": round(support, 4) if support else None,
            "resistance": round(resistance, 4) if resistance else None,
            "funding": {
                "rate": round(funding_rate, 6) if funding_rate else 0,
                "pressure": funding_pressure,
            },
            "open_interest": {
                "value": round(oi, 2) if oi else 0,
                "change": futures_data.get("oi_change_percent", 0) if futures_data else 0,
            },
            "volume": volume_info,
            "indicators": {
                "rsi": details.get("rsi"),
                "macd_histogram": details.get("macd_histogram"),
                "adx": details.get("adx"),
            },
            "data_sources": data_sources,
            "data_freshness": "live",
            "last_updated": now_iso,
            "multi_timeframe_alignment": {
                "major_aligned": major_aligned,
                "aligned_tfs": mtf_aggregated.get("timeframe_count", 0) if mtf_aggregated else 0,
                "aggregate_direction": mtf_aggregated.get("direction", "neutral") if mtf_aggregated else "neutral",
            },
        }


canonical_signal = CanonicalSignalEngine()
