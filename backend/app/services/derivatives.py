"""
Institutional-Grade Derivatives Analysis Engine

Comprehensive derivatives market analysis including:
- Funding rate analysis and annualized rate calculation
- Open interest delta, trend, and price divergence detection
- Long/short ratio interpretation with extreme thresholds
- Liquidation heatmaps, clustering, and large liquidation zones
- Basis analysis and contango/backwardation detection
- Premium index calculation
- Gamma exposure estimation
- Aggregated snapshot and async streaming
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
import asyncio
import math
from app.core.logging import logger


class DerivativesEngine:
    FUNDING_BULLISH_THRESHOLD = -0.0001
    FUNDING_BEARISH_THRESHOLD = 0.0001
    LIQUIDATION_CLUSTER_DISTANCE_PCT = 0.005
    ANNUALIZED_FUNDING_PERIODS = 1095

    def analyze_funding(
        self,
        symbol: str,
        funding_rate: float,
        next_funding_time: datetime,
        funding_history: Optional[List[float]] = None,
    ) -> Dict:
        history = funding_history or []
        annualized = funding_rate * self.ANNUALIZED_FUNDING_PERIODS * 100

        if funding_rate < self.FUNDING_BULLISH_THRESHOLD:
            signal = "bullish"
            interpretation = "Shorts paying longs; expect upward pressure"
        elif funding_rate > self.FUNDING_BEARISH_THRESHOLD:
            signal = "bearish"
            interpretation = "Longs paying shorts; expect downward pressure"
        else:
            signal = "neutral"
            interpretation = "Funding within normal range"

        trend = "stable"
        pressure = "neutral"
        if len(history) >= 3:
            recent = history[-3:]
            if all(recent[i] < recent[i + 1] for i in range(len(recent) - 1)):
                trend = "increasing"
                pressure = "scaling" if abs(recent[-1]) > abs(recent[0]) else "neutral"
            elif all(recent[i] > recent[i + 1] for i in range(len(recent) - 1)):
                trend = "decreasing"
                pressure = "decaying"
            else:
                trend = "mixed"

        now = datetime.now(timezone.utc)
        seconds_to_funding = max(0, (next_funding_time - now).total_seconds())
        hours_to_funding = round(seconds_to_funding / 3600, 2)

        return {
            "symbol": symbol,
            "funding_rate": round(funding_rate * 100, 6),
            "funding_rate_raw": funding_rate,
            "annualized_rate": round(annualized, 4),
            "signal": signal,
            "interpretation": interpretation,
            "trend": trend,
            "pressure": pressure,
            "next_funding_time": next_funding_time.isoformat() if isinstance(next_funding_time, datetime) else str(next_funding_time),
            "hours_to_funding": hours_to_funding,
            "funding_history": [round(f * 100, 6) for f in history],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def analyze_open_interest(
        self,
        symbol: str,
        oi_current: float,
        oi_change_24h: float,
        oi_history: Optional[List[float]] = None,
        price_change_24h: Optional[float] = None,
    ) -> Dict:
        history = oi_history or []
        oi_delta_direction = "up" if oi_change_24h > 0 else ("down" if oi_change_24h < 0 else "flat")
        oi_delta_magnitude = "significant" if abs(oi_change_24h) > 0.1 else ("moderate" if abs(oi_change_24h) > 0.05 else "minor")
        oi_change_pct = round(oi_change_24h * 100, 2)

        trend = "neutral"
        if len(history) >= 5:
            recent = history[-5:]
            avg = sum(recent) / len(recent)
            if oi_current > avg * 1.05:
                trend = "accumulating"
            elif oi_current < avg * 0.95:
                trend = "distributing"
            else:
                trend = "sideways"

        divergence = None
        divergence_strength = 0
        if price_change_24h is not None and oi_change_24h != 0:
            if oi_change_24h > 0 and price_change_24h < -0.02:
                divergence = "bearish"
                divergence_strength = round(abs(oi_change_24h) + abs(price_change_24h), 4)
            elif oi_change_24h < 0 and price_change_24h > 0.02:
                divergence = "bullish"
                divergence_strength = round(abs(oi_change_24h) + abs(price_change_24h), 4)
            elif oi_change_24h > 0 and price_change_24h > 0.02:
                divergence = "confirmation_bullish"
                divergence_strength = round(min(abs(oi_change_24h), abs(price_change_24h)), 4)
            elif oi_change_24h < 0 and price_change_24h < -0.02:
                divergence = "confirmation_bearish"
                divergence_strength = round(min(abs(oi_change_24h), abs(price_change_24h)), 4)

        return {
            "symbol": symbol,
            "oi_current": round(oi_current, 2),
            "oi_change_24h_pct": oi_change_pct,
            "oi_change_24h_raw": oi_change_24h,
            "oi_delta_direction": oi_delta_direction,
            "oi_delta_magnitude": oi_delta_magnitude,
            "oi_trend": trend,
            "price_change_24h_pct": round(price_change_24h * 100, 2) if price_change_24h is not None else None,
            "divergence": divergence,
            "divergence_strength": divergence_strength if divergence else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def analyze_long_short_ratio(
        self,
        long_ratio: float,
        short_ratio: float,
        long_short_ratio_value: float,
    ) -> Dict:
        total = long_ratio + short_ratio
        long_pct = round((long_ratio / total) * 100, 2) if total > 0 else 50.0
        short_pct = round((short_ratio / total) * 100, 2) if total > 0 else 50.0

        if long_ratio > short_ratio:
            majority_side = "long"
            majority_pct = long_pct
        elif short_ratio > long_ratio:
            majority_side = "short"
            majority_pct = short_pct
        else:
            majority_side = "balanced"
            majority_pct = 50.0

        extreme = False
        extreme_type = None
        if long_short_ratio_value >= 2.0:
            extreme = True
            extreme_type = "long_dominated"
        elif long_short_ratio_value <= 0.5:
            extreme = True
            extreme_type = "short_dominated"

        if long_short_ratio_value > 1.2:
            interpretation = "Strong long bias; potential overcrowding"
        elif long_short_ratio_value < 0.8:
            interpretation = "Strong short bias; potential squeeze setup"
        elif long_short_ratio_value > 1.05:
            interpretation = "Slight long bias"
        elif long_short_ratio_value < 0.95:
            interpretation = "Slight short bias"
        else:
            interpretation = "Balanced positioning"

        if extreme:
            interpretation += " — EXTREME: " + ("longs overcrowded, squeeze risk" if extreme_type == "long_dominated" else "shorts overcrowded, squeeze imminent")

        return {
            "long_ratio_pct": long_pct,
            "short_ratio_pct": short_pct,
            "long_short_ratio": round(long_short_ratio_value, 4),
            "majority_side": majority_side,
            "majority_pct": majority_pct,
            "extreme": extreme,
            "extreme_type": extreme_type,
            "interpretation": interpretation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def analyze_liquidations(self, liquidations: List[Dict]) -> Dict:
        if not liquidations:
            return {
                "total_liquidations": 0,
                "total_long_liquidations": 0,
                "total_short_liquidations": 0,
                "total_long_value": 0.0,
                "total_short_value": 0.0,
                "long_short_ratio": None,
                "largest_liquidation": None,
                "heatmap": [],
                "clusters": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        total_long_value = 0.0
        total_short_value = 0.0
        total_long_count = 0
        total_short_count = 0
        largest = None

        heatmap_dict: Dict[str, Dict] = {}

        for liq in liquidations:
            price = liq.get("price", 0)
            value = abs(liq.get("value", 0))
            side = liq.get("side", "unknown").lower()

            if side == "long":
                total_long_value += value
                total_long_count += 1
            elif side == "short":
                total_short_value += value
                total_short_count += 1

            if largest is None or value > largest["value"]:
                largest = {
                    "price": price,
                    "value": value,
                    "side": side,
                    "symbol": liq.get("symbol", ""),
                    "time": liq.get("time", ""),
                }

            price_key = self._price_bucket(price)
            if price_key not in heatmap_dict:
                heatmap_dict[price_key] = {"price_level": price_key, "total_value": 0.0, "count": 0, "long_value": 0.0, "short_value": 0.0}
            heatmap_dict[price_key]["total_value"] += value
            heatmap_dict[price_key]["count"] += 1
            if side == "long":
                heatmap_dict[price_key]["long_value"] += value
            elif side == "short":
                heatmap_dict[price_key]["short_value"] += value

        heatmap = sorted(heatmap_dict.values(), key=lambda x: x["total_value"], reverse=True)

        clusters = self.get_large_liquidation_zones(liquidations, threshold=100000)

        ls_ratio = round(total_long_value / total_short_value, 4) if total_short_value > 0 else (99.99 if total_long_value > 0 else None)

        return {
            "total_liquidations": total_long_count + total_short_count,
            "total_long_liquidations": total_long_count,
            "total_short_liquidations": total_short_count,
            "total_long_value": round(total_long_value, 2),
            "total_short_value": round(total_short_value, 2),
            "long_short_ratio": ls_ratio,
            "largest_liquidation": largest,
            "heatmap": heatmap[:20],
            "clusters": clusters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def analyze_basis(self, spot_price: float, futures_price: float, expiry_days: float) -> Dict:
        basis = futures_price - spot_price
        basis_pct = (basis / spot_price) * 100 if spot_price else 0.0
        annualized_basis = (basis_pct / expiry_days) * 365 if expiry_days > 0 else 0.0

        if basis > 0:
            market_status = "contango"
            interpretation = "Futures above spot; market expects higher prices"
        elif basis < 0:
            market_status = "backwardation"
            interpretation = "Futures below spot; market expects lower prices or immediate demand"
        else:
            market_status = "par"
            interpretation = "Futures at parity with spot"

        basis_strength = "strong" if abs(basis_pct) > 1.0 else ("moderate" if abs(basis_pct) > 0.3 else "weak")

        return {
            "spot_price": round(spot_price, 4),
            "futures_price": round(futures_price, 4),
            "basis": round(basis, 4),
            "basis_pct": round(basis_pct, 4),
            "annualized_basis_pct": round(annualized_basis, 4),
            "expiry_days": round(expiry_days, 2),
            "market_status": market_status,
            "basis_strength": basis_strength,
            "interpretation": interpretation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_premium_index(self, mark_price: float, index_price: float) -> float:
        if not index_price:
            return 0.0
        return round(((mark_price - index_price) / index_price) * 100, 6)

    def get_gamma_exposure(self, option_data: Optional[Dict] = None) -> Dict:
        if option_data is not None:
            strikes = option_data.get("strikes", [])
            gex_levels = []
            total_gamma = 0.0
            for strike in strikes:
                gamma = strike.get("gamma", 0)
                oi = strike.get("open_interest", 0)
                gex = gamma * oi * strike.get("price", 1)
                gex_levels.append({
                    "strike": strike.get("strike", 0),
                    "gamma": gamma,
                    "open_interest": oi,
                    "gex": round(gex, 2),
                    "side": strike.get("side", "call"),
                })
                total_gamma += gex

            gex_levels.sort(key=lambda x: abs(x["gex"]), reverse=True)
            return {
                "data_source": "real",
                "total_gamma_exposure": round(total_gamma, 2),
                "gamma_levels": gex_levels[:30],
                "gamma_positive": total_gamma > 0,
                "interpretation": "Positive gamma: market stabilizing" if total_gamma > 0 else "Negative gamma: market prone to moves",
                "zero_gex_level": self._find_zero_gex(gex_levels),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "available": False,
            "data_source": None,
            "reason": "Real options gamma provider is not configured",
            "total_gamma_exposure": None,
            "gamma_levels": [],
            "gamma_positive": None,
            "interpretation": None,
            "zero_gex_level": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_large_liquidation_zones(self, liquidations: List[Dict], threshold: float = 100000) -> List[Dict]:
        large = [l for l in liquidations if abs(l.get("value", 0)) >= threshold]
        if not large:
            return []

        sorted_liqs = sorted(large, key=lambda x: x.get("price", 0))
        clusters = []
        current_cluster = [sorted_liqs[0]]

        for liq in sorted_liqs[1:]:
            prev_price = current_cluster[-1].get("price", 0)
            curr_price = liq.get("price", 0)
            distance_pct = abs(curr_price - prev_price) / prev_price if prev_price else 1
            if distance_pct <= self.LIQUIDATION_CLUSTER_DISTANCE_PCT:
                current_cluster.append(liq)
            else:
                cluster_result = self._summarize_cluster(current_cluster)
                if cluster_result["total_value"] >= threshold:
                    clusters.append(cluster_result)
                current_cluster = [liq]

        cluster_result = self._summarize_cluster(current_cluster)
        if cluster_result["total_value"] >= threshold:
            clusters.append(cluster_result)

        clusters.sort(key=lambda x: x["total_value"], reverse=True)
        return clusters

    def get_aggregated_derivatives_snapshot(
        self,
        symbol: str,
        funding_rate: float = 0.0,
        next_funding_time: Optional[datetime] = None,
        funding_history: Optional[List[float]] = None,
        oi_current: float = 0.0,
        oi_change_24h: float = 0.0,
        oi_history: Optional[List[float]] = None,
        price_change_24h: Optional[float] = None,
        long_ratio: float = 50.0,
        short_ratio: float = 50.0,
        long_short_ratio_value: float = 1.0,
        liquidations: Optional[List[Dict]] = None,
        spot_price: float = 0.0,
        futures_price: float = 0.0,
        expiry_days: float = 30.0,
        mark_price: float = 0.0,
        index_price: float = 0.0,
        option_data: Optional[Dict] = None,
        liquidation_threshold: float = 100000,
    ) -> Dict:
        nft = next_funding_time or (datetime.now(timezone.utc) + timedelta(hours=8))

        funding = self.analyze_funding(symbol, funding_rate, nft, funding_history)
        oi = self.analyze_open_interest(symbol, oi_current, oi_change_24h, oi_history, price_change_24h)
        ls = self.analyze_long_short_ratio(long_ratio, short_ratio, long_short_ratio_value)
        liqs = self.analyze_liquidations(liquidations or [])
        basis = self.analyze_basis(spot_price, futures_price, expiry_days)
        premium = self.get_premium_index(mark_price, index_price)
        gex = self.get_gamma_exposure(option_data)
        zones = self.get_large_liquidation_zones(liquidations or [], liquidation_threshold)

        aggregate_signal = self._compute_aggregate_signal(funding, oi, ls, basis, premium)

        return {
            "symbol": symbol,
            "aggregate_signal": aggregate_signal,
            "funding": funding,
            "open_interest": oi,
            "long_short_ratio": ls,
            "liquidations": liqs,
            "basis": basis,
            "premium_index": premium,
            "gamma_exposure": gex,
            "large_liquidation_zones": zones,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def stream_updates(self, symbols: List[str], interval_seconds: float = 10.0):
        while True:
            for symbol in symbols:
                try:
                    snapshot = self.get_aggregated_derivatives_snapshot(symbol)
                    yield {"type": "derivatives_update", "data": snapshot}
                except Exception as e:
                    logger.error(f"Derivatives stream error for {symbol}: {e}")
                    yield {"type": "derivatives_error", "symbol": symbol, "error": str(e)}
            await asyncio.sleep(interval_seconds)

    def _price_bucket(self, price: float) -> float:
        magnitude = 10 ** math.floor(math.log10(max(price, 1)))
        return round(price / magnitude) * magnitude

    def _summarize_cluster(self, cluster: List[Dict]) -> Dict:
        total_value = sum(abs(l.get("value", 0)) for l in cluster)
        prices = [l.get("price", 0) for l in cluster]
        long_value = sum(abs(l.get("value", 0)) for l in cluster if l.get("side", "").lower() == "long")
        short_value = sum(abs(l.get("value", 0)) for l in cluster if l.get("side", "").lower() == "short")
        return {
            "price_min": round(min(prices), 4),
            "price_max": round(max(prices), 4),
            "price_avg": round(sum(prices) / len(prices), 4),
            "total_value": round(total_value, 2),
            "total_long_value": round(long_value, 2),
            "total_short_value": round(short_value, 2),
            "count": len(cluster),
        }

    def _find_zero_gex(self, gex_levels: List[Dict]) -> Optional[float]:
        if not gex_levels:
            return None
        pos_cross = None
        for i in range(len(gex_levels) - 1):
            if gex_levels[i]["gex"] > 0 > gex_levels[i + 1]["gex"]:
                pos_cross = (gex_levels[i]["strike"] + gex_levels[i + 1]["strike"]) / 2
                break
            if gex_levels[i]["gex"] < 0 < gex_levels[i + 1]["gex"]:
                pos_cross = (gex_levels[i]["strike"] + gex_levels[i + 1]["strike"]) / 2
                break
        return round(pos_cross, 2) if pos_cross else None

    def _compute_aggregate_signal(
        self,
        funding: Dict,
        oi: Dict,
        ls: Dict,
        basis: Dict,
        premium: float,
    ) -> Dict:
        signals = []
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0

        if funding.get("signal") == "bullish":
            bullish_count += 1
            signals.append({"indicator": "funding", "signal": "bullish"})
        elif funding.get("signal") == "bearish":
            bearish_count += 1
            signals.append({"indicator": "funding", "signal": "bearish"})
        else:
            neutral_count += 1
            signals.append({"indicator": "funding", "signal": "neutral"})

        divergence = oi.get("divergence")
        if divergence and "bullish" in divergence:
            bullish_count += 1
            signals.append({"indicator": "oi_divergence", "signal": "bullish", "strength": oi.get("divergence_strength")})
        elif divergence and "bearish" in divergence:
            bearish_count += 1
            signals.append({"indicator": "oi_divergence", "signal": "bearish", "strength": oi.get("divergence_strength")})
        else:
            neutral_count += 1
            signals.append({"indicator": "oi_divergence", "signal": "neutral"})

        ls_extreme = ls.get("extreme_type")
        if ls_extreme == "long_dominated":
            bearish_count += 1
            signals.append({"indicator": "long_short_ratio", "signal": "bearish", "detail": "Overcrowded longs"})
        elif ls_extreme == "short_dominated":
            bullish_count += 1
            signals.append({"indicator": "long_short_ratio", "signal": "bullish", "detail": "Overcrowded shorts"})
        else:
            neutral_count += 1
            signals.append({"indicator": "long_short_ratio", "signal": "neutral"})

        if basis.get("market_status") == "contango":
            neutral_count += 1
            signals.append({"indicator": "basis", "signal": "neutral"})
        elif basis.get("market_status") == "backwardation":
            bearish_count += 1
            signals.append({"indicator": "basis", "signal": "bearish"})
        else:
            neutral_count += 1
            signals.append({"indicator": "basis", "signal": "neutral"})

        if premium > 0.1:
            bearish_count += 1
            signals.append({"indicator": "premium_index", "signal": "bearish"})
        elif premium < -0.1:
            bullish_count += 1
            signals.append({"indicator": "premium_index", "signal": "bullish"})
        else:
            neutral_count += 1
            signals.append({"indicator": "premium_index", "signal": "neutral"})

        total = bullish_count + bearish_count + neutral_count
        if total == 0:
            direction = "neutral"
            confidence = 0
        elif bullish_count > bearish_count:
            direction = "bullish"
            confidence = round((bullish_count / total) * 100, 1)
        elif bearish_count > bullish_count:
            direction = "bearish"
            confidence = round((bearish_count / total) * 100, 1)
        else:
            direction = "neutral"
            confidence = round((neutral_count / total) * 100, 1)

        return {
            "direction": direction,
            "confidence": confidence,
            "bullish_signals": bullish_count,
            "bearish_signals": bearish_count,
            "neutral_signals": neutral_count,
            "total_signals": total,
            "signal_breakdown": signals,
        }


derivatives_engine = DerivativesEngine()
