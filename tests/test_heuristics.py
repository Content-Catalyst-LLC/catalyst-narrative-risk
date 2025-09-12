from narrative_risk.service import score_simple_risk

def test_zero_total_low():
    m = score_simple_risk([], 0.0, 0.0)
    assert m["score"] == 0 and m["level"] == "Low"
