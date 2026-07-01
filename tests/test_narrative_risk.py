from narrative_risk.service import build_narrative_risk_record, score_narrative_risk, score_simple_risk


def test_high_risk_claim_scores_high():
    result = score_narrative_risk(
        claim="Major unsupported claim",
        source_type="unknown",
        evidence_strength="weak",
        uncertainty="high",
        narrative_volatility="high",
        stakeholder_pressure="high",
        time_sensitivity="high",
        consequences="critical",
        review_status="not_reviewed",
        source_count=0,
    )
    assert result["risk_level"] == "High"
    assert result["risk_score"] >= 70
    assert result["flags"]


def test_lower_risk_claim_scores_low():
    result = score_narrative_risk(
        claim="Narrow claim with strong support",
        source_type="official_or_primary",
        evidence_strength="strong",
        uncertainty="low",
        narrative_volatility="low",
        stakeholder_pressure="low",
        time_sensitivity="low",
        consequences="low",
        review_status="reviewed",
        source_count=5,
    )
    assert result["risk_level"] == "Low"
    assert result["risk_score"] < 40


def test_record_has_required_fields():
    record = build_narrative_risk_record({"claim": "Test claim"})
    assert record["record_type"] == "catalyst_narrative_risk_record"
    assert "generated_at" in record
    assert "decision_note" in record


def test_legacy_simple_risk_zero_total():
    m = score_simple_risk([], 0.0, 0.0)
    assert m["score"] == 0 and m["level"] == "Low"
