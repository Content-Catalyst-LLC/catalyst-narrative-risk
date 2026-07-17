import json
from pathlib import Path

from app import create_app

DATA = Path(__file__).resolve().parents[1] / "data"


def test_api_returns_canonical_record():
    client = create_app().test_client()
    response = client.post("/api/narrative-risk", json={"claim": "API claim"})
    assert response.status_code == 200
    record = response.get_json()
    assert record["contract"]["contract_version"] == "1.3.0"
    assert record["method_snapshot"]["method_version"] == "1.3.0"
    assert record["identifiers"]["ledger_schema_id"].endswith("/1.3.0")
    assert record["evidence_ledger"]["coverage"]["overall"]["coverage_status"] == "none"
    assert record["human_decision"]["disposition"] == "undecided"


def test_api_exposes_contract_vocabularies_and_method_snapshot():
    client = create_app().test_client()
    contract = client.get("/api/narrative-risk/contract").get_json()
    vocabularies = client.get("/api/narrative-risk/vocabularies").get_json()
    method = client.get("/api/narrative-risk/methods/current").get_json()
    assert contract["contract_version"] == "1.3.0"
    assert contract["ledger_schema_id"].endswith("/1.3.0")
    assert vocabularies["vocabulary_version"] == "1.3.0"
    assert "evidence_relation_type" in vocabularies["vocabularies"]
    assert method["method_snapshot"]["method_version"] == "1.3.0"
    assert method["method_snapshot"]["ledger_policy"]["policy_version"] == "1.3.0"
    assert len(method["method_snapshot_sha256"]) == 64


def test_api_analyzes_evidence_ledger():
    client = create_app().test_client()
    payload = json.loads((DATA / "sample_narrative_risk_input.json").read_text())
    response = client.post("/api/narrative-risk/ledger/analyze", json=payload)
    assert response.status_code == 200
    analysis = response.get_json()
    assert analysis["evidence_ledger"]["derived_scoring_inputs"] == {
        "ledger_applied": True,
        "source_type": "official_or_primary",
        "evidence_strength": "strong",
        "source_count": 2,
        "basis": "Derived from evidence relationships linked to the primary claim using the embedded v1.3.0 ledger policy.",
    }


def test_api_verifies_generated_record():
    client = create_app().test_client()
    record = client.post("/api/narrative-risk", json={"claim": "Verify API claim"}).get_json()
    response = client.post("/api/narrative-risk/verify", json=record)
    assert response.status_code == 200
    report = response.get_json()
    assert report["exact_match"] is True
    assert report["evidence_ledger_hash_match"] is True


def test_api_imports_first_party_source_handoffs():
    client = create_app().test_client()
    knowledge = json.loads((DATA / "handoffs" / "knowledge_library_source.json").read_text())
    dataset = json.loads((DATA / "handoffs" / "catalyst_data_source.json").read_text())
    knowledge_response = client.post("/api/narrative-risk/import/knowledge-library", json=knowledge)
    dataset_response = client.post("/api/narrative-risk/import/catalyst-data", json=dataset)
    assert knowledge_response.status_code == 200
    assert dataset_response.status_code == 200
    assert knowledge_response.get_json()["source"]["provenance"]["acquisition_method"] == "knowledge_library"
    assert dataset_response.get_json()["source"]["provenance"]["acquisition_method"] == "catalyst_data"


def test_api_migrates_v1_1_0_record():
    client = create_app().test_client()
    legacy = json.loads((Path(__file__).parent / "fixtures" / "legacy-v1.1.0-record.json").read_text())
    response = client.post("/api/narrative-risk/migrate/v1.1.0", json=legacy)
    assert response.status_code == 200
    migrated = response.get_json()
    assert migrated["contract"]["contract_version"] == "1.3.0"
    assert migrated["migration"]["from_schema_version"] == "1.1.0"
    assert migrated["evidence_ledger"]["coverage"]["overall"]["source_count"] == 0


