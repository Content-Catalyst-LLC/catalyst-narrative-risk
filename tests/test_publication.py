from base64 import b64decode
import json
from pathlib import Path

import pytest

from app import create_app
from narrative_risk.contracts import sha256_digest
from narrative_risk.errors import NarrativeRiskValidationError
from narrative_risk.workspaces import SQLiteCaseRepository

CASE_ID = "urn:uuid:90000000-0000-4000-8000-000000000001"
WORKFLOW_ID = "urn:uuid:90000000-0000-4000-8000-000000000002"
ASSIGNMENT_ID = "urn:uuid:90000000-0000-4000-8000-000000000003"


def repository(tmp_path, name="publication.sqlite3"):
    return SQLiteCaseRepository(tmp_path / name)


def create_case(repo):
    return repo.create_case(
        case_id=CASE_ID,
        title="Governed narrative publication",
        summary="A traceable public briefing test.",
        initial_payload={"claim": "Available evidence indicates the initiative may improve public trust."},
        created_at="2026-07-17T12:00:00+00:00",
    )


def approve_publication(repo, case_id=CASE_ID):
    template = {
        "name": "Final publication approval",
        "description": "A compact final review for publication tests.",
        "stages": [
            {"stage": "final", "required": True, "required_role": "final_approver", "instructions": "Approve publication."}
        ],
        "default_due_days": 7,
        "escalation_days": 1,
    }
    workflow = repo.start_governance_workflow(
        case_id,
        workflow_id=WORKFLOW_ID,
        template_snapshot=template,
        started_at="2026-07-17T12:30:00+00:00",
    )
    assignment = repo.assign_reviewer(
        workflow["workflow_id"],
        assignment_id=ASSIGNMENT_ID,
        stage="final",
        reviewer_id="approver:publication",
        reviewer_role="final_approver",
        due_at="2026-07-20T00:00:00+00:00",
        created_at="2026-07-17T12:35:00+00:00",
    )
    repo.add_governance_decision(
        workflow["workflow_id"],
        stage="final",
        disposition="approve_with_conditions",
        decided_by="approver:publication",
        decider_role="final_approver",
        assignment_id=assignment["assignment_id"],
        rationale="Approved with attribution and evidence-date disclosure.",
        conditions=["Publish only with the reviewed evidence note."],
        required_wording=["Available evidence indicates"],
        publication_restrictions=["attribution_required", "disclosure_required"],
        disclosures=["Evidence was reviewed on July 17, 2026."],
        valid_until="2027-01-31T23:59:59+00:00",
        reassessment_at="2026-12-15T12:00:00+00:00",
        decided_at="2026-07-17T13:00:00+00:00",
    )
    return repo.get_case_governance_workflow(case_id, include_details=True, at="2026-07-17T14:00:00+00:00")


def create_public_package(repo):
    create_case(repo)
    approve_publication(repo)
    briefing = repo.create_publication_briefing(
        CASE_ID,
        audience="public",
        classification="public",
        generated_at="2026-07-17T14:00:00+00:00",
        generated_by="publisher:test",
    )
    package = repo.create_publication_package(
        briefing["briefing_id"],
        formats=["json", "markdown", "html", "pdf", "csv", "jsonld"],
        slug="governed-narrative-publication",
        status="ready",
        generated_at="2026-07-17T14:05:00+00:00",
        generated_by="publisher:test",
        idempotency_key="publication-test-1",
    )
    return briefing, package


def test_internal_briefing_is_available_without_approval_but_public_is_blocked(tmp_path):
    repo = repository(tmp_path)
    case = create_case(repo)
    internal = repo.create_publication_briefing(
        case["case_id"], classification="internal", generated_at="2026-07-17T12:15:00+00:00"
    )
    assert internal["public_safe"] is False
    assert internal["publication_readiness"] == "not_assessed"
    with pytest.raises(NarrativeRiskValidationError, match="public briefing requires"):
        repo.create_publication_briefing(
            case["case_id"], classification="public", generated_at="2026-07-17T12:20:00+00:00"
        )


