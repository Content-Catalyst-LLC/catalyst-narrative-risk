import json
from copy import deepcopy
from pathlib import Path

import pytest

from app import create_app
from narrative_risk.comparisons import (
    build_comparative_portfolio,
    build_decision_studio_handoff,
    build_evidence_matrix,
    evaluate_scenario,
    normalize_comparison_set,
    normalize_scenario,
    run_sensitivity_analysis,
)
from narrative_risk.contracts import sha256_digest
from narrative_risk.errors import NarrativeRiskValidationError
from narrative_risk.workspaces import SQLiteCaseRepository

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "urn:uuid:80000000-0000-4000-8000-000000000001"


def sample_payload():
    return json.loads((ROOT / "data" / "sample_narrative_risk_input.json").read_text())


def build_workspace(tmp_path):
    repository = SQLiteCaseRepository(tmp_path / "comparisons.sqlite3")
    repository.create_case(
        case_id=CASE_ID,
        title="Comparative energy narrative",
        initial_payload=sample_payload(),
        created_at="2026-07-17T12:00:00+00:00",
    )
    second_payload = deepcopy(sample_payload())
    second_payload["claim"] = "The pilot may have reduced energy use, but attribution remains uncertain."
    second_payload["uncertainty"] = "high"
    second_payload["narrative_volatility"] = "high"
    second_payload["narrative_nodes"][0]["text"] = second_payload["claim"]
    second_payload["claims"][0]["text"] = second_payload["claim"]
    repository.add_revision(
        CASE_ID,
        payload=second_payload,
        created_at="2026-07-17T13:00:00+00:00",
        change_note="Alternative qualified frame",
    )
    revisions = repository.list_revisions(CASE_ID)
    comparison = repository.create_comparison_set(CASE_ID, {
        "title": "Measured reduction versus qualified attribution",
        "description": "Compare the audited result with a more cautious causal frame.",
        "status": "active",
        "comparison_mode": "revision",
        "members": [
            {"label": "Audited result", "revision_id": revisions[0]["revision_id"], "record_id": revisions[0]["record_id"], "frame": "Measured performance", "assumptions": ["Weather normalization is valid"]},
            {"label": "Qualified attribution", "revision_id": revisions[1]["revision_id"], "record_id": revisions[1]["record_id"], "frame": "Attribution uncertainty", "assumptions": ["Unobserved factors may contribute"]},
        ],
        "created_at": "2026-07-17T14:00:00+00:00",
        "updated_at": "2026-07-17T14:00:00+00:00",
    })
    return repository, revisions, comparison


def test_comparison_set_requires_two_distinct_records():
    with pytest.raises(NarrativeRiskValidationError, match="at least two"):
        normalize_comparison_set({"title": "Bad", "members": []}, case_id=CASE_ID)


def test_comparison_set_persists_and_updates_case_summary(tmp_path):
    repository, revisions, comparison = build_workspace(tmp_path)
    assert comparison["baseline_member_id"] == comparison["members"][0]["member_id"]
    assert repository.list_comparison_sets(case_id=CASE_ID) == [comparison]
    case = repository.get_case(CASE_ID)
    assert case["comparison_set_count"] == 1
    assert case["comparative_status"] == "comparison_ready"


def test_evidence_matrix_exposes_claim_coverage_divergence(tmp_path):
    repository, revisions, comparison = build_workspace(tmp_path)
    matrix = repository.generate_comparative_evidence_matrix(comparison["comparison_id"], generated_at="2026-07-17T15:00:00+00:00")
    assert matrix["summary"]["member_count"] == 2
    assert matrix["summary"]["claim_count"] >= 2
    assert matrix["summary"]["divergence_count"] >= 1
    assert matrix["matrix_sha256"] == sha256_digest({k: v for k, v in matrix.items() if k != "matrix_sha256"})


