import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest

from narrative_risk.contracts import sha256_digest
from narrative_risk.errors import NarrativeRiskValidationError
from narrative_risk.monitoring import (
    build_monitoring_snapshot,
    compare_monitoring_snapshots,
    evaluate_source_freshness,
)
from narrative_risk.service import build_narrative_risk_record
from narrative_risk.workspaces import SQLiteCaseRepository

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / "data" / "sample_narrative_risk_input.json").read_text())


def urn():
    return f"urn:uuid:{uuid4()}"


def record(payload=None, generated_at="2026-07-17T12:10:00+00:00"):
    return build_narrative_risk_record(payload or deepcopy(SAMPLE), generated_at=generated_at)


def test_source_freshness_uses_versioned_thresholds():
    current = evaluate_source_freshness(record(), at="2026-07-18T12:00:00+00:00")
    assert current["status"] == "current"
    stale = evaluate_source_freshness(record(), at="2030-07-18T12:00:00+00:00")
    assert stale["counts"]["stale"] == 2
    assert stale["reassessment_recommended"] is True


def test_snapshot_is_schema_valid_and_hash_verifiable():
    value = record()
    snapshot = build_monitoring_snapshot(
        value, case_id=value["identifiers"]["case_id"], revision_id=urn(),
        captured_at="2026-07-18T12:00:00+00:00", trigger="manual", snapshot_id=urn(),
    )
    digest_payload = dict(snapshot)
    digest_payload.pop("snapshot_sha256")
    assert snapshot["snapshot_version"] == "2.0.0"
    assert snapshot["snapshot_sha256"] == sha256_digest(digest_payload)
    assert snapshot["freshness_report"]["source_count"] == 2


def test_snapshot_comparison_detects_material_wording_evidence_and_score_changes():
    first_record = record()
    first = build_monitoring_snapshot(
        first_record, case_id=first_record["identifiers"]["case_id"], revision_id=urn(),
        captured_at="2026-07-18T12:00:00+00:00", snapshot_id=urn(),
    )
    changed_payload = deepcopy(SAMPLE)
    changed_payload["claim"] = "The pilot proves energy use will always fall by 12 percent."
    changed_payload["claims"][0]["text"] = changed_payload["claim"]
    changed_payload["narrative_nodes"][0]["text"] = changed_payload["claim"]
    changed_payload["uncertainty"] = "high"
    changed_payload["evidence_items"].append({
        "evidence_id": "urn:catalyst:narrative-risk:evidence:sha256:" + "1" * 64,
        "source_id": changed_payload["sources"][0]["source_id"],
        "evidence_type": "finding", "excerpt": "Follow-up results were mixed.",
        "locator": "p. 21", "captured_at": "2026-07-19T12:00:00+00:00", "notes": "",
    })
    changed_payload["relationships"].append({
        "relationship_id": "urn:catalyst:narrative-risk:relationship:sha256:" + "2" * 64,
        "claim_id": changed_payload["claims"][0]["claim_id"],
        "evidence_id": "urn:catalyst:narrative-risk:evidence:sha256:" + "1" * 64,
        "relation_type": "contradict", "strength": "moderate", "notes": "",
    })
    second_record = record(changed_payload, generated_at="2026-07-19T12:10:00+00:00")
    # Keep snapshots in one case even though analytical record IDs remain immutable.
    second = build_monitoring_snapshot(
        second_record, case_id=first["case_id"], revision_id=urn(),
        captured_at="2026-07-19T12:00:00+00:00", snapshot_id=urn(),
    )
    comparison = compare_monitoring_snapshots(
        first, second, compared_at="2026-07-19T12:30:00+00:00",
        method_snapshot=second_record["method_snapshot"], comparison_id=urn(),
    )
    assert comparison["wording_changes"]
    assert comparison["confidence_changes"]
    assert comparison["evidence_changes"]["added_evidence_ids"]
    assert comparison["materiality_score"] > 0
    assert comparison["material_change"] is True