def test_api_rejects_missing_claim_invalid_vocabulary_and_non_json_body():
    client = create_app().test_client()
    missing = client.post("/api/narrative-risk", json={})
    invalid = client.post("/api/narrative-risk", json={"claim": "x", "source_type": "made_up"})
    non_json = client.post("/api/narrative-risk", data="not-json", content_type="text/plain")
    assert missing.status_code == 400
    assert missing.get_json()["message"] == "claim is required"
    assert invalid.status_code == 400
    assert invalid.get_json()["message"].startswith("source_type must be one of:")
    assert non_json.status_code == 400
    assert non_json.get_json()["message"] == "request body must be a JSON object"


def test_api_persistent_case_revision_review_export_and_import(tmp_path):
    source = create_app({"NARRATIVE_RISK_DATABASE": str(tmp_path / "source.sqlite3")}).test_client()
    created = source.post("/api/narrative-risk/cases", json={
        "case_id": "urn:uuid:50000000-0000-4000-8000-000000000001",
        "title": "API workspace case",
        "tags": ["API", "Review"],
        "initial_payload": {"claim": "The API persists cases."},
        "created_at": "2026-07-17T12:00:00+00:00"
    })
    assert created.status_code == 201
    case = created.get_json()
    assert case["current_revision"] == 1

    details = source.get(f"/api/narrative-risk/cases/{case['case_id']}?include_details=true").get_json()
    revision_id = details["revisions"][0]["revision_id"]
    review = source.post(f"/api/narrative-risk/cases/{case['case_id']}/reviews", json={
        "revision_id": revision_id,
        "event_type": "comment",
        "body": "API review comment."
    })
    assert review.status_code == 201

    listing = source.get("/api/narrative-risk/cases?tags=Review&status=draft").get_json()
    assert listing["count"] == 1
    bundle = source.get(f"/api/narrative-risk/cases/{case['case_id']}/export?exported_at=2026-07-17T15:00:00%2B00:00").get_json()
    assert len(bundle["bundle_sha256"]) == 64

    target = create_app({"NARRATIVE_RISK_DATABASE": str(tmp_path / "target.sqlite3")}).test_client()
    imported = target.post("/api/narrative-risk/cases/import", json=bundle)
    assert imported.status_code == 201
    assert imported.get_json()["verification"]["bundle_sha256_match"] is True


def test_api_saved_views_archive_restore_and_workspace_health(tmp_path):
    client = create_app({"NARRATIVE_RISK_DATABASE": str(tmp_path / "workspace.sqlite3")}).test_client()
    case = client.post("/api/narrative-risk/cases", json={"title": "Archive API case"}).get_json()
    view = client.post("/api/narrative-risk/saved-views", json={
        "name": "Active queue", "owner_id": "reviewer:api", "filters": {"status": "active", "archived": False}
    })
    assert view.status_code == 201
    assert client.get("/api/narrative-risk/saved-views?owner_id=reviewer:api").get_json()["count"] == 1
    assert client.post(f"/api/narrative-risk/cases/{case['case_id']}/archive", json={}).get_json()["archived"] is True
    assert client.post(f"/api/narrative-risk/cases/{case['case_id']}/restore", json={}).get_json()["archived"] is False
    health = client.get("/api/narrative-risk/workspaces/health").get_json()
    assert health["workspace_version"] == "1.3.0"
    assert health["counts"]["cases"] == 1


def test_api_migrates_v1_2_0_record():
    client = create_app({"NARRATIVE_RISK_DATABASE": ":memory:"}).test_client()
    legacy = json.loads((Path(__file__).parent / "fixtures" / "legacy-v1.2.0-record.json").read_text())
    response = client.post("/api/narrative-risk/migrate/v1.2.0", json=legacy)
    assert response.status_code == 200
    migrated = response.get_json()
    assert migrated["contract"]["contract_version"] == "1.3.0"
    assert migrated["migration"]["from_schema_version"] == "1.2.0"
