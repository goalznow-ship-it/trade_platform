"""
AI Market Brain — Central Intelligence Engine

Synthesizes ALL inputs into one unified market assessment:
- Technical + SMC analysis via institutional scoring and multi-timeframe
- Order flow analysis (orderbook, trades, CVD, spoofing, icebergs)
- Derivatives analysis (funding, OI, long/short, liquidations, basis)
- Macro analysis (DXY, NASDAQ, VIX, yields, CPI, FOMC, ETF flows)
- On-chain analysis (exchange flows, whale activity, stablecoins, reserves)
- Social sentiment analysis (Twitter, Reddit, Telegram, GitHub, community)
- Whale tracker (large transfers, whale alerts)
- Portfolio risk from risk_service

Outputs: overall score, bull/bear/crash/squeeze probabilities, regime,
         contributing factors, alt season signal.
"""

from typing import List, Dict
from datetime import datetime, timezone
import asyncio
import math
from app.core.logging import logger

try:
    from app.services.orderflow import orderflow_engine
except ImportError:
    orderflow_engine = None

try:
    from app.services.derivatives import derivatives_engine
except ImportError:
    derivatives_engine = None

try:
    from app.services.smc_engine import smc_engine
except ImportError:
    smc_engine = None

try:
    from app.services.institutional_scoring import institutional_scorer
except ImportError:
    institutional_scorer = None

try:
    from app.services.multi_timeframe import multi_timeframe_engine
except ImportError:
    multi_timeframe_engine = None

try:
    from app.services.market_coverage import market_coverage
except ImportError:
    market_coverage = None

try:
    from app.services.macro_engine import macro_engine
except ImportError:
    macro_engine = None

try:
    from app.services.onchain import onchain_engine
except ImportError:
    onchain_engine = None

try:
    from app.services.social_sentiment import social_sentiment
except ImportError:
    social_sentiment = None

try:
    from app.services.whale import whale_tracker
except ImportError:
    whale_tracker = None

try:
    from app.services.risk import risk_service
except ImportError:
    risk_service = None

try:
    from app.services.market import market_service
except ImportError:
    market_service = None


