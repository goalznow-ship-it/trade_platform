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
