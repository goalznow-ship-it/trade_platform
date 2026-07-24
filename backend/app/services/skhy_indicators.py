import numpy as np
import math
from typing import Tuple, Optional

def calculate_ema(data: list, period: int) -> list:
    if len(data) < period:
        return []
    multiplier = 2.0 / (period + 1)
    ema = [data[0]]
    for i in range(1, len(data)):
        ema.append((data[i] - ema[-1]) * multiplier + ema[-1])
    return ema

def calculate_sma(data: list, period: int) -> list:
    if len(data) < period:
        return []
    result = []
    for i in range(len(data) - period + 1):
        result.append(sum(data[i:i + period]) / period)
    return [result[0]] * (period - 1) + result

def calculate_rsi(data: list, period: int = 14) -> list:
    if len(data) < period + 1:
        return []
    deltas = [data[i] - data[i - 1] for i in range(1, len(data))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi = [100 - (100 / (1 + avg_gain / avg_loss))] if avg_loss != 0 else [100]
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rsi.append(100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss != 0 else 100)
    return [None] * period + rsi

def calculate_macd(data: list, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    if not ema_fast or not ema_slow:
        return {"macd": [], "signal": [], "histogram": []}
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(min(len(ema_fast), len(ema_slow)))]
    signal_line = calculate_ema(macd_line, signal)
    if not signal_line:
        return {"macd": macd_line, "signal": [], "histogram": []}
    histogram = [macd_line[i] - signal_line[i] if i < len(signal_line) else 0 for i in range(len(macd_line))]
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

def calculate_adx(high: list, low: list, close: list, period: int = 14) -> list:
    if len(close) < period + 1:
        return []
    tr = [max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1])) for i in range(1, len(close))]
    up_move = [high[i] - high[i - 1] for i in range(1, len(high))]
    down_move = [low[i - 1] - low[i] for i in range(1, len(low))]
    plus_dm = [up_move[i] if up_move[i] > down_move[i] and up_move[i] > 0 else 0 for i in range(len(up_move))]
    minus_dm = [down_move[i] if down_move[i] > up_move[i] and down_move[i] > 0 else 0 for i in range(len(down_move))]

    def _smooth(values, period):
        result = [sum(values[:period])]
        for i in range(period, len(values)):
            result.append(result[-1] - result[-1] / period + values[i])
        return result

    tr_smooth = _smooth(tr, period)
    plus_smooth = _smooth(plus_dm, period)
    minus_smooth = _smooth(minus_dm, period)
    plus_di = [100 * p / t if t != 0 else 0 for p, t in zip(plus_smooth, tr_smooth)]
    minus_di = [100 * m / t if t != 0 else 0 for m, t in zip(minus_smooth, tr_smooth)]
    dx = [100 * abs(p - m) / (p + m) if (p + m) != 0 else 0 for p, m in zip(plus_di, minus_di)]
    adx = calculate_ema(dx, period)
    return adx

def calculate_atr(high: list, low: list, close: list, period: int = 14) -> list:
    if len(close) < period + 1:
        return [None] * len(close)
    tr = [max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1])) for i in range(1, len(close))]
    inner = [sum(tr[:period]) / period]
    for i in range(period, len(tr)):
        inner.append((inner[-1] * (period - 1) + tr[i]) / period)
    return [None] * period + inner

def calculate_bollinger(data: list, period: int = 20, std_mult: float = 2.0) -> dict:
    if len(data) < period:
        return {"upper": [], "middle": [], "lower": []}
    sma = calculate_sma(data, period)
    upper, lower = [], []
    for i in range(len(data)):
        if i < period - 1 or sma[i] is None:
            upper.append(None)
            lower.append(None)
        else:
            std = np.std(data[i - period + 1:i + 1])
            upper.append(sma[i] + std_mult * std)
            lower.append(sma[i] - std_mult * std)
    return {"upper": upper, "middle": sma, "lower": lower}

def calculate_stochastic_rsi(data: list, period: int = 14, k: int = 3, d: int = 3) -> dict:
    if len(data) < period:
        return {"k": [], "d": []}
    rsi = calculate_rsi(data, period)
    rsi_vals = [r for r in rsi if r is not None]
    if len(rsi_vals) < period:
        return {"k": [], "d": []}
    stoch = []
    for i in range(period, len(rsi_vals) + 1):
        window = rsi_vals[i - period:i]
        min_r = min(window)
        max_r = max(window)
        stoch.append(100 * (rsi_vals[i - 1] - min_r) / (max_r - min_r) if max_r != min_r else 50)
    k_line = calculate_sma(stoch, k) if len(stoch) >= k else []
    d_line = calculate_ema(k_line, d) if len(k_line) >= d else []
    return {"k": k_line if k_line else stoch, "d": d_line if d_line else []}