def test_public_briefing_carries_governance_conditions_and_redactions(tmp_path):
    repo = repository(tmp_path)
    create_case(repo)
    governed = approve_publication(repo)
    briefing = repo.create_publication_briefing(
        CASE_ID, audience="public", classification="public", generated_at="2026-07-17T14:00:00+00:00"
    )
    assert governed["publication_allowed"] is True
    assert briefing["public_safe"] is True
    assert briefing["publication_readiness"] == "conditional"
    assert briefing["sections"]["governance_summary"]["required_wording"] == ["Available evidence indicates"]
    assert briefing["disclosures"] == ["Evidence was reviewed on July 17, 2026."]
    assert "method_notes" in briefing["redactions"]
    assert briefing["briefing_sha256"] == sha256_digest({k: v for k, v in briefing.items() if k != "briefing_sha256"})


def test_publication_package_exports_six_formats_and_is_idempotent(tmp_path):
    repo = repository(tmp_path)
    briefing, package = create_public_package(repo)
    assert package["classification"] == "public"
    assert package["public_safe"] is True
    assert {item["format"] for item in package["artifacts"]} == {"json", "markdown", "html", "pdf", "csv", "jsonld"}
    for item in package["artifacts"]:
        raw = b64decode(item["content"]) if item["content_encoding"] == "base64" else item["content"].encode("utf-8")
        assert len(raw) == item["size_bytes"]
        assert __import__("hashlib").sha256(raw).hexdigest() == item["content_sha256"]
    assert b64decode(repo.get_publication_artifact(package["package_id"], "pdf")["content"]).startswith(b"%PDF-1.4")
    repeated = repo.create_publication_package(briefing["briefing_id"], idempotency_key="publication-test-1")
    assert repeated["package_id"] == package["package_id"]


def test_publish_embed_and_platform_handoff_require_public_safe_package(tmp_path):
    repo = repository(tmp_path)
    _, package = create_public_package(repo)
    published = repo.update_publication_package_status(
        package["package_id"],
        status="published",
        public_url="https://example.org/research/governed-narrative-publication",
        changed_at="2026-07-17T14:10:00+00:00",
    )
    embed = repo.create_public_embed(
        published["package_id"], slug="governed-narrative-embed", created_at="2026-07-17T14:15:00+00:00"
    )
    handoff = repo.create_platform_handoff(
        published["package_id"], target="knowledge_library", generated_at="2026-07-17T14:20:00+00:00"
    )
    assert embed["status"] == "active"
    assert "iframe" in embed["embed_code"]
    assert handoff["payload"]["formats"] == ["json", "markdown", "html", "pdf", "csv", "jsonld"]
    assert handoff["package_sha256"] == published["package_sha256"]


def test_api_key_scopes_rate_limits_and_revocation(tmp_path):
    repo = repository(tmp_path)
    created = repo.create_api_key(
        name="Publication reader",
        scopes=["publication:read"],
        rate_limit_per_minute=1,
        created_at="2026-07-17T15:00:00+00:00",
    )
    secret = created["secret"]
    assert secret.startswith(created["api_key"]["key_prefix"])
    authenticated = repo.authenticate_api_key(secret, "publication:read", used_at="2026-07-17T15:01:00+00:00")
    assert authenticated["name"] == "Publication reader"
    with pytest.raises(NarrativeRiskValidationError, match="rate limit"):
        repo.authenticate_api_key(secret, "publication:read", used_at="2026-07-17T15:01:30+00:00")
    with pytest.raises(NarrativeRiskValidationError, match="lacks required scope"):
        repo.authenticate_api_key(secret, "publication:write", used_at="2026-07-17T15:03:00+00:00")
    revoked = repo.revoke_api_key(created["api_key"]["api_key_id"])
    assert revoked["status"] == "revoked"
    with pytest.raises(NarrativeRiskValidationError, match="not active"):
        repo.authenticate_api_key(secret, "publication:read", used_at="2026-07-17T15:04:00+00:00")