def test_repository_persists_snapshots_watches_alerts_and_timeline(tmp_path):
    db = tmp_path / "monitor.sqlite3"
    repo = SQLiteCaseRepository(db)
    case = repo.create_case(title="Monitored case", initial_payload=deepcopy(SAMPLE))
    watch = repo.create_watchlist(
        case["case_id"], name="Daily evidence watch", cadence="daily",
        trigger_types=["source_stale", "material_change", "new_evidence", "site_intelligence_event"],
        created_at="2026-07-18T08:00:00+00:00", next_check_at="2026-07-18T09:00:00+00:00",
    )
    check = repo.run_watchlist_check(watch["watch_id"], checked_at="2030-07-18T12:00:00+00:00")
    assert check["snapshot"]["freshness_report"]["counts"]["stale"] == 2
    assert any(item["alert_type"] == "source_stale" for item in check["alerts"])
    alert = check["alerts"][0]
    acknowledged = repo.update_monitoring_alert_status(
        alert["alert_id"], status="acknowledged", actor_id="reviewer:one",
        changed_at="2030-07-18T12:05:00+00:00",
    )
    assert acknowledged["status"] == "acknowledged"
    repo.close()

    reopened = SQLiteCaseRepository(db)
    assert len(reopened.list_monitoring_snapshots(case["case_id"])) == 1
    assert len(reopened.list_watchlists(case_id=case["case_id"])) == 1
    assert reopened.list_monitoring_alerts(case_id=case["case_id"])[0]["status"] == "acknowledged"
    timeline = reopened.case_timeline(case["case_id"])
    assert {item["event_type"] for item in timeline["events"]} >= {"revision", "monitoring_snapshot", "monitoring_alert"}
    reopened.close()


def test_site_intelligence_handoff_creates_watch_alert(tmp_path):
    repo = SQLiteCaseRepository(tmp_path / "site.sqlite3")
    case = repo.create_case(title="Site Intelligence monitored", initial_payload=deepcopy(SAMPLE))
    watch = repo.create_watchlist(case["case_id"], name="Site event watch", trigger_types=["site_intelligence_event"])
    handoff = {
        "handoff_type": "site_intelligence_monitoring_event",
        "handoff_version": "2.0.0",
        "event_id": urn(), "observed_at": "2026-07-20T12:00:00+00:00",
        "case_id": case["case_id"], "event_type": "material_change",
        "headline": "New official measurement published",
        "summary": "The new measurement materially revises the prior estimate.",
        "source_url": "https://example.org/update", "source_title": "Official update",
        "source_content_sha256": "a" * 64,
        "affected_claim_ids": [SAMPLE["claims"][0]["claim_id"]],
        "confidence": "high", "payload": {"observed_value": 8.4},
    }
    result = repo.ingest_site_intelligence_event(handoff, ingested_at="2026-07-20T12:01:00+00:00")
    assert result["alerts"][0]["watch_id"] == watch["watch_id"]
    assert result["alerts"][0]["severity"] == "high"
    assert repo.list_site_intelligence_events(case["case_id"]) == [handoff]
    repo.close()


def test_monitoring_artifacts_round_trip_in_portable_bundle(tmp_path):
    source = SQLiteCaseRepository(tmp_path / "source.sqlite3")
    case = source.create_case(title="Portable monitored case", initial_payload=deepcopy(SAMPLE))
    watch = source.create_watchlist(case["case_id"], name="Manual watch", trigger_types=["source_stale"])
    source.run_watchlist_check(watch["watch_id"], checked_at="2030-07-18T12:00:00+00:00")
    bundle = source.export_case_bundle(case["case_id"], exported_at="2030-07-18T13:00:00+00:00")
    assert bundle["monitoring_snapshots"]
    assert bundle["watchlists"]
    assert bundle["monitoring_alerts"]
    source.close()

    target = SQLiteCaseRepository(tmp_path / "target.sqlite3")
    target.import_case_bundle(bundle)
    reexported = target.export_case_bundle(case["case_id"], exported_at=bundle["exported_at"])
    assert reexported == bundle
    target.close()


def test_invalid_snapshot_case_mismatch_is_rejected():
    first_record = record()
    second_record = record({"claim": "A second sufficiently detailed claim."})
    first = build_monitoring_snapshot(first_record, case_id=urn(), revision_id=urn(), snapshot_id=urn())
    second = build_monitoring_snapshot(second_record, case_id=urn(), revision_id=urn(), snapshot_id=urn())
    with pytest.raises(NarrativeRiskValidationError, match="same case"):
        compare_monitoring_snapshots(first, second, method_snapshot=second_record["method_snapshot"])