def test_scenario_evaluation_is_advisory_and_preserves_baseline_record(tmp_path):
    repository, revisions, comparison = build_workspace(tmp_path)
    baseline_before = repository.get_revision(revisions[0]["revision_id"])["record"]
    scenario = repository.create_scenario(comparison["comparison_id"], {
        "name": "Adversarial evidence challenge",
        "scenario_type": "adversarial",
        "description": "Stress-test the claim under weak evidence and high volatility.",
        "assumptions": ["Primary data are unavailable", "Public scrutiny increases"],
        "parameter_overrides": {"evidence_strength": "weak", "source_count": 1, "uncertainty": "high", "narrative_volatility": "high", "stakeholder_pressure": "high"},
        "status": "active",
    })
    result = repository.evaluate_scenario(scenario["scenario_id"], generated_at="2026-07-17T16:00:00+00:00")
    assert result["deltas"]["risk_score"] > 0
    assert result["result_sha256"] == sha256_digest({k: v for k, v in result.items() if k != "result_sha256"})
    assert repository.get_revision(revisions[0]["revision_id"])["record"] == baseline_before
    assert repository.get_case(CASE_ID)["evaluated_scenario_count"] == 1


def test_scenario_rejects_unknown_override():
    comparison_id = "urn:uuid:80000000-0000-4000-8000-000000000002"
    with pytest.raises(NarrativeRiskValidationError, match="unsupported scenario override"):
        normalize_scenario({"name": "Bad", "parameter_overrides": {"secret_weight": 99}}, comparison_id=comparison_id, case_id=CASE_ID)


def test_sensitivity_analysis_identifies_score_drivers(tmp_path):
    repository, revisions, comparison = build_workspace(tmp_path)
    analysis = repository.run_comparative_sensitivity(
        comparison["comparison_id"],
        dimensions=["evidence_strength", "uncertainty", "consequences"],
        generated_at="2026-07-17T17:00:00+00:00",
    )
    assert analysis["dimensions"] == ["evidence_strength", "uncertainty", "consequences"]
    assert len(analysis["runs"]) >= 10
    assert analysis["drivers"][0]["range"] >= analysis["drivers"][-1]["range"]
    assert analysis["analysis_sha256"] == sha256_digest({k: v for k, v in analysis.items() if k != "analysis_sha256"})


def test_comparative_portfolio_aggregates_members_scenarios_and_governance(tmp_path):
    repository, revisions, comparison = build_workspace(tmp_path)
    scenario = repository.create_scenario(comparison["comparison_id"], {"name": "Worst case", "scenario_type": "worst_case", "parameter_overrides": {"uncertainty": "high", "consequences": "critical"}})
    repository.evaluate_scenario(scenario["scenario_id"], generated_at="2026-07-17T18:00:00+00:00")
    repository.run_comparative_sensitivity(comparison["comparison_id"], dimensions=["uncertainty"], generated_at="2026-07-17T18:05:00+00:00")
    portfolio = repository.get_comparative_portfolio(CASE_ID, generated_at="2026-07-17T18:10:00+00:00")
    assert portfolio["comparison_count"] == 1
    assert portfolio["member_count"] == 2
    assert portfolio["scenario_count"] == 1
    assert portfolio["evaluated_scenario_count"] == 1
    assert portfolio["publication_readiness"] == "not_assessed"


def test_decision_studio_handoff_contains_selected_scenarios_and_integrity(tmp_path):
    repository, revisions, comparison = build_workspace(tmp_path)
    repository.generate_comparative_evidence_matrix(comparison["comparison_id"], generated_at="2026-07-17T19:00:00+00:00")
    scenario = repository.create_scenario(comparison["comparison_id"], {"name": "Counterfactual", "scenario_type": "counterfactual", "parameter_overrides": {"source_count": 0, "evidence_strength": "unclear"}})
    repository.evaluate_scenario(scenario["scenario_id"], generated_at="2026-07-17T19:05:00+00:00")
    repository.run_comparative_sensitivity(comparison["comparison_id"], dimensions=["source_count"], generated_at="2026-07-17T19:10:00+00:00")
    handoff = repository.create_decision_studio_handoff(comparison["comparison_id"], selected_scenario_ids=[scenario["scenario_id"]], generated_at="2026-07-17T19:15:00+00:00")
    assert handoff["handoff_type"] == "catalyst_narrative_risk_decision_studio_handoff"
    assert handoff["selected_scenario_ids"] == [scenario["scenario_id"]]
    assert len(handoff["scenario_results"]) == 1
    assert handoff["handoff_sha256"] == sha256_digest({k: v for k, v in handoff.items() if k != "handoff_sha256"})


