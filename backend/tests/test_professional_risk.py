from app.services.professional_risk import professional_risk


def test_leverage_changes_margin_not_stop_risk_quantity():
    unlevered = professional_risk.calculate_position_size(
        capital=10_000, entry_price=100, stop_loss=95,
        risk_percent=0.02, leverage=1,
    )
    leveraged = professional_risk.calculate_position_size(
        capital=10_000, entry_price=100, stop_loss=95,
        risk_percent=0.02, leverage=5,
    )
    assert unlevered["position_size"] == leveraged["position_size"]
    assert leveraged["margin_required"] == unlevered["position_value"] / 5
    assert leveraged["risk_amount"] == 200


def test_position_notional_is_capped_by_available_leverage():
    result = professional_risk.calculate_position_size(
        capital=1_000, entry_price=100, stop_loss=99.99,
        risk_percent=0.02, leverage=2,
    )
    assert result["position_value"] <= 2_000
