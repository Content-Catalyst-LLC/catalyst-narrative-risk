import json
from copy import deepcopy
from pathlib import Path

import pytest

from narrative_risk.contracts import current_method_snapshot, sha256_digest
from narrative_risk.errors import NarrativeRiskValidationError
from narrative_risk.ledger import harvard_citation, stable_ledger_id
from narrative_risk.service import build_narrative_risk_record, score_narrative_risk, verify_record_reproducibility

SAMPLE = json.loads((Path(__file__).resolve().parents[1] / "data" / "sample_narrative_risk_input.json").read_text())


def analyze(payload=None):
    return score_narrative_risk(deepcopy(SAMPLE if payload is None else payload))


def test_claim_only_payload_creates_deterministic_primary_claim_and_empty_ledger():
    first = analyze({"claim": "A claim with no item-level evidence."})
    second = analyze({"claim": "A claim with no item-level evidence."})
    ledger = first["evidence_ledger"]
    assert ledger["claims"] == second["evidence_ledger"]["claims"]
    assert ledger["claims"][0]["role"] == "primary"
    assert ledger["claims"][0]["claim_id"].startswith("urn:catalyst:narrative-risk:claim:sha256:")
    assert ledger["coverage"]["overall"]["coverage_status"] == "none"
    assert ledger["derived_scoring_inputs"]["ledger_applied"] is False


def test_sample_ledger_derives_scalar_scoring_inputs_and_substantial_primary_coverage():
    result = analyze()
    ledger = result["evidence_ledger"]
    assert result["normalized_input"]["source_type"] == "official_or_primary"
    assert result["normalized_input"]["evidence_strength"] == "strong"
    assert result["normalized_input"]["source_count"] == 2
    primary = next(item for item in ledger["coverage"]["per_claim"] if item["claim_id"] == ledger["primary_claim_id"])
    assert primary["coverage_status"] == "substantial"
    assert primary["independent_source_count"] == 2
    assert ledger["coverage"]["overall"]["coverage_status"] == "partial"


def test_manual_source_fields_may_match_but_may_not_conflict_with_ledger_derivation():
    matching = deepcopy(SAMPLE)
    matching.update({"source_type": "official_or_primary", "evidence_strength": "strong", "source_count": 2})
    assert analyze(matching)["normalized_input"]["source_count"] == 2
    for field, value in (("source_type", "unknown"), ("evidence_strength", "weak"), ("source_count", 9)):
        conflicting = deepcopy(SAMPLE)
        conflicting[field] = value
        with pytest.raises(NarrativeRiskValidationError, match=f"{field} conflicts with the value derived"):
            analyze(conflicting)


def test_single_independence_group_downgrades_strong_evidence_to_moderate():
    payload = deepcopy(SAMPLE)
    payload["sources"][1]["independence_group"] = payload["sources"][0]["independence_group"]
    result = analyze(payload)
    assert result["evidence_ledger"]["derived_scoring_inputs"]["evidence_strength"] == "moderate"
    assert any("not independent" in flag.lower() or "dependent" in flag.lower() for flag in result["interpretation"]["flags"])


def test_contradiction_downgrades_strength_and_marks_claim_contested():
    payload = deepcopy(SAMPLE)
    payload["relationships"][1]["relation_type"] = "contradict"
    payload["relationships"][1]["strength"] = "moderate"
    result = analyze(payload)
    ledger = result["evidence_ledger"]
    primary = next(item for item in ledger["coverage"]["per_claim"] if item["claim_id"] == ledger["primary_claim_id"])
    assert ledger["derived_scoring_inputs"]["evidence_strength"] == "limited"
    assert primary["coverage_status"] == "contested"
    assert primary["contested"] is True
    assert ledger["coverage"]["overall"]["contested_claim_count"] == 1


def test_duplicate_source_inherits_original_independence_group_and_is_counted():
    payload = deepcopy(SAMPLE)
    payload["sources"][1]["duplicate_of_source_id"] = payload["sources"][0]["source_id"]
    payload["sources"][1].pop("independence_group")
    result = analyze(payload)
    ledger = result["evidence_ledger"]
    assert ledger["sources"][1]["independence_group"] == ledger["sources"][0]["independence_group"]
    assert ledger["coverage"]["overall"]["duplicate_source_count"] == 1
    assert ledger["derived_scoring_inputs"]["source_count"] == 2
    assert ledger["derived_scoring_inputs"]["evidence_strength"] == "moderate"


def test_stale_sources_and_indirect_only_sources_create_review_guidance():
    payload = deepcopy(SAMPLE)
    for source in payload["sources"]:
        source["freshness"] = "stale"
        source["directness"] = "indirect"
    interpretation = analyze(payload)["interpretation"]
    joined_flags = " ".join(interpretation["flags"]).lower()
    joined_actions = " ".join(interpretation["review_actions"]).lower()
    assert "stale" in joined_flags
    assert "indirect" in joined_flags
    assert "refresh" in joined_actions
    assert "direct" in joined_actions


