import json
from pathlib import Path

import pytest

from narrative_risk.connected import build_platform_profile
from narrative_risk.contracts import contract_definition, load_json, ROOT, sha256_digest
from narrative_risk.errors import NarrativeRiskValidationError
from narrative_risk.workspaces import SQLiteCaseRepository

CASE_ID = "urn:uuid:90000000-0000-4000-8000-000000000001"


def repo(tmp_path):
    return SQLiteCaseRepository(tmp_path / "connected.sqlite3")


def test_platform_profile_is_complete_and_tamper_evident():
    manifest = load_json(ROOT / "narrative_risk_manifest.json")
    profile = build_platform_profile(manifest=manifest, contract=contract_definition(), generated_at="2026-07-18T18:00:00+00:00")
    assert profile["profile_version"] == "2.0.0"
    assert len(profile["modules"]) == 10
    assert sha256_digest({k: v for k, v in profile.items() if k != "profile_sha256"}) == profile["profile_sha256"]


def test_connected_event_route_dossier_and_institutional_workspace(tmp_path):
    repository = repo(tmp_path)
    repository.create_case(
        case_id=CASE_ID,
        title="Connected case",
        organization_id="org:catalyst",
        initial_payload={"claim": "A connected claim requires governed evidence."},
        created_at="2026-07-18T18:01:00+00:00",
    )
    event = repository.ingest_platform_event({
        "case_id": CASE_ID,
        "source_module": "knowledge_library",
        "target_modules": ["narrative_risk", "research_librarian"],
        "event_type": "evidence_added",
        "occurred_at": "2026-07-18T18:02:00+00:00",
        "idempotency_key": "knowledge-library:evidence:1",
        "payload": {"source_id": "source:1"},
    })
    duplicate = repository.ingest_platform_event({
        "event_id": event["event_id"],
        "case_id": CASE_ID,
        "source_module": "knowledge_library",
        "target_modules": ["narrative_risk", "research_librarian"],
        "event_type": "evidence_added",
        "occurred_at": "2026-07-18T18:02:00+00:00",
        "idempotency_key": "knowledge-library:evidence:1",
        "payload": {"source_id": "source:1"},
    })
    assert duplicate == event
    route = repository.create_integration_route({
        "case_id": CASE_ID,
        "source_module": "narrative_risk",
        "target_module": "decision_studio",
        "artifact_type": "canonical-record",
        "artifact_id": repository.list_revisions(CASE_ID)[0]["record_id"],
        "status": "delivered",
        "created_at": "2026-07-18T18:03:00+00:00",
        "payload_sha256": "a" * 64,
    })
    dossier = repository.create_connected_dossier(CASE_ID, generated_at="2026-07-18T18:04:00+00:00")
    workspace = repository.create_institutional_workspace("org:catalyst", generated_at="2026-07-18T18:05:00+00:00")
    assert dossier["analytical_summary"]["risk_score"] is not None
    assert dossier["module_links"][1]["event_count"] == 1
    assert route["target_module"] == "decision_studio"
    assert workspace["case_count"] == 1
    assert workspace["connected_dossier_ids"] == [dossier["dossier_id"]]


def test_platform_event_idempotency_rejects_changed_content(tmp_path):
    repository = repo(tmp_path)
    repository.create_case(case_id=CASE_ID, title="Case", initial_payload={"claim": "Claim."})
    base = {
        "case_id": CASE_ID,
        "source_module": "site_intelligence",
        "target_modules": ["narrative_risk"],
        "event_type": "monitoring_signal",
        "idempotency_key": "signal:1",
        "payload": {"signal": "first"},
    }
    repository.ingest_platform_event(base)
    changed = dict(base)
    changed["payload"] = {"signal": "changed"}
    with pytest.raises(NarrativeRiskValidationError, match="idempotency_key"):
        repository.ingest_platform_event(changed)


def test_connected_bundle_round_trip(tmp_path):
    source = repo(tmp_path / "source")
    source.create_case(case_id=CASE_ID, title="Bundle", organization_id="org:a", initial_payload={"claim": "Bundle claim."})
    source.ingest_platform_event({"case_id": CASE_ID, "source_module": "catalyst_data", "target_modules": ["narrative_risk"], "event_type": "evidence_added", "idempotency_key": "dataset:1", "payload": {"dataset_id": "d1"}})
    source.create_integration_route({"case_id": CASE_ID, "source_module": "narrative_risk", "target_module": "knowledge_library", "artifact_type": "briefing", "artifact_id": "brief:1", "payload_sha256": "b" * 64})
    source.create_connected_dossier(CASE_ID)
    bundle = source.export_case_bundle(CASE_ID, exported_at="2026-07-18T18:10:00+00:00")
    report = source.verify_bundle(bundle)
    assert report["connected_case_ids_match"] is True
    assert report["connected_hashes_match"] is True
    target = repo(tmp_path / "target")
    target.import_case_bundle(bundle)
    rebuilt = target.export_case_bundle(CASE_ID, exported_at="2026-07-18T18:10:00+00:00")
    assert rebuilt == bundle

def test_connected_api_endpoints(tmp_path):
    from app import create_app
    app = create_app({"TESTING": True, "NARRATIVE_RISK_DATABASE": str(tmp_path / "api.sqlite3")})
    client = app.test_client()
    profile = client.get("/api/narrative-risk/platform/profile")
    assert profile.status_code == 200
    assert profile.get_json()["profile_version"] == "2.0.0"
    created = client.post("/api/narrative-risk/cases", json={"case_id": CASE_ID, "title": "API connected", "organization_id": "org:api", "initial_payload": {"claim": "API claim."}})
    assert created.status_code == 201
    event = client.post("/api/narrative-risk/platform/events", json={"case_id": CASE_ID, "source_module": "site_intelligence", "target_modules": ["narrative_risk"], "event_type": "monitoring_signal", "idempotency_key": "api:signal:1", "payload": {"signal": "changed"}})
    assert event.status_code == 201
    dossier = client.post(f"/api/narrative-risk/cases/{CASE_ID}/connected-dossiers", json={"generated_at": "2026-07-18T19:00:00+00:00"})
    assert dossier.status_code == 201
    workspace = client.post("/api/narrative-risk/institutional-workspaces/org:api", json={"generated_at": "2026-07-18T19:01:00+00:00"})
    assert workspace.status_code == 201
    assert workspace.get_json()["case_count"] == 1
