import json
import re
from pathlib import Path

import pytest

from narrative_risk.service import (
    VERSION,
    NarrativeRiskValidationError,
    build_narrative_risk_record,
    score_narrative_risk,
    validate_narrative_risk_record,
)

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "scoring-parity.json").read_text())


@pytest.mark.parametrize("case", FIXTURES["valid"], ids=lambda case: case["name"])
def test_python_scoring_matches_canonical_fixtures(case):
    assert score_narrative_risk(**case["payload"]) == case["expected"]


@pytest.mark.parametrize("case", FIXTURES["invalid"], ids=lambda case: case["name"])
def test_invalid_payloads_fail_consistently(case):
    with pytest.raises(NarrativeRiskValidationError, match=re.escape(case["message"])):
        build_narrative_risk_record(case["payload"])


def test_zero_weight_values_remain_zero():
    result = score_narrative_risk(
        claim="Zero weights must remain canonical.",
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
    assert result["components"]["source_type"] == 0
    assert result["components"]["evidence_strength"] == 0
    assert result["components"]["review_status"] == 0
    assert result["risk_score"] == 10


def test_record_validates_against_schema():
    record = build_narrative_risk_record({"claim": "Schema-valid record"}, generated_at="2026-07-17T12:00:00+00:00")
    validate_narrative_risk_record(record)
    assert record["method_version"] == VERSION
    assert record["schema_version"] == VERSION
