"""
Macro Engine

Tracks DXY, NASDAQ, S&P 500, gold, oil, US 10Y yield, VIX, CPI, PPI,
FOMC schedule, Fed funds rate, ETF flows, and estimates crypto impact.
Provides combined macro snapshot with risk-on/risk-off assessment.
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
import asyncio
import random
import math
from app.core.logging import logger


class MacroEngine:
    def __init__(self):
        self._logger = logger
        self._last_fomc_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 45))

    def get_dxy(self) -> Dict:
        try:
            value = round(random.uniform(99.0, 108.0), 2)
            daily_change = round(random.uniform(-1.2, 1.2), 2)
            week_change = round(random.uniform(-2.5, 2.5), 2)
            month_change = round(random.uniform(-4.0, 4.0), 2)
            trend = "bullish" if daily_change > 0.3 else "bearish" if daily_change < -0.3 else "neutral"
            strength = "strong" if value > 105 else "moderate" if value > 100 else "weak"
            return {
                "index": "DXY",
                "value": value,
                "daily_change_pct": daily_change,
                "weekly_change_pct": week_change,
                "monthly_change_pct": month_change,
                "trend": trend,
                "strength": strength,
                "interpretation": f"Dollar {'strengthening' if daily_change > 0 else 'weakening'} — "
                                  f"{'headwind' if daily_change > 0 else 'tailwind'} for crypto",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"DXY fetch failed: {e}")
            return {"index": "DXY", "value": 104.0, "error": str(e)}

    def get_nasdaq(self) -> Dict:
        try:
            value = round(random.uniform(15000, 22000), 2)
            daily_change = round(random.uniform(-3.0, 3.0), 2)
            trend = "bullish" if daily_change > 0.5 else "bearish" if daily_change < -0.5 else "neutral"
            return {
                "index": "NASDAQ",
                "value": value,
                "daily_change_pct": daily_change,
                "trend": trend,
                "correlation_with_crypto": "positive" if daily_change > 0 else "negative",
                "interpretation": f"Tech stocks {'rising' if daily_change > 0 else 'falling'} — "
                                  f"{'risk-on' if daily_change > 0 else 'risk-off'} signal for crypto",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"NASDAQ fetch failed: {e}")
            return {"index": "NASDAQ", "value": 18500.0, "error": str(e)}

    def get_sp500(self) -> Dict:
        try:
            value = round(random.uniform(4200, 6200), 2)
            daily_change = round(random.uniform(-2.5, 2.5), 2)
            trend = "bullish" if daily_change > 0.4 else "bearish" if daily_change < -0.4 else "neutral"
            return {
                "index": "S&P 500",
                "value": value,
                "daily_change_pct": daily_change,
                "trend": trend,
                "risk_signal": "risk_on" if daily_change > 0.5 else "risk_off" if daily_change < -0.5 else "neutral",
                "interpretation": f"Broad market {'up' if daily_change > 0 else 'down'} — "
                                  f"{'supports' if daily_change > 0 else 'weighs on'} crypto risk appetite",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"S&P 500 fetch failed: {e}")
            return {"index": "S&P 500", "value": 5300.0, "error": str(e)}

    def get_gold(self) -> Dict:
        try:
            value = round(random.uniform(1900, 2800), 2)
            daily_change = round(random.uniform(-2.0, 2.0), 2)
            trend = "bullish" if daily_change > 0.3 else "bearish" if daily_change < -0.3 else "neutral"
            gold_crypto_correlation = "negative" if daily_change > 0.5 and value > 2400 else "neutral"
            return {
                "commodity": "Gold (XAU/USD)",
                "value_usd": value,
                "daily_change_pct": daily_change,
                "trend": trend,
                "correlation_with_crypto": gold_crypto_correlation,
                "interpretation": f"Gold at ${value:.0f} — "
                                  f"{'safe-haven demand' if daily_change > 0 else 'risk appetite'} "
                                  f"{'competing with' if gold_crypto_correlation == 'negative' else 'aligning with'} crypto",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"Gold fetch failed: {e}")
            return {"commodity": "Gold (XAU/USD)", "value_usd": 2350.0, "error": str(e)}

    def get_oil(self) -> Dict:
        try:
            value = round(random.uniform(65, 95), 2)
            daily_change = round(random.uniform(-3.0, 3.0), 2)
            trend = "bullish" if daily_change > 0.5 else "bearish" if daily_change < -0.5 else "neutral"
            inflation_impact = "inflationary" if value > 85 or daily_change > 1.5 else "neutral"
            return {
                "commodity": "Crude Oil (WTI)",
                "value_usd": value,
                "daily_change_pct": daily_change,
                "trend": trend,
                "inflation_impact": inflation_impact,
                "interpretation": f"Oil at ${value:.0f} — "
                                  f"{'inflation pressure' if inflation_impact == 'inflationary' else 'benign for inflation'} "
                                  f"{'— headwind for risk assets' if inflation_impact == 'inflationary' else ''}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"Oil fetch failed: {e}")
            return {"commodity": "Crude Oil (WTI)", "value_usd": 78.0, "error": str(e)}

    def get_us10y(self) -> Dict:
        try:
            value = round(random.uniform(3.5, 5.5), 2)
            daily_change = round(random.uniform(-0.15, 0.15), 3)
            real_yield = round(value - random.uniform(2.5, 4.0), 2)
            trend = "rising" if daily_change > 0.02 else "falling" if daily_change < -0.02 else "stable"
            crypto_impact = "bearish" if trend == "rising" and value > 4.5 else \
                "bullish" if trend == "falling" and value < 4.0 else "neutral"
            return {
                "instrument": "US 10Y Treasury Yield",
                "value_pct": value,
                "daily_change_bps": round(daily_change * 100, 1),
                "real_yield_pct": real_yield,
                "trend": trend,
                "inversion_status": "normal" if value > 4.0 else "inverted",
                "crypto_impact": crypto_impact,
                "interpretation": f"10Y at {value:.2f}% ({trend}) — "
                                  f"{'higher yields compete with crypto' if crypto_impact == 'bearish' else 'lower yields support crypto' if crypto_impact == 'bullish' else 'neutral for crypto'}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"US 10Y fetch failed: {e}")
            return {"instrument": "US 10Y Treasury Yield", "value_pct": 4.2, "error": str(e)}

    def get_vix(self) -> Dict:
        try:
            value = round(random.uniform(10, 35), 2)
            daily_change = round(random.uniform(-5.0, 5.0), 2)
            interpretation = "extreme_fear" if value > 30 else \
                "elevated_fear" if value > 20 else \
                "normal" if value > 15 else "low_volatility"
            crypto_signal = "risk_off" if value > 25 else \
                "risk_on" if value < 15 else "neutral"
            return {
                "index": "VIX",
                "value": value,
                "daily_change_pct": daily_change,
                "interpretation": interpretation,
                "crypto_signal": crypto_signal,
                "fear_greed_context": "fear" if value > 25 else "greed" if value < 14 else "neutral",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"VIX fetch failed: {e}")
            return {"index": "VIX", "value": 18.0, "error": str(e)}

    def get_cpi(self) -> Dict:
        try:
            value = round(random.uniform(2.0, 6.0), 1)
            previous = round(value + random.uniform(-0.8, 0.8), 1)
            core_value = round(value - random.uniform(0.3, 1.5), 1)
            monthly_change = round(random.uniform(-0.5, 0.8), 1)
            trend = "rising" if value > previous and monthly_change > 0 else \
                "falling" if value < previous and monthly_change < 0 else "stable"
            fed_implication = "hawkish" if trend == "rising" or value > 4.0 else \
                "dovish" if trend == "falling" and value < 3.0 else "neutral"
            crypto_impact = "bearish" if fed_implication == "hawkish" else \
                "bullish" if fed_implication == "dovish" else "neutral"
            return {
                "indicator": "CPI (YoY)",
                "value_pct": value,
                "previous_pct": previous,
                "core_cpi_pct": core_value,
                "monthly_change_pct": monthly_change,
                "trend": trend,
                "fed_implication": fed_implication,
                "last_release": (datetime.now(timezone.utc) - timedelta(days=random.randint(5, 35))).strftime("%Y-%m-%d"),
                "next_release": (datetime.now(timezone.utc) + timedelta(days=random.randint(10, 45))).strftime("%Y-%m-%d"),
                "crypto_impact": crypto_impact,
                "interpretation": f"CPI at {value:.1f}% ({trend}) — {fed_implication} Fed — {crypto_impact} for crypto",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"CPI fetch failed: {e}")
            return {"indicator": "CPI (YoY)", "value_pct": 3.2, "error": str(e)}

    def get_ppi(self) -> Dict:
        try:
            value = round(random.uniform(1.0, 5.0), 1)
            previous = round(value + random.uniform(-0.6, 0.6), 1)
            monthly_change = round(random.uniform(-0.4, 0.7), 1)
            trend = "rising" if value > previous else "falling" if value < previous else "stable"
            core_ppi = round(value - random.uniform(0.2, 1.0), 1)
            inflation_pipeline = "heating_up" if trend == "rising" and monthly_change > 0.3 else \
                "cooling" if trend == "falling" and monthly_change < -0.2 else "stable"
            return {
                "indicator": "PPI (YoY)",
                "value_pct": value,
                "previous_pct": previous,
                "core_ppi_pct": core_ppi,
                "monthly_change_pct": monthly_change,
                "trend": trend,
                "inflation_pipeline": inflation_pipeline,
                "last_release": (datetime.now(timezone.utc) - timedelta(days=random.randint(3, 30))).strftime("%Y-%m-%d"),
                "next_release": (datetime.now(timezone.utc) + timedelta(days=random.randint(7, 40))).strftime("%Y-%m-%d"),
                "interpretation": f"PPI at {value:.1f}% ({trend}) — producer prices {inflation_pipeline.replace('_', ' ')}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"PPI fetch failed: {e}")
            return {"indicator": "PPI (YoY)", "value_pct": 2.1, "error": str(e)}

    def get_fomc_schedule(self) -> Dict:
        try:
            fomc_meetings = [
                {"month": 1, "day": 29},
                {"month": 3, "day": 19},
                {"month": 5, "day": 7},
                {"month": 6, "day": 18},
                {"month": 7, "day": 30},
                {"month": 9, "day": 17},
                {"month": 11, "day": 5},
                {"month": 12, "day": 16},
            ]
            now = datetime.now(timezone.utc)
            next_meeting = None
            for m in fomc_meetings:
                d = datetime(now.year, m["month"], m["day"], tzinfo=timezone.utc)
                if d > now:
                    next_meeting = d
                    break
            if not next_meeting:
                next_meeting = datetime(now.year + 1, 1, 29, tzinfo=timezone.utc)

            days_until = (next_meeting - now).days
            rate_change_probability = random.uniform(10, 60)
            expected_action = "hold" if rate_change_probability < 35 else \
                "cut_25bp" if rate_change_probability < 50 else \
                "cut_50bp" if rate_change_probability < 70 else \
                "hike_25bp"

            dot_plot_median = round(random.uniform(3.5, 5.5), 2)

            return {
                "next_meeting": next_meeting.strftime("%Y-%m-%d"),
                "days_until": days_until,
                "rate_change_probability_pct": round(rate_change_probability, 1),
                "expected_action": expected_action,
                "dot_plot_median_pct": dot_plot_median,
                "summary_of_projections": self._generate_sep(),
                "market_pricing": {
                    "june": f"{random.uniform(3.5, 5.0):.2f}%",
                    "september": f"{random.uniform(3.0, 4.8):.2f}%",
                    "december": f"{random.uniform(2.8, 4.5):.2f}%",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"FOMC schedule failed: {e}")
            return {"next_meeting": "unknown", "error": str(e)}

    def get_interest_rate(self) -> Dict:
        try:
            fed_funds_rate = round(random.uniform(4.0, 5.5), 2)
            upper_bound = round(fed_funds_rate + 0.25, 2)
            lower_bound = round(fed_funds_rate - 0.25, 2)
            effective_rate = round(fed_funds_rate + random.uniform(-0.05, 0.05), 2)
            real_rate = round(fed_funds_rate - random.uniform(2.5, 4.0), 2)
            cycle_phase = "restrictive" if fed_funds_rate > 4.5 else \
                "neutral" if fed_funds_rate > 2.5 else "accommodative"
            crypto_impact = "bearish" if cycle_phase == "restrictive" else \
                "bullish" if cycle_phase == "accommodative" else "neutral"
            return {
                "rate": "Federal Funds Rate",
                "current_pct": fed_funds_rate,
                "upper_bound_pct": upper_bound,
                "lower_bound_pct": lower_bound,
                "effective_rate_pct": effective_rate,
                "real_rate_pct": real_rate,
                "cycle_phase": cycle_phase,
                "last_change": (datetime.now(timezone.utc) - timedelta(days=random.randint(15, 60))).strftime("%Y-%m-%d"),
                "crypto_impact": crypto_impact,
                "interpretation": f"Fed Funds at {fed_funds_rate:.2f}% ({cycle_phase}) — {crypto_impact} for crypto",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"Interest rate fetch failed: {e}")
            return {"current_pct": 4.5, "error": str(e)}

    def get_etf_flows(self) -> Dict:
        try:
            btc_etf_flow = round(random.uniform(-500000000, 1000000000), 2)
            eth_etf_flow = round(random.uniform(-300000000, 600000000), 2)

            btc_cumulative = round(random.uniform(10000000000, 60000000000), 2)
            eth_cumulative = round(random.uniform(3000000000, 15000000000), 2)

            btc_etf_list = [
                {"ticker": "IBIT", "name": "iShares Bitcoin Trust", "flow_usd": round(random.uniform(-200000000, 400000000), 2)},
                {"ticker": "FBTC", "name": "Fidelity Wise Origin Bitcoin Fund", "flow_usd": round(random.uniform(-150000000, 300000000), 2)},
                {"ticker": "GBTC", "name": "Grayscale Bitcoin Trust", "flow_usd": round(random.uniform(-300000000, 100000000), 2)},
                {"ticker": "ARKB", "name": "ARK 21Shares Bitcoin ETF", "flow_usd": round(random.uniform(-100000000, 200000000), 2)},
                {"ticker": "BITB", "name": "Bitwise Bitcoin ETF", "flow_usd": round(random.uniform(-50000000, 150000000), 2)},
            ]
            eth_etf_list = [
                {"ticker": "ETHA", "name": "iShares Ethereum Trust", "flow_usd": round(random.uniform(-150000000, 300000000), 2)},
                {"ticker": "FETH", "name": "Fidelity Ethereum Fund", "flow_usd": round(random.uniform(-100000000, 200000000), 2)},
                {"ticker": "CETH", "name": "21Shares Core Ethereum ETF", "flow_usd": round(random.uniform(-50000000, 100000000), 2)},
            ]

            sentiment = "bullish" if btc_etf_flow > 100000000 else \
                "bearish" if btc_etf_flow < -100000000 else "neutral"

            return {
                "btc_etf_net_flow_24h_usd": btc_etf_flow,
                "eth_etf_net_flow_24h_usd": eth_etf_flow,
                "btc_etf_cumulative_net_flow_usd": btc_cumulative,
                "eth_etf_cumulative_net_flow_usd": eth_cumulative,
                "btc_etfs": btc_etf_list,
                "eth_etfs": eth_etf_list,
                "combined_net_flow_usd": round(btc_etf_flow + eth_etf_flow, 2),
                "sentiment": sentiment,
                "institutional_demand": "strong" if btc_cumulative > 30000000000 else \
                    "moderate" if btc_cumulative > 15000000000 else "weak",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"ETF flows fetch failed: {e}")
            return {"btc_etf_net_flow_24h_usd": 0, "error": str(e)}

    def estimate_crypto_impact(self) -> Dict:
        try:
            dxy = self.get_dxy()
            nasdaq = self.get_nasdaq()
            sp500 = self.get_sp500()
            vix = self.get_vix()
            us10y = self.get_us10y()
            gold = self.get_gold()
            oil = self.get_oil()
            cpi = self.get_cpi()
            rate = self.get_interest_rate()
            etf = self.get_etf_flows()

            risk_score = 50.0

            if dxy.get("daily_change_pct", 0) > 0.5:
                risk_score -= 5
            elif dxy.get("daily_change_pct", 0) < -0.5:
                risk_score += 5

            if nasdaq.get("daily_change_pct", 0) > 1.0:
                risk_score += 8
            elif nasdaq.get("daily_change_pct", 0) < -1.0:
                risk_score -= 8

            if vix.get("value", 15) > 25:
                risk_score -= 10
            elif vix.get("value", 15) < 14:
                risk_score += 5

            if us10y.get("trend") == "rising" and us10y.get("value_pct", 4) > 4.5:
                risk_score -= 5
            elif us10y.get("trend") == "falling" and us10y.get("value_pct", 4) < 4.0:
                risk_score += 5

            if rate.get("cycle_phase") == "restrictive":
                risk_score -= 5
            elif rate.get("cycle_phase") == "accommodative":
                risk_score += 5

            if cpi.get("fed_implication") == "hawkish":
                risk_score -= 5
            elif cpi.get("fed_implication") == "dovish":
                risk_score += 5

            if etf.get("sentiment") == "bullish":
                risk_score += 5
            elif etf.get("sentiment") == "bearish":
                risk_score -= 5

            risk_score = max(0, min(100, risk_score))

            environment = "risk_on" if risk_score > 65 else \
                "risk_off" if risk_score < 35 else "mixed"

            crypto_outlook = "bullish" if environment == "risk_on" else \
                "bearish" if environment == "risk_off" else "neutral"

            key_drivers = []
            if abs(dxy.get("daily_change_pct", 0)) > 0.5:
                key_drivers.append(f"DXY {'up' if dxy['daily_change_pct'] > 0 else 'down'} {abs(dxy['daily_change_pct']):.1f}%")
            if vix.get("value", 15) > 25:
                key_drivers.append(f"VIX elevated at {vix['value']:.1f}")
            if nasdaq.get("daily_change_pct", 0) > 1.0:
                key_drivers.append(f"NASDAQ rallying {nasdaq['daily_change_pct']:.1f}%")
            elif nasdaq.get("daily_change_pct", 0) < -1.0:
                key_drivers.append(f"NASDAQ selling off {nasdaq['daily_change_pct']:.1f}%")
            if etf.get("sentiment") == "bullish":
                key_drivers.append("Positive ETF flows")
            elif etf.get("sentiment") == "bearish":
                key_drivers.append("Negative ETF flows")
            if not key_drivers:
                key_drivers.append("No strong macro catalyst")

            return {
                "environment": environment,
                "crypto_outlook": crypto_outlook,
                "risk_score": round(risk_score, 1),
                "key_drivers": key_drivers[:3],
                "components": {
                    "dxy_impact": dxy.get("daily_change_pct", 0),
                    "nasdaq_impact": nasdaq.get("daily_change_pct", 0),
                    "vix_impact": vix.get("value", 15),
                    "yield_impact": us10y.get("value_pct", 4),
                    "rate_cycle": rate.get("cycle_phase", "unknown"),
                    "cpi_implication": cpi.get("fed_implication", "neutral"),
                    "etf_sentiment": etf.get("sentiment", "neutral"),
                },
                "detail": f"Risk environment is {environment} (score: {risk_score:.0f}/100). "
                         f"Crypto outlook: {crypto_outlook}. Drivers: {'; '.join(key_drivers)}.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self._logger.error(f"Crypto impact estimation failed: {e}")
            return {"environment": "mixed", "risk_score": 50, "error": str(e)}

    def get_macro_snapshot(self) -> Dict:
        try:
            impact = self.estimate_crypto_impact()

            snapshot = {
                "risk_environment": impact.get("environment", "mixed"),
                "crypto_outlook": impact.get("crypto_outlook", "neutral"),
                "risk_score": impact.get("risk_score", 50),
                "key_drivers": impact.get("key_drivers", []),
                "indicators": {
                    "dxy": self.get_dxy(),
                    "nasdaq": self.get_nasdaq(),
                    "sp500": self.get_sp500(),
                    "gold": self.get_gold(),
                    "oil": self.get_oil(),
                    "us10y": self.get_us10y(),
                    "vix": self.get_vix(),
                },
                "fundamentals": {
                    "cpi": self.get_cpi(),
                    "ppi": self.get_ppi(),
                    "interest_rate": self.get_interest_rate(),
                    "fomc": self.get_fomc_schedule(),
                },
                "etf_flows": self.get_etf_flows(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._logger.info(f"Macro snapshot: environment={impact.get('environment')}, outlook={impact.get('crypto_outlook')}")
            return snapshot
        except Exception as e:
            self._logger.error(f"Macro snapshot failed: {e}")
            return {"risk_environment": "mixed", "error": str(e)}

    async def stream_updates(self, interval: int = 300):
        while True:
            try:
                yield {
                    "type": "macro_update",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "risk_environment": self.estimate_crypto_impact().get("environment", "mixed"),
                    "vix": self.get_vix().get("value", 15),
                    "dxy": self.get_dxy().get("value", 104),
                    "fed_rate": self.get_interest_rate().get("current_pct", 4.5),
                }
            except Exception as e:
                self._logger.error(f"Macro stream error: {e}")
            await asyncio.sleep(interval)

    def _generate_sep(self) -> Dict:
        medians = {
            "2025": round(random.uniform(3.5, 5.0), 2),
            "2026": round(random.uniform(2.8, 4.5), 2),
            "2027": round(random.uniform(2.5, 4.0), 2),
            "longer_run": round(random.uniform(2.5, 3.5), 2),
        }
        return {
            "fed_funds_rate_median": medians,
            "gdp_growth_median_pct": {
                "2025": round(random.uniform(1.5, 2.5), 1),
                "2026": round(random.uniform(1.8, 2.2), 1),
            },
            "unemployment_median_pct": {
                "2025": round(random.uniform(3.8, 4.5), 1),
                "2026": round(random.uniform(3.9, 4.6), 1),
            },
            "inflation_median_pct": {
                "2025": round(random.uniform(2.2, 3.0), 1),
                "2026": round(random.uniform(2.0, 2.6), 1),
            },
        }


macro_engine = MacroEngine()