def test_publication_bundle_round_trip_is_exact(tmp_path):
    source = repository(tmp_path, "source.sqlite3")
    _, package = create_public_package(source)
    source.update_publication_package_status(
        package["package_id"], status="published", public_url="https://example.org/publication",
        changed_at="2026-07-17T14:10:00+00:00",
    )
    source.create_public_embed(package["package_id"], created_at="2026-07-17T14:15:00+00:00")
    source.create_platform_handoff(package["package_id"], target="research_librarian", generated_at="2026-07-17T14:20:00+00:00")
    bundle = source.export_case_bundle(CASE_ID, exported_at="2026-07-17T16:00:00+00:00")
    verification = source.verify_bundle(bundle)
    assert verification["publication_hashes_match"] is True
    target = repository(tmp_path, "target.sqlite3")
    imported = target.import_case_bundle(bundle)
    assert imported["verification"]["bundle_sha256_match"] is True
    reexported = target.export_case_bundle(CASE_ID, exported_at="2026-07-17T16:00:00+00:00")
    assert reexported == bundle


def test_publication_api_scopes_openapi_and_public_embed(tmp_path):
    database = tmp_path / "api.sqlite3"
    app = create_app({
        "NARRATIVE_RISK_DATABASE": str(database),
        "NARRATIVE_RISK_REQUIRE_API_KEY": True,
        "NARRATIVE_RISK_ADMIN_TOKEN": "admin-token",
    })
    client = app.test_client()
    repo = app.extensions["narrative_risk_repository"]
    create_case(repo)
    approve_publication(repo)

    denied = client.post(f"/api/narrative-risk/cases/{CASE_ID}/briefings", json={"classification": "public"})
    assert denied.status_code == 401

    created_key = client.post(
        "/api/narrative-risk/api-keys",
        headers={"X-CNRISK-Admin-Token": "admin-token"},
        json={"name": "Publication API", "scopes": ["publication:read", "publication:write", "embeds:write", "handoffs:write"]},
    )
    assert created_key.status_code == 201
    secret = created_key.get_json()["secret"]
    auth = {"Authorization": f"Bearer {secret}"}
    briefing_response = client.post(
        f"/api/narrative-risk/cases/{CASE_ID}/briefings",
        headers=auth,
        json={"audience": "public", "classification": "public", "generated_at": "2026-07-17T14:00:00+00:00"},
    )
    assert briefing_response.status_code == 201
    briefing = briefing_response.get_json()
    package_response = client.post(
        f"/api/narrative-risk/briefings/{briefing['briefing_id']}/packages",
        headers=auth,
        json={"formats": ["html", "json"], "slug": "api-publication", "status": "ready", "generated_at": "2026-07-17T14:05:00+00:00"},
    )
    assert package_response.status_code == 201
    package = package_response.get_json()
    embed_response = client.post(
        f"/api/narrative-risk/packages/{package['package_id']}/embeds",
        headers=auth,
        json={"slug": "api-publication-embed", "created_at": "2026-07-17T14:10:00+00:00"},
    )
    assert embed_response.status_code == 201
    public = client.get("/api/narrative-risk/embed/api-publication-embed")
    assert public.status_code == 200
    assert public.get_json()["artifact"]["format"] == "html"
    openapi = client.get("/api/narrative-risk/openapi.json").get_json()
    assert openapi["openapi"] == "3.1.0"
    assert openapi["info"]["version"] == "1.9.0"


def test_api_migrates_v1_8_0_record():
    client = create_app({"NARRATIVE_RISK_DATABASE": ":memory:"}).test_client()
    legacy = json.loads((Path(__file__).parent / "fixtures" / "legacy-v1.8.0-record.json").read_text())
    response = client.post("/api/narrative-risk/migrate/v1.8.0", json=legacy)
    assert response.status_code == 200
    migrated = response.get_json()
    assert migrated["contract"]["contract_version"] == "1.9.0"
    assert migrated["migration"]["from_schema_version"] == "1.8.0"
