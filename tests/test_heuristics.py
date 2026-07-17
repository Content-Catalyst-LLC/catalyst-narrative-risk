from narrative_risk.legacy import score_simple_risk


def test_deprecated_legacy_shim_is_isolated_and_stable():
    result = score_simple_risk([], 0.0, 0.0)
    assert result["score"] == 0
    assert result["level"] == "Low"
