"""
Order Flow Analysis Engine

Institutional-grade order flow analytics:
- Order book imbalance and pressure ratios
- Cumulative volume delta (CVD) simulation
- Large order detection (>0.5% of total)
- Liquidity vacuum detection
- Spoof detection heuristics
- Iceberg order detection
- Aggressive trade classification
- Absorption ratio calculation
"""

import numpy as np
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from app.services.indicators import indicator_service
from app.core.logging import logger


class OrderFlowAnalysis:
    def __init__(self):
        self.logger = logger

    def analyze_orderbook(self, bids: List[Dict], asks: List[Dict]) -> Dict:
        top_bids = bids[:50]
        top_asks = asks[:50]
        if not top_bids or not top_asks:
            return {"error": "empty_orderbook"}

        total_bid_vol = sum(b["amount"] for b in top_bids)
        total_ask_vol = sum(a["amount"] for a in top_asks)
        imbalance_raw = (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol + 1e-9)
        pressure_ratio = total_bid_vol / (total_ask_vol + 1e-9)
        total_volume = total_bid_vol + total_ask_vol
        large_threshold = total_volume * 0.005

        large_bids = [b for b in top_bids if b["amount"] >= large_threshold]
        large_asks = [a for a in top_asks if a["amount"] >= large_threshold]

        vacuum = self.detect_liquidity_vacuum(top_bids, top_asks)

        bid_prices = sorted(set(b["price"] for b in top_bids), reverse=True)
        ask_prices = sorted(set(a["price"] for a in top_asks))
        cvd = 0.0
        midpoint = None
        if bid_prices and ask_prices:
            midpoint = (bid_prices[0] + ask_prices[0]) / 2
            for b in top_bids:
                cvd -= b["amount"]
            for a in top_asks:
                cvd += a["amount"]

        bid_depth_profile = self._depth_profile(top_bids, "bid")
        ask_depth_profile = self._depth_profile(top_asks, "ask")

        return {
            "symbol": None,
            "bid_volume": round(total_bid_vol, 4),
            "ask_volume": round(total_ask_vol, 4),
            "imbalance": round(imbalance_raw, 4),
            "imbalance_label": self._imbalance_label(imbalance_raw),
            "bid_ask_ratio": round(pressure_ratio, 4),
            "cumulative_volume_delta": round(cvd, 4),
            "mid_price": round(midpoint, 4) if midpoint else None,
            "large_orders": {
                "bid_count": len(large_bids),
                "ask_count": len(large_asks),
                "bid_volume": round(sum(b["amount"] for b in large_bids), 4),
                "ask_volume": round(sum(a["amount"] for a in large_asks), 4),
                "orders": [{"side": "bid", "price": b["price"], "amount": b["amount"]} for b in large_bids] +
                          [{"side": "ask", "price": a["price"], "amount": a["amount"]} for a in large_asks],
            },
            "liquidity_vacuum": vacuum,
            "bid_depth_profile": bid_depth_profile,
            "ask_depth_profile": ask_depth_profile,
            "total_levels": {"bids": len(top_bids), "asks": len(top_asks)},
        }

    def analyze_trades(self, trades: List[Dict]) -> Dict:
        if not trades:
            return {"error": "empty_trades"}

        buy_volume = 0.0
        sell_volume = 0.0
        aggressive_buys = 0
        aggressive_sells = 0
        aggressive_buy_vol = 0.0
        aggressive_sell_vol = 0.0
        cvd = 0.0
        trade_count = len(trades)

        for t in trades:
            side = t.get("side", "").lower()
            amount = t.get("amount", 0)
            price = t.get("price", 0)

            if side == "buy":
                buy_volume += amount
                cvd += amount
                if t.get("aggressive", False):
                    aggressive_buys += 1
                    aggressive_buy_vol += amount
            elif side == "sell":
                sell_volume += amount
                cvd -= amount
                if t.get("aggressive", False):
                    aggressive_sells += 1
                    aggressive_sell_vol += amount

        total_volume = buy_volume + sell_volume
        absorption_ratio = 0.0
        if total_volume > 0:
            absorption_ratio = abs(buy_volume - sell_volume) / total_volume

        buy_sell_ratio = buy_volume / (sell_volume + 1e-9)
        aggressive_ratio = (aggressive_buy_vol + aggressive_sell_vol) / (total_volume + 1e-9)

        return {
            "symbol": None,
            "trade_count": trade_count,
            "buy_volume": round(buy_volume, 4),
            "sell_volume": round(sell_volume, 4),
            "total_volume": round(total_volume, 4),
            "buy_sell_ratio": round(buy_sell_ratio, 4),
            "cumulative_volume_delta": round(cvd, 4),
            "aggressive_buys": aggressive_buys,
            "aggressive_sells": aggressive_sells,
            "aggressive_buy_volume": round(aggressive_buy_vol, 4),
            "aggressive_sell_volume": round(aggressive_sell_vol, 4),
            "aggressive_ratio": round(aggressive_ratio, 4),
            "absorption_ratio": round(absorption_ratio, 4),
            "absorption_label": self._absorption_label(absorption_ratio),
            "buy_volume_pct": round(buy_volume / (total_volume + 1e-9) * 100, 2),
            "sell_volume_pct": round(sell_volume / (total_volume + 1e-9) * 100, 2),
        }

    def get_orderbook_imbalance(self, bids: List[Dict], asks: List[Dict]) -> float:
        bid_vol = sum(b.get("amount", 0) for b in (bids or []))
        ask_vol = sum(a.get("amount", 0) for a in (asks or []))
        total = bid_vol + ask_vol
        if total == 0:
            return 0.0
        return (bid_vol - ask_vol) / total

    def detect_iceberg(self, asks: List[Dict], bids: List[Dict]) -> Dict:
        icebergs = []

        for label, levels in [("ask", asks or []), ("bid", bids or [])]:
            price_groups: Dict[float, List[float]] = {}
            for lvl in levels:
                price = lvl.get("price", 0)
                amount = lvl.get("amount", 0)
                price_rounded = round(price, 2)
                if price_rounded not in price_groups:
                    price_groups[price_rounded] = []
                price_groups[price_rounded].append(amount)

            for price, amounts in price_groups.items():
                if len(amounts) >= 3 and np.std(amounts) < np.mean(amounts) * 0.15:
                    icebergs.append({
                        "side": label,
                        "price": price,
                        "visible_slices": len(amounts),
                        "avg_slice_size": round(np.mean(amounts), 4),
                        "total_estimated": round(np.mean(amounts) * (len(amounts) + 2), 4),
                        "confidence": "high" if len(amounts) >= 5 else "medium",
                    })

        return {
            "iceberg_orders": icebergs,
            "count": len(icebergs),
            "total_estimated_volume": round(sum(i["total_estimated"] for i in icebergs), 4),
        }

    def detect_liquidity_vacuum(self, bids: List[Dict], asks: List[Dict], threshold_pct: float = 0.001) -> Dict:
        vacuums = []

        for label, levels, ascending in [("bid", bids or [], False), ("ask", asks or [], True)]:
            sorted_levels = sorted(levels, key=lambda x: x["price"], reverse=not ascending)
            prices = [l["price"] for l in sorted_levels]
            for i in range(len(prices) - 1):
                gap_pct = abs(prices[i + 1] - prices[i]) / ((prices[i] + prices[i + 1]) / 2 + 1e-9)
                if gap_pct > threshold_pct:
                    vacuums.append({
                        "side": label,
                        "gap": round(abs(prices[i + 1] - prices[i]), 4),
                        "gap_pct": round(gap_pct * 100, 4),
                        "from_price": round(prices[i], 4),
                        "to_price": round(prices[i + 1], 4),
                        "severity": "high" if gap_pct > threshold_pct * 5 else "medium" if gap_pct > threshold_pct * 2 else "low",
                    })

        return {
            "vacuums": vacuums[:20],
            "count": len(vacuums),
            "max_gap_pct": round(max((v["gap_pct"] for v in vacuums), default=0), 4),
            "avg_gap_pct": round(np.mean([v["gap_pct"] for v in vacuums]), 4) if vacuums else 0,
        }

    def detect_spoofing(self, snapshot_history: List[Dict]) -> Dict:
        if not snapshot_history or len(snapshot_history) < 2:
            return {"error": "insufficient_snapshots", "spoof_signals": [], "count": 0}

        alerts = []
        suspicious_prices: Dict[float, int] = {}

        for i in range(1, len(snapshot_history)):
            prev = snapshot_history[i - 1]
            curr = snapshot_history[i]

            for side in ("bid", "ask"):
                prev_levels = {l["price"]: l["amount"] for l in prev.get(f"{side}s", [])}
                curr_levels = {l["price"]: l["amount"] for l in curr.get(f"{side}s", [])}

                appeared = set(curr_levels.keys()) - set(prev_levels.keys())
                vanished = set(prev_levels.keys()) - set(curr_levels.keys())
                reappeared = appeared & set(prev_levels.keys())

                for price in appeared:
                    rounded = round(price, 2)
                    suspicious_prices[rounded] = suspicious_prices.get(rounded, 0) + 1

                for price in reappeared:
                    rounded = round(price, 2)
                    suspicious_prices[rounded] = suspicious_prices.get(rounded, 0) + 2

            for price, score in list(suspicious_prices.items()):
                if score >= 3:
                    alerts.append({
                        "price": price,
                        "appear_disappear_count": score,
                        "side": "both",
                        "confidence": "high" if score >= 6 else "medium",
                    })
                    suspicious_prices[price] = 0

        alerts = sorted(alerts, key=lambda x: x["appear_disappear_count"], reverse=True)[:10]

        return {
            "spoof_signals": alerts,
            "count": len(alerts),
            "analyzed_snapshots": len(snapshot_history),
            "total_suspicious_activity": sum(a["appear_disappear_count"] for a in alerts),
        }

    def get_aggregated_snapshot(self, symbol: str, bid_data: List[Dict], ask_data: List[Dict], trades: List[Dict]) -> Dict:
        bids = bid_data or []
        asks = ask_data or []
        trades = trades or []

        orderbook = self.analyze_orderbook(bids, asks)
        trade_analysis = self.analyze_trades(trades)
        iceberg = self.detect_iceberg(asks, bids)
        vacuum = self.detect_liquidity_vacuum(bids, asks)

        total_bid_vol = sum(b.get("amount", 0) for b in bids)
        total_ask_vol = sum(a.get("amount", 0) for a in asks)
        spread = 0.0
        if asks and bids:
            best_ask = min(a["price"] for a in asks)
            best_bid = max(b["price"] for b in bids)
            spread = best_ask - best_bid

        return {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "spread": round(spread, 4),
            "spread_pct": round(spread / ((best_ask + best_bid) / 2) * 100, 4) if asks and bids else 0,
            "mid_price": orderbook.get("mid_price"),
            "orderbook": orderbook,
            "trades": trade_analysis,
            "iceberg": iceberg,
            "liquidity_vacuum": vacuum,
            "market_mood": self._market_mood(orderbook, trade_analysis),
            "total_bid_volume": round(total_bid_vol, 4),
            "total_ask_volume": round(total_ask_vol, 4),
        }

    def _depth_profile(self, levels: List[Dict], side: str) -> Dict:
        if not levels:
            return {"clusters": 0, "avg_size": 0, "top_heavy": False}

        sorted_levels = sorted(levels, key=lambda x: x["price"], reverse=(side == "bid"))
        amounts = [l["amount"] for l in sorted_levels]

        clusters = 0
        cluster_threshold = np.mean(amounts) * 0.5 if amounts else 0
        for amt in amounts:
            if amt > cluster_threshold:
                clusters += 1

        top_half_sum = sum(amounts[:max(1, len(amounts) // 2)])
        bottom_half_sum = sum(amounts[len(amounts) // 2:])
        top_heavy = top_half_sum > bottom_half_sum * 1.2 if bottom_half_sum > 0 else True

        return {
            "total_levels": len(levels),
            "clusters": clusters,
            "avg_size": round(np.mean(amounts), 4),
            "max_size": round(max(amounts), 4),
            "min_size": round(min(amounts), 4),
            "median_size": round(float(np.median(amounts)), 4),
            "top_heavy": top_heavy,
            "concentration": round(max(amounts) / (sum(amounts) + 1e-9) * 100, 2),
        }

    def _imbalance_label(self, value: float) -> str:
        if value > 0.5:
            return "extreme_buy_pressure"
        elif value > 0.25:
            return "strong_buy_pressure"
        elif value > 0.1:
            return "moderate_buy_pressure"
        elif value < -0.5:
            return "extreme_sell_pressure"
        elif value < -0.25:
            return "strong_sell_pressure"
        elif value < -0.1:
            return "moderate_sell_pressure"
        else:
            return "neutral"

    def _absorption_label(self, ratio: float) -> str:
        if ratio < 0.1:
            return "high_absorption"
        elif ratio < 0.25:
            return "moderate_absorption"
        elif ratio < 0.5:
            return "low_absorption"
        else:
            return "no_absorption"

    def _market_mood(self, orderbook: Dict, trade_analysis: Dict) -> str:
        ob_imb = orderbook.get("imbalance", 0)
        buy_sell = trade_analysis.get("buy_sell_ratio", 1)
        score = (ob_imb * 0.5) + (np.log10(buy_sell + 1e-9) * 0.5)
        if score > 0.3:
            return "bullish"
        elif score < -0.3:
            return "bearish"
        else:
            return "neutral"


orderflow_engine = OrderFlowAnalysis()
