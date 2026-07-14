"""
Execution Engine — Phase 20

Pre-trade validation gate that enforces ALL checks before trade execution.
Every trade must pass every check to be approved.
"""

import asyncio
import math
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from app.core.logging import logger

try:
    from app.services.professional_risk import professional_risk
    HAS_PROFESSIONAL_RISK = True
except ImportError:
    professional_risk = None
    HAS_PROFESSIONAL_RISK = False
    logger.warning("ExecutionEngine: professional_risk not available")

try:
    from app.services.smc_engine import smc_engine
    HAS_SMC_ENGINE = True
except ImportError:
    smc_engine = None
    HAS_SMC_ENGINE = False
    logger.warning("ExecutionEngine: smc_engine not available")

try:
    from app.services.market import market_service
    HAS_MARKET_SERVICE = True
except ImportError:
    market_service = None
    HAS_MARKET_SERVICE = False
    logger.warning("ExecutionEngine: market_service not available")


class ExecutionEngine:
    MAX_SPREAD_PCT: float = 0.001
    MAX_LEVERAGE: int = 125
    MIN_LIQUIDATION_DISTANCE: float = 0.05
    MIN_RISK_REWARD: float = 1.5
    MAX_CORRELATION_SCORE: float = 0.7
    MAX_FUNDING_RATE_ABS: float = 0.01

    async def validate_trade(self, trade_request: Dict) -> Dict:
        symbol = trade_request.get("symbol", "")
        direction = trade_request.get("direction", "long")
        entry = trade_request.get("entry_price", 0)
        sl = trade_request.get("stop_loss", 0)
        tp = trade_request.get("take_profit", 0)
        leverage = trade_request.get("leverage", 1)
        balance = trade_request.get("balance", 0)
        quantity = trade_request.get("quantity", 0)
        price = trade_request.get("price", entry)
        portfolio = trade_request.get("portfolio", {})
        timeframe = trade_request.get("timeframe", "1h")

        checks = {}

        trend_check = await self.check_trend_alignment(symbol, direction, timeframe)
        checks["trend_alignment"] = trend_check

        liquidity_check = await self.check_liquidity(symbol)
        checks["liquidity"] = liquidity_check

        spread_check = await self.check_spread(symbol)
        checks["spread"] = spread_check

        funding_check = await self.check_funding(symbol)
        checks["funding"] = funding_check

        correlation_check = await self.check_correlation(symbol, portfolio)
        checks["correlation"] = correlation_check

        risk_check = await self.check_risk(symbol, direction, entry, sl, tp, leverage, balance)
        checks["risk"] = risk_check

        margin_check = await self.check_margin(leverage, quantity * price if quantity else 0, balance)
        checks["margin"] = margin_check

        lev_check = await self.check_leverage(symbol, leverage)
        checks["leverage"] = lev_check

        filters_check = await self.check_exchange_filters(symbol, quantity, price)
        checks["exchange_filters"] = filters_check

        liq_dist_check = await self.check_liquidation_distance(entry, sl, leverage)
        checks["liquidation_distance"] = liq_dist_check

        all_passed = all(check.get("passed", False) for check in checks.values())

        return {
            "symbol": symbol,
            "direction": direction,
            "passed": all_passed,
            "checks": checks,
            "check_count": len(checks),
            "passed_count": sum(1 for c in checks.values() if c.get("passed", False)),
            "failed_count": sum(1 for c in checks.values() if not c.get("passed", False)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def check_trend_alignment(self, symbol: str, direction: str, timeframe: str = "1h") -> Dict:
        if not HAS_SMC_ENGINE or not HAS_MARKET_SERVICE:
            return {"check": "trend_alignment", "passed": True, "reason": "Skipped — SMC engine or market service unavailable"}

        try:
            data = await market_service.get_ohlcv(symbol, "binance", timeframe, 100)
            if not data or len(data) < 30:
                return {"check": "trend_alignment", "passed": True, "reason": "Insufficient data, skipped"}

            smc_result = smc_engine.analyze(data)
            if "error" in smc_result:
                return {"check": "trend_alignment", "passed": True, "reason": f"SMC analysis unavailable: {smc_result['error']}"}

            trend = smc_result.get("trend", "ranging")
            structure = smc_result.get("structure", {})

            direction_map = {
                "long": ("uptrend", "expansion"),
                "short": ("downtrend", "contraction"),
            }
            favorable_trends = direction_map.get(direction, ())

            if trend in favorable_trends:
                return {
                    "check": "trend_alignment",
                    "passed": True,
                    "trend": trend,
                    "direction": direction,
                    "reason": f"Trend {trend} aligns with {direction} trade",
                }

            net_bos = smc_result.get("net_bos", 0)
            if direction == "long" and net_bos > 2:
                return {
                    "check": "trend_alignment",
                    "passed": True,
                    "trend": trend,
                    "direction": direction,
                    "reason": f"Bullish BOS momentum ({net_bos}) outweighs neutral trend",
                }
            if direction == "short" and net_bos < -2:
                return {
                    "check": "trend_alignment",
                    "passed": True,
                    "trend": trend,
                    "direction": direction,
                    "reason": f"Bearish BOS momentum ({net_bos}) outweighs neutral trend",
                }

            return {
                "check": "trend_alignment",
                "passed": False,
                "trend": trend,
                "direction": direction,
                "reason": f"Trend {trend} does not align with {direction} trade direction",
            }
        except Exception as e:
            logger.error(f"check_trend_alignment error for {symbol}: {e}")
            return {"check": "trend_alignment", "passed": True, "reason": f"Check failed, skipped: {str(e)}"}

    async def check_liquidity(self, symbol: str) -> Dict:
        if not HAS_MARKET_SERVICE:
            return {"check": "liquidity", "passed": True, "reason": "Skipped — market service unavailable"}

        try:
            ob = await market_service.get_orderbook(symbol, "binance", 50)
            if not ob or not ob.get("bids") or not ob.get("asks"):
                return {"check": "liquidity", "passed": True, "reason": "Order book unavailable, skipped"}

            total_bid_vol = sum(b[1] for b in ob["bids"])
            total_ask_vol = sum(a[1] for a in ob["asks"])
            spread = ob["asks"][0][0] - ob["bids"][0][0] if ob["asks"] and ob["bids"] else 0
            mid = (ob["asks"][0][0] + ob["bids"][0][0]) / 2 if ob["asks"] and ob["bids"] else 1
            spread_pct = spread / mid if mid > 0 else 0

            total_depth = total_bid_vol + total_ask_vol

            issues = []
            if total_depth < 100000:
                issues.append(f"Low total order book depth: {total_depth:.0f} units")
            if spread_pct > self.MAX_SPREAD_PCT * 2:
                issues.append(f"Wide spread: {spread_pct * 100:.4f}%")
            if total_bid_vol == 0 or total_ask_vol == 0:
                issues.append("One-sided order book")

            passed = len(issues) == 0
            return {
                "check": "liquidity",
                "passed": passed,
                "bid_volume": round(total_bid_vol, 2),
                "ask_volume": round(total_ask_vol, 2),
                "total_depth": round(total_depth, 2),
                "spread_pct": round(spread_pct * 100, 4),
                "bid_depth_10": [{"price": b[0], "volume": b[1]} for b in ob["bids"]],
                "ask_depth_10": [{"price": a[0], "volume": a[1]} for a in ob["asks"]],
                "reason": "; ".join(issues) if issues else "Liquidity is adequate",
            }
        except Exception as e:
            logger.error(f"check_liquidity error for {symbol}: {e}")
            return {"check": "liquidity", "passed": True, "reason": f"Check failed, skipped: {str(e)}"}

    async def check_spread(self, symbol: str, max_spread_pct: float = 0.001) -> Dict:
        if not HAS_MARKET_SERVICE:
            return {"check": "spread", "passed": True, "reason": "Skipped — market service unavailable"}

        try:
            ticker = await market_service.get_ticker(symbol)
            if not ticker or ticker.get("bid") is None or ticker.get("ask") is None:
                return {"check": "spread", "passed": True, "reason": "Ticker unavailable, skipped"}

            bid = ticker["bid"]
            ask = ticker["ask"]
            spread_abs = ask - bid
            mid = (ask + bid) / 2
            spread_pct = spread_abs / mid if mid > 0 else 0

            passed = spread_pct <= max_spread_pct
            return {
                "check": "spread",
                "passed": passed,
                "bid": bid,
                "ask": ask,
                "spread_abs": round(spread_abs, 8),
                "spread_pct": round(spread_pct * 100, 4),
                "max_allowed_pct": round(max_spread_pct * 100, 4),
                "reason": f"Spread {spread_pct * 100:.4f}% within limit {max_spread_pct * 100:.4f}%" if passed
                else f"Spread {spread_pct * 100:.4f}% exceeds max {max_spread_pct * 100:.4f}%",
            }
        except Exception as e:
            logger.error(f"check_spread error for {symbol}: {e}")
            return {"check": "spread", "passed": True, "reason": f"Check failed, skipped: {str(e)}"}

    async def check_funding(self, symbol: str) -> Dict:
        if not HAS_MARKET_SERVICE:
            return {"check": "funding", "passed": True, "reason": "Skipped — market service unavailable"}

        try:
            funding = await market_service.get_funding_rate(symbol)
            if not funding or funding.get("funding_rate") is None:
                return {"check": "funding", "passed": True, "reason": "Funding rate unavailable, skipped"}

            fr = funding["funding_rate"]

            passed = abs(fr) <= self.MAX_FUNDING_RATE_ABS

            pressure = "neutral"
            if fr < -0.0005:
                pressure = "bullish"
            elif fr > 0.0005:
                pressure = "bearish"

            return {
                "check": "funding",
                "passed": passed,
                "funding_rate": round(fr, 6),
                "funding_rate_8h": round(fr * 3, 6),
                "pressure": pressure,
                "reason": f"Funding rate {fr * 100:.4f}% ({pressure}) within acceptable range" if passed
                else f"Funding rate {fr * 100:.4f}% exceeds max {self.MAX_FUNDING_RATE_ABS * 100:.2f}%",
            }
        except Exception as e:
            logger.error(f"check_funding error for {symbol}: {e}")
            return {"check": "funding", "passed": True, "reason": f"Check failed, skipped: {str(e)}"}

    async def check_correlation(self, symbol: str, portfolio: Dict) -> Dict:
        if not portfolio:
            return {"check": "correlation", "passed": True, "reason": "No portfolio provided, skipped"}

        try:
            existing_symbols = portfolio.get("symbols", [])
            if not existing_symbols:
                return {"check": "correlation", "passed": True, "reason": "Empty portfolio, no correlation risk"}

            base = symbol.split("/")[0] if "/" in symbol else symbol
            concentrated = sum(1 for s in existing_symbols if base in s)

            exposure = portfolio.get("exposures", {})
            current_exposure = exposure.get(symbol, 0)
            total_exposure = sum(exposure.values()) if exposure else 0
            exposure_pct = current_exposure / total_exposure if total_exposure > 0 else 0

            issues = []
            if concentrated > 2:
                issues.append(f"{concentrated} positions with base asset {base}")
            if exposure_pct > 0.3:
                issues.append(f"Exposure {exposure_pct * 100:.1f}% exceeds 30% single-asset limit")

            passed = len(issues) == 0
            return {
                "check": "correlation",
                "passed": passed,
                "base_asset": base,
                "concentrated_positions": concentrated,
                "exposure_pct": round(exposure_pct * 100, 2),
                "reason": "; ".join(issues) if issues else "Correlation risk acceptable",
            }
        except Exception as e:
            logger.error(f"check_correlation error: {e}")
            return {"check": "correlation", "passed": True, "reason": f"Check failed, skipped: {str(e)}"}

    async def check_risk(
        self, symbol: str, direction: str, entry: float, sl: float,
        tp: float, leverage: int, balance: float
    ) -> Dict:
        if not HAS_PROFESSIONAL_RISK:
            return {"check": "risk", "passed": True, "reason": "Skipped — professional_risk unavailable"}

        try:
            if not entry or entry <= 0:
                return {"check": "risk", "passed": False, "reason": "Invalid entry price"}
            if not sl or sl <= 0:
                return {"check": "risk", "passed": False, "reason": "Invalid stop loss"}
            if entry == sl:
                return {"check": "risk", "passed": False, "reason": "Stop loss equals entry price"}
            if balance <= 0:
                return {"check": "risk", "passed": False, "reason": "Insufficient balance"}

            data = None
            atr_val = None
            if HAS_MARKET_SERVICE:
                try:
                    data = await market_service.get_ohlcv(symbol, "binance", "1h", 100)
                    if data:
                        from app.services.indicators import indicator_service
                        atr_val = indicator_service.atr(data)
                except Exception:
                    pass

            risk_pct = abs(entry - sl) / entry * leverage * 100

            rr = 0
            if tp and sl:
                rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            validation = professional_risk.validate_trade(
                symbol=symbol,
                direction=direction,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                leverage=leverage,
                balance=balance,
                atr_value=atr_val,
                data=data,
            )

            sizing = professional_risk.calculate_position_size(
                capital=balance,
                entry_price=entry,
                stop_loss=sl,
                risk_percent=abs(entry - sl) / entry,
                leverage=leverage,
                atr_value=atr_val,
            )

            passed = validation.get("passed", False)

            return {
                "check": "risk",
                "passed": passed,
                "risk_percent": round(risk_pct, 2),
                "risk_reward": round(rr, 2),
                "position_sizing": sizing,
                "validation_checks": validation.get("checks", []),
                "reason": "All risk checks passed" if passed
                else f"Risk check failed: {validation.get('checks', [{}])[-1].get('reason', 'unknown')}",
            }
        except Exception as e:
            logger.error(f"check_risk error: {e}")
            return {"check": "risk", "passed": True, "reason": f"Check failed, skipped: {str(e)}"}

    async def check_margin(self, leverage: int, position_size_value: float, balance: float) -> Dict:
        try:
            if leverage <= 0:
                return {"check": "margin", "passed": False, "reason": "Leverage must be positive"}

            if balance <= 0:
                return {"check": "margin", "passed": False, "reason": "Zero or negative balance"}

            margin_required = position_size_value / leverage if leverage > 0 else position_size_value

            passed = margin_required <= balance
            margin_ratio = margin_required / balance if balance > 0 else float("inf")

            return {
                "check": "margin",
                "passed": passed,
                "position_value": round(position_size_value, 2),
                "margin_required": round(margin_required, 2),
                "balance": round(balance, 2),
                "margin_ratio": round(margin_ratio, 4),
                "free_margin": round(balance - margin_required, 2),
                "reason": f"Sufficient margin (${margin_required:.2f} / ${balance:.2f})" if passed
                else f"Insufficient margin: ${margin_required:.2f} required, ${balance:.2f} available",
            }
        except Exception as e:
            logger.error(f"check_margin error: {e}")
            return {"check": "margin", "passed": True, "reason": f"Check failed, skipped: {str(e)}"}

    async def check_leverage(self, symbol: str, requested_leverage: int, max_leverage: int = 125) -> Dict:
        try:
            if requested_leverage < 1:
                return {"check": "leverage", "passed": False, "reason": "Leverage must be at least 1x"}

            passed = requested_leverage <= max_leverage

            recommended = 1
            if passed:
                if requested_leverage <= 2:
                    recommended = requested_leverage
                elif requested_leverage <= 5:
                    recommended = 3
                elif requested_leverage <= 10:
                    recommended = 5
                elif requested_leverage <= 20:
                    recommended = 10
                elif requested_leverage <= 50:
                    recommended = 20
                else:
                    recommended = 50

            return {
                "check": "leverage",
                "passed": passed,
                "requested": requested_leverage,
                "max_allowed": max_leverage,
                "recommended": recommended,
                "reason": f"Leverage {requested_leverage}x within {max_leverage}x limit" if passed
                else f"Leverage {requested_leverage}x exceeds max {max_leverage}x",
            }
        except Exception as e:
            logger.error(f"check_leverage error: {e}")
            return {"check": "leverage", "passed": True, "reason": f"Check failed, skipped: {str(e)}"}

    async def check_exchange_filters(self, symbol: str, quantity: float, price: float) -> Dict:
        if not HAS_MARKET_SERVICE:
            return {"check": "exchange_filters", "passed": True, "reason": "Skipped — market service unavailable"}

        try:
            import ccxt
            ex = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            markets = ex.load_markets()

            if symbol not in markets:
                return {"check": "exchange_filters", "passed": True, "reason": f"Symbol {symbol} not found in exchange markets, skipped"}

            market = markets[symbol]
            limits = market.get("limits", {})
            precision = market.get("precision", {})

            issues = []

            lot_size = limits.get("amount", {})
            min_qty = lot_size.get("min", 0)
            max_qty = lot_size.get("max", float("inf"))
            step_size = lot_size.get("step", 0)

            if quantity > 0:
                if quantity < min_qty:
                    issues.append(f"Quantity {quantity} below min lot {min_qty}")
                if quantity > max_qty:
                    issues.append(f"Quantity {quantity} exceeds max lot {max_qty}")
                if step_size > 0:
                    remains = quantity % step_size
                    if remains > 1e-8:
                        adjusted = round(quantity - remains, 8)
                        issues.append(f"Quantity not aligned to lot step {step_size}, suggested: {adjusted}")

            notional = limits.get("cost", {})
            min_notional = notional.get("min", 0)
            if quantity > 0 and price > 0:
                notional_value = quantity * price
                if notional_value < min_notional:
                    issues.append(f"Notional ${notional_value:.2f} below min ${min_notional:.2f}")

            price_filter = limits.get("price", {})
            min_price = price_filter.get("min", 0)
            max_price = price_filter.get("max", float("inf"))
            tick_size = price_filter.get("step", 0)
            if price > 0:
                if price < min_price:
                    issues.append(f"Price {price} below min {min_price}")
                if price > max_price:
                    issues.append(f"Price {price} exceeds max {max_price}")
                if tick_size > 0:
                    price_remains = price % tick_size
                    if price_remains > 1e-8:
                        adjusted_price = round(price - price_remains, 8)
                        issues.append(f"Price not aligned to tick size {tick_size}, suggested: {adjusted_price}")

            passed = len(issues) == 0
            return {
                "check": "exchange_filters",
                "passed": passed,
                "symbol": symbol,
                "min_quantity": min_qty,
                "max_quantity": max_qty,
                "step_size": step_size,
                "min_notional": min_notional,
                "tick_size": tick_size,
                "issues": issues,
                "reason": "; ".join(issues) if issues else "All exchange filters passed",
            }
        except Exception as e:
            logger.error(f"check_exchange_filters error for {symbol}: {e}")
            return {"check": "exchange_filters", "passed": True, "reason": f"Check failed, skipped: {str(e)}"}

    async def check_liquidation_distance(self, entry: float, sl: float, leverage: int) -> Dict:
        try:
            if not entry or entry <= 0:
                return {"check": "liquidation_distance", "passed": False, "reason": "Invalid entry price"}

            if leverage < 1:
                leverage = 1

            liq_price = self._estimate_liquidation_price(entry, sl, leverage)

            if liq_price is None:
                return {"check": "liquidation_distance", "passed": True, "reason": "Cannot estimate liquidation price, skipped"}

            dist_pct = abs(liq_price - entry) / entry * 100
            sl_dist_pct = abs(entry - sl) / entry * 100

            min_dist = self.MIN_LIQUIDATION_DISTANCE * 100
            passed = dist_pct >= min_dist

            if liq_price == sl:
                passed = True

            return {
                "check": "liquidation_distance",
                "passed": passed,
                "entry_price": entry,
                "stop_loss": sl,
                "liquidation_price": round(liq_price, 4),
                "distance_to_liquidation_pct": round(dist_pct, 2),
                "distance_to_sl_pct": round(sl_dist_pct, 2),
                "leverage": leverage,
                "reason": f"Liquidation at {liq_price:.4f} ({dist_pct:.2f}% from entry) — buffer adequate" if passed
                else f"Liquidation too close: {dist_pct:.2f}% from entry, minimum {min_dist:.1f}%",
            }
        except Exception as e:
            logger.error(f"check_liquidation_distance error: {e}")
            return {"check": "liquidation_distance", "passed": True, "reason": f"Check failed, skipped: {str(e)}"}

    async def get_trade_approval(self, trade_request: Dict) -> Dict:
        validation = await self.validate_trade(trade_request)
        checks = validation.get("checks", {})
        rejection_reasons = self.get_rejection_reasons(checks)

        risk_score = self._calculate_risk_score(checks)

        result = {
            "symbol": trade_request.get("symbol", ""),
            "direction": trade_request.get("direction", "long"),
            "approved": validation["passed"],
            "risk_score": risk_score,
            "risk_label": self._risk_label(risk_score),
            "validation": validation,
            "rejection_reasons": rejection_reasons,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if validation["passed"]:
            result["execution_plan"] = await self.get_execution_plan(trade_request)

        return result

    def get_rejection_reasons(self, checks: Dict) -> List[str]:
        reasons = []
        for check_name, check_result in checks.items():
            if not check_result.get("passed", False):
                reason = check_result.get("reason", "Unknown failure")
                reasons.append(f"[{check_name}] {reason}")
        return reasons

    async def estimate_slippage(self, symbol: str, quantity: float, side: str) -> Dict:
        if not HAS_MARKET_SERVICE:
            return {"symbol": symbol, "estimated_slippage_pct": 0.001, "reason": "Market service unavailable, default slippage"}

        try:
            ob = await market_service.get_orderbook(symbol, "binance", 50)
            if not ob or not ob.get("bids") or not ob.get("asks"):
                return {"symbol": symbol, "estimated_slippage_pct": 0.001, "reason": "Order book unavailable, default slippage"}

            levels = ob["asks"] if side == "buy" else ob["bids"]
            mid = (ob["asks"][0][0] + ob["bids"][0][0]) / 2

            remaining = quantity
            total_cost = 0.0
            avg_price = 0.0

            for level_price, level_qty in levels:
                fill = min(remaining, level_qty)
                total_cost += fill * level_price
                remaining -= fill
                if remaining <= 0:
                    avg_price = total_cost / quantity
                    break

            if remaining > 0:
                avg_price = total_cost / (quantity - remaining) if quantity > remaining else mid
                filled_pct = (quantity - remaining) / quantity * 100 if quantity > 0 else 0
                return {
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "estimated_slippage_pct": round(abs(avg_price - mid) / mid * 100, 4),
                    "avg_price": round(avg_price, 4),
                    "mid_price": round(mid, 4),
                    "filled_pct": round(filled_pct, 2),
                    "unfilled_qty": round(remaining, 6),
                    "reason": f"Insufficient depth — {filled_pct:.1f}% filled, {remaining:.4f} unfilled",
                }

            slippage_pct = abs(avg_price - mid) / mid * 100 if mid > 0 else 0

            liquidity_tier = "low" if slippage_pct > 0.01 else "medium" if slippage_pct > 0.003 else "high"

            return {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "estimated_slippage_pct": round(slippage_pct, 4),
                "avg_price": round(avg_price, 4),
                "mid_price": round(mid, 4),
                "liquidity_tier": liquidity_tier,
                "levels_consumed": len(levels),
                "reason": f"Estimated slippage {slippage_pct:.4f}% ({liquidity_tier} liquidity)",
            }
        except Exception as e:
            logger.error(f"estimate_slippage error for {symbol}: {e}")
            return {"symbol": symbol, "estimated_slippage_pct": 0.001, "reason": f"Estimation failed: {str(e)}"}

    async def get_execution_plan(self, trade_request: Dict) -> Dict:
        symbol = trade_request.get("symbol", "")
        direction = trade_request.get("direction", "long")
        entry = trade_request.get("entry_price", 0)
        quantity = trade_request.get("quantity", 0)
        price = trade_request.get("price", entry)
        slippage_tolerance = trade_request.get("slippage_tolerance", 0.001)

        slippage = await self.estimate_slippage(symbol, quantity, direction)

        is_large_order = quantity > 10000

        if is_large_order:
            entry_method = "iceberg"
            limit_price = entry * 0.998 if direction == "long" else entry * 1.002
            time_in_force = "GTC"
            iceberg_qty = quantity / 5
            reason = "Large order — iceberg order recommended to minimize market impact"
        elif slippage.get("estimated_slippage_pct", 0) > slippage_tolerance * 100:
            entry_method = "limit"
            limit_price = entry * 0.997 if direction == "long" else entry * 1.003
            time_in_force = "GTC"
            iceberg_qty = None
            reason = "High slippage — limit order recommended"
        else:
            entry_method = "market"
            limit_price = entry
            time_in_force = "IOC"
            iceberg_qty = None
            reason = "Adequate liquidity — market order acceptable"

        return {
            "symbol": symbol,
            "direction": direction,
            "entry_method": entry_method,
            "limit_price_suggestion": round(limit_price, 4) if entry_method != "market" else None,
            "quantity": quantity,
            "iceberg": is_large_order,
            "iceberg_quantity": round(iceberg_qty, 6) if iceberg_qty else None,
            "time_in_force": time_in_force,
            "estimated_slippage": slippage,
            "is_large_order": is_large_order,
            "reason": reason,
        }

    def _estimate_liquidation_price(self, entry: float, sl: float, leverage: int) -> Optional[float]:
        if leverage <= 1:
            return sl

        diff = abs(entry - sl)
        liq_buffer = diff * 1.3

        if entry > sl:
            return entry - liq_buffer
        return entry + liq_buffer

    def _calculate_risk_score(self, checks: Dict) -> int:
        score = 100

        deduction_map = {
            "trend_alignment": 15,
            "liquidity": 10,
            "spread": 5,
            "funding": 10,
            "correlation": 10,
            "risk": 20,
            "margin": 10,
            "leverage": 5,
            "exchange_filters": 5,
            "liquidation_distance": 10,
        }

        for check_name, check in checks.items():
            if not check.get("passed", False):
                deduction = deduction_map.get(check_name, 5)
                score -= deduction

        return max(0, min(100, score))

    def _risk_label(self, score: int) -> str:
        if score >= 95:
            return "very_low"
        elif score >= 85:
            return "low"
        elif score >= 70:
            return "medium"
        elif score >= 50:
            return "high"
        return "very_high"


execution_engine = ExecutionEngine()
