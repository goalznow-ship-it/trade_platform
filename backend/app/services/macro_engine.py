"""Macro market facade backed by real Yahoo Finance quotes.

Economic releases and ETF flows remain explicitly unavailable until authoritative
providers are configured; no estimated or random values are returned.
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict
import yfinance as yf
from app.core.provider_health import provider_health


class MacroEngine:
    SYMBOLS = {
        "dxy": "DX-Y.NYB",
        "nasdaq": "^IXIC",
        "sp500": "^GSPC",
        "gold": "GC=F",
        "oil": "CL=F",
        "us10y": "^TNX",
        "vix": "^VIX",
    }

    def _quote(self, key: str) -> Dict:
        symbol = self.SYMBOLS[key]
        if not provider_health.allow_request("yahoo_finance"):
            return {
                "available": False, "source": "yahoo_finance", "symbol": symbol,
                "reason": "Provider circuit breaker is open",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        try:
            history = yf.Ticker(symbol).history(period="5d", interval="1d")
            if history.empty:
                raise ValueError("No quote returned")
            close = float(history["Close"].iloc[-1])
            previous = float(history["Close"].iloc[-2]) if len(history) > 1 else close
            change = ((close - previous) / previous * 100) if previous else 0.0
            result = {
                "available": True,
                "source": "yahoo_finance",
                "symbol": symbol,
                "value": close,
                "daily_change_pct": change,
                "trend": "bullish" if change > 0 else "bearish" if change < 0 else "neutral",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            provider_health.success("yahoo_finance")
            return result
        except Exception as exc:
            provider_health.failure("yahoo_finance", exc)
            return {
                "available": False,
                "source": "yahoo_finance",
                "symbol": symbol,
                "reason": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_dxy(self) -> Dict: return self._quote("dxy")
    def get_nasdaq(self) -> Dict: return self._quote("nasdaq")
    def get_sp500(self) -> Dict: return self._quote("sp500")
    def get_gold(self) -> Dict: return self._quote("gold")
    def get_oil(self) -> Dict: return self._quote("oil")
    def get_us10y(self) -> Dict: return self._quote("us10y")
    def get_vix(self) -> Dict: return self._quote("vix")

    @staticmethod
    def _unavailable(source: str) -> Dict:
        return {
            "available": False,
            "source": source,
            "reason": "Authoritative economic data provider not configured",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_cpi(self) -> Dict: return self._unavailable("cpi")
    def get_ppi(self) -> Dict: return self._unavailable("ppi")
    def get_fomc_schedule(self) -> Dict: return self._unavailable("fomc")
    def get_interest_rate(self) -> Dict: return self._unavailable("fed_funds")
    def get_etf_flows(self) -> Dict: return self._unavailable("etf_flows")

    def estimate_crypto_impact(self) -> Dict:
        return self._unavailable("macro_impact")

    def get_macro_snapshot(self) -> Dict:
        indicators = {name: self._quote(name) for name in self.SYMBOLS}
        available = [item for item in indicators.values() if item.get("available")]
        return {
            "available": bool(available),
            "source": "yahoo_finance",
            "indicators": indicators,
            "fundamentals": {
                "cpi": self.get_cpi(),
                "ppi": self.get_ppi(),
                "fomc": self.get_fomc_schedule(),
                "interest_rate": self.get_interest_rate(),
            },
            "etf_flows": self.get_etf_flows(),
            "risk_environment": "unavailable",
            "risk_score": None,
            "crypto_outlook": "unavailable",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def stream_updates(self, interval: int = 300):
        while True:
            yield await asyncio.to_thread(self.get_macro_snapshot)
            await asyncio.sleep(interval)


macro_engine = MacroEngine()
provider_health.configure("yahoo_finance", True)