def calculate_cci(high: list, low: list, close: list, period: int = 20) -> list:
    if len(close) < period:
        return []
    tp = [(high[i] + low[i] + close[i]) / 3 for i in range(len(close))]
    sma_tp = calculate_sma(tp, period)
    cci = []
    for i in range(len(tp)):
        if i < period - 1 or sma_tp[i] is None:
            cci.append(None)
        else:
            mean_dev = sum(abs(tp[j] - sma_tp[i]) for j in range(i - period + 1, i + 1)) / period
            cci.append((tp[i] - sma_tp[i]) / (0.015 * mean_dev) if mean_dev != 0 else 0)
    return cci

def calculate_mfi(high: list, low: list, close: list, volume: list, period: int = 14) -> list:
    if len(close) < period + 1:
        return []
    typical = [(high[i] + low[i] + close[i]) / 3 for i in range(len(close))]
    mf = [typical[i] * volume[i] for i in range(len(typical))]
    mfi = []
    for i in range(period, len(mf)):
        pos, neg = 0, 0
        for j in range(i - period, i):
            if typical[j + 1] > typical[j]:
                pos += mf[j + 1]
            else:
                neg += mf[j + 1]
        mfi.append(100 - (100 / (1 + pos / neg)) if neg != 0 else 100)
    return [None] * (period) + mfi

def calculate_obv(close: list, volume: list) -> list:
    obv = [0]
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            obv.append(obv[-1] + volume[i])
        elif close[i] < close[i - 1]:
            obv.append(obv[-1] - volume[i])
        else:
            obv.append(obv[-1])
    return obv

def calculate_cmf(high: list, low: list, close: list, volume: list, period: int = 20) -> list:
    if len(close) < period:
        return []
    mfv = [volume[i] * ((close[i] - low[i]) - (high[i] - close[i])) / (high[i] - low[i]) if (high[i] - low[i]) != 0 else 0 for i in range(len(close))]
    cmf = []
    for i in range(period - 1, len(mfv)):
        vol_sum = sum(volume[i - period + 1:i + 1])
        cmf.append(sum(mfv[i - period + 1:i + 1]) / vol_sum if vol_sum != 0 else 0)
    return [None] * (period - 1) + cmf

def calculate_supertrend(high: list, low: list, close: list, period: int = 10, multiplier: float = 3.0) -> dict:
    if len(close) < period + 1:
        return {"trend": [], "direction": []}
    atr = calculate_atr(high, low, close, period)
    hl_avg = [(high[i] + low[i]) / 2 for i in range(len(close))]
    upper = [0] * len(close)
    lower = [0] * len(close)
    trend = [0] * len(close)
    direction = [""] * len(close)
    for i in range(1, len(close)):
        if atr[i] is None:
            upper[i] = upper[i - 1] if i > 0 else 0
            lower[i] = lower[i - 1] if i > 0 else 0
            trend[i] = trend[i - 1] if i > 0 else 1
            continue
        atr_val = atr[i] if atr[i] else 0
        upper[i] = hl_avg[i] + multiplier * atr_val
        lower[i] = hl_avg[i] - multiplier * atr_val
        if close[i] > upper[i - 1]:
            trend[i] = 1
        elif close[i] < lower[i - 1]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]
        if trend[i] == 1:
            upper[i] = min(upper[i], upper[i - 1]) if trend[i - 1] == 1 else upper[i]
            lower[i] = max(lower[i], lower[i - 1]) if trend[i - 1] == -1 else lower[i]
        elif trend[i] == -1:
            lower[i] = max(lower[i], lower[i - 1]) if trend[i - 1] == -1 else lower[i]
            upper[i] = min(upper[i], upper[i - 1]) if trend[i - 1] == 1 else upper[i]
        direction[i] = "up" if trend[i] == 1 else "down"
    return {"trend": trend, "direction": direction, "upper": upper, "lower": lower}

