"""
Institutional Scoring Engine

100-point weighted scoring system:
  Trend:      20 pts
  Momentum:   15 pts
  Volume:     15 pts
  Liquidity:  15 pts
  SMC:        20 pts
  Risk:       15 pts
  Total:     100 pts

Classification:
  95-100: Institutional Grade
  90-94:  Excellent
  85-89:  Very Strong
  80-84:  Strong
  70-79:  Watchlist
  <70:    Reject
"""
import numpy as np
from typing import Optional
from app.services.indicators import indicator_service


class InstitutionalScorer:
    def __init__(self):
        self.trend_weight = 20
        self.momentum_weight = 15
        self.volume_weight = 15
        self.liquidity_weight = 15
        self.smc_weight = 20
        self.risk_weight = 15

    async def score(self, symbol: str, data: list, timeframe: str = "1h",
                    smc_data: Optional[dict] = None,
                    futures_data: Optional[dict] = None) -> dict:
        if len(data) < 50:
            return self._empty(symbol, timeframe, "Insufficient data")

        trend = self._score_trend(data)
        momentum = self._score_momentum(data)
        volume = self._score_volume(data)
        liquidity = self._score_liquidity(data, futures_data)
        smc = self._score_smc(data, smc_data)
        risk = self._score_risk(data, futures_data)

        scores = {
            "trend": trend,
            "momentum": momentum,
            "volume": volume,
            "liquidity": liquidity,
            "smc": smc,
            "risk": risk,
        }

        # Each category scorer already returns signed points capped by its
        # configured category weight. Summing them produces the intended
        # institutional score on the -100..100 scale.
        total = sum(scores.values())

        direction = "long" if total > 5 else ("short" if total < -5 else "neutral")
        abs_score = abs(total)
        classification = self._classify(abs_score)

        long_prob = max(0, min(100, 50 + total * 0.5))
        short_prob = 100 - long_prob

        details = self._build_details(data, scores)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "total_score": round(total, 1),
            "abs_score": round(abs_score, 1),
            "classification": classification,
            "direction": direction,
            "long_probability": round(long_prob, 1),
            "short_probability": round(short_prob, 1),
            "scores": {k: round(v, 1) for k, v in scores.items()},
            "weights": {
                "trend": self.trend_weight,
                "momentum": self.momentum_weight,
                "volume": self.volume_weight,
                "liquidity": self.liquidity_weight,
                "smc": self.smc_weight,
                "risk": self.risk_weight,
            },
            "details": details,
            "risk_level": "low" if abs_score >= 70 else "medium" if abs_score >= 40 else "high",
        }

    def _score_trend(self, data: list) -> float:
        score = 0.0
        closes = [d["close"] for d in data]
        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]

        ema_9 = indicator_service.ema(data, 9)
        ema_20 = indicator_service.ema(data, 20)
        ema_50 = indicator_service.ema(data, 50)
        ema_200 = indicator_service.ema(data, 200)

        current_price = closes[-1]

        if ema_9 and ema_20 and ema_50:
            if current_price > ema_9[-1] > ema_20[-1] > ema_50[-1]:
                score += 6
            elif current_price > ema_20[-1] > ema_50[-1]:
                score += 4
            elif current_price > ema_20[-1]:
                score += 2
            elif current_price < ema_9[-1] < ema_20[-1] < ema_50[-1]:
                score -= 6
            elif current_price < ema_20[-1] < ema_50[-1]:
                score -= 4
            elif current_price < ema_20[-1]:
                score -= 2

        if ema_200:
            if current_price > ema_200[-1]:
                score += 2
            else:
                score -= 2

        macd = indicator_service.macd(data)
        if isinstance(macd, dict) and "current_histogram" in macd:
            hist = macd["current_histogram"]
            signal = macd.get("current_signal", 0)
            if hist > 0 and hist > signal:
                score += 3
            elif hist < 0 and hist < signal:
                score -= 3

        adx = indicator_service.adx(data)
        if isinstance(adx, dict):
            adx_val = adx.get("current_adx", 0)
            if adx_val > 25:
                di_plus = adx.get("plus_di", [0])[-1] if adx.get("plus_di") else 0
                di_minus = adx.get("minus_di", [0])[-1] if adx.get("minus_di") else 0
                if di_plus > di_minus:
                    score += 3
                else:
                    score -= 3
            elif adx_val < 20:
                score -= 2

        supertrend = indicator_service.supertrend(data)
        if isinstance(supertrend, dict) and supertrend.get("current_direction") == "uptrend":
            score += 4
        elif isinstance(supertrend, dict) and supertrend.get("current_direction") == "downtrend":
            score -= 4

        hh = highs[-1] > max(highs[-6:-1]) if len(highs) > 5 else False
        ll = lows[-1] < min(lows[-6:-1]) if len(lows) > 5 else False
        if hh:
            score += 2
        if ll:
            score -= 2

        return max(-self.trend_weight, min(self.trend_weight, score))

    def _score_momentum(self, data: list) -> float:
        score = 0.0
        closes = [d["close"] for d in data]

        rsi = indicator_service.rsi(data)
        if isinstance(rsi, dict):
            rsi_val = rsi.get("current", 50)
            if rsi_val > 70:
                score -= 3
            elif rsi_val > 60:
                score += 1
            elif rsi_val > 50:
                score += 3
            elif rsi_val > 40:
                score -= 1
            elif rsi_val > 30:
                score -= 3
            else:
                score += 2

        stoch_rsi = indicator_service.stochastic_rsi(data)
        if isinstance(stoch_rsi, dict):
            k = stoch_rsi.get("k", [])
            d = stoch_rsi.get("d", [])
            if k and d and len(k) > 0 and len(d) > 0:
                k_val, d_val = k[-1], d[-1]
                if k_val > d_val and k_val < 20:
                    score += 3
                elif k_val < d_val and k_val > 80:
                    score -= 3
                elif k_val > d_val:
                    score += 1
                elif k_val < d_val:
                    score -= 1

        roc = ((closes[-1] / closes[-10]) - 1) * 100 if len(closes) > 10 else 0
        if roc > 5:
            score += 2
        elif roc > 2:
            score += 1
        elif roc < -5:
            score -= 2
        elif roc < -2:
            score -= 1

        bb = indicator_service.bollinger(data)
        if isinstance(bb, dict) and bb.get("upper") and bb.get("lower") and bb.get("middle"):
            upper = bb["upper"][-1]
            lower = bb["lower"][-1]
            middle = bb["middle"][-1]
            current = closes[-1]
            if current >= upper:
                score -= 3
            elif current <= lower:
                score += 3
            elif current > middle:
                score += 1
            elif current < middle:
                score -= 1

        return max(-self.momentum_weight, min(self.momentum_weight, score))

    def _score_volume(self, data: list) -> float:
        score = 0.0
        volumes = [d["volume"] for d in data]

        if len(volumes) >= 20:
            avg_vol = np.mean(volumes[-20:])
            current_vol = volumes[-1]
            vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1

            if vol_ratio > 3:
                score += 5
            elif vol_ratio > 2:
                score += 4
            elif vol_ratio > 1.5:
                score += 2
            elif vol_ratio < 0.5:
                score -= 2
            elif vol_ratio < 0.3:
                score -= 3

        cmf = indicator_service.cmf(data)
        if cmf and len(cmf) > 0:
            cmf_val = cmf[-1]
            if cmf_val > 0.1:
                score += 3
            elif cmf_val > 0.05:
                score += 2
            elif cmf_val < -0.1:
                score -= 3
            elif cmf_val < -0.05:
                score -= 2

        obv_values = [d.get("obv", 0) for d in data]
        if len(obv_values) >= 5:
            obv_trend = np.polyfit(range(5), obv_values[-5:], 1)[0] if len(obv_values) >= 5 else 0
            if obv_trend > 0:
                score += 2
            elif obv_trend < 0:
                score -= 2

        close_prices = [d["close"] for d in data]
        if len(close_prices) >= 20:
            if current_vol > avg_vol and close_prices[-1] > close_prices[-2]:
                score += 3
            elif current_vol > avg_vol and close_prices[-1] < close_prices[-2]:
                score -= 3

        return max(-self.volume_weight, min(self.volume_weight, score))

    def _score_liquidity(self, data: list, futures: Optional[dict] = None) -> float:
        score = 0.0
        closes = [d["close"] for d in data]

        if futures:
            funding = futures.get("funding_rate", 0)
            if funding > 0.01:
                score -= 4
            elif funding > 0.005:
                score -= 2
            elif funding < -0.01:
                score += 4
            elif funding < -0.005:
                score += 2

            oi = futures.get("open_interest", 0)
            if oi and len(closes) > 10:
                oi_change = futures.get("oi_change_percent", 0)
                if oi_change > 10:
                    if closes[-1] > closes[-2]:
                        score += 3
                    else:
                        score -= 3
                elif oi_change < -10:
                    score -= 2

        bid_ask_spread = futures.get("spread_percent", 0) if futures else 0
        if 0 < bid_ask_spread < 0.01:
            score += 3
        elif bid_ask_spread > 0.05:
            score -= 3

        volumes = [d["volume"] for d in data]
        if len(volumes) >= 5:
            avg_vol = np.mean(volumes[-5:])
            if avg_vol > 100000:
                score += 3
            elif avg_vol > 10000:
                score += 1
            elif avg_vol < 1000:
                score -= 3

        return max(-self.liquidity_weight, min(self.liquidity_weight, score))

    def _score_smc(self, data: list, smc_data: Optional[dict] = None) -> float:
        score = 0.0
        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]
        closes = [d["close"] for d in data]
        opens = [d["open"] for d in data]

        if smc_data:
            bos = smc_data.get("bos_events", [])
            choch = smc_data.get("choch_events", [])

            bullish_bos = sum(1 for b in bos if b.get("type") == "bullish_bos")
            bearish_bos = sum(1 for b in bos if b.get("type") == "bearish_bos")
            bullish_choch = sum(1 for c in choch if c.get("type") == "bullish_choch")
            bearish_choch = sum(1 for c in choch if c.get("type") == "bearish_choch")

            net_bos = bullish_bos - bearish_bos
            net_choch = bullish_choch - bearish_choch
            score += max(-6, min(6, net_bos * 2 + net_choch * 3))

            order_blocks = smc_data.get("order_blocks", [])
            for ob in order_blocks[:3]:
                if ob.get("type") == "bullish":
                    score += 2
                elif ob.get("type") == "bearish":
                    score -= 2

            fvg = smc_data.get("fair_value_gaps", [])
            for f in fvg[:3]:
                if f.get("type") == "bullish_fvg":
                    score += 2
                elif f.get("type") == "bearish_fvg":
                    score -= 2

            liquidity = smc_data.get("liquidity_zones", [])
            for lz in liquidity[:3]:
                if lz.get("type") == "buy_side":
                    score += 1.5
                elif lz.get("type") == "sell_side":
                    score -= 1.5

            trend = smc_data.get("trend", "ranging")
            if trend == "uptrend":
                score += 3
            elif trend == "downtrend":
                score -= 3

        else:
            for i in range(2, min(10, len(data))):
                if lows[-i] > highs[-(i + 1)]:
                    fvg_bullish = True
                    if closes[-1] > lows[-i]:
                        score += 3
                    break
                if highs[-i] < lows[-(i + 1)]:
                    fvg_bearish = True
                    if closes[-1] < highs[-i]:
                        score -= 3
                    break

            if len(highs) >= 10:
                recent_high = max(highs[-10:])
                recent_low = min(lows[-10:])
                current = closes[-1]
                if current > recent_high:
                    score += 4
                elif current < recent_low:
                    score -= 4

            for i in range(-5, -1):
                if closes[i] > opens[i] and lows[i] < lows[i + 1] and closes[i + 1] > closes[i]:
                    score += 2
                    break
                if closes[i] < opens[i] and highs[i] > highs[i + 1] and closes[i + 1] < closes[i]:
                    score -= 2
                    break

        return max(-self.smc_weight, min(self.smc_weight, score))

    def _score_risk(self, data: list, futures: Optional[dict] = None) -> float:
        score = 0.0
        closes = [d["close"] for d in data]
        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]

        volatility = np.std([(highs[i] - lows[i]) / closes[i] for i in range(len(closes))]) * 100 if len(closes) > 1 else 0
        atr = indicator_service.atr(data)
        atr_pct = atr / closes[-1] * 100 if atr and closes else 0

        if atr_pct < 1:
            score += 4
        elif atr_pct < 2:
            score += 2
        elif atr_pct > 4:
            score -= 4
        elif atr_pct > 3:
            score -= 2

        if volatility < 1:
            score += 2
        elif volatility > 3:
            score -= 2

        returns = [abs(closes[i] / closes[i - 1] - 1) * 100 for i in range(1, len(closes))]
        max_single_move = max(returns) if returns else 0
        if max_single_move > 5:
            score -= 3
        elif max_single_move > 3:
            score -= 1

        bb = indicator_service.bollinger(data)
        if isinstance(bb, dict) and bb.get("upper") and bb.get("lower") and bb.get("middle"):
            width = (bb["upper"][-1] - bb["lower"][-1]) / bb["middle"][-1] * 100
            if width > 8:
                score -= 3
            elif width < 2:
                score += 3

        if futures:
            liq_long = futures.get("liquidation_zones", {}).get("long_liquidation_zone", 0)
            liq_short = futures.get("liquidation_zones", {}).get("short_liquidation_zone", 0)
            current = closes[-1]
            if liq_long and current:
                liq_dist = abs(current - liq_long) / current * 100
                if liq_dist < 2:
                    score -= 3
            if liq_short and current:
                liq_dist = abs(liq_short - current) / current * 100
                if liq_dist < 2:
                    score -= 3

        return max(-self.risk_weight, min(self.risk_weight, score))

    def _classify(self, score: float) -> str:
        if score >= 95:
            return "institutional_grade"
        elif score >= 90:
            return "excellent"
        elif score >= 85:
            return "very_strong"
        elif score >= 80:
            return "strong"
        elif score >= 70:
            return "watchlist"
        return "reject"

    def _build_details(self, data: list, scores: dict) -> dict:
        closes = [d["close"] for d in data]
        rsi = indicator_service.rsi(data)
        macd = indicator_service.macd(data)
        adx = indicator_service.adx(data)
        bb = indicator_service.bollinger(data)

        return {
            "rsi": round(rsi.get("current", 50), 1) if isinstance(rsi, dict) else None,
            "macd_histogram": round(macd.get("current_histogram", 0), 4) if isinstance(macd, dict) else None,
            "adx": round(adx.get("current_adx", 0), 1) if isinstance(adx, dict) else None,
            "supertrend": adx.get("current_direction", "neutral") if isinstance(adx, dict) else "neutral",
            "atr": round(indicator_service.atr(data), 2) if indicator_service.atr(data) else None,
            "current_price": closes[-1] if closes else 0,
            "volume_ratio": round(
                data[-1]["volume"] / (np.mean([d["volume"] for d in data[-20:]]) or 1), 2
            ) if len(data) >= 20 else 1,
        }

    def _empty(self, symbol: str, timeframe: str, reason: str) -> dict:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "total_score": 0,
            "abs_score": 0,
            "classification": "reject",
            "direction": "neutral",
            "long_probability": 50,
            "short_probability": 50,
            "scores": {},
            "weights": {},
            "details": {},
            "risk_level": "unknown",
            "error": reason,
        }


institutional_scorer = InstitutionalScorer()
