from datetime import datetime, timedelta
from typing import Optional
from app.services.ai_analysis import ai_engine
from app.services.market import market_service
from app.services.indicators import indicator_service
from app.services.signals import signal_service


class EnterpriseSignalEngine:
    async def analyze_market_structure(self, data: list) -> dict:
        if len(data) < 30:
            return {"structure": "insufficient_data", "bos": [], "choch": [], "liquidity_zones": []}

        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]
        closes = [d["close"] for d in data]

        # Higher High / Lower Low detection
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        hh = recent_highs[-1] > max(recent_highs[:-1]) if len(recent_highs) > 1 else False
        ll = recent_lows[-1] < min(recent_lows[:-1]) if len(recent_lows) > 1 else False
        lh = recent_highs[-1] < max(recent_highs[:-1]) if len(recent_highs) > 1 else False
        hl = recent_lows[-1] > min(recent_lows[:-1]) if len(recent_lows) > 1 else False

        if hh and hl:
            trend = "uptrend"
        elif ll and lh:
            trend = "downtrend"
        else:
            trend = "ranging"

        # Break of Structure (BOS) detection
        bos_events = []
        for i in range(5, len(data) - 1):
            if highs[i] > max(highs[max(0, i - 5):i]) and closes[i] > closes[i - 1]:
                bos_events.append({"index": i, "type": "bullish_bos", "price": highs[i], "time": data[i].get("time", 0)})
            if lows[i] < min(lows[max(0, i - 5):i]) and closes[i] < closes[i - 1]:
                bos_events.append({"index": i, "type": "bearish_bos", "price": lows[i], "time": data[i].get("time", 0)})

        # Change of Character (CHoCH) detection
        choch_events = []
        for i in range(10, len(data) - 1):
            prev_highs = highs[i - 5:i]
            prev_lows = lows[i - 5:i]
            if highs[i] > max(prev_highs) and lows[i] > min(prev_lows) and closes[i] < closes[i - 1]:
                choch_events.append({"index": i, "type": "bearish_choch", "price": highs[i], "time": data[i].get("time", 0)})
            if lows[i] < min(prev_lows) and highs[i] < max(prev_highs) and closes[i] > closes[i - 1]:
                choch_events.append({"index": i, "type": "bullish_choch", "price": lows[i], "time": data[i].get("time", 0)})

        # Liquidity zones
        liquidity_zones = []
        for i in range(10, len(data) - 1):
            if highs[i] > max(highs[i - 5:i + 5]) and closes[i] < highs[i]:
                liquidity_zones.append({"type": "sell_side", "price": round(highs[i], 2), "strength": "strong" if highs[i] > max(highs[max(0, i - 10):i + 10]) else "moderate"})
            if lows[i] < min(lows[i - 5:i + 5]) and closes[i] > lows[i]:
                liquidity_zones.append({"type": "buy_side", "price": round(lows[i], 2), "strength": "strong" if lows[i] < min(lows[max(0, i - 10):i + 10]) else "moderate"})

        # Order blocks
        order_blocks = []
        for i in range(10, len(data) - 1):
            candle = data[i]
            prev = data[i - 1]
            if candle["close"] > candle["open"] and prev["close"] < prev["open"]:
                order_blocks.append({"type": "bullish", "price_low": round(min(candle["open"], prev["close"]), 2), "price_high": round(max(candle["open"], prev["close"]), 2)})
            if candle["close"] < candle["open"] and prev["close"] > prev["open"]:
                order_blocks.append({"type": "bearish", "price_low": round(min(candle["close"], prev["open"]), 2), "price_high": round(max(candle["close"], prev["open"]), 2)})

        # Fair Value Gap detection
        fvg_zones = []
        for i in range(2, len(data)):
            if data[i]["low"] > data[i - 2]["high"]:
                fvg_zones.append({"type": "bullish_fvg", "low": round(data[i - 2]["high"], 2), "high": round(data[i]["low"], 2)})
            if data[i]["high"] < data[i - 2]["low"]:
                fvg_zones.append({"type": "bearish_fvg", "low": round(data[i]["high"], 2), "high": round(data[i - 2]["low"], 2)})

        return {
            "trend": trend,
            "higher_high": hh,
            "lower_low": ll,
            "lower_high": lh,
            "higher_low": hl,
            "bos_events": bos_events[-5:],
            "choch_events": choch_events[-3:],
            "liquidity_zones": liquidity_zones[-5:],
            "order_blocks": order_blocks[-5:],
            "fair_value_gaps": fvg_zones[-5:],
            "current_price": round(closes[-1], 2) if closes else 0,
        }

    async def analyze_futures(self, symbol: str) -> dict:
        try:
            from app.services.multi_exchange import exchange_registry
            ex = exchange_registry.get_exchange("binance")
            funding = await ex.fetch_funding_rate(symbol.replace("/", "")) if hasattr(ex, "fetch_funding_rate") else None
            oi = await ex.fetch_open_interest(symbol.replace("/", "")) if hasattr(ex, "fetch_open_interest") else None
        except Exception:
            funding = None
            oi = None

        funding_rate = funding["funding_rate"] if funding else 0
        oi_value = oi["open_interest"] if oi else 0

        # Funding pressure assessment
        if funding_rate > 0.01:
            funding_pressure = "bearish"
        elif funding_rate < -0.01:
            funding_pressure = "bullish"
        else:
            funding_pressure = "neutral"

        # Liquidation zones estimation (simplified)
        data = await market_service.get_ohlcv(symbol, "binance", "1h", 100)
        if data:
            recent_lows = min(d["low"] for d in data[-20:])
            recent_highs = max(d["high"] for d in data[-20:])
            current = data[-1]["close"]
            liq_long_zone = round(current * 0.95, 2)
            liq_short_zone = round(current * 1.05, 2)
        else:
            liq_long_zone = 0
            liq_short_zone = 0

        return {
            "funding_rate": round(funding_rate, 6),
            "funding_rate_8h": round(funding_rate * 3, 6),
            "funding_pressure": funding_pressure,
            "open_interest": round(oi_value, 2),
            "liquidation_zones": {
                "long_liquidation_zone": liq_long_zone,
                "short_liquidation_zone": liq_short_zone,
            },
        }

    async def generate_enterprise_signal(self, symbol: str, timeframe: str = "1h", exchange: str = "binance") -> dict:
        data = await market_service.get_ohlcv(symbol, exchange, timeframe, 200)
        if not data or len(data) < 50:
            return {"symbol": symbol, "error": "Insufficient data"}

        analysis = await ai_engine.analyze(symbol, data, timeframe)
        structure = await self.analyze_market_structure(data)
        futures = await self.analyze_futures(symbol)
        indicators = await self._compute_enhanced_indicators(data)
        signals_result = await signal_service.generate_signals(symbol, data, timeframe)

        current_price = data[-1]["close"]
        direction = analysis.get("prediction", "neutral")
        conf = analysis.get("confidence", 0)
        risk = analysis.get("risk_level", "medium")
        scores = analysis.get("scores", {})

        # Build reasons
        reasons = []
        if structure["trend"] == "uptrend":
            reasons.append(f"{timeframe} bullish structure detected")
        elif structure["trend"] == "downtrend":
            reasons.append(f"{timeframe} bearish structure detected")

        for key, val in scores.items():
            if abs(val) > 0.3:
                label = key.replace("_", " ").title()
                reasons.append(f"{label} {'favorable' if val > 0 else 'unfavorable'} ({'+' if val > 0 else ''}{val * 100:.0f}%)")

        if futures["funding_pressure"] != "neutral":
            reasons.append(f"Funding {futures['funding_pressure']} ({futures['funding_rate']:.6f}%)")

        ema_trend = indicators.get("ema_trend", "neutral")
        if ema_trend != "neutral":
            reasons.append(f"EMA alignment: {ema_trend}")

        # Entry / SL / TP
        sl_pct = 0.03 if risk == "low" else 0.05 if risk == "medium" else 0.08
        entry = current_price
        tp1_mult = 1.03 if direction == "long" else 0.97
        tp2_mult = 1.06 if direction == "long" else 0.94
        tp3_mult = 1.10 if direction == "long" else 0.90
        sl_mult = 1 - sl_pct if direction == "long" else 1 + sl_pct

        rr = abs((entry * tp1_mult - entry) / (entry * sl_mult - entry)) if entry * sl_mult != entry else 1.0

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": round(current_price, 2),
            "direction": direction,
            "confidence": round(conf, 1),
            "risk_level": risk,
            "entry_price": round(entry, 2),
            "entry_zone": {"low": round(entry * 0.995, 2), "high": round(entry * 1.005, 2)},
            "stop_loss": round(entry * sl_mult, 2),
            "take_profit_1": round(entry * tp1_mult, 2),
            "take_profit_2": round(entry * tp2_mult, 2),
            "take_profit_3": round(entry * tp3_mult, 2),
            "risk_reward": round(rr, 2),
            "long_probability": round(analysis.get("long_probability", 50), 1),
            "short_probability": round(analysis.get("short_probability", 50), 1),
            "reasons": reasons[:6],
            "market_structure": {
                "trend": structure["trend"],
                "bos_count": len(structure["bos_events"]),
                "choch_count": len(structure["choch_events"]),
                "liquidity_zones": structure["liquidity_zones"][:3],
                "order_blocks": structure["order_blocks"][:3],
            },
            "futures": {
                "funding_rate": futures["funding_rate"],
                "funding_pressure": futures["funding_pressure"],
                "liquidation_zones": futures["liquidation_zones"],
            },
            "indicators": {
                "rsi": indicators.get("rsi"),
                "macd": indicators.get("macd"),
                "adx": indicators.get("adx"),
                "ema_trend": ema_trend,
                "bb_position": indicators.get("bb_position"),
            },
        }

    async def _compute_enhanced_indicators(self, data: list) -> dict:
        try:
            rsi_result = indicator_service.rsi(data)
            macd_result = indicator_service.macd(data)
            bollinger = indicator_service.bollinger(data)
            ema_20 = indicator_service.ema(data, 20)
            ema_50 = indicator_service.ema(data, 50)
            ema_200 = indicator_service.ema(data, 200)

            current_price = data[-1]["close"]
            ema_20_val = ema_20[-1] if ema_20 and len(ema_20) > 0 else None
            ema_50_val = ema_50[-1] if ema_50 and len(ema_50) > 0 else None
            ema_200_val = ema_200[-1] if ema_200 and len(ema_200) > 0 else None

            if ema_20_val and ema_50_val and ema_200_val:
                if current_price > ema_20_val > ema_50_val > ema_200_val:
                    ema_trend = "strong_bullish"
                elif current_price > ema_20_val > ema_50_val:
                    ema_trend = "bullish"
                elif current_price < ema_20_val < ema_50_val < ema_200_val:
                    ema_trend = "strong_bearish"
                elif current_price < ema_20_val < ema_50_val:
                    ema_trend = "bearish"
                else:
                    ema_trend = "neutral"
            else:
                ema_trend = "neutral"

            bb_upper = bollinger["upper"][-1] if bollinger and bollinger.get("upper") else None
            bb_lower = bollinger["lower"][-1] if bollinger and bollinger.get("lower") else None
            if bb_upper and bb_lower:
                if current_price >= bb_upper:
                    bb_position = "above_upper"
                elif current_price <= bb_lower:
                    bb_position = "below_lower"
                else:
                    bb_position = "inside"
            else:
                bb_position = "unknown"

            adx_result = indicator_service.adx(data)

            return {
                "rsi": round(rsi_result["current"], 1) if isinstance(rsi_result, dict) and "current" in rsi_result else None,
                "macd": round(macd_result["current_histogram"], 2) if isinstance(macd_result, dict) and "current_histogram" in macd_result else None,
                "adx": round(adx_result["current_adx"], 1) if isinstance(adx_result, dict) and "current_adx" in adx_result else None,
                "ema_trend": ema_trend,
                "ema_20": round(ema_20_val, 2) if ema_20_val else None,
                "ema_50": round(ema_50_val, 2) if ema_50_val else None,
                "bb_position": bb_position,
            }
        except Exception:
            return {"rsi": None, "macd": None, "adx": None, "ema_trend": "unknown"}


enterprise_signal_engine = EnterpriseSignalEngine()
