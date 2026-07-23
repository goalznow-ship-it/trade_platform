import pytest

from app.services.institutional_scoring import InstitutionalScorer


@pytest.mark.asyncio
async def test_score_uses_full_100_point_scale(monkeypatch):
    scorer = InstitutionalScorer()
    category_points = {
        "trend": 20,
        "momentum": 15,
        "volume": 15,
        "liquidity": 15,
        "smc": 20,
        "risk": 15,
    }
    for category, points in category_points.items():
        monkeypatch.setattr(
            scorer,
            f"_score_{category}",
            lambda *args, _points=points, **kwargs: _points,
        )
    monkeypatch.setattr(scorer, "_build_details", lambda *args: {})

    result = await scorer.score(
        "BTC/USDT",
        [{"close": 1, "high": 1, "low": 1, "volume": 1}] * 50,
    )

    assert result["total_score"] == 100
    assert result["abs_score"] == 100
    assert result["classification"] == "institutional_grade"
    assert result["direction"] == "long"
    assert result["long_probability"] == 100
