import asyncio
from typing import Optional, List, Callable
from app.services.market import market_service
from app.services.indicators import indicator_service
from app.services.ai_analysis import ai_engine
from app.core.logging import logger


class EnterpriseScanner:
    def __init__(self):
        self.logger = logger
        self.default_symbols = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
            "MATIC/USDT", "ATOM/USDT", "UNI/USDT", "ARB/USDT", "OP/USDT",
            "INJ/USDT", "TIA/USDT", "SEI/USDT", "APT/USDT", "SUI/USDT",
            "PEPE/USDT", "FIL/USDT", "NEAR/USDT", "APT/USDT", "LDO/USDT",
        ]

    async def scan_by_filter(self, filter_type: str, symbols: Optional[List[str]] = None,
                              timeframe: str = "1h", limit: int = 10) -> list:
        symbols = symbols or self.default_symbols
        results = []
        for symbol in symbols:
            try:
                data = await market_service.get_ohlcv(symbol, "binance", timeframe, 100)
                if not data or len(data) < 50:
                    continue
                score = await self._apply_filter(filter_type, data)
                if score is not None:
                    results.append({"symbol": symbol, "score": score, "filter": filter_type})
            except Exception:
                continue
            await asyncio.sleep(0.05)

        results.sort(key=lambda r: abs(r["score"]), reverse=True)
        return results[:limit]

    async def scan_multi_filter(self, filters: List[str], symbols: Optional[List[str]] = None,
                                 timeframe: str = "1h", limit: int = 20) -> list:
        all_results = []
        for f in filters:
            batch = await self.scan_by_filter(f, symbols, timeframe, limit // len(filters))
            all_results.extend(batch)
        all_results.sort(key=lambda r: abs(r["score"]), reverse=True)
        return all_results[:limit]

    async def _apply_filter(self, filter_type: str, data: list) -> Optional[float]:
        filters = {
            "rsi_oversold": self._rsi_oversold,
            "rsi_overbought": self._rsi_overbought,
            "volume_spike": self._volume_spike,
            "breakout": self._breakout,
            "breakdown": self._breakdown,
            "ema_bullish": self._ema_bullish_cross,
            "ema_bearish": self._ema_bearish_cross,
            "macd_bullish": self._macd_bullish,
            "macd_bearish": self._macd_bearish,
            "high_volatility": self._high_volatility,
            "strong_trend": self._strong_trend,
            "liquidity_grab": self._liquidity_grab,
            "golden_cross": self._golden_cross,
            "death_cross": self._death_cross,
            "supertrend_bullish": self._supertrend_bullish,
            "supertrend_bearish": self._supertrend_bearish,
        }
        handler = filters.get(filter_type)
        if handler:
            return handler(data)
        return None

    def _rsi_oversold(self, data: list) -> float:
        rsi = indicator_service.rsi(data, 14)
        val = rsi.get("current", 50)
        if val < 30:
            return (30 - val) / 30 * 100
        return 0

    def _rsi_overbought(self, data: list) -> float:
        rsi = indicator_service.rsi(data, 14)
        val = rsi.get("current", 50)
        if val > 70:
            return (val - 70) / 30 * 100
        return 0

    def _volume_spike(self, data: list) -> float:
        if len(data) < 20:
            return 0
        volumes = [d["volume"] for d in data]
        avg = sum(volumes[-20:]) / 20 if volumes else 1
        current = volumes[-1] if volumes else 0
        if avg > 0 and current > avg * 2:
            return min((current / avg - 1) * 50, 100)
        return 0

    def _breakout(self, data: list) -> float:
        if len(data) < 20:
            return 0
        highs = [d["high"] for d in data]
        close = data[-1]["close"]
        resistance = max(highs[-20:]) if highs else close
        if close > resistance:
            return min((close / resistance - 1) * 1000, 100)
        return 0

    def _breakdown(self, data: list) -> float:
        if len(data) < 20:
            return 0
        lows = [d["low"] for d in data]
        close = data[-1]["close"]
        support = min(lows[-20:]) if lows else close
        if close < support:
            return min((support / close - 1) * 1000, 100)
        return 0

    def _ema_bullish_cross(self, data: list) -> float:
        ema9 = indicator_service.ema(data, 9)
        ema21 = indicator_service.ema(data, 21)
        if len(ema9) < 2 or len(ema21) < 2:
            return 0
        if ema9[-1] > ema21[-1] and ema9[-2] <= ema21[-2]:
            return 90
        if ema9[-1] > ema21[-1]:
            return 50
        return 0

    def _ema_bearish_cross(self, data: list) -> float:
        ema9 = indicator_service.ema(data, 9)
        ema21 = indicator_service.ema(data, 21)
        if len(ema9) < 2 or len(ema21) < 2:
            return 0
        if ema9[-1] < ema21[-1] and ema9[-2] >= ema21[-2]:
            return 90
        if ema9[-1] < ema21[-1]:
            return 50
        return 0

    def _macd_bullish(self, data: list) -> float:
        macd = indicator_service.macd(data)
        hist = macd.get("histogram", [])
        if len(hist) >= 2:
            if hist[-1] > 0 and hist[-2] <= 0:
                return 90
            if hist[-1] > 0:
                return 60
        return 0

    def _macd_bearish(self, data: list) -> float:
        macd = indicator_service.macd(data)
        hist = macd.get("histogram", [])
        if len(hist) >= 2:
            if hist[-1] < 0 and hist[-2] >= 0:
                return 90
            if hist[-1] < 0:
                return 60
        return 0

    def _high_volatility(self, data: list) -> float:
        if len(data) < 14:
            return 0
        atr_vals = indicator_service.atr(data, 14)
        if not atr_vals:
            return 0
        close = data[-1]["close"]
        if close > 0:
            atr_pct = atr_vals[-1] / close * 100
            return min(atr_pct * 10, 100)
        return 0

    def _strong_trend(self, data: list) -> float:
        adx = indicator_service.adx(data, 14)
        val = adx.get("current_adx", 0)
        return min(val * 2, 100)

    def _liquidity_grab(self, data: list) -> float:
        if len(data) < 10:
            return 0
        highs = [d["high"] for d in data[-10:]]
        lows = [d["low"] for d in data[-10:]]
        closes = [d["close"] for d in data[-10:]]
        recent_high = max(highs)
        recent_low = min(lows)
        current = closes[-1] if closes else 0
        if current > recent_high:
            return 70
        if current < recent_low:
            return 70
        return 0

    def _golden_cross(self, data: list) -> float:
        sma50 = indicator_service.sma(data, 50)
        sma200 = indicator_service.sma(data, 200)
        if len(sma50) >= 2 and len(sma200) >= 2:
            if sma50[-1] > sma200[-1] and sma50[-2] <= sma200[-2]:
                return 100
            if sma50[-1] > sma200[-1]:
                return 70
        return 0

    def _death_cross(self, data: list) -> float:
        sma50 = indicator_service.sma(data, 50)
        sma200 = indicator_service.sma(data, 200)
        if len(sma50) >= 2 and len(sma200) >= 2:
            if sma50[-1] < sma200[-1] and sma50[-2] >= sma200[-2]:
                return 100
            if sma50[-1] < sma200[-1]:
                return 70
        return 0

    def _supertrend_bullish(self, data: list) -> float:
        st = indicator_service.supertrend(data, 10, 3)
        if st.get("current_direction") == "uptrend":
            return 80
        return 0

    def _supertrend_bearish(self, data: list) -> float:
        st = indicator_service.supertrend(data, 10, 3)
        if st.get("current_direction") == "downtrend":
            return 80
        return 0

    @property
    def available_filters(self) -> list:
        return [
            "rsi_oversold", "rsi_overbought", "volume_spike",
            "breakout", "breakdown", "ema_bullish", "ema_bearish",
            "macd_bullish", "macd_bearish", "high_volatility",
            "strong_trend", "liquidity_grab", "golden_cross",
            "death_cross", "supertrend_bullish", "supertrend_bearish",
        ]


enterprise_scanner = EnterpriseScanner()
