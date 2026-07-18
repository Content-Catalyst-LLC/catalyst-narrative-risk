from copy import deepcopy
from pathlib import Path

import pytest

from narrative_risk.errors import NarrativeRiskValidationError
from narrative_risk.hardening import (
    audit_wordpress_accessibility,
    build_performance_report,
    build_production_readiness_report,
    build_retention_assessment,
    build_security_readiness_report,
    create_sqlite_backup,
    normalize_privacy_policy,
    restore_sqlite_backup,
    verify_sqlite_backup,
)
from narrative_risk.workspaces import SQLiteCaseRepository

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "urn:uuid:a0000000-0000-4000-8000-000000000001"
POLICY_ID = "urn:uuid:a0000000-0000-4000-8000-000000000002"


def secure_config(database_path: str) -> dict:
    return {
        "environment": "production", "debug": False, "require_api_key": True,
        "admin_token_length": 48, "enforce_https": True, "secure_headers": True,
        "allowed_origins": ["https://sustainablecatalyst.com"],
        "max_content_length": 1_048_576, "database_path": database_path,
        "backup_directory": "/secure/backups", "retention_policy_configured": True,
        "encryption_at_rest_attested": True, "cookie_secure": True,
    }


def test_security_readiness_blocks_unsafe_production_and_never_exposes_secrets(tmp_path):
    report = build_security_readiness_report(
        {"environment": "production", "debug": True, "admin_token": "do-not-export"},
        generated_at="2026-07-17T12:00:00+00:00",
    )
    assert report["status"] == "blocked"
    assert "debug_disabled" in report["blocking_check_ids"]
    assert "do-not-export" not in str(report)


def test_security_readiness_accepts_explicit_production_controls(tmp_path):
    report = build_security_readiness_report(
        secure_config(str(tmp_path / "workspace.sqlite3")),
        generated_at="2026-07-17T12:00:00+00:00",
    )
    assert report["status"] == "ready"
    assert report["readiness_score"] == 100
    assert len(report["report_sha256"]) == 64


def test_privacy_policy_and_retention_assessment_are_hashed():
    policy = normalize_privacy_policy({
        "policy_id": POLICY_ID, "name": "Seven-year policy", "status": "active",
        "default_retention_days": 30, "created_at": "2026-07-17T12:00:00+00:00",
    })
    case = {
        "case_id": CASE_ID, "created_at": "2025-01-01T00:00:00+00:00",
        "updated_at": "2025-01-01T00:00:00+00:00", "archived_at": None,
        "revisions": [{}], "review_events": [], "governance_workflow": None,
        "review_assignments": [], "governance_decisions": [], "monitoring_snapshots": [],
        "monitoring_comparisons": [], "watchlists": [], "monitoring_alerts": [],
        "site_intelligence_events": [], "stakeholder_actors": [], "stakeholder_relationships": [],
        "stakeholder_incentives": [], "stakeholder_pressures": [], "stakeholder_consequences": [],
        "comparison_sets": [], "comparative_evidence_matrices": [], "scenarios": [],
        "scenario_results": [], "sensitivity_analyses": [], "decision_studio_handoffs": [],
        "publication_briefings": [], "publication_packages": [], "public_embeds": [],
        "platform_handoffs": [], "activity": [],
    }
    assessment = build_retention_assessment(case, policy, assessed_at="2026-07-17T12:00:00+00:00")
    assert assessment["status"] == "action_required"
    assert "canonical_revisions" in assessment["due_categories"]
    assert len(assessment["assessment_sha256"]) == 64


def test_sqlite_backup_verification_restore_and_tamper_detection(tmp_path):
    source = SQLiteCaseRepository(tmp_path / "source.sqlite3")
    source.create_case(case_id=CASE_ID, title="Backup case", initial_payload={"claim": "Back up this claim."})
    source.close()
    manifest = create_sqlite_backup(
        tmp_path / "source.sqlite3", tmp_path / "backup.sqlite3",
        created_at="2026-07-17T12:00:00+00:00",
    )
    assert verify_sqlite_backup(manifest)["verified"] is True
    restored = restore_sqlite_backup(manifest, tmp_path / "restored.sqlite3")
    assert restored["restored"] is True
    assert SQLiteCaseRepository(tmp_path / "restored.sqlite3").get_case(CASE_ID)["title"] == "Backup case"
    tampered = deepcopy(manifest); tampered["backup_size_bytes"] += 1
    with pytest.raises(NarrativeRiskValidationError, match="manifest hash mismatch"):
        verify_sqlite_backup(tampered)


def test_wordpress_accessibility_audit_passes_all_static_contracts():
    report = audit_wordpress_accessibility(
        ROOT / "wordpress/catalyst-narrative-risk-demo",
        generated_at="2026-07-17T12:00:00+00:00",
    )
    assert report["status"] == "pass"
    assert report["score"] == 100
    assert report["button_count"] == report["typed_button_count"]


def test_repository_privacy_assessment_survives_bundle_round_trip(tmp_path):
    source = SQLiteCaseRepository(tmp_path / "source.sqlite3")
    source.create_case(case_id=CASE_ID, title="Privacy bundle", initial_payload={"claim": "Private review claim."}, created_at="2025-01-01T00:00:00+00:00")
    source.save_privacy_policy({"policy_id": POLICY_ID, "name": "Policy", "status": "active", "default_retention_days": 30, "created_at": "2026-07-17T12:00:00+00:00"})
    assessment = source.assess_case_retention(CASE_ID, assessed_at="2026-07-17T12:01:00+00:00")
    bundle = source.export_case_bundle(CASE_ID, exported_at="2026-07-17T12:02:00+00:00")
    verification = source.verify_bundle(bundle)
    assert verification["privacy_hashes_match"] is True
    assert bundle["retention_assessments"] == [assessment]
    target = SQLiteCaseRepository(tmp_path / "target.sqlite3")
    target.import_case_bundle(bundle)
    assert target.export_case_bundle(CASE_ID, exported_at=bundle["exported_at"]) == bundle


def test_repository_database_diagnostics_and_performance_report(tmp_path):
    repository = SQLiteCaseRepository(tmp_path / "workspace.sqlite3")
    repository.create_case(case_id=CASE_ID, title="Performance", initial_payload={"claim": "Fast enough."})
    diagnostics = repository.database_diagnostics()
    assert diagnostics["integrity_check"] == "ok"
    assert diagnostics["foreign_key_violation_count"] == 0
    report = build_performance_report(repository, case_id=CASE_ID, generated_at="2026-07-17T12:00:00+00:00")
    assert report["status"] == "pass"
    assert {item["metric"] for item in report["metrics"]} == {"health_ms", "list_cases_ms", "bundle_ms", "bundle_bytes", "database_bytes"}


def test_aggregate_readiness_requires_verified_backup(tmp_path):
    repository = SQLiteCaseRepository(tmp_path / "workspace.sqlite3")
    security = build_security_readiness_report(secure_config(str(tmp_path / "workspace.sqlite3")), generated_at="2026-07-17T12:00:00+00:00")
    accessibility = audit_wordpress_accessibility(ROOT / "wordpress/catalyst-narrative-risk-demo", generated_at="2026-07-17T12:00:00+00:00")
    performance = build_performance_report(repository, generated_at="2026-07-17T12:00:00+00:00")
    report = build_production_readiness_report(
        security_report=security, accessibility_report=accessibility,
        performance_report=performance, database_diagnostics=repository.database_diagnostics(),
        generated_at="2026-07-17T12:00:00+00:00",
    )
    assert report["status"] == "needs_attention"
    assert report["backup_verified"] is False