def test_comparative_bundle_round_trip_is_exact(tmp_path):
    source, revisions, comparison = build_workspace(tmp_path)
    source.generate_comparative_evidence_matrix(comparison["comparison_id"], generated_at="2026-07-17T20:00:00+00:00")
    scenario = source.create_scenario(comparison["comparison_id"], {"name": "Base case", "scenario_type": "base_case", "parameter_overrides": {"uncertainty": "medium"}})
    source.evaluate_scenario(scenario["scenario_id"], generated_at="2026-07-17T20:05:00+00:00")
    source.run_comparative_sensitivity(comparison["comparison_id"], dimensions=["uncertainty"], generated_at="2026-07-17T20:10:00+00:00")
    source.create_decision_studio_handoff(comparison["comparison_id"], generated_at="2026-07-17T20:15:00+00:00")
    bundle = source.export_case_bundle(CASE_ID, exported_at="2026-07-17T20:20:00+00:00")
    report = SQLiteCaseRepository.verify_bundle(bundle)
    assert report["comparative_case_ids_match"] is True
    assert report["comparative_hashes_match"] is True
    target = SQLiteCaseRepository(tmp_path / "comparison-target.sqlite3")
    target.import_case_bundle(bundle)
    assert target.export_case_bundle(CASE_ID, exported_at=bundle["exported_at"]) == bundle


def test_api_comparative_workflow(tmp_path):
    client = create_app({"NARRATIVE_RISK_DATABASE": str(tmp_path / "api-comparison.sqlite3")}).test_client()
    created = client.post("/api/narrative-risk/cases", json={"case_id": CASE_ID, "title": "API comparative", "initial_payload": sample_payload(), "created_at": "2026-07-17T12:00:00+00:00"})
    assert created.status_code == 201
    second_payload = deepcopy(sample_payload()); second_payload["uncertainty"] = "high"; second_payload["claim"] = "A qualified alternative narrative."; second_payload["claims"][0]["text"] = second_payload["claim"]; second_payload["narrative_nodes"][0]["text"] = second_payload["claim"]
    revised = client.post(f"/api/narrative-risk/cases/{CASE_ID}/revisions", json={"payload": second_payload, "created_at": "2026-07-17T13:00:00+00:00"})
    assert revised.status_code == 201
    details = client.get(f"/api/narrative-risk/cases/{CASE_ID}?include_details=true").get_json()
    members = [{"label": f"Revision {r['revision_number']}", "revision_id": r["revision_id"], "record_id": r["record_id"]} for r in details["revisions"]]
    comparison_response = client.post(f"/api/narrative-risk/cases/{CASE_ID}/comparisons", json={"title": "API comparison", "members": members})
    assert comparison_response.status_code == 201
    comparison = comparison_response.get_json()
    scenario_response = client.post(f"/api/narrative-risk/comparisons/{comparison['comparison_id']}/scenarios", json={"name": "API worst case", "scenario_type": "worst_case", "parameter_overrides": {"uncertainty": "high", "consequences": "critical"}})
    assert scenario_response.status_code == 201
    scenario = scenario_response.get_json()
    evaluated = client.post(f"/api/narrative-risk/scenarios/{scenario['scenario_id']}/evaluate", json={"generated_at": "2026-07-17T14:00:00+00:00"})
    assert evaluated.status_code == 201
    portfolio = client.get(f"/api/narrative-risk/cases/{CASE_ID}/comparative-portfolio").get_json()
    assert portfolio["scenario_count"] == 1
    assert portfolio["evaluated_scenario_count"] == 1