def calculate_vwap(data: list) -> list:
    result = []
    cum_pv, cum_vol = 0, 0
    for d in data:
        tp = (d["high"] + d["low"] + d["close"]) / 3
        cum_pv += tp * d["volume"]
        cum_vol += d["volume"]
        result.append(cum_pv / cum_vol if cum_vol != 0 else tp)
    return result

def calculate_relative_volume(volume: list, period: int = 20) -> list:
    if len(volume) < period:
        return []
    result = []
    for i in range(len(volume)):
        if i < period:
            result.append(None)
        else:
            avg_vol = sum(volume[i - period:i]) / period
            result.append(volume[i] / avg_vol if avg_vol != 0 else 0)
    return result

class SkhyIndicators:
    def analyze(self, data: list) -> dict:
        closes = [d["close"] for d in data]
        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]
        volumes = [d["volume"] for d in data]
        opens = [d["open"] for d in data]

        ema9 = calculate_ema(closes, 9)
        ema20 = calculate_ema(closes, 20)
        ema50 = calculate_ema(closes, 50) if len(closes) >= 50 else []
        ema100 = calculate_ema(closes, 100) if len(closes) >= 100 else []
        ema200 = calculate_ema(closes, 200) if len(closes) >= 200 else []
        rsi = calculate_rsi(closes)
        macd = calculate_macd(closes)
        adx = calculate_adx(highs, lows, closes)
        atr = calculate_atr(highs, lows, closes)
        bb = calculate_bollinger(closes)
        stoch_rsi = calculate_stochastic_rsi(closes)
        cci = calculate_cci(highs, lows, closes)
        mfi = calculate_mfi(highs, lows, closes, volumes)
        obv = calculate_obv(closes, volumes)
        cmf = calculate_cmf(highs, lows, closes, volumes)
        st = calculate_supertrend(highs, lows, closes)
        vwap = calculate_vwap(data)
        rel_vol = calculate_relative_volume(volumes)

        current = {
            "close": closes[-1] if closes else None,
            "volume": volumes[-1] if volumes else None,
        }

        interpretation = self._interpret_indicators(
            current, closes, highs, lows, volumes,
            ema9, ema20, ema50, ema100, ema200,
            rsi, macd, adx, atr, bb, stoch_rsi, cci, mfi, obv, cmf, st, vwap, rel_vol,
        )

        return {
            "ema9": ema9, "ema20": ema20, "ema50": ema50, "ema100": ema100, "ema200": ema200,
            "rsi": rsi, "macd": macd, "adx": adx, "atr": atr,
            "bollinger": bb, "stoch_rsi": stoch_rsi, "cci": cci, "mfi": mfi,
            "obv": obv, "cmf": cmf, "supertrend": st, "vwap": vwap, "relative_volume": rel_vol,
            "interpretation": interpretation,
        }

    def _interpret_indicators(self, current, closes, highs, lows, volumes, ema9, ema20, ema50, ema100, ema200,
                              rsi, macd, adx, atr, bb, stoch_rsi, cci, mfi, obv, cmf, st, vwap, rel_vol) -> dict:
        close = current["close"]
        interp = {"trend": {}, "momentum": {}, "volume": {}, "volatility": {}, "overall": "neutral"}

        bullish_count = 0
        bearish_count = 0

        ema_signals = {}
        if len(ema9) > 0 and len(ema20) > 0:
            if ema9[-1] > ema20[-1]:
                ema_signals["ema_cross"] = "bullish"
                bullish_count += 1
            else:
                ema_signals["ema_cross"] = "bearish"
                bearish_count += 1
        if len(ema50) > 0 and close:
            if close > ema50[-1]:
                ema_signals["price_vs_ema50"] = "bullish"
                bullish_count += 1
            else:
                ema_signals["price_vs_ema50"] = "bearish"
                bearish_count += 1
        if len(ema200) > 0 and close:
            if close > ema200[-1]:
                ema_signals["price_vs_ema200"] = "bullish"
            else:
                ema_signals["price_vs_ema200"] = "bearish"
        interp["trend"]["ema"] = ema_signals
        interp["trend"]["bias"] = "bullish" if bullish_count > bearish_count else "bearish" if bearish_count > bullish_count else "neutral"

        rsi_val = rsi[-1] if rsi and rsi[-1] is not None else None
        if rsi_val:
            if rsi_val > 70:
                interp["momentum"]["rsi"] = "overbought"
                bearish_count += 1
            elif rsi_val > 60:
                interp["momentum"]["rsi"] = "bullish"
                bullish_count += 1
            elif rsi_val > 40:
                interp["momentum"]["rsi"] = "neutral"
            elif rsi_val > 30:
                interp["momentum"]["rsi"] = "bearish"
                bearish_count += 1
            else:
                interp["momentum"]["rsi"] = "oversold"
                bullish_count += 1

        if macd.get("histogram") and len(macd["histogram"]) > 1:
            prev_hist = macd["histogram"][-2] if len(macd["histogram"]) >= 2 else 0
            curr_hist = macd["histogram"][-1]
            if curr_hist > prev_hist:
                interp["momentum"]["macd"] = "bullish"
                bullish_count += 1
            elif curr_hist < prev_hist:
                interp["momentum"]["macd"] = "bearish"
                bearish_count += 1
            else:
                interp["momentum"]["macd"] = "neutral"

        adx_val = adx[-1] if adx and len(adx) > 0 and adx[-1] is not None else None
        if adx_val:
            if adx_val > 25:
                interp["trend"]["adx"] = "strong_trend"
            elif adx_val > 20:
                interp["trend"]["adx"] = "trending"
            else:
                interp["trend"]["adx"] = "weak_trend"

        if bb.get("upper") and len(bb["upper"]) > 0:
            upper_bb = bb["upper"][-1]
            lower_bb = bb["lower"][-1]
            if close and upper_bb and lower_bb:
                bb_width = (upper_bb - lower_bb) / (upper_bb + lower_bb) * 200 if upper_bb + lower_bb > 0 else 0
                interp["volatility"]["bollinger_width"] = bb_width
                if close >= upper_bb:
                    interp["momentum"]["bollinger"] = "overbought"
                elif close <= lower_bb:
                    interp["momentum"]["bollinger"] = "oversold"
                else:
                    interp["momentum"]["bollinger"] = "neutral"

        if st.get("direction") and len(st["direction"]) > 0:
            interp["trend"]["supertrend"] = st["direction"][-1]
            if st["direction"][-1] == "up":
                bullish_count += 1
            else:
                bearish_count += 1

        cci_val = cci[-1] if cci and len(cci) > 0 and cci[-1] is not None else None
        if cci_val:
            if cci_val > 100:
                interp["momentum"]["cci"] = "overbought"
            elif cci_val > 0:
                interp["momentum"]["cci"] = "bullish"
            elif cci_val > -100:
                interp["momentum"]["cci"] = "bearish"
            else:
                interp["momentum"]["cci"] = "oversold"

        mfi_val = mfi[-1] if mfi and len(mfi) > 0 and mfi[-1] is not None else None
        if mfi_val:
            if mfi_val > 80:
                interp["volume"]["mfi"] = "overbought"
            elif mfi_val > 20:
                interp["volume"]["mfi"] = "neutral"
            else:
                interp["volume"]["mfi"] = "oversold"

        cmf_val = cmf[-1] if cmf and len(cmf) > 0 and cmf[-1] is not None else None
        if cmf_val:
            if cmf_val > 0.05:
                interp["volume"]["cmf"] = "bullish"
                bullish_count += 1
            elif cmf_val < -0.05:
                interp["volume"]["cmf"] = "bearish"
                bearish_count += 1
            else:
                interp["volume"]["cmf"] = "neutral"

        rel_vol_val = rel_vol[-1] if rel_vol and len(rel_vol) > 0 and rel_vol[-1] is not None else None
        if rel_vol_val:
            if rel_vol_val > 1.5:
                interp["volume"]["relative_volume"] = "high"
            elif rel_vol_val > 1.0:
                interp["volume"]["relative_volume"] = "above_average"
            else:
                interp["volume"]["relative_volume"] = "below_average"

        if bullish_count > bearish_count + 1:
            interp["overall"] = "bullish"
        elif bearish_count > bullish_count + 1:
            interp["overall"] = "bearish"
        else:
            interp["overall"] = "neutral"

        if ema9 and len(ema9) > 1 and ema20 and len(ema20) > 1:
            interp["trend"]["ema_alignment"] = "bullish_aligned" if ema9[-1] > ema20[-1] > (ema50[-1] if ema50 else 0) else "bearish_aligned" if ema9[-1] < ema20[-1] < (ema50[-1] if ema50 else 0) else "mixed"

        return interp

skhy_indicators = SkhyIndicators()
