"""
Elliott Wave Analysis Engine
- Automatic wave counting (impulse 1-5, corrective A-B-C)
- Next wave projection with targets
- Fibonacci relationships between waves
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


class ElliottWaveEngine:
    def analyze(self, data: list) -> dict:
        if len(data) < 100:
            return {"count": "unknown", "current_phase": "neutral", "next_wave": None, "waves": []}
        closes = np.array([d["close"] for d in data])
        highs = np.array([d["high"] for d in data])
        lows = np.array([d["low"] for d in data])

        def find_swings(values, window=5):
            peaks, troughs = [], []
            for i in range(window, len(values) - window):
                if values[i] == max(values[i - window:i + window + 1]):
                    peaks.append({"index": i, "price": float(values[i])})
                if values[i] == min(values[i - window:i + window + 1]):
                    troughs.append({"index": i, "price": float(values[i])})
            return peaks, troughs

        peaks, troughs = find_swings(closes, 7)

        def is_impulse(waves_list):
            if len(waves_list) < 5:
                return False, []
            for i in range(len(waves_list) - 4):
                w = waves_list[i:i + 5]
                if len(w) < 5:
                    continue
                types = [x.get("type") for x in w]
                prices = [x.get("price", 0) for x in w]
                if types == ["up", "up", "up", "up", "up"]:
                    if prices[1] > prices[0] and prices[2] > prices[1] and prices[3] > prices[2] and prices[4] > prices[3]:
                        return True, w
                if types == ["down", "down", "down", "down", "down"]:
                    if prices[1] < prices[0] and prices[2] < prices[1] and prices[3] < prices[2] and prices[4] < prices[3]:
                        return True, w
            return False, []

        def is_corrective(waves_list):
            if len(waves_list) < 3:
                return False, []
            for i in range(len(waves_list) - 2):
                w = waves_list[i:i + 3]
                types = [x.get("type") for x in w]
                prices = [x.get("price", 0) for x in w]
                if types == ["down", "up", "down"]:
                    if prices[1] < prices[0] and prices[2] < prices[0]:
                        return True, w
                if types == ["up", "down", "up"]:
                    if prices[1] > prices[0] and prices[2] > prices[0]:
                        return True, w
            return False, []

        combined = []
        pi, ti = 0, 0
        last_price = closes[0]
        while pi < len(peaks) and ti < len(troughs):
            if peaks[pi]["index"] < troughs[ti]["index"]:
                combined.append({"type": "up" if peaks[pi]["price"] > last_price else "down", "price": peaks[pi]["price"], "index": peaks[pi]["index"], "label": None})
                last_price = peaks[pi]["price"]
                pi += 1
            else:
                combined.append({"type": "up" if troughs[ti]["price"] > last_price else "down", "price": troughs[ti]["price"], "index": troughs[ti]["index"], "label": None})
                last_price = troughs[ti]["price"]
                ti += 1
        while pi < len(peaks):
            combined.append({"type": "up" if peaks[pi]["price"] > last_price else "down", "price": peaks[pi]["price"], "index": peaks[pi]["index"], "label": None})
            last_price = peaks[pi]["price"]
            pi += 1
        while ti < len(troughs):
            combined.append({"type": "up" if troughs[ti]["price"] > last_price else "down", "price": troughs[ti]["price"], "index": troughs[ti]["index"], "label": None})
            last_price = troughs[ti]["price"]
            ti += 1

        if not combined:
            return {"count": "unknown", "current_phase": "neutral", "next_wave": None, "waves": []}

        best_model = "unknown"
        wave_labels = []
        impulse_found, impulse_waves = is_impulse(combined)
        corrective_found, corrective_waves = is_corrective(combined)

        ew_count = 0
        fib_targets = {}
        next_wave = None

        if impulse_found:
            best_model = "impulse"
            for i, w in enumerate(impulse_waves):
                label = f"{i + 1}" if i < 5 else None
                if label:
                    w["label"] = label
                    wave_labels.append({"wave": label, "type": w["type"], "price": w["price"], "index": w["index"]})
                    ew_count = i + 1
            w1 = impulse_waves[0]["price"]
            w3 = impulse_waves[2]["price"]
            w5 = impulse_waves[4]["price"]
            w2 = impulse_waves[1]["price"]
            w4 = impulse_waves[3]["price"]

            is_up_trend = impulse_waves[0]["type"] == "up"
            total_move = abs(w5 - w1)
            fib_targets = {
                "wave_3_target": round(w1 + 1.618 * abs(w2 - w1) if is_up_trend else w1 - 1.618 * abs(w2 - w1), 4),
                "wave_5_target": round(w3 + 0.382 * abs(w4 - w3) if is_up_trend else w3 - 0.382 * abs(w4 - w3), 4),
                "extension_1.272": round(w5 + 0.272 * total_move if is_up_trend else w5 - 0.272 * total_move, 4),
                "extension_1.618": round(w5 + 0.618 * total_move if is_up_trend else w5 - 0.618 * total_move, 4),
            }
            next_wave = {
                "label": "A",
                "type": "corrective",
                "direction": "down" if is_up_trend else "up",
                "estimated_target": fib_targets.get("wave_5_target", w5),
            }
            ew_count = 5

        elif corrective_found:
            best_model = "corrective"
            for i, w in enumerate(corrective_waves):
                label = chr(65 + i)
                w["label"] = label
                wave_labels.append({"wave": label, "type": w["type"], "price": w["price"], "index": w["index"]})
                ew_count = i + 1

            is_flat = abs(corrective_waves[0]["price"] - corrective_waves[2]["price"]) / max(corrective_waves[0]["price"], corrective_waves[2]["price"]) < 0.02
            move = abs(corrective_waves[2]["price"] - corrective_waves[1]["price"])
            next_wave = {
                "label": "1" if not wave_labels else str(int(wave_labels[-1]["wave"]) + 1 if wave_labels[-1]["wave"].isdigit() else "1"),
                "type": "impulse",
                "direction": "up" if corrective_waves[-1]["type"] == "down" else "down",
                "estimated_target": round(corrective_waves[-1]["price"] + move * 0.618 if corrective_waves[-1]["type"] == "down" else corrective_waves[-1]["price"] - move * 0.618, 4),
            }
            ew_count = 3
        else:
            recent = combined[-6:]
            if len(recent) >= 3:
                wave_labels = [{"wave": str(i + 1), "type": w["type"], "price": w["price"], "index": w["index"]} for i, w in enumerate(recent)]
                ew_count = len(recent)
                if ew_count <= 3:
                    best_model = "forming_impulse" if recent[0]["type"] == "up" else "forming_corrective"
                else:
                    best_model = "extended"

        current_price = float(closes[-1])
        recent_trend = "up" if closes[-10] < closes[-1] else "down" if closes[-10] > closes[-1] else "neutral"
        ratio_change = abs(closes[-1] - closes[-10]) / closes[-10] * 100 if closes[-10] > 0 else 0
        momentum = "strong" if ratio_change > 5 else "moderate" if ratio_change > 2 else "weak"

        return _convert({
            "count": best_model,
            "current_phase": recent_trend,
            "momentum": momentum,
            "next_wave": next_wave,
            "wave_count": ew_count,
            "waves": wave_labels,
            "fib_targets": fib_targets if fib_targets else None,
            "current_wave": wave_labels[-1] if wave_labels else None,
            "estimated_completion": f"Wave {ew_count} of {best_model}" if ew_count else "analyzing",
        })


elliott_wave = ElliottWaveEngine()
