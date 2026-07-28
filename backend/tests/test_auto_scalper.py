from app.api.v1.auto_scalper import AutoScalperConfig
from app.services.auto_scalper import AutoScalperService


def test_liquid_tight_spread_market_scores_above_illiquid_market():
    liquid = {
        "bid": 100.0, "ask": 100.01, "last": 100.005,
        "quoteVolume": 500_000_000, "percentage": 3.0,
    }
    illiquid = {
        "bid": 100.0, "ask": 100.5, "last": 100.25,
        "quoteVolume": 10_000, "percentage": 20.0,
    }
    assert AutoScalperService._pre_score(liquid) > 60
    assert AutoScalperService._pre_score(illiquid) == 0


def test_safe_default_config_is_paper_and_single_position():
    config = AutoScalperConfig()
    assert config.mode == "paper"
    assert config.max_positions == 1
    assert config.max_leverage == 3
    assert config.risk_per_trade_pct <= 0.5


def test_position_size_is_capped_by_allocated_capital_and_leverage():
    quantity = AutoScalperService._position_size(
        {"entry": 100, "stop_loss": 99},
        {
            "capital_usdt": 10,
            "risk_per_trade_pct": 0.5,
            "max_leverage": 3,
        },
    )
    assert quantity == 0.05
    assert quantity * 100 <= 30


def test_live_mode_requires_explicit_model_value():
    config = AutoScalperConfig(
        mode="live",
        live_confirmation="REAL PULLA AUTO TRADE",
    )
    assert config.mode == "live"
