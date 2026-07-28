from app.services.canonical_signal import CanonicalSignalEngine
from app.services.skhy_market_data import ccxt_symbol, normalize_symbol
from app.services.signal_direction import normalize_signal_direction


def test_symbol_normalization_for_top_30_terminal():
    assert normalize_symbol("BTC/USDT") == "BTCUSDT"
    assert normalize_symbol("BTC/USDT:USDT") == "BTCUSDT"
    assert normalize_symbol("skhy") == "SKHYUSDT"
    assert ccxt_symbol("1000PEPEUSDT") == "1000PEPE/USDT:USDT"


def test_canonical_signal_normalizes_buy_and_sell():
    engine = CanonicalSignalEngine()
    long_signal = engine.build("BTCUSDT", signal_data={"direction": "BUY", "confidence": 80})
    short_signal = engine.build("BTCUSDT", signal_data={"direction": "SELL", "confidence": 80})
    assert long_signal["direction"] == "long"
    assert long_signal["long_score"] > long_signal["short_score"]
    assert short_signal["direction"] == "short"
    assert short_signal["short_score"] > short_signal["long_score"]


def test_neutral_signal_is_not_mislabeled_short():
    signal = CanonicalSignalEngine().build(
        "BTCUSDT",
        signal_data={"direction": "WAIT", "confidence": 90},
    )
    assert signal["direction"] == "neutral"
    assert signal["long_score"] == 50
    assert signal["short_score"] == 50


def test_direction_aliases_and_unknown_values():
    assert normalize_signal_direction("BUY") == "long"
    assert normalize_signal_direction("SATIŞ") == "short"
    assert normalize_signal_direction("WAIT") == "neutral"
    assert normalize_signal_direction(None) == "neutral"