class AICentralBrain:
    TECHNICAL_WEIGHT = 0.20
    SMC_WEIGHT = 0.15
    ORDERFLOW_WEIGHT = 0.10
    DERIVATIVES_WEIGHT = 0.10
    MACRO_WEIGHT = 0.15
    ONCHAIN_WEIGHT = 0.10
    SENTIMENT_WEIGHT = 0.10
    WHALE_WEIGHT = 0.05
    RISK_WEIGHT = 0.05

    def __init__(self):
        self._logger = logger
        self._assessment_cache: Dict[str, Dict] = {}
        self._last_update: Dict[str, datetime] = {}
        self._cache_ttl_seconds = 30

    async def assess_market(self, symbol: str) -> Dict:
        try:
            now = datetime.now(timezone.utc)
            if symbol in self._assessment_cache:
                elapsed = (now - self._last_update.get(symbol, now)).total_seconds()
                if elapsed < self._cache_ttl_seconds:
                    return self._assessment_cache[symbol]

            tasks = []
            tasks.append(self._get_technical_score(symbol))
            tasks.append(self._get_smc_score(symbol))
            tasks.append(self._get_orderflow_score(symbol))
            tasks.append(self._get_derivatives_score(symbol))
            tasks.append(self._get_macro_score())
            tasks.append(self._get_onchain_score(symbol))
            tasks.append(self._get_sentiment_score(symbol))
            tasks.append(self._get_whale_score(symbol))
            tasks.append(self._get_risk_score())

            results = await asyncio.gather(*tasks, return_exceptions=True)

            scores = {}
            factors = []
            engine_results = {}

            labels = [
                "technical", "smc", "orderflow", "derivatives",
                "macro", "onchain", "sentiment", "whale", "risk",
            ]

            for label, result in zip(labels, results):
                if isinstance(result, Exception):
                    self._logger.warning(f"Brain {symbol} {label} error: {result}")
                    scores[label] = 50.0
                    engine_results[label] = {"error": str(result)}
                elif isinstance(result, dict):
                    scores[label] = result.get("score", 50.0)
                    engine_results[label] = result
                    if result.get("factors"):
                        factors.extend(result["factors"])
                else:
                    scores[label] = 50.0
                    engine_results[label] = {"score": 50.0}

            overall_score = self.get_weighted_score(scores)

            bull_prob = self._compute_bull_probability(scores, engine_results)
            bear_prob = self._compute_bear_probability(scores, bull_prob)
            crash_prob = await self.get_crash_risk(
                engine_results.get("technical", {}),
                engine_results.get("onchain", {}),
                engine_results.get("macro", {}),
                engine_results.get("derivatives", {}),
            )
            squeeze = await self.get_squeeze_risk(
                engine_results.get("derivatives", {}),
                engine_results.get("orderflow", {}),
                engine_results.get("sentiment", {}),
            )

            top_symbols_scores = await self._get_top_symbols_scores()
            btc_dom = await self._get_btc_dominance()
            alt_season = self.get_alt_season_signal(top_symbols_scores, btc_dom)

            regime = self.detect_regime(overall_score, bull_prob, bear_prob)

            contributing_factors = self.get_explanation({
                "regime": regime,
                "scores": scores,
                "overall": overall_score,
                "bull_prob": bull_prob,
                "bear_prob": bear_prob,
                "crash_prob": crash_prob,
                "short_squeeze_prob": squeeze.get("short_squeeze_probability", 0),
                "long_squeeze_prob": squeeze.get("long_squeeze_probability", 0),
                "alt_season_prob": alt_season,
            })

            result = {
                "symbol": symbol,
                "overall_market_score": round(overall_score, 1),
                "bull_probability": round(bull_prob, 1),
                "bear_probability": round(bear_prob, 1),
                "crash_probability": round(crash_prob, 1),
                "short_squeeze_probability": round(squeeze.get("short_squeeze_probability", 0), 1),
                "long_squeeze_probability": round(squeeze.get("long_squeeze_probability", 0), 1),
                "alt_season_probability": round(alt_season, 1),
                "confidence": self._compute_confidence(scores),
                "regime": regime,
                "contributing_factors": contributing_factors,
                "sub_scores": {k: round(v, 1) for k, v in scores.items()},
                "engine_results": engine_results,
                "timestamp": now.isoformat(),
            }

            self._assessment_cache[symbol] = result
            self._last_update[symbol] = now
            return result

        except Exception as e:
            self._logger.error(f"Brain assess_market failed for {symbol}: {e}")
            return self._empty_assessment(symbol, str(e))

    def get_weighted_score(self, scores: Dict) -> float:
        weights = {
            "technical": self.TECHNICAL_WEIGHT,
            "smc": self.SMC_WEIGHT,
            "orderflow": self.ORDERFLOW_WEIGHT,
            "derivatives": self.DERIVATIVES_WEIGHT,
            "macro": self.MACRO_WEIGHT,
            "onchain": self.ONCHAIN_WEIGHT,
            "sentiment": self.SENTIMENT_WEIGHT,
            "whale": self.WHALE_WEIGHT,
            "risk": self.RISK_WEIGHT,
        }

        dynamic_weights = self._compute_dynamic_weights(scores, weights)

        total_weight = 0.0
        weighted_sum = 0.0
        for key, w in dynamic_weights.items():
            if key in scores:
                weighted_sum += scores[key] * w
                total_weight += w

        if total_weight == 0:
            return 50.0

        base_score = weighted_sum / total_weight
        variance = self._score_variance(scores, dynamic_weights, base_score)
        divergence_penalty = max(0, min(10, variance * 2))
        final_score = base_score - divergence_penalty * 0.5
        return max(0, min(100, final_score))

    def detect_regime(
        self,
        overall_score: float,
        bull_prob: float,
        bear_prob: float,
    ) -> str:
        if overall_score >= 85 and bull_prob >= 80:
            return "strong_bullish"
        if overall_score >= 70 and bull_prob >= 60:
            return "bullish"
        if overall_score <= 15 and bear_prob >= 80:
            return "strong_bearish"
        if overall_score <= 30 and bear_prob >= 60:
            return "bearish"
        if bear_prob >= 75 and overall_score <= 25:
            return "crash_risk"
        if bull_prob >= 75 and bear_prob >= 60:
            return "squeeze_risk"
        return "neutral"

    async def get_crash_risk(
        self,
        technical: Dict,
        onchain: Dict,
        macro: Dict,
        derivatives: Dict,
    ) -> float:
        signals = []
        weights = []

        tech_score = technical.get("score", 50) if isinstance(technical, dict) else 50
        if tech_score < 25:
            signals.append(90)
            weights.append(0.25)
        elif tech_score < 35:
            signals.append(60)
            weights.append(0.25)
        elif tech_score > 75:
            signals.append(5)
            weights.append(0.25)
        else:
            signals.append(30)
            weights.append(0.25)

        onchain_score = onchain.get("score", 50) if isinstance(onchain, dict) else 50
        if onchain_score < 25:
            signals.append(85)
            weights.append(0.15)
        elif onchain_score < 40:
            signals.append(55)
            weights.append(0.15)
        else:
            signals.append(15)
            weights.append(0.15)

        if isinstance(macro, dict):
            vix = macro.get("vix", {}).get("value", 15) if isinstance(macro.get("vix"), dict) else 15
            env = macro.get("risk_environment", "mixed")
            if vix > 30:
                signals.append(85)
                weights.append(0.20)
            elif vix > 22:
                signals.append(50)
                weights.append(0.20)
            elif env == "risk_off":
                signals.append(55)
                weights.append(0.20)
            else:
                signals.append(10)
                weights.append(0.20)

        if isinstance(derivatives, dict):
            funding = derivatives.get("funding", {})
            if isinstance(funding, dict):
                funding_signal = funding.get("signal", "neutral")
                if funding_signal == "bearish":
                    signals.append(60)
                    weights.append(0.15)
                elif funding_signal == "bullish":
                    signals.append(15)
                    weights.append(0.15)
                else:
                    signals.append(30)
                    weights.append(0.15)

            ls = derivatives.get("long_short_ratio", {})
            if isinstance(ls, dict):
                ls_val = ls.get("long_short_ratio", 1.0)
                if ls_val > 2.0:
                    signals.append(40)
                    weights.append(0.10)
                elif ls_val < 0.5:
                    signals.append(20)
                    weights.append(0.10)
                else:
                    signals.append(30)
                    weights.append(0.10)

            liqs = derivatives.get("liquidations", {})
            if isinstance(liqs, dict):
                total_long_value = liqs.get("total_long_value", 0)
                total_short_value = liqs.get("total_short_value", 0)
                total_longs = liqs.get("total_long_liquidations", 0)
                total_shorts = liqs.get("total_short_liquidations", 0)
                long_liq_total = total_long_value * max(total_longs, 1)
                short_liq_total = total_short_value * max(total_shorts, 1)
                if long_liq_total > short_liq_total * 2:
                    signals.append(50)
                    weights.append(0.15)
                elif short_liq_total > long_liq_total * 2:
                    signals.append(25)
                    weights.append(0.15)

        total_weight = sum(weights) if weights else 1
        crash_prob = sum(s * w for s, w in zip(signals, weights)) / total_weight
        return max(0, min(100, crash_prob))

    async def get_squeeze_risk(
        self,
        derivatives: Dict,
        orderflow: Dict,
        sentiment: Dict,
    ) -> Dict:
        short_squeeze_signals = []
        long_squeeze_signals = []
        weights = []

        if isinstance(derivatives, dict):
            ls = derivatives.get("long_short_ratio", {})
            if isinstance(ls, dict):
                ls_val = ls.get("long_short_ratio", 1.0)
                if ls_val < 0.4:
                    short_squeeze_signals.append(95)
                    weights.append(0.35)
                elif ls_val < 0.7:
                    short_squeeze_signals.append(70)
                    weights.append(0.35)
                else:
                    short_squeeze_signals.append(20)
                    weights.append(0.35)

                if ls_val > 2.5:
                    long_squeeze_signals.append(95)
                elif ls_val > 1.8:
                    long_squeeze_signals.append(65)
                else:
                    long_squeeze_signals.append(15)

            funding = derivatives.get("funding", {})
            if isinstance(funding, dict):
                funding_rate = abs(funding.get("funding_rate_raw", 0))
                annualized = funding.get("annualized_rate", 0)
                if abs(annualized) > 50:
                    if funding.get("signal") == "bullish":
                        short_squeeze_signals.append(80)
                    else:
                        long_squeeze_signals.append(80)
                    if len(weights) <= 1:
                        weights.append(0.25)
                elif abs(annualized) > 25:
                    if funding.get("signal") == "bullish":
                        short_squeeze_signals.append(50)
                    else:
                        long_squeeze_signals.append(50)
                    if len(weights) <= 1:
                        weights.append(0.25)

        if isinstance(orderflow, dict):
            imb = orderflow.get("imbalance", 0) if isinstance(orderflow.get("imbalance"), (int, float)) else 0
            if imb < -0.5:
                short_squeeze_signals.append(65)
                weights.append(0.20)
            elif imb > 0.5:
                long_squeeze_signals.append(65)
                weights.append(0.20)

        if isinstance(sentiment, dict):
            sent_score = sentiment.get("score", 50) if isinstance(sentiment.get("score"), (int, float)) else 50
            if sent_score < 20:
                short_squeeze_signals.append(70)
                weights.append(0.20)
            elif sent_score > 80:
                long_squeeze_signals.append(70)
                weights.append(0.20)

        if not weights:
            weights = [1.0]
        if not short_squeeze_signals:
            short_squeeze_signals = [10]
        if not long_squeeze_signals:
            long_squeeze_signals = [10]

        total_w = sum(weights) / len(short_squeeze_signals) if short_squeeze_signals else 1
        short_squeeze_prob = (
            sum(s * (w / len(short_squeeze_signals)) for s, w in zip(short_squeeze_signals, weights[:len(short_squeeze_signals)]))
            / total_w if total_w > 0 else 10
        )
        long_squeeze_prob = (
            sum(s * (w / len(long_squeeze_signals)) for s, w in zip(long_squeeze_signals, weights[:len(long_squeeze_signals)]))
            / (sum(weights[:len(long_squeeze_signals)]) / max(len(long_squeeze_signals), 1)) if sum(weights[:len(long_squeeze_signals)]) > 0 else 10
        )

        return {
            "short_squeeze_probability": max(0, min(100, short_squeeze_prob)),
            "long_squeeze_probability": max(0, min(100, long_squeeze_prob)),
        }

    def get_alt_season_signal(
        self,
        top_symbols_scores: List[float],
        btc_dominance: float,
    ) -> float:
        if not top_symbols_scores:
            return 50.0

        alt_scores = [s for s in top_symbols_scores if s != 0]
        if not alt_scores:
            return 50.0

        alt_avg = sum(alt_scores) / len(alt_scores)
        alt_score_normalized = alt_avg / 100.0

        dom_factor = max(0, 1 - (btc_dominance / 100.0))
        dom_factor = max(0, min(1, dom_factor * 2))

        signal = alt_score_normalized * 60 + dom_factor * 40
        return max(0, min(100, signal * 100))

    def get_explanation(self, factors: Dict) -> List[str]:
        explanations = []
        scores = factors.get("scores", {})
        regime = factors.get("regime", "neutral")
        overall = factors.get("overall", 50)

        if regime == "strong_bullish":
            explanations.append("Aggregate market structure strongly bullish across all timeframes")
        elif regime == "bullish":
            explanations.append("Market exhibiting bullish tendencies with aligned technicals")
        elif regime == "strong_bearish":
            explanations.append("Aggregate market structure strongly bearish across all timeframes")
        elif regime == "bearish":
            explanations.append("Market exhibiting bearish tendencies across multiple engines")
        elif regime == "crash_risk":
            explanations.append("Elevated crash risk detected: bearish alignment with on-chain distribution and macro headwinds")
        elif regime == "squeeze_risk":
            explanations.append("Extreme positioning detected: potential squeeze event imminent")
        else:
            explanations.append("Market in neutral consolidation zone")

        if scores:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1])
            lowest = sorted_scores[:2] if len(sorted_scores) >= 2 else sorted_scores
            highest = sorted_scores[-2:] if len(sorted_scores) >= 2 else sorted_scores

            for name, val in highest:
                if val > 65:
                    label = name.replace("_", " ").title()
                    explanations.append(f"{label} score strong at {val:.0f}/100")

            for name, val in lowest:
                if val < 40:
                    label = name.replace("_", " ").title()
                    explanations.append(f"{label} score weak at {val:.0f}/100 — potential headwind")

        crash = factors.get("crash_prob", 0)
        if crash > 60:
            explanations.append(f"Crash risk elevated at {crash:.0f}% — hedge or reduce exposure")
        elif crash > 40:
            explanations.append(f"Moderate crash risk at {crash:.0f}% — monitor closely")

        squeeze_ss = factors.get("short_squeeze_prob", 0)
        squeeze_ls = factors.get("long_squeeze_prob", 0)
        if squeeze_ss > 60:
            explanations.append(f"Short squeeze potential high at {squeeze_ss:.0f}% — short positions at risk")
        if squeeze_ls > 60:
            explanations.append(f"Long squeeze potential high at {squeeze_ls:.0f}% — longs at risk of liquidation cascade")

        alt_season = factors.get("alt_season_prob", 0)
        if alt_season > 70:
            explanations.append(f"Alt season signal strong at {alt_season:.0f}% — capital rotation from BTC to altcoins")
        elif alt_season < 30:
            explanations.append(f"BTC dominance high at {100 - alt_season:.0f}% — risk-off from altcoins")

        return explanations

    async def stream_brain_updates(
        self,
        symbols: List[str],
        interval: int = 60,
    ):
        while True:
            batch = []
            for symbol in symbols:
                try:
                    assessment = await self.assess_market(symbol)
                    batch.append(assessment)
                except Exception as e:
                    self._logger.error(f"Brain stream error for {symbol}: {e}")
                    batch.append({
                        "symbol": symbol,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            has_errors = any("error" in a for a in batch)
            yield {
                "type": "brain_update",
                "data": batch,
                "has_errors": has_errors,
                "batch_size": len(batch),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await asyncio.sleep(interval)

    def _compute_dynamic_weights(
        self,
        scores: Dict,
        base_weights: Dict,
    ) -> Dict:
        dynamic = dict(base_weights)
        total = len(scores)
        if total < 3:
            return dynamic

        values = [v for v in scores.values()]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)

        for key in dynamic:
            if key in scores:
                deviation = abs(scores[key] - mean)
                if std_dev > 0 and deviation > std_dev:
                    dynamic[key] *= 0.8
                elif std_dev > 0 and deviation < std_dev * 0.3:
                    dynamic[key] *= 1.1

        return dynamic

    def _score_variance(
        self,
        scores: Dict,
        weights: Dict,
        weighted_mean: float,
    ) -> float:
        values = []
        for key, w in weights.items():
            if key in scores:
                values.append((scores[key] - weighted_mean) ** 2 * w)

        if not values:
            return 0.0
        return sum(values) / sum(weights.values())

    def _compute_bull_probability(
        self,
        scores: Dict,
        engine_results: Dict,
    ) -> float:
        raw_bull = 50.0

        positive_scores = sum(1 for v in scores.values() if v > 60)
        negative_scores = sum(1 for v in scores.values() if v < 40)
        net = positive_scores - negative_scores
        raw_bull += net * 5

        technical = engine_results.get("technical", {})
        if isinstance(technical, dict):
            t_dir = technical.get("direction", "neutral")
            if t_dir == "long":
                raw_bull += 8
            elif t_dir == "short":
                raw_bull -= 8

        derivatives = engine_results.get("derivatives", {})
        if isinstance(derivatives, dict):
            agg = derivatives.get("aggregate_signal", {})
            if isinstance(agg, dict):
                if agg.get("direction") == "bullish":
                    raw_bull += 5
                elif agg.get("direction") == "bearish":
                    raw_bull -= 5

        onchain = engine_results.get("onchain", {})
        if isinstance(onchain, dict):
            combined_signal = onchain.get("combined_signal", "neutral")
            if "accumulation" in combined_signal:
                raw_bull += 6
            elif "distribution" in combined_signal:
                raw_bull -= 6

        macro = engine_results.get("macro", {})
        if isinstance(macro, dict):
            outlook = macro.get("crypto_outlook", "neutral")
            if outlook == "bullish":
                raw_bull += 5
            elif outlook == "bearish":
                raw_bull -= 5

        return max(0, min(100, raw_bull))

    def _compute_bear_probability(
        self,
        scores: Dict,
        bull_prob: float,
    ) -> float:
        bear_prob = 100 - bull_prob
        negative_scores = sum(1 for v in scores.values() if v < 35)
        very_negative = sum(1 for v in scores.values() if v < 20)
        bear_prob += negative_scores * 3 + very_negative * 2
        return max(0, min(100, bear_prob))

    def _compute_confidence(self, scores: Dict) -> float:
        values = list(scores.values())
        if not values:
            return 0

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)

        extreme_count = sum(1 for v in values if v > 75 or v < 25)
        extreme_ratio = extreme_count / len(values)

        confidence = 50.0
        if extreme_ratio > 0.6:
            confidence += 25
        elif extreme_ratio > 0.4:
            confidence += 15
        elif extreme_ratio > 0.2:
            confidence += 5

        if std_dev < 10:
            confidence -= 15
        elif std_dev > 20:
            confidence += 10

        return max(0, min(100, confidence))

    async def _get_technical_score(self, symbol: str) -> Dict:
        try:
            data = None
            if market_service:
                data = await market_service.get_ohlcv(symbol, "binance", "1h", 100)

            smc_data = None
            if data and len(data) >= 30 and smc_engine:
                smc_data = smc_engine.analyze(data)

            if institutional_scorer and data and len(data) >= 50:
                score_result = await institutional_scorer.score(symbol, data, "1h", smc_data)
                score = 50 + score_result.get("total_score", 0)
                direction = score_result.get("direction", "neutral")
                factors = []
                if direction == "long":
                    factors.append("Technical indicators aligned bullish")
                elif direction == "short":
                    factors.append("Technical indicators aligned bearish")
                return {
                    "score": max(0, min(100, score)),
                    "direction": direction,
                    "classification": score_result.get("classification", "reject"),
                    "details": score_result.get("details", {}),
                    "factors": factors,
                }

            return {"score": 50.0, "direction": "neutral", "factors": ["Technical data unavailable"]}
        except Exception as e:
            self._logger.warning(f"Technical score error for {symbol}: {e}")
            return {"score": 50.0, "direction": "neutral", "error": str(e)}

    async def _get_smc_score(self, symbol: str) -> Dict:
        try:
            data = None
            if market_service:
                data = await market_service.get_ohlcv(symbol, "binance", "1h", 100)

            if smc_engine and data and len(data) >= 30:
                smc = smc_engine.analyze(data)
                factors = []
                score = 50.0
                structure = smc.get("structure", {})
                trend = smc.get("trend", "ranging")

                if trend == "uptrend":
                    score += 15
                    factors.append("Market structure in uptrend (HH/HL)")
                elif trend == "downtrend":
                    score -= 15
                    factors.append("Market structure in downtrend (LH/LL)")
                elif trend == "expansion":
                    score += 5
                    factors.append("Market in expansion phase")
                elif trend == "contraction":
                    score -= 5
                    factors.append("Market contracting — potential breakout")

                bos_count = smc.get("net_bos", 0)
                score += max(-10, min(10, bos_count * 3))
                if bos_count > 2:
                    factors.append(f"Strong break of structure ({bos_count} net bullish BOS)")
                elif bos_count < -2:
                    factors.append(f"Bearish break of structure ({abs(bos_count)} net bearish BOS)")

                choch_count = smc.get("net_choch", 0)
                score += max(-10, min(10, choch_count * 4))
                if choch_count > 1:
                    factors.append("Change of character detected — trend shift")

                fvg_count = len(smc.get("fair_value_gaps", []))
                if fvg_count > 3:
                    factors.append(f"Multiple fair value gaps ({fvg_count}) — liquidity targets")

                sweep = smc.get("liquidity_sweep")
                if sweep:
                    factors.append(f"Liquidity sweep detected ({sweep.get('type', 'unknown')})")

                displacement = smc.get("displacement", {})
                if isinstance(displacement, dict) and displacement.get("detected"):
                    factors.append(f"Displacement move — {displacement.get('direction', 'unknown')}")

                return {
                    "score": max(0, min(100, score)),
                    "trend": trend,
                    "structure": structure,
                    "bos_count": smc.get("bos_count", 0),
                    "choch_count": smc.get("choch_count", 0),
                    "factors": factors,
                }

            return {"score": 50.0, "factors": ["SMC analysis unavailable"]}
        except Exception as e:
            self._logger.warning(f"SMC score error for {symbol}: {e}")
            return {"score": 50.0, "error": str(e)}

    async def _get_orderflow_score(self, symbol: str) -> Dict:
        try:
            if not orderflow_engine:
                return {"score": 50.0, "factors": ["Order flow engine unavailable"]}

            bid_data = await self._get_orderbook_side(symbol, "bids")
            ask_data = await self._get_orderbook_side(symbol, "asks")
            trades_data = await self._get_recent_trades(symbol)

            if not bid_data or not ask_data:
                return {"score": 50.0, "factors": ["Order book data unavailable"]}

            snapshot = orderflow_engine.get_aggregated_snapshot(
                symbol, bid_data, ask_data, trades_data or []
            )

            score = 50.0
            factors = []
            ob = snapshot.get("orderbook", {})
            imb = ob.get("imbalance", 0)
            if imb > 0.3:
                score += 10
                factors.append("Strong order book bid pressure")
            elif imb < -0.3:
                score -= 10
                factors.append("Strong order book ask pressure")

            trades = snapshot.get("trades", {})
            bsr = trades.get("buy_sell_ratio", 1.0)
            if bsr > 1.5:
                score += 8
                factors.append("Aggressive buying dominates recent trades")
            elif bsr < 0.67:
                score -= 8
                factors.append("Aggressive selling dominates recent trades")

            cvd = snapshot.get("cumulative_volume_delta") or trades.get("cumulative_volume_delta", 0)
            if cvd > 0:
                score += 4
            elif cvd < 0:
                score -= 4

            large = ob.get("large_orders", {})
            large_bids = large.get("bid_count", 0)
            large_asks = large.get("ask_count", 0)
            if large_bids > large_asks * 2:
                score += 5
                factors.append("Large institutional bids detected")
            elif large_asks > large_bids * 2:
                score -= 5
                factors.append("Large institutional asks detected")

            vacuum = ob.get("liquidity_vacuum", {}).get("count", 0)
            if vacuum > 3:
                factors.append(f"Liquidity vacuums detected ({vacuum} zones) — slippage risk")

            return {
                "score": max(0, min(100, score)),
                "imbalance": imb,
                "buy_sell_ratio": bsr,
                "cvd": cvd,
                "market_mood": snapshot.get("market_mood", "neutral"),
                "factors": factors,
            }
        except Exception as e:
            self._logger.warning(f"Orderflow score error for {symbol}: {e}")
            return {"score": 50.0, "error": str(e)}

    async def _get_derivatives_score(self, symbol: str) -> Dict:
        try:
            if not derivatives_engine:
                return {"score": 50.0, "factors": ["Derivatives engine unavailable"]}

            raw_symbol = symbol.replace("/USDT", "USDT")

            funding_data = None
            oi_data = None
            ticker_data = None
            if market_service:
                funding_data = await market_service.get_funding_rate(symbol)
                oi_data = await market_service.get_open_interest(symbol)
                ticker_data = await market_service.get_ticker(symbol)

            funding_rate = 0.0
            if funding_data and isinstance(funding_data, dict):
                funding_rate = funding_data.get("funding_rate", 0) or 0

            oi_current = 0.0
            oi_change_24h = 0.0
            if oi_data and isinstance(oi_data, dict):
                oi_current = oi_data.get("open_interest", 0) or 0
                oi_change_24h = oi_data.get("change_percent", 0) or 0

            price_change_24h = None
            if ticker_data and isinstance(ticker_data, dict):
                price_change_24h = (ticker_data.get("change_percent", 0) or 0) / 100.0

            nft = datetime.now(timezone.utc)

            snapshot = derivatives_engine.get_aggregated_derivatives_snapshot(
                symbol=symbol,
                funding_rate=funding_rate,
                next_funding_time=nft,
                oi_current=oi_current,
                oi_change_24h=oi_change_24h,
                price_change_24h=price_change_24h,
            )

            score = 50.0
            factors = []
            agg = snapshot.get("aggregate_signal", {})
            if agg.get("direction") == "bullish":
                score += 12
                factors.append("Derivatives aggregate signal bullish")
            elif agg.get("direction") == "bearish":
                score -= 12
                factors.append("Derivatives aggregate signal bearish")

            funding = snapshot.get("funding", {})
            if isinstance(funding, dict):
                ann = funding.get("annualized_rate", 0)
                if ann > 30:
                    score -= 8
                    factors.append(f"Funding expensive (annualized {ann:.1f}%) — crowded long")
                elif ann < -30:
                    score += 8
                    factors.append(f"Negative funding ({ann:.1f}% annualized) — shorts paying")

            oi = snapshot.get("open_interest", {})
            if isinstance(oi, dict):
                div = oi.get("divergence")
                if div == "confirmation_bullish":
                    score += 6
                    factors.append("OI rising with price — strong bullish confirmation")
                elif div == "confirmation_bearish":
                    score -= 6
                    factors.append("OI rising as price falls — distribution")

            ls = snapshot.get("long_short_ratio", {})
            if isinstance(ls, dict):
                ls_val = ls.get("long_short_ratio", 1.0)
                if ls_val < 0.5:
                    score += 8
                    factors.append("Extreme short positioning — squeeze setup")
                elif ls_val > 2.0:
                    score -= 8
                    factors.append("Extreme long positioning — crowded trade")

            liqs = snapshot.get("liquidations", {})
            if isinstance(liqs, dict):
                total_long_liq_value = liqs.get("total_long_value", 0)
                total_short_liq_value = liqs.get("total_short_value", 0)
                if total_long_liq_value > total_short_liq_value * 3:
                    score -= 5
                    factors.append("Large long liquidations — cascading risk")
                elif total_short_liq_value > total_long_liq_value * 3:
                    score += 5
                    factors.append("Large short liquidations — squeeze fuel")

            return {
                "score": max(0, min(100, score)),
                "aggregate_signal": agg,
                "funding": funding,
                "open_interest": oi,
                "long_short_ratio": ls,
                "factors": factors,
            }
        except Exception as e:
            self._logger.warning(f"Derivatives score error for {symbol}: {e}")
            return {"score": 50.0, "error": str(e)}

    async def _get_macro_score(self) -> Dict:
        try:
            if not macro_engine:
                return {"score": 50.0, "factors": ["Macro engine unavailable"]}

            snapshot = macro_engine.get_macro_snapshot()
            if not snapshot.get("available"):
                return {"score": None, "available": False, "factors": ["Macro data unavailable"]}
            score = 50.0
            factors = []

            risk_score = snapshot.get("risk_score", 50)
            score += (risk_score - 50) * 0.5

            env = snapshot.get("risk_environment", "mixed")
            if env == "risk_on":
                factors.append("Risk-on macro environment supporting crypto")
                score += 8
            elif env == "risk_off":
                factors.append("Risk-off macro environment pressuring crypto")
                score -= 8

            outlook = snapshot.get("crypto_outlook", "neutral")
            if outlook == "bullish":
                score += 6
            elif outlook == "bearish":
                score -= 6

            indicators = snapshot.get("indicators", {})
            vix_data = indicators.get("vix", {})
            if isinstance(vix_data, dict):
                vix = vix_data.get("value", 15)
                if vix > 25:
                    score -= 8
                    factors.append(f"VIX elevated ({vix:.1f}) — fear in markets")
                elif vix < 14:
                    score += 5
                    factors.append(f"VIX low ({vix:.1f}) — complacency")

            dxy_data = indicators.get("dxy", {})
            if isinstance(dxy_data, dict):
                dxy_trend = dxy_data.get("trend", "neutral")
                dxy_val = dxy_data.get("value", 104)
                if dxy_trend == "bullish" and dxy_val > 105:
                    score -= 6
                    factors.append(f"DXY strengthening ({dxy_val:.1f}) — dollar headwind")
                elif dxy_trend == "bearish" and dxy_val < 101:
                    score += 4
                    factors.append(f"DXY weakening ({dxy_val:.1f}) — dollar tailwind")

            fundamentals = snapshot.get("fundamentals", {})
            rate_data = fundamentals.get("interest_rate", {})
            if isinstance(rate_data, dict):
                cycle = rate_data.get("cycle_phase", "neutral")
                if cycle == "restrictive":
                    score -= 5
                    factors.append("Restrictive Fed policy — headwind for risk assets")
                elif cycle == "accommodative":
                    score += 5
                    factors.append("Accommodative Fed policy — supportive for crypto")

            etf = snapshot.get("etf_flows", {})
            if isinstance(etf, dict):
                etf_sentiment = etf.get("sentiment", "neutral")
                if etf_sentiment == "bullish":
                    score += 5
                    factors.append("Positive ETF flows — institutional demand")
                elif etf_sentiment == "bearish":
                    score -= 5
                    factors.append("Negative ETF flows — institutional selling")

            return {
                "score": max(0, min(100, score)),
                "risk_environment": env,
                "risk_score": risk_score,
                "crypto_outlook": outlook,
                "vix": vix_data,
                "dxy": dxy_data,
                "factors": factors,
            }
        except Exception as e:
            self._logger.warning(f"Macro score error: {e}")
            return {"score": 50.0, "error": str(e)}

    async def _get_onchain_score(self, symbol: str) -> Dict:
        try:
            if not onchain_engine:
                return {"score": 50.0, "factors": ["On-chain engine unavailable"]}

            snapshot = onchain_engine.get_onchain_snapshot(symbol)
            if not snapshot.get("available"):
                return {"score": None, "available": False, "factors": ["On-chain data unavailable"]}
            score = snapshot.get("combined_score", 50.0)
            factors = []

            combined_signal = snapshot.get("combined_signal", "neutral")
            if "strong_accumulation" in combined_signal:
                factors.append("Strong on-chain accumulation — exchange outflows high")
            elif combined_signal == "accumulation":
                factors.append("On-chain accumulation detected")
            elif "strong_distribution" in combined_signal:
                factors.append("Strong on-chain distribution — exchange inflows high")
            elif combined_signal == "distribution":
                factors.append("On-chain distribution detected")

            whale = snapshot.get("whale_activity", {})
            if isinstance(whale, dict):
                if whale.get("accumulation"):
                    score += 5
                    if not any("accumulation" in f for f in factors):
                        factors.append("Whale accumulation detected")
                if whale.get("distribution"):
                    score -= 5
                    if not any("distribution" in f for f in factors):
                        factors.append("Whale distribution detected")

            reserves = snapshot.get("exchange_reserves", {})
            if isinstance(reserves, dict):
                reserve_trend = reserves.get("trend", "stable")
                if reserve_trend == "distributing":
                    score -= 4
                    factors.append("Exchange reserves rising — selling pressure")

            dormant = snapshot.get("dormant_supply", {})
            if isinstance(dormant, dict):
                if dormant.get("awakening_detected"):
                    score -= 3
                    factors.append("Dormant supply awakening — potential selling")

            stablecoin = onchain_engine.get_stablecoin_flow()
            if isinstance(stablecoin, dict) and "error" not in stablecoin:
                if stablecoin.get("market_signal") == "bullish":
                    score += 4
                    factors.append("Stablecoin inflows rising — buying power accumulating")
                elif stablecoin.get("market_signal") == "bearish":
                    score -= 4
                    factors.append("Stablecoin outflows rising — selling pressure")

            return {
                "score": max(0, min(100, score)),
                "combined_signal": combined_signal,
                "whale_accumulation": whale.get("accumulation", False) if isinstance(whale, dict) else False,
                "whale_distribution": whale.get("distribution", False) if isinstance(whale, dict) else False,
                "factors": factors,
            }
        except Exception as e:
            self._logger.warning(f"On-chain score error for {symbol}: {e}")
            return {"score": 50.0, "error": str(e)}

    async def _get_sentiment_score(self, symbol: str) -> Dict:
        try:
            if not social_sentiment:
                return {"score": 50.0, "factors": ["Social sentiment engine unavailable"]}

            snapshot = social_sentiment.get_social_sentiment_snapshot(symbol)
            if not snapshot.get("available"):
                return {"score": None, "available": False, "factors": ["Social sentiment unavailable"]}
            score = snapshot.get("combined_score", 50.0)
            factors = []

            classification = snapshot.get("classification", "neutral")
            if classification == "extreme_greed":
                score -= 5
                factors.append("Extreme greed in social sentiment — potential top")
            elif classification == "greed":
                score += 3
                factors.append("Greed sentiment — retail bullish")
            elif classification == "fear":
                score -= 3
                factors.append("Fear sentiment — retail bearish")
            elif classification == "extreme_fear":
                score += 5
                factors.append("Extreme fear — potential bottom")

            fomo = snapshot.get("fomo_index", 0)
            if fomo > 60:
                score -= 4
                factors.append("FOMO index elevated — euphoria risk")

            fear_idx = snapshot.get("fear_index", 0)
            if fear_idx > 60:
                score += 3
                factors.append("High fear index — contrarian buy signal")

            return {
                "score": max(0, min(100, score)),
                "classification": classification,
                "fomo_index": fomo,
                "fear_index": fear_idx,
                "factors": factors,
            }
        except Exception as e:
            self._logger.warning(f"Sentiment score error for {symbol}: {e}")
            return {"score": 50.0, "error": str(e)}

    async def _get_whale_score(self, symbol: str) -> Dict:
        try:
            if not whale_tracker:
                return {"score": 50.0, "factors": ["Whale tracker unavailable"]}

            alerts = await whale_tracker.get_alerts(since_hours=24)
            score = 50.0
            factors = []

            relevant = [a for a in alerts if a.get("symbol", "") in symbol.upper()]

            bullish_whales = sum(1 for a in relevant if a.get("direction") == "bullish")
            bearish_whales = sum(1 for a in relevant if a.get("direction") == "bearish")

            if bullish_whales > bearish_whales:
                score += 8
                factors.append(f"{bullish_whales} bullish whale moves vs {bearish_whales} bearish")
            elif bearish_whales > bullish_whales:
                score -= 8
                factors.append(f"{bearish_whales} bearish whale moves vs {bullish_whales} bullish")

            high_impact = [a for a in relevant if a.get("impact", 0) > 80]
            if high_impact:
                for alert in high_impact[:2]:
                    factors.append(f"High-impact whale move: {alert.get('type', 'transfer')} {alert.get('direction', 'unknown')}")

            all_high_impact = [a for a in alerts if a.get("impact", 0) > 80]
            net_direction = sum(
                1 for a in all_high_impact if a.get("direction") == "bullish"
            ) - sum(1 for a in all_high_impact if a.get("direction") == "bearish")
            if net_direction > 0:
                score += 4
            elif net_direction < 0:
                score -= 4

            return {
                "score": max(0, min(100, score)),
                "whale_alerts_count": len(alerts),
                "relevant_count": len(relevant),
                "bullish_whales": bullish_whales,
                "bearish_whales": bearish_whales,
                "factors": factors,
            }
        except Exception as e:
            self._logger.warning(f"Whale score error for {symbol}: {e}")
            return {"score": 50.0, "error": str(e)}

    async def _get_risk_score(self) -> Dict:
        try:
            return {"score": 50.0, "factors": ["Portfolio risk: neutral (no active session)"]}
        except Exception as e:
            self._logger.warning(f"Risk score error: {e}")
            return {"score": 50.0, "error": str(e)}

    async def _get_orderbook_side(
        self,
        symbol: str,
        side: str,
    ) -> List[Dict]:
        try:
            raw_symbol = symbol.replace("/", "").upper()
            if market_service:
                ob = await market_service.get_orderbook(symbol)
                if isinstance(ob, dict):
                    return ob.get(side, [])
            return []
        except Exception:
            return []

    async def _get_recent_trades(self, symbol: str) -> List[Dict]:
        try:
            if market_service:
                data = await market_service.get_recent_trades(symbol, limit=100)
                if isinstance(data, list):
                    return data
            return []
        except Exception:
            return []

    async def _get_top_symbols_scores(self) -> List[float]:
        try:
            if not market_coverage:
                return []
            symbols = await market_coverage.get_top_symbols(count=10)
            scores = []
            for s in symbols:
                try:
                    assessment = await self.assess_market(s)
                    scores.append(assessment.get("overall_market_score", 50))
                except Exception:
                    scores.append(50)
            return scores
        except Exception:
            return []

    async def _get_btc_dominance(self) -> float:
        try:
            if market_service:
                dom = await market_service.get_btc_dominance()
                if isinstance(dom, (int, float)):
                    return float(dom)
            return 55.0
        except Exception:
            return 55.0

    def _empty_assessment(self, symbol: str, error: str) -> Dict:
        return {
            "symbol": symbol,
            "overall_market_score": 50.0,
            "bull_probability": 50.0,
            "bear_probability": 50.0,
            "crash_probability": 5.0,
            "short_squeeze_probability": 5.0,
            "long_squeeze_probability": 5.0,
            "alt_season_probability": 50.0,
            "confidence": 0.0,
            "regime": "neutral",
            "contributing_factors": [f"Assessment failed: {error}"],
            "sub_scores": {},
            "engine_results": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error,
        }


ai_brain = AICentralBrain()