def test_no_primary_relationships_retains_scalar_inputs_and_requests_relationships():
    payload = deepcopy(SAMPLE)
    supporting_id = payload["claims"][1]["claim_id"]
    payload["relationships"] = [
        {**relationship, "claim_id": supporting_id}
        for relationship in payload["relationships"][:1]
    ]
    payload.update({"source_type": "reputable_secondary", "evidence_strength": "moderate", "source_count": 2})
    result = analyze(payload)
    assert result["evidence_ledger"]["derived_scoring_inputs"]["ledger_applied"] is False
    assert result["normalized_input"]["source_type"] == "reputable_secondary"
    assert any("link each material claim" in action.lower() for action in result["interpretation"]["review_actions"])


def test_supporting_claim_without_positive_relationship_is_counted_as_unsupported():
    payload = deepcopy(SAMPLE)
    supporting_id = payload["claims"][1]["claim_id"]
    payload["relationships"] = [r for r in payload["relationships"] if r["claim_id"] != supporting_id]
    ledger = analyze(payload)["evidence_ledger"]
    assert ledger["coverage"]["overall"]["unsupported_claim_count"] == 1
    coverage = next(item for item in ledger["coverage"]["per_claim"] if item["claim_id"] == supporting_id)
    assert coverage["coverage_status"] == "none"


def test_excerpt_hash_and_complete_ledger_hash_are_deterministic():
    first = analyze()["evidence_ledger"]
    second = analyze()["evidence_ledger"]
    assert first["evidence_items"][0]["excerpt_sha256"] == sha256_digest(SAMPLE["evidence_items"][0]["excerpt"])
    assert sha256_digest(first) == sha256_digest(second)


def test_stable_ledger_ids_change_with_canonical_material():
    first = stable_ledger_id("claim", {"text": "A", "role": "primary"})
    second = stable_ledger_id("claim", {"role": "primary", "text": "A"})
    changed = stable_ledger_id("claim", {"text": "B", "role": "primary"})
    assert first == second
    assert first != changed
    with pytest.raises(NarrativeRiskValidationError, match="unsupported ledger identifier kind"):
        stable_ledger_id("case", {"text": "A"})


def test_harvard_citation_supports_authors_dates_urls_and_missing_metadata():
    source = analyze()["evidence_ledger"]["sources"][0]
    citation = harvard_citation(source)
    assert citation.startswith("Energy Audit Team (2026) Pilot meter audit.")
    assert "Available at:" in citation and "Accessed: 2026-07-17" in citation
    sparse = deepcopy(source)
    sparse.update({"creators": [], "published_year": None, "publisher": "", "url": None, "accessed_at": None})
    assert harvard_citation(sparse) == "Unknown author (n.d.) Pilot meter audit."


def test_record_reproduction_includes_exact_evidence_ledger_hash():
    record = build_narrative_risk_record(
        deepcopy(SAMPLE),
        generated_at="2026-07-17T12:00:00+00:00",
        record_id="urn:uuid:00000000-0000-4000-8000-000000000101",
        case_id="urn:uuid:00000000-0000-4000-8000-000000000102",
    )
    report = verify_record_reproducibility(record)
    assert report["exact_match"] is True
    assert report["evidence_ledger_hash_match"] is True
    assert record["reproducibility"]["evidence_ledger_sha256"] == sha256_digest(record["evidence_ledger"])


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda p: p["claims"].append({**p["claims"][0], "claim_id": p["claims"][1]["claim_id"]}), "duplicate claim_id"),
        (lambda p: p["claims"].append({**p["claims"][1], "claim_id": "urn:catalyst:narrative-risk:claim:sha256:" + "3" * 64, "role": "primary"}), "exactly one primary claim"),
        (lambda p: p["evidence_items"][0].update(source_id="urn:catalyst:narrative-risk:source:sha256:" + "f" * 64), "does not reference a normalized source"),
        (lambda p: p["relationships"][0].update(claim_id="urn:catalyst:narrative-risk:claim:sha256:" + "f" * 64), "does not reference a normalized claim"),
        (lambda p: p["relationships"][0].update(evidence_id="urn:catalyst:narrative-risk:evidence:sha256:" + "f" * 64), "does not reference normalized evidence"),
        (lambda p: p["sources"][0].update(url="not-a-url"), "absolute http or https URL"),
        (lambda p: p["sources"][0]["provenance"].update(content_sha256="ABC"), "lowercase SHA-256 digest"),
    ],
)
def test_invalid_ledger_structures_are_rejected(mutation, message):
    payload = deepcopy(SAMPLE)
    mutation(payload)
    with pytest.raises(NarrativeRiskValidationError, match=message):
        analyze(payload)


def test_method_ledger_policy_is_embedded_in_every_record():
    record = build_narrative_risk_record({"claim": "Method policy is embedded."})
    assert record["method_snapshot"] == current_method_snapshot()
    assert record["method_snapshot"]["ledger_policy"]["positive_relation_types"] == ["support", "qualify"]
