from typing import Literal

SignalDirection = Literal["long", "short", "neutral"]


def normalize_signal_direction(value: object) -> SignalDirection:
    direction = str(value or "").strip().lower()
    if direction in {
        "long", "buy", "bull", "bullish", "strong_long",
        "alış", "aliş", "alis", "yüksəliş", "yukselis",
    }:
        return "long"
    if direction in {
        "short", "sell", "bear", "bearish", "strong_short",
        "satış", "satiş", "satis", "eniş", "enis",
    }:
        return "short"
    return "neutral"
