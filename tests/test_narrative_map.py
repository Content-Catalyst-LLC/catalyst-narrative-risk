import json
from copy import deepcopy
from pathlib import Path

import pytest

from narrative_risk.errors import NarrativeRiskValidationError
from narrative_risk.narrative_map import build_narrative_map, stable_map_id
from narrative_risk.service import build_narrative_risk_record, score_narrative_risk, verify_record_reproducibility

DATA = Path(__file__).resolve().parents[1] / "data" / "sample_narrative_risk_input.json"


def test_default_map_is_created_from_evidence_ledger_claims():
    analysis = score_narrative_risk({"claim": "A bounded factual statement."})
    narrative_map = analysis["narrative_map"]
    assert narrative_map["map_version"] == "1.7.0"
    assert len(narrative_map["nodes"]) == 1
    assert narrative_map["nodes"][0]["claim_id"] == analysis["evidence_ledger"]["primary_claim_id"]
    assert narrative_map["analysis"]["summary"]["map_status"] == "complete"


def test_sample_map_exposes_decomposition_and_wording_comparison():
    payload = json.loads(DATA.read_text())
    narrative_map = score_narrative_risk(payload)["narrative_map"]
    assert narrative_map["analysis"]["summary"]["node_count"] == 3
    assert narrative_map["analysis"]["summary"]["link_count"] == 2
    assert narrative_map["wording_comparisons"][0]["risk_direction"] == "higher"
    assert "always" in narrative_map["wording_comparisons"][0]["added_terms"]


def test_causal_language_without_causal_link_is_high_severity():
    result = score_narrative_risk({"claim": "The indicator proves the program caused the outcome.", "uncertainty": "high", "evidence_strength": "limited"})
    codes = {item["code"] for item in result["narrative_map"]["analysis"]["issues"]}
    assert "unsupported_causal_structure" in codes
    assert "confidence_evidence_mismatch" in codes
    assert result["narrative_map"]["analysis"]["summary"]["map_status"] == "needs_review"


def test_prediction_requires_time_scope_or_predictive_structure():
    payload = {
        "claim": "Demand will rise.",
        "claims": [{"text": "Demand will rise.", "claim_type": "predictive", "role": "primary"}],
    }
    issues = score_narrative_risk(payload)["narrative_map"]["analysis"]["issues"]
    assert any(item["code"] == "unbounded_prediction" for item in issues)


def test_quantity_without_baseline_is_detected():
    base = score_narrative_risk({"claim": "Use fell 10 percent."})
    claim_id = base["evidence_ledger"]["primary_claim_id"]
    payload = {
        "claim": "Use fell 10 percent.",
        "narrative_nodes": [{
            "text": "Use fell 10 percent.", "node_type": "factual_claim", "role": "primary",
            "claim_id": claim_id, "quantities": [{"value": 10, "unit": "percent"}],
        }],
    }
    issues = score_narrative_risk(payload)["narrative_map"]["analysis"]["issues"]
    assert any(item["code"] == "quantity_without_baseline" for item in issues)


def test_dependency_cycle_is_reported():
    seed = score_narrative_risk({"claim": "Primary claim."})
    claim_id = seed["evidence_ledger"]["primary_claim_id"]
    nodes = [
        {"node_id": "urn:catalyst:narrative-risk:node:sha256:" + "a" * 64, "text": "Primary claim.", "node_type": "factual_claim", "role": "primary", "claim_id": claim_id},
        {"node_id": "urn:catalyst:narrative-risk:node:sha256:" + "b" * 64, "text": "Assumption A.", "node_type": "assumption", "role": "supporting"},
    ]
    links = [
        {"from_node_id": nodes[0]["node_id"], "to_node_id": nodes[1]["node_id"], "relation_type": "depends_on"},
        {"from_node_id": nodes[1]["node_id"], "to_node_id": nodes[0]["node_id"], "relation_type": "depends_on"},
    ]
    result = score_narrative_risk({"claim": "Primary claim.", "narrative_nodes": nodes, "narrative_links": links})
    assert any(item["code"] == "dependency_cycle" for item in result["narrative_map"]["analysis"]["issues"])


def test_invalid_node_claim_reference_is_rejected():
    with pytest.raises(NarrativeRiskValidationError, match="claim_id does not reference"):
        score_narrative_risk({
            "claim": "Claim.",
            "narrative_nodes": [{"text": "Claim.", "role": "primary", "claim_id": "urn:catalyst:narrative-risk:claim:sha256:" + "f" * 64}],
        })


def test_invalid_link_reference_is_rejected():
    with pytest.raises(NarrativeRiskValidationError, match="from_node_id does not reference"):
        score_narrative_risk({
            "claim": "Claim.",
            "narrative_links": [{
                "from_node_id": "urn:catalyst:narrative-risk:node:sha256:" + "a" * 64,
                "to_node_id": "urn:catalyst:narrative-risk:node:sha256:" + "b" * 64,
                "relation_type": "supports",
            }],
        })


def test_multiple_primary_nodes_are_rejected():
    with pytest.raises(NarrativeRiskValidationError, match="exactly one primary node"):
        score_narrative_risk({
            "claim": "Claim.",
            "narrative_nodes": [
                {"text": "Claim.", "role": "primary"},
                {"text": "Second.", "role": "primary"},
            ],
        })


def test_selected_variant_must_exist():
    with pytest.raises(NarrativeRiskValidationError, match="selected_variant_id"):
        score_narrative_risk({
            "claim": "Claim.",
            "wording_variants": [{"text": "Claim.", "status": "current"}],
            "selected_variant_id": "urn:catalyst:narrative-risk:variant:sha256:" + "f" * 64,
        })


def test_stable_map_identifier_is_deterministic():
    material = {"text": "Claim", "role": "primary"}
    assert stable_map_id("node", material) == stable_map_id("node", deepcopy(material))
    assert stable_map_id("node", material).startswith("urn:catalyst:narrative-risk:node:sha256:")


def test_record_includes_narrative_map_integrity_layer():
    record = build_narrative_risk_record({"claim": "Integrity map."})
    report = verify_record_reproducibility(record)
    assert report["narrative_map_hash_match"] is True
    assert record["reproducibility"]["narrative_map_sha256"]


def test_tampered_narrative_map_is_detected_by_payload_hash():
    record = build_narrative_risk_record({"claim": "Tamper map."})
    tampered = deepcopy(record)
    tampered["narrative_map"]["nodes"][0]["text"] = "Changed wording."
    report = verify_record_reproducibility(tampered)
    assert report["narrative_map_hash_match"] is False
    assert report["record_payload_hash_match"] is False
