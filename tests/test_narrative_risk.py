import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from narrative_risk.contracts import current_method_snapshot, sha256_digest
from narrative_risk.service import (
    CONTRACT_ID,
    METHOD_ID,
    SCHEMA_ID,
    VERSION,
    NarrativeRiskValidationError,
    build_narrative_risk_record,
    reproduce_narrative_risk_record,
    score_narrative_risk,
    validate_narrative_risk_record,
    verify_record_reproducibility,
)

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "scoring-parity.json").read_text())
FIXED = {
    "generated_at": "2026-07-17T12:00:00+00:00",
    "record_id": "urn:uuid:00000000-0000-4000-8000-000000000001",
    "case_id": "urn:uuid:00000000-0000-4000-8000-000000000002",
}


@pytest.mark.parametrize("case", FIXTURES["valid"], ids=lambda case: case["name"])
def test_python_scoring_matches_canonical_fixtures(case):
    assert score_narrative_risk(case["payload"]) == case["expected"]


@pytest.mark.parametrize("case", FIXTURES["invalid"], ids=lambda case: case["name"])
def test_invalid_payloads_fail_consistently(case):
    with pytest.raises(NarrativeRiskValidationError, match=re.escape(case["message"])):
        score_narrative_risk(case["payload"])


def test_zero_weight_values_remain_zero():
    result = score_narrative_risk({
        "claim": "Zero weights must remain canonical.",
        "source_type": "official_or_primary",
        "evidence_strength": "strong",
        "uncertainty": "low",
        "narrative_volatility": "low",
        "stakeholder_pressure": "low",
        "time_sensitivity": "low",
        "consequences": "low",
        "review_status": "reviewed",
        "source_count": 5,
    })
    components = result["calculations"]["components"]
    assert components["source_type"]["weight"] == 0
    assert components["evidence_strength"]["weight"] == 0
    assert components["review_status"]["weight"] == 0
    assert result["calculations"]["risk_score"] == 10


def test_record_has_canonical_layers_and_identifiers():
    record = build_narrative_risk_record({"claim": "Canonical record"}, **FIXED)
    validate_narrative_risk_record(record)
    assert record["contract"] == {"contract_id": CONTRACT_ID, "contract_version": VERSION}
    assert record["identifiers"]["method_id"] == METHOD_ID
    assert record["identifiers"]["schema_id"] == SCHEMA_ID
    assert set(record) >= {
        "normalized_input", "calculations", "interpretation", "human_decision", "method_snapshot"
    }
    assert "risk_score" not in record
    assert "claim" not in record


def test_method_snapshot_is_complete_and_hashed():
    record = build_narrative_risk_record({"claim": "Method snapshot"}, **FIXED)
    method = record["method_snapshot"]
    assert method == current_method_snapshot()
    assert record["method_snapshot_sha256"] == sha256_digest(method)
    assert method["algorithm"]["thresholds"][1] == {"level": "Medium", "minimum": 40, "maximum": 69}
    assert method["components"]["source_type"]["rationale"]
    assert method["components"]["source_type"]["remediation"]


def test_human_decision_is_separate_and_not_inferred_from_score():
    record = build_narrative_risk_record({
        "claim": "High risk does not imply rejection.",
        "source_type": "unknown", "evidence_strength": "weak", "uncertainty": "high",
        "narrative_volatility": "high", "stakeholder_pressure": "high", "time_sensitivity": "high",
        "consequences": "critical", "review_status": "not_reviewed", "source_count": 0,
    }, **FIXED)
    assert record["interpretation"]["risk_level"] == "High"
    assert record["human_decision"] == {
        "status": "draft", "disposition": "undecided", "reviewer_id": None,
        "reviewer_name": None, "reviewed_at": None, "notes": "",
    }


def test_record_reproduces_exactly_from_stored_method_and_schema_identity():
    record = build_narrative_risk_record(
        {"claim": "Reproducible record", "source_count": 4},
        human_decision={
            "status": "reviewed", "disposition": "approved_with_conditions",
            "reviewer_id": "reviewer-1", "reviewer_name": "Reviewer",
            "reviewed_at": "2026-07-17T13:00:00+00:00", "notes": "Retain uncertainty note.",
        },
        **FIXED,
    )
    reproduced = reproduce_narrative_risk_record(record)
    assert reproduced == record
    assert verify_record_reproducibility(record) == {
        "exact_match": True,
        "method_snapshot_hash_match": True,
        "canonical_input_hash_match": True,
        "record_payload_hash_match": True,
        "record_id": FIXED["record_id"],
        "method_id": METHOD_ID,
        "method_version": VERSION,
        "schema_id": SCHEMA_ID,
    }


def test_tampered_method_snapshot_is_detected():
    record = build_narrative_risk_record({"claim": "Tamper test"}, **FIXED)
    tampered = deepcopy(record)
    tampered["method_snapshot"]["weights"]["source_type"]["unknown"] = 99
    with pytest.raises(NarrativeRiskValidationError, match="method_snapshot_sha256"):
        reproduce_narrative_risk_record(tampered)


def test_custom_human_decision_validation():
    with pytest.raises(NarrativeRiskValidationError, match="human_decision.disposition must be one of"):
        build_narrative_risk_record(
            {"claim": "Decision validation"}, human_decision={"disposition": "auto_approved"}, **FIXED
        )
