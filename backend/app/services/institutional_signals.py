"""
Institutional Signal Engine

Integrates:
- Multi-timeframe analysis
- Institutional scoring (100-point)
- SMC/ICT engine
- Professional risk engine
- Real market data

Produces comprehensive signals with all required fields.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, List
from app.services.market import market_service
from app.services.institutional_scoring import institutional_scorer
from app.services.smc_engine import smc_engine
from app.services.multi_timeframe import multi_timeframe
from app.services.professional_risk import professional_risk
from app.services.indicators import indicator_service
from app.core.logging import logger


class InstitutionalSignalEngine:
    def __init__(self):
        self._scan_lock = asyncio.Lock()

    async def generate_signal(
        self,
        symbol: str,
        timeframe: str = "1h",
        capital: float = 10000,
        risk_percent: float = 0.02,
    ) -> dict:
        from app.core.cache import cache_get, cache_set

        cache_key = (
            f"institutional:signal:{symbol}:{timeframe}:"
            f"{capital:.2f}:{risk_percent:.4f}"
        )
        cached = await cache_get(cache_key)
        if isinstance(cached, dict):
            return cached

        data = await market_service.get_ohlcv(symbol, "binance", timeframe, 200)
        if not data or len(data) < 50:
            result = self._empty_signal(symbol, timeframe, "Insufficient OHLCV data")
            await cache_set(cache_key, result, ttl=10)
            return result

        current_price = data[-1]["close"]

        smc_data = smc_engine.analyze(data)
        inst_score = await institutional_scorer.score(symbol, data, timeframe, smc_data)

        details = inst_score.get("details", {})
        atr = details.get("atr") or indicator_service.latest_atr(data)

        direction = inst_score["direction"]
        abs_score = inst_score["abs_score"]
        if abs_score < 70:
            result = {
                **self._empty_signal(symbol, timeframe, f"Score {abs_score}/100 below 70 threshold"),
                "institutional_score": inst_score,
                "direction": direction,
                "confidence": abs_score,
                "current_price": round(current_price, 4),
            }
            await cache_set(cache_key, result, ttl=15)
            return result

        # The expensive six-timeframe and derivatives analysis only adds value
        # after the primary institutional score passes the execution gate.
        mtf, futures_data = await asyncio.gather(
            multi_timeframe.analyze(symbol),
            self._get_futures_data(symbol),
        )
        if direction == "neutral":
            aggregated = mtf.get("aggregated")
            if aggregated and aggregated.get("direction") != "neutral":
                direction = aggregated["direction"]
                inst_score["direction"] = direction

        entry_zone = self._calculate_entry_zone(current_price, atr, direction)
        stop_loss = self._calculate_stop_loss(current_price, atr, data, direction, smc_data)
        tp1, tp2, tp3 = self._calculate_take_profits(entry_zone["mid"], stop_loss, direction, inst_score)

        rr1 = abs(tp1 - entry_zone["mid"]) / abs(entry_zone["mid"] - stop_loss) if abs(entry_zone["mid"] - stop_loss) > 0 else 0
        rr2 = abs(tp2 - entry_zone["mid"]) / abs(entry_zone["mid"] - stop_loss) if abs(entry_zone["mid"] - stop_loss) > 0 else 0
        rr3 = abs(tp3 - entry_zone["mid"]) / abs(entry_zone["mid"] - stop_loss) if abs(entry_zone["mid"] - stop_loss) > 0 else 0

        risk_result = professional_risk.calculate_position_size(
            capital=capital,
            entry_price=entry_zone["mid"],
            stop_loss=stop_loss,
            risk_percent=risk_percent,
            atr_value=atr,
        )

        invalidation = self._calculate_invalidation(current_price, direction, smc_data, data)

        score_details = inst_score.get("scores", {})
        reasons = self._build_reasons(direction, inst_score, smc_data, mtf, futures_data)

        hold_time = self._estimate_hold_time(timeframe, direction)

        alignment = mtf.get("alignment", {})
        major_aligned = alignment.get("major_aligned", False) if alignment else False

        if not major_aligned and abs_score > 80:
            abs_score = min(abs_score, 80)

        classification = "institutional_grade" if abs_score >= 95 else \
                         "excellent" if abs_score >= 90 else \
                         "very_strong" if abs_score >= 85 else \
                         "strong" if abs_score >= 80 else "watchlist"

        validation = professional_risk.validate_trade(
            symbol=symbol,
            direction=direction,
            entry_price=entry_zone["mid"],
            stop_loss=stop_loss,
            take_profit=tp1,
            leverage=risk_result.get("leverage", 1),
            balance=capital,
            atr_value=atr,
            data=data,
        )

        trade_request = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_zone["mid"],
            "stop_loss": stop_loss,
            "take_profit": tp1,
            "leverage": risk_result.get("leverage", 1),
            "balance": capital,
            "quantity": risk_result.get("position_size", 0),
            "current_price": current_price,
        }
        execution = await self._get_execution_approval(trade_request)

        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "current_price": round(current_price, 4),
            "direction": direction,
            "confidence": round(abs_score, 1),
            "classification": classification,
            "entry_zone": entry_zone,
            "stop_loss": round(stop_loss, 4),
            "take_profit_1": round(tp1, 4),
            "take_profit_2": round(tp2, 4),
            "take_profit_3": round(tp3, 4),
            "risk_reward_1": round(rr1, 2),
            "risk_reward_2": round(rr2, 2),
            "risk_reward_3": round(rr3, 2),
            "risk_percent": round(abs(entry_zone["mid"] - stop_loss) / entry_zone["mid"] * 100, 2),
            "reward_percent_1": round(abs(tp1 - entry_zone["mid"]) / entry_zone["mid"] * 100, 2),
            "expected_hold_time": hold_time,
            "invalidation": invalidation,
            "reasons": reasons,
            "institutional_score": inst_score,
            "multi_timeframe": mtf.get("aggregated"),
            "alignment": alignment,
            "market_structure": {
                "trend": smc_data.get("trend", "unknown"),
                "bos_count": smc_data.get("bos_count", 0),
                "choch_count": smc_data.get("choch_count", 0),
                "liquidity_sweep": smc_data.get("liquidity_sweep"),
                "premium_discount": smc_data.get("premium_discount", {}),
                "displacement": smc_data.get("displacement"),
            },
            "futures": futures_data,
            "position_sizing": risk_result,
            "validation": validation,
            "execution": execution,
            "indicators": {
                key: details.get(key) for key in
                ["rsi", "macd_histogram", "adx", "supertrend", "atr", "volume_ratio"]
                if details.get(key) is not None
            },
        }
        await cache_set(cache_key, result, ttl=15)
        return result

    async def scan_all(self, min_score: float = 70, limit: int = 10) -> List[dict]:
        from app.services.market_coverage import market_coverage
        from app.core.cache import cache_get, cache_set

        cache_key = "institutional:scan:all"
        cached = await cache_get(cache_key)
        if isinstance(cached, list):
            return [
                signal for signal in cached
                if signal.get("confidence", 0) >= min_score
            ][:limit]

        async with self._scan_lock:
            cached = await cache_get(cache_key)
            if isinstance(cached, list):
                return [
                    signal for signal in cached
                    if signal.get("confidence", 0) >= min_score
                ][:limit]

            symbols = await market_coverage.get_top_symbols(30)
            semaphore = asyncio.Semaphore(6)

            async def analyze_symbol(symbol: str) -> Optional[dict]:
                async with semaphore:
                    try:
                        return await self.generate_signal(symbol)
                    except Exception as e:
                        logger.debug(f"Scan error {symbol}: {e}")
                return None

            scanned = await asyncio.gather(
                *(analyze_symbol(symbol) for symbol in symbols),
            )
            results = [signal for signal in scanned if signal is not None]
            results.sort(key=lambda r: r.get("confidence", 0), reverse=True)
            await cache_set(cache_key, results, ttl=30)
            return [
                signal for signal in results
                if signal.get("confidence", 0) >= min_score
            ][:limit]

    def _calculate_entry_zone(self, price: float, atr: float, direction: str) -> dict:
        if direction == "long":
            atr_offset = atr * 0.3 if atr else price * 0.003
            return {
                "min": round(price * 0.995, 4),
                "max": round(price * 1.002, 4),
                "mid": round(price, 4),
            }
        else:
            atr_offset = atr * 0.3 if atr else price * 0.003
            return {
                "min": round(price * 0.998, 4),
                "max": round(price * 1.005, 4),
                "mid": round(price, 4),
            }

    def _calculate_stop_loss(self, price: float, atr: float, data: list,
                              direction: str, smc_data: dict) -> float:
        atr_stop = professional_risk.calculate_atr_stop(data, 1.5, direction)

        if smc_data:
            order_blocks = smc_data.get("order_blocks", [])
            if direction == "long":
                for ob in order_blocks:
                    if ob["type"] == "bearish" and ob["price_low"] < price:
                        return ob["price_low"]
            else:
                for ob in order_blocks:
                    if ob["type"] == "bullish" and ob["price_high"] > price:
                        return ob["price_high"]

        if atr_stop:
            return atr_stop

        if direction == "long":
            return round(price * 0.97, 4)
        return round(price * 1.03, 4)

    def _calculate_take_profits(self, entry: float, stop: float, direction: str,
                                 score: dict) -> tuple:
        risk = abs(entry - stop)
        abs_score = score.get("abs_score", 50)
        rr_multiplier = 1 + (abs_score / 100)

        if direction == "long":
            tp1 = entry + risk * 1.5
            tp2 = entry + risk * 3.0
            tp3 = entry + risk * 5.0
        else:
            tp1 = entry - risk * 1.5
            tp2 = entry - risk * 3.0
            tp3 = entry - risk * 5.0

        return tp1, tp2, tp3

    def _calculate_invalidation(self, price: float, direction: str,
                                 smc_data: dict, data: list) -> str:
        if direction == "long":
            if smc_data:
                pools = smc_data.get("liquidity_pools", [])
                for p in pools:
                    if p["type"] == "sell_side" and p["price"] < price:
                        return f"Price breaks below sell-side liquidity at {p['price']}"
            return f"Price closes below {price * 0.97:.2f} (3% drop from current)"
        else:
            if smc_data:
                pools = smc_data.get("liquidity_pools", [])
                for p in pools:
                    if p["type"] == "buy_side" and p["price"] > price:
                        return f"Price breaks above buy-side liquidity at {p['price']}"
            return f"Price closes above {price * 1.03:.2f} (3% rise from current)"

    def _build_reasons(self, direction: str, score: dict, smc: dict,
                        mtf: dict, futures: Optional[dict]) -> List[str]:
        reasons = []
        scores = score.get("scores", {})

        if direction == "long":
            if scores.get("trend", 0) > 5:
                reasons.append(f"Strong bullish trend ({scores['trend']:.0f}/20)")
            if scores.get("momentum", 0) > 5:
                reasons.append(f"Positive momentum ({scores['momentum']:.0f}/15)")
            if scores.get("volume", 0) > 5:
                reasons.append(f"Volume confirmation ({scores['volume']:.0f}/15)")
            if scores.get("smc", 0) > 5:
                reasons.append(f"SMC structure bullish ({scores['smc']:.0f}/20)")
        else:
            if scores.get("trend", 0) < -5:
                reasons.append(f"Strong bearish trend ({abs(scores['trend']):.0f}/20)")
            if scores.get("momentum", 0) < -5:
                reasons.append(f"Negative momentum ({abs(scores['momentum']):.0f}/15)")
            if scores.get("volume", 0) < -5:
                reasons.append(f"Volume confirms bearish ({abs(scores['volume']):.0f}/15)")
            if scores.get("smc", 0) < -5:
                reasons.append(f"SMC structure bearish ({abs(scores['smc']):.0f}/20)")

        if smc:
            trend = smc.get("trend", "")
            if direction == "long" and trend in ("uptrend", "expansion"):
                reasons.append(f"Market in {trend} phase")
            elif direction == "short" and trend in ("downtrend", "contraction"):
                reasons.append(f"Market in {trend} phase")

            liq_sweep = smc.get("liquidity_sweep")
            if liq_sweep:
                reasons.append(f"Liquidity sweep: {liq_sweep['type']}")

            disp = smc.get("displacement")
            if disp and disp.get("detected"):
                reasons.append(f"Displacement move: {disp['direction']} ({disp.get('move_percent', 0)}%)")

            pd = smc.get("premium_discount", {})
            zone = pd.get("zone", "")
            if zone in ("discount", "deep_discount") and direction == "long":
                reasons.append(f"Price in discount zone ({zone})")
            elif zone in ("premium", "premium_high") and direction == "short":
                reasons.append(f"Price in premium zone ({zone})")

        if mtf and mtf.get("aggregated"):
            agg = mtf["aggregated"]
            reasons.append(f"Multi-timeframe: {agg.get('timeframe_count', 0)} TFs aligned {direction}")
            alignment = mtf.get("alignment", {})
            if alignment.get("major_aligned"):
                reasons.append("Major timeframes aligned (1W/1D/4H)")

        if futures:
            fp = futures.get("funding_pressure", "neutral")
            if fp == "bullish" and direction == "long":
                reasons.append("Funding rate favors longs")
            elif fp == "bearish" and direction == "short":
                reasons.append("Funding rate favors shorts")
            fr = futures.get("funding_rate", 0)
            if abs(fr) > 0.005:
                reasons.append(f"Elevated funding: {fr:.4f}%")

        return reasons[:8]

    def _estimate_hold_time(self, timeframe: str, direction: str) -> str:
        mapping = {
            "1w": "1-4 weeks",
            "1d": "1-7 days",
            "4h": "12-48 hours",
            "1h": "4-24 hours",
            "15m": "30-120 minutes",
            "5m": "10-30 minutes",
        }
        return mapping.get(timeframe, "1-24 hours")

    async def _get_futures_data(self, symbol: str) -> Optional[dict]:
        try:
            from app.services.market import market_service

            funding, oi, ticker = await asyncio.gather(
                market_service.get_funding_rate(symbol),
                market_service.get_open_interest(symbol),
                market_service.get_ticker(symbol),
                return_exceptions=True,
            )
            result = {"funding": funding, "oi": oi, "ticker": ticker}
        except Exception:
            return None

        if not result:
            return None

        funding_rate = result["funding"].get("funding_rate", 0) if result.get("funding") else 0
        oi_value = result["oi"].get("open_interest", 0) if result.get("oi") else 0
        price = result["ticker"].get("price", 0) if result.get("ticker") else 0

        funding_pressure = "bullish" if funding_rate < -0.005 else "bearish" if funding_rate > 0.005 else "neutral"

        return {
            "funding_rate": round(funding_rate, 6),
            "funding_rate_8h": round(funding_rate * 3, 6),
            "funding_pressure": funding_pressure,
            "open_interest": round(oi_value, 2),
            "open_interest_usd": round(oi_value * price, 0) if price else 0,
        }

    def _empty_signal(self, symbol: str, timeframe: str, reason: str) -> dict:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "error": reason,
            "direction": "neutral",
            "confidence": 0,
            "classification": "reject",
            "reasons": [reason],
        }


    async def _get_execution_approval(self, trade_request: dict) -> dict:
        try:
            from app.services.execution_engine import execution_engine
            approval = await execution_engine.get_trade_approval(trade_request)
            plan = await execution_engine.get_execution_plan(trade_request)
            slippage = await execution_engine.estimate_slippage(
                trade_request["symbol"],
                trade_request.get("quantity", 0),
                trade_request["direction"],
            )
            return {
                "approved": approval.get("approved", False),
                "risk_score": approval.get("risk_score", 0),
                "risk_label": approval.get("risk_label", "unknown"),
                "rejection_reasons": approval.get("rejection_reasons", []),
                "execution_plan": plan,
                "estimated_slippage": slippage,
            }
        except Exception as e:
            return {
                "approved": False,
                "risk_score": 100,
                "risk_label": "unvalidated",
                "rejection_reasons": ["Execution gate unavailable"],
                "note": f"Signal is not trade-eligible because execution validation failed: {e}",
            }


institutional_signal_engine = InstitutionalSignalEngine()
