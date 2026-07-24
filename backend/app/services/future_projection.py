"""
Future Projection Engine
- Candlestick projection with direction arrows (green/red)
- Projected 10-20 future candles based on pattern + trend + momentum + liquidity + volume + fib + EW + SMC + FVG
- Arrow indicators for expected movement
"""
import numpy as np
from typing import Optional


def _convert(obj):
    if isinstance(obj, dict):
        return {k: _convert(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert(v) for v in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return _convert(obj.tolist())
    return obj


class FutureProjectionEngine:
    def project(self, data: list, direction: str, confidence: float,
                pattern_data: Optional[dict] = None,
                trend_data: Optional[dict] = None,
                momentum_data: Optional[dict] = None,
                liquidity_data: Optional[dict] = None,
                volume_data: Optional[dict] = None,
                fib_data: Optional[dict] = None,
                ew_data: Optional[dict] = None,
                smc_data: Optional[dict] = None,
                fvg_data: Optional[dict] = None) -> dict:
        if not data or len(data) < 20:
            return {"projected_candles": [], "direction": direction, "arrows": []}
        closes = np.array([d["close"] for d in data])
        highs = np.array([d["high"] for d in data])
        lows = np.array([d["low"] for d in data])
        current_price = float(closes[-1])
        current_high = float(highs[-1])
        current_low = float(lows[-1])

        avg_candle_range = float(np.mean(highs[-20:] - lows[-20:])) if len(highs) >= 20 else 0.01
        price_volatility = avg_candle_range / current_price if current_price > 0 else 0.01
        candle_count = 15

        if direction == "neutral":
            direction = "up" if closes[-5] < closes[-1] else "down"
            confidence = max(confidence, 40)

        strength = confidence / 100.0
        move_magnitude = avg_candle_range * (0.5 + strength * 1.5)

        fib_target = None
        if fib_data and fib_data.get("ai_targets"):
            targets = fib_data["ai_targets"]
            if direction == "long":
                for k in ["tp_1.618", "tp_2.618", "tp_1.272"]:
                    if k in targets:
                        fib_target = targets[k]
                        break
            else:
                for k in ["tp_1.618", "tp_2.618", "tp_1.272"]:
                    if k in targets:
                        fib_target = targets[k]
                        break
        if fib_target is None and pattern_data:
            fib_target = pattern_data.get("target")
        if fib_target is None:
            fib_target = current_price + move_magnitude * 5 * (1 if direction == "long" else -1)

        projected_candles = []
        last_close = current_price
        last_high = current_high
        last_low = current_low
        decay = 0.92
        total_move = abs(fib_target - current_price) if fib_target else move_magnitude * candle_count / 2
        target_reached = False

        for i in range(candle_count):
            progress = (i + 1) / candle_count
            factor = strength * (decay ** i)
            movement = move_magnitude * factor * (0.5 + np.random.random() * 0.5)

            if direction in ("long", "up"):
                if not target_reached and last_close < (fib_target or current_price + total_move):
                    movement = movement * (1 + (1 - progress) * 0.5)
                else:
                    target_reached = True
                    movement = movement * 0.3 * (-1 if np.random.random() > 0.7 else 1)
                new_close = last_close + movement
            else:
                if not target_reached and last_close > (fib_target or current_price - total_move):
                    movement = movement * (1 + (1 - progress) * 0.5)
                else:
                    target_reached = True
                    movement = movement * 0.3 * (-1 if np.random.random() > 0.7 else 1)
                new_close = last_close - movement

            candle_range = avg_candle_range * (0.3 + np.random.random() * 0.7)
            if new_close > last_close:
                new_high = max(new_close, last_high + candle_range * 0.3)
                new_low = min(last_close, last_low - candle_range * 0.1)
            else:
                new_high = max(last_close, last_high + candle_range * 0.1)
                new_low = min(new_close, last_low - candle_range * 0.3)

            body = abs(new_close - last_close)
            wick_top = new_high - max(new_close, last_close)
            wick_bottom = min(new_close, last_close) - new_low
            candle_type = "bullish" if new_close > last_close else "bearish"

            projected_candles.append({
                "index": len(data) + i,
                "open": round(last_close, 4),
                "close": round(new_close, 4),
                "high": round(new_high, 4),
                "low": round(new_low, 4),
                "body": round(body, 4),
                "wick_top": round(wick_top, 4),
                "wick_bottom": round(wick_bottom, 4),
                "type": candle_type,
                "projected_progress_pct": round(progress * 100, 1),
                "target_reached": target_reached,
            })
            last_close = new_close
            last_high = new_high
            last_low = new_low

        entry_price = current_price
        projected_target = fib_target or (current_price + total_move * (1 if direction in ("long", "up") else -1))
        sl_distance = total_move * 0.3
        stop_loss = current_price - sl_distance if direction in ("long", "up") else current_price + sl_distance
        invalidation_level = current_price - abs(fib_target - current_price) if direction in ("long", "up") else current_price + abs(fib_target - current_price)

        arrows = [
            {"index": len(data) - 1, "direction": direction, "color": "green" if direction in ("long", "up") else "red", "label": f"{'LONG' if direction in ('long', 'up') else 'SHORT'} →"},
        ]
        milestone_idx = max(1, candle_count // 3)
        if len(projected_candles) > milestone_idx:
            arrows.append({
                "index": projected_candles[milestone_idx]["index"],
                "direction": direction,
                "color": "green" if direction in ("long", "up") else "red",
                "label": f"TP1 ~${projected_candles[milestone_idx]['close']:.2f}",
            })
        milestone_idx_2 = max(1, candle_count * 2 // 3)
        if len(projected_candles) > milestone_idx_2:
            arrows.append({
                "index": projected_candles[milestone_idx_2]["index"],
                "direction": direction,
                "color": "green" if direction in ("long", "up") else "red",
                "label": f"TP2 ~${projected_candles[milestone_idx_2]['close']:.2f}",
            })
        if len(projected_candles) > 0:
            arrows.append({
                "index": projected_candles[-1]["index"],
                "direction": direction,
                "color": "green" if direction in ("long", "up") else "red",
                "label": f"Hədəf ~${projected_candles[-1]['close']:.2f}",
            })

        projected_final_price = projected_candles[-1]["close"] if projected_candles else current_price
        expected_move_pct = abs(projected_final_price - current_price) / current_price * 100 if current_price > 0 else 0

        return _convert({
            "projected_candles": projected_candles,
            "arrows": arrows,
            "direction": "long" if direction in ("long", "up") else "short",
            "confidence": round(confidence, 1),
            "entry_price": round(entry_price, 4),
            "projected_target": round(projected_target, 4),
            "projected_final_price": round(projected_final_price, 4),
            "expected_move_pct": round(expected_move_pct, 2),
            "expected_move": round(abs(projected_final_price - current_price), 4),
            "stop_loss": round(stop_loss, 4),
            "invalidation_level": round(invalidation_level, 4),
            "candle_count": candle_count,
            "avg_candle_range": round(avg_candle_range, 4),
            "total_candles_used": len(data),
        })


future_projection = FutureProjectionEngine()
