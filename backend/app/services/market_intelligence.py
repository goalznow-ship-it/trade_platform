"""Canonical real-market snapshot used by Radar, Futures and Dashboard."""

import asyncio
import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.logging import logger
from app.services.data_contract import data_meta, unavailable, utc_now


class MarketIntelligenceService:
    SPOT_URL = "https://api.binance.com"
    FUTURES_URL = "https://fapi.binance.com"
    COINGECKO_URL = "https://api.coingecko.com/api/v3"
    SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "SUIUSDT")

    def __init__(self) -> None:
        self._history: dict[str, deque[dict[str, float]]] = defaultdict(lambda: deque(maxlen=30))

    async def _json(self, url: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def _module(self, name: str, source: str, call, errors: dict) -> Any:
        try:
            value = await call()
            return value
        except Exception as exc:
            reason = f"{type(exc).__name__}: {str(exc)[:240]}"
            logger.warning("%s provider failed: %s", name, reason)
            errors[name] = reason
            return unavailable(source, reason)

    async def _dominance(self) -> dict:
        payload = await self._json(f"{self.COINGECKO_URL}/global")
        value = payload.get("data", {}).get("market_cap_percentage", {}).get("btc")
        if not isinstance(value, (int, float)):
            raise ValueError("CoinGecko response did not contain BTC dominance")
        updated = datetime.fromtimestamp(
            payload.get("data", {}).get("updated_at", datetime.now().timestamp()),
            tz=timezone.utc,
        ).isoformat()
        return {"value": round(float(value), 2), **data_meta("CoinGecko Global", last_updated=updated, max_age_seconds=300)}

    async def _prices(self) -> dict:
        payload = await self._json(
            f"{self.SPOT_URL}/api/v3/ticker/24hr",
            {"symbols": json.dumps(self.SYMBOLS)},
        )
        now = utc_now()
        items = []
        for row in payload:
            price = float(row["lastPrice"])
            items.append({
                "symbol": row["symbol"],
                "price": price,
                "change_24h": float(row["priceChangePercent"]),
                "volume_24h": float(row["quoteVolume"]),
                **data_meta("Binance Spot", last_updated=now, max_age_seconds=30),
            })
        by_symbol = {item["symbol"]: item for item in items}
        btc = by_symbol.get("BTCUSDT")
        eth = by_symbol.get("ETHUSDT")
        ratio = (eth["price"] / btc["price"]) if btc and eth and btc["price"] else None
        return {
            "items": items,
            "eth_btc_ratio": {
                "value": round(ratio, 8) if ratio is not None else None,
                **data_meta("Binance Spot", last_updated=now, max_age_seconds=30),
            },
            **data_meta("Binance Spot", last_updated=now, max_age_seconds=30),
        }

    async def _futures(self) -> dict:
        premium, oi_rows, ratio_rows, ticker_rows = await asyncio.gather(
            self._json(f"{self.FUTURES_URL}/fapi/v1/premiumIndex"),
            asyncio.gather(*[
                self._json(f"{self.FUTURES_URL}/fapi/v1/openInterest", {"symbol": symbol})
                for symbol in self.SYMBOLS
            ]),
            asyncio.gather(*[
                self._json(
                    f"{self.FUTURES_URL}/futures/data/globalLongShortAccountRatio",
                    {"symbol": symbol, "period": "5m", "limit": 2},
                )
                for symbol in self.SYMBOLS
            ]),
            self._json(f"{self.FUTURES_URL}/fapi/v1/ticker/24hr"),
        )
        now = utc_now()
        premium_by_symbol = {row["symbol"]: row for row in premium if row.get("symbol") in self.SYMBOLS}
        ticker_by_symbol = {row["symbol"]: row for row in ticker_rows if row.get("symbol") in self.SYMBOLS}
        items = []
        for symbol, oi, ratios in zip(self.SYMBOLS, oi_rows, ratio_rows):
            mark = premium_by_symbol.get(symbol, {})
            ticker = ticker_by_symbol.get(symbol, {})
            price = float(mark["markPrice"]) if mark.get("markPrice") else None
            oi_amount = float(oi["openInterest"]) if oi.get("openInterest") else None
            current_ratio = ratios[-1] if ratios else {}
            previous_oi = self._history[symbol][-1]["oi"] if self._history[symbol] else None
            oi_change = (
                ((oi_amount - previous_oi) / previous_oi) * 100
                if oi_amount is not None and previous_oi
                else None
            )
            if oi_amount is not None:
                self._history[symbol].append({"oi": oi_amount, "time": datetime.now().timestamp()})
            items.append({
                "symbol": symbol,
                "exchange": "Binance Futures",
                "funding_rate": float(mark["lastFundingRate"]) if mark.get("lastFundingRate") is not None else None,
                "next_funding_time": datetime.fromtimestamp(int(mark["nextFundingTime"]) / 1000, tz=timezone.utc).isoformat() if mark.get("nextFundingTime") else None,
                "open_interest": oi_amount,
                "open_interest_usd": oi_amount * price if oi_amount is not None and price is not None else None,
                "oi_change": round(oi_change, 3) if oi_change is not None else None,
                "long_short_ratio": float(current_ratio["longShortRatio"]) if current_ratio.get("longShortRatio") else None,
                "long_account": float(current_ratio["longAccount"]) if current_ratio.get("longAccount") else None,
                "short_account": float(current_ratio["shortAccount"]) if current_ratio.get("shortAccount") else None,
                "price": price,
                "change_24h": float(ticker["priceChangePercent"]) if ticker.get("priceChangePercent") else None,
                "volume": float(ticker["quoteVolume"]) if ticker.get("quoteVolume") else None,
                **data_meta("Binance Futures REST", last_updated=now, max_age_seconds=30),
            })
        return {"items": items, **data_meta("Binance Futures REST", last_updated=now, max_age_seconds=30)}

    async def _liquidations(self) -> dict:
        # Binance's public force-order endpoint can be unavailable by region. That is
        # represented explicitly instead of manufacturing heatmap levels.
        rows = await self._json(f"{self.FUTURES_URL}/fapi/v1/allForceOrders", {"limit": 100})
        now = utc_now()
        clusters: dict[tuple[str, int], dict] = {}
        for row in rows:
            symbol = row.get("symbol")
            price = float(row.get("averagePrice") or row.get("price") or 0)
            quantity = float(row.get("executedQty") or row.get("origQty") or 0)
            if not symbol or not price or not quantity:
                continue
            bucket = round(price, max(0, 2 - len(str(int(price)))))
            key = (symbol, int(bucket * 100))
            cluster = clusters.setdefault(key, {
                "symbol": symbol, "price": price, "notional": 0.0, "count": 0,
                "side": "long" if row.get("side") == "SELL" else "short",
            })
            cluster["notional"] += price * quantity
            cluster["count"] += 1
        result = sorted(clusters.values(), key=lambda item: item["notional"], reverse=True)[:20]
        return {"items": result, **data_meta("Binance Futures force orders", last_updated=now, max_age_seconds=60)}

    def _alerts(self, futures: dict, prices: dict, liquidations: dict, whales: dict) -> list[dict]:
        now = utc_now()
        alerts = []
        for item in futures.get("items", []):
            if item.get("oi_change") is not None and abs(item["oi_change"]) >= 3:
                alerts.append({"type": "oi_spike", "symbol": item["symbol"], "message": f"OI {item['oi_change']:+.2f}% dəyişdi"})
            if item.get("funding_rate") is not None and abs(item["funding_rate"]) >= 0.0005:
                alerts.append({"type": "funding_extreme", "symbol": item["symbol"], "message": f"Funding {item['funding_rate'] * 100:+.4f}%"})
            if item.get("change_24h") is not None and abs(item["change_24h"]) >= 8:
                alerts.append({"type": "price_volatility_spike", "symbol": item["symbol"], "message": f"24s qiymət dəyişməsi {item['change_24h']:+.2f}%"})
        for item in prices.get("items", []):
            if item.get("volume_24h") and item["volume_24h"] >= 5_000_000_000:
                alerts.append({"type": "volume_anomaly", "symbol": item["symbol"], "message": "24s həcm $5 mlrd həddini keçib"})
        liq_total = sum(item.get("notional", 0) for item in liquidations.get("items", []))
        if liq_total >= 10_000_000:
            alerts.append({"type": "liquidation_burst", "symbol": "MARKET", "message": f"Likvidasiya axını ${liq_total:,.0f}"})
        for item in whales.get("items", []):
            alerts.append({"type": "whale_transfer", "symbol": item.get("symbol"), "message": "Böyük on-chain transfer"})
        return [{**alert, "last_updated": now, "source": "Canonical anomaly engine"} for alert in alerts]

    async def snapshot(self) -> dict:
        errors: dict[str, str] = {}
        dominance, prices, futures, liquidations = await asyncio.gather(
            self._module("btc_dominance", "CoinGecko Global", self._dominance, errors),
            self._module("prices", "Binance Spot", self._prices, errors),
            self._module("futures", "Binance Futures REST", self._futures, errors),
            self._module("liquidations", "Binance Futures force orders", self._liquidations, errors),
        )
        whales = {
            "items": [],
            **data_meta(
                "Whale provider",
                error_reason="Provider konfiqurasiya edilməyib",
                configured=False,
            ),
        }
        return {
            "btc_dominance": dominance,
            "prices": prices,
            "futures": futures,
            "liquidations": liquidations,
            "whale_transactions": whales,
            "alerts": self._alerts(futures, prices, liquidations, whales),
            "provider_errors": errors,
            "module_errors": dict(errors),
            **data_meta("Canonical market intelligence", fallback_used=bool(errors)),
        }


market_intelligence = MarketIntelligenceService()
