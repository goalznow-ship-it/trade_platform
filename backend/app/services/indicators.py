import pandas as pd
import numpy as np

class IndicatorService:
    @staticmethod
    def _to_series(data: list, field: str = 'close'):
        if not data:
            return pd.Series(dtype=float)
        return pd.to_numeric(pd.Series([d[field] for d in data]), errors="coerce")

    @staticmethod
    def sma(data: list, period: int = 20, field: str = 'close') -> list:
        s = IndicatorService._to_series(data, field)
        return s.rolling(period).mean().dropna().tolist()

    @staticmethod
    def ema(data: list, period: int = 20, field: str = 'close') -> list:
        s = IndicatorService._to_series(data, field)
        return s.ewm(span=period, adjust=False).mean().dropna().tolist()

    @staticmethod
    def rsi(data: list, period: int = 14) -> dict:
        s = IndicatorService._to_series(data)
        delta = s.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0))
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        values = rsi.dropna().tolist()
        return {
            'values': values,
            'current': values[-1] if values else 50,
            'oversold': values[-1] < 30 if values else False,
            'overbought': values[-1] > 70 if values else False,
        }

    @staticmethod
    def macd(data: list) -> dict:
        s = IndicatorService._to_series(data)
        ema12 = s.ewm(span=12, adjust=False).mean()
        ema26 = s.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal
        return {
            'macd': macd_line.dropna().tolist(),
            'signal': signal.dropna().tolist(),
            'histogram': histogram.dropna().tolist(),
            'current_macd': float(macd_line.iloc[-1]) if len(macd_line) > 0 else 0,
            'current_signal': float(signal.iloc[-1]) if len(signal) > 0 else 0,
            'current_histogram': float(histogram.iloc[-1]) if len(histogram) > 0 else 0,
        }

    @staticmethod
    def bollinger(data: list, period: int = 20, std: float = 2.0) -> dict:
        s = IndicatorService._to_series(data)
        sma = s.rolling(period).mean()
        std_dev = s.rolling(period).std()
        return {
            'upper': (sma + std_dev * std).dropna().tolist(),
            'middle': sma.dropna().tolist(),
            'lower': (sma - std_dev * std).dropna().tolist(),
        }

    @staticmethod
    def adx(data: list, period: int = 14) -> dict:
        high = IndicatorService._to_series(data, 'high')
        low = IndicatorService._to_series(data, 'low')
        close = IndicatorService._to_series(data)
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        up = high.diff()
        down = -low.diff()
        plus_dm = ((up > down) & (up > 0)).astype(float) * up
        minus_dm = ((down > up) & (down > 0)).astype(float) * down
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx = dx.rolling(period).mean()
        return {
            'adx': adx.dropna().tolist(),
            'plus_di': plus_di.dropna().tolist(),
            'minus_di': minus_di.dropna().tolist(),
            'current_adx': float(adx.dropna().iloc[-1]) if len(adx.dropna()) > 0 else 0,
        }

    @staticmethod
    def atr(data: list, period: int = 14) -> list:
        high = IndicatorService._to_series(data, 'high')
        low = IndicatorService._to_series(data, 'low')
        close = IndicatorService._to_series(data)
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period).mean().dropna().tolist()

    @staticmethod
    def latest_atr(data: list, period: int = 14) -> float | None:
        values = IndicatorService.atr(data, period)
        return float(values[-1]) if values else None

    @staticmethod
    def supertrend(data: list, period: int = 10, multiplier: float = 3.0) -> dict:
        if not data:
            return {'supertrend': [], 'direction': [], 'current_direction': 'unavailable'}
        high = IndicatorService._to_series(data, 'high')
        low = IndicatorService._to_series(data, 'low')
        close = IndicatorService._to_series(data)
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        hl_avg = (high + low) / 2
        upper_band = hl_avg + multiplier * atr
        lower_band = hl_avg - multiplier * atr
        supertrend = pd.Series(np.nan, index=close.index)
        direction = pd.Series(1, index=close.index)
        for i in range(period, len(close)):
            if close.iloc[i] > upper_band.iloc[i - 1]:
                direction.iloc[i] = 1
            elif close.iloc[i] < lower_band.iloc[i - 1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i - 1]
            if direction.iloc[i] == 1:
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
        return {
            'supertrend': supertrend.dropna().tolist(),
            'direction': direction.dropna().tolist(),
            'current_direction': 'uptrend' if direction.iloc[-1] == 1 else 'downtrend',
        }

    @staticmethod
    def vwap(data: list) -> list:
        if not data:
            return []
        df = pd.DataFrame(data)
        denominator = df['volume'].cumsum().replace(0, np.nan)
        vwap = (df['close'] * df['volume']).cumsum() / denominator
        return vwap.dropna().tolist()

    @staticmethod
    def obv(data: list) -> list:
        if not data:
            return []
        close = IndicatorService._to_series(data)
        volume = IndicatorService._to_series(data, 'volume')
        direction = np.sign(close.diff()).fillna(0)
        obv = (volume * direction).cumsum()
        return obv.dropna().tolist()

    @staticmethod
    def cmf(data: list, period: int = 20) -> list:
        df = pd.DataFrame(data)
        mfv = df['volume'] * ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low']).replace(0, np.nan)
        cmf = mfv.rolling(period).sum() / df['volume'].rolling(period).sum()
        return cmf.dropna().tolist()

    @staticmethod
    def stochastic_rsi(data: list, period: int = 14) -> dict:
        rsi_data = IndicatorService.rsi(data, period)
        rsi_values = pd.Series(rsi_data['values'])
        k = 100 * ((rsi_values - rsi_values.rolling(period).min()) /
                   (rsi_values.rolling(period).max() - rsi_values.rolling(period).min()).replace(0, np.nan))
        d = k.rolling(3).mean()
        return {
            'k': k.dropna().tolist(),
            'd': d.dropna().tolist(),
        }

    @staticmethod
    def ichimoku(data: list) -> dict:
        high = IndicatorService._to_series(data, 'high')
        low = IndicatorService._to_series(data, 'low')
        close = IndicatorService._to_series(data)
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        senkou_a = (tenkan + kijun) / 2
        senkou_b = (high.rolling(52).max() + low.rolling(52).min()) / 2
        chikou = close.shift(-26)
        return {
            'tenkan_sen': tenkan.dropna().tolist(),
            'kijun_sen': kijun.dropna().tolist(),
            'senkou_span_a': senkou_a.dropna().tolist(),
            'senkou_span_b': senkou_b.dropna().tolist(),
            'chikou_span': chikou.dropna().tolist(),
        }

    @staticmethod
    def volume_profile(data: list, num_bins: int = 10) -> dict:
        if not data or num_bins < 1:
            return {'bins': [], 'poc': {}}
        df = pd.DataFrame(data)
        price_min = df['low'].min()
        price_max = df['high'].max()
        bin_size = (price_max - price_min) / num_bins
        if bin_size == 0:
            volume = float(df['volume'].sum())
            item = {'price_low': float(price_min), 'price_high': float(price_max), 'volume': volume}
            return {'bins': [item], 'poc': item}
        bins = []
        for i in range(num_bins):
            lower = price_min + i * bin_size
            upper = lower + bin_size
            mask = (df['close'] >= lower) & (df['close'] < upper)
            vol = df[mask]['volume'].sum()
            bins.append({
                'price_low': lower,
                'price_high': upper,
                'volume': float(vol),
            })
        return {'bins': bins, 'poc': max(bins, key=lambda b: b['volume']) if bins else {}}

    @staticmethod
    def pivot_points(data: list, lookback: int = 20) -> dict:
        highs = pd.Series([d['high'] for d in data])
        lows = pd.Series([d['low'] for d in data])
        pivots_high = []
        pivots_low = []
        for i in range(2, len(data) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                pivots_high.append({'price': float(highs[i]), 'index': i})
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                pivots_low.append({'price': float(lows[i]), 'index': i})
        return {
            'resistance': [p for p in pivots_high[-5:]],
            'support': [p for p in pivots_low[-5:]],
            'recent_high': float(highs.tail(lookback).max()),
            'recent_low': float(lows.tail(lookback).min()),
        }

indicator_service = IndicatorService()
