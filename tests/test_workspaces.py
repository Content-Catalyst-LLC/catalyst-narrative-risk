import json
import sqlite3
from copy import deepcopy

import pytest

from narrative_risk.contracts import sha256_digest
from narrative_risk.errors import NarrativeRiskValidationError
from narrative_risk.workspaces import SQLiteCaseRepository

CASE_ID = "urn:uuid:40000000-0000-4000-8000-000000000001"
REVISION_ID = "urn:uuid:40000000-0000-4000-8000-000000000002"
EVENT_ID = "urn:uuid:40000000-0000-4000-8000-000000000003"
VIEW_ID = "urn:uuid:40000000-0000-4000-8000-000000000004"


def repo(tmp_path):
    return SQLiteCaseRepository(tmp_path / "workspace.sqlite3")


def test_case_with_initial_revision_persists_across_repository_reopen(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    first = SQLiteCaseRepository(database)
    case = first.create_case(
        case_id=CASE_ID,
        title="Pilot energy claim",
        summary="Institutional review case.",
        organization_id="org:city",
        project_id="project:pilot",
        status="active",
        priority="high",
        tags=["Energy", "Pilot", "energy"],
        initial_payload={"claim": "The pilot reduced energy use."},
        created_at="2026-07-17T12:00:00+00:00",
        created_by="reviewer:one",
    )
    assert case["case_id"] == CASE_ID
    assert case["current_revision"] == 1
    assert case["revision_count"] == 1
    assert case["tags"] == ["Energy", "Pilot"]
    first.close()

    second = SQLiteCaseRepository(database)
    restored = second.get_case(CASE_ID, include_details=True)
    assert restored["title"] == "Pilot energy claim"
    assert restored["revisions"][0]["record"]["identifiers"]["case_id"] == CASE_ID
    assert restored["activity"][0]["event_type"] == "case_created"
    assert restored["activity"][1]["event_type"] == "revision_added"
    second.close()


def test_revisions_are_numbered_immutable_and_hash_checked(tmp_path):
    repository = repo(tmp_path)
    repository.create_case(case_id=CASE_ID, title="Revision case")
    first = repository.add_revision(
        CASE_ID,
        revision_id=REVISION_ID,
        payload={"claim": "First wording."},
        created_at="2026-07-17T12:00:00+00:00",
        change_note="Initial wording",
    )
    second = repository.add_revision(CASE_ID, payload={"claim": "Narrower second wording."})
    assert [item["revision_number"] for item in repository.list_revisions(CASE_ID)] == [1, 2]
    assert first["record_sha256"] == sha256_digest(first["record"])
    assert second["revision_number"] == 2

    with repository._transaction() as connection:
        connection.execute("UPDATE revisions SET record_sha256=? WHERE revision_id=?", ("0" * 64, REVISION_ID))
    with pytest.raises(NarrativeRiskValidationError, match="revision record hash mismatch"):
        repository.get_revision(REVISION_ID)


def test_record_case_mismatch_and_duplicate_record_are_rejected(tmp_path):
    repository = repo(tmp_path)
    other = "urn:uuid:40000000-0000-4000-8000-000000000099"
    repository.create_case(case_id=CASE_ID, title="Case one")
    repository.create_case(case_id=other, title="Case two")
    revision = repository.add_revision(CASE_ID, payload={"claim": "Bound record."})
    with pytest.raises(NarrativeRiskValidationError, match="record case_id does not match"):
        repository.add_revision(other, record=revision["record"])
    with pytest.raises(NarrativeRiskValidationError, match="revision or record identifier already exists"):
        repository.add_revision(CASE_ID, record=revision["record"])


def test_review_events_and_activity_are_append_only(tmp_path):
    repository = repo(tmp_path)
    repository.create_case(case_id=CASE_ID, title="Review case", initial_payload={"claim": "Review me."})
    revision = repository.list_revisions(CASE_ID)[0]
    event = repository.add_review_event(
        CASE_ID,
        event_id=EVENT_ID,
        revision_id=revision["revision_id"],
        event_type="comment",
        author_id="reviewer:1",
        author_name="Reviewer One",
        body="Clarify the measured period.",
        metadata={"visibility": "internal"},
        created_at="2026-07-17T13:00:00+00:00",
    )
    assert event["body"].startswith("Clarify")
    assert repository.get_case(CASE_ID)["review_event_count"] == 1
    activity = repository.list_activity(CASE_ID)
    assert activity[-1]["event_type"] == "review_event_added"
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with repository._transaction() as connection:
            connection.execute("UPDATE activity SET event_type='changed' WHERE activity_id=?", (activity[0]["activity_id"],))
    with pytest.raises(NarrativeRiskValidationError, match="body is required"):
        repository.add_review_event(CASE_ID, event_type="comment", body="")


def test_case_search_update_archive_and_restore(tmp_path):
    repository = repo(tmp_path)
    repository.create_case(case_id=CASE_ID, title="Energy transition", summary="Pilot analysis", tags=["Energy"], priority="high")
    other = repository.create_case(title="Water baseline", tags=["Water"], priority="normal")
    updated = repository.update_case(CASE_ID, {"status": "in_review", "tags": ["Energy", "Public"]})
    assert updated["status"] == "in_review"
    assert repository.list_cases(query="transition", tags=["public"])[0]["case_id"] == CASE_ID
    assert repository.list_cases(priority="normal")[0]["case_id"] == other["case_id"]
    archived = repository.archive_case(CASE_ID, archived_at="2026-07-17T14:00:00+00:00")
    assert archived["archived"] is True
    assert repository.list_cases(query="transition") == []
    assert repository.list_cases(query="transition", archived=True)[0]["case_id"] == CASE_ID
    assert repository.restore_case(CASE_ID)["archived"] is False


def test_saved_views_are_validated_and_persisted(tmp_path):
    repository = repo(tmp_path)
    view = repository.save_view(
        view_id=VIEW_ID,
        name="High-priority review queue",
        owner_id="reviewer:1",
        filters={"status": "in_review", "priority": "high", "tags": ["Public"], "archived": False},
        created_at="2026-07-17T15:00:00+00:00",
    )
    assert view["filters"]["priority"] == "high"
    assert repository.list_saved_views(owner_id="reviewer:1") == [view]
    with pytest.raises(NarrativeRiskValidationError, match="unsupported saved-view filter"):
        repository.save_view(name="Bad", filters={"unknown": True})


def test_portable_bundle_round_trip_preserves_case_revisions_reviews_and_activity(tmp_path):
    source = SQLiteCaseRepository(tmp_path / "source.sqlite3")
    source.create_case(
        case_id=CASE_ID,
        title="Portable case",
        initial_payload={"claim": "Portable evidence claim."},
        created_at="2026-07-17T12:00:00+00:00",
    )
    revision = source.list_revisions(CASE_ID)[0]
    source.add_review_event(
        CASE_ID,
        event_id=EVENT_ID,
        revision_id=revision["revision_id"],
        body="Review comment.",
        created_at="2026-07-17T13:00:00+00:00",
    )
    bundle = source.export_case_bundle(CASE_ID, exported_at="2026-07-17T16:00:00+00:00")
    report = SQLiteCaseRepository.verify_bundle(bundle)
    assert report["bundle_sha256_match"] is True
    assert report["all_revision_hashes_match"] is True

    target = SQLiteCaseRepository(tmp_path / "target.sqlite3")
    imported = target.import_case_bundle(bundle)
    assert imported["case"]["case_id"] == CASE_ID
    exported_again = target.export_case_bundle(CASE_ID, exported_at=bundle["exported_at"])
    assert exported_again == bundle


def test_bundle_tampering_and_duplicate_import_are_rejected(tmp_path):
    source = repo(tmp_path)
    source.create_case(case_id=CASE_ID, title="Bundle case", initial_payload={"claim": "Bundle claim."})
    bundle = source.export_case_bundle(CASE_ID)
    tampered = deepcopy(bundle)
    tampered["case"]["title"] = "Changed"
    with pytest.raises(NarrativeRiskValidationError, match="bundle_sha256"):
        SQLiteCaseRepository(tmp_path / "target.sqlite3").import_case_bundle(tampered)
    with pytest.raises(NarrativeRiskValidationError, match="case already exists"):
        source.import_case_bundle(bundle)


def test_workspace_health_reports_persistent_counts(tmp_path):
    repository = repo(tmp_path)
    repository.create_case(case_id=CASE_ID, title="Health", initial_payload={"claim": "Health claim."})
    repository.save_view(name="All", filters={})
    health = repository.health()
    assert health["workspace_version"] == "1.4.0"
    assert health["counts"]["cases"] == 1
    assert health["counts"]["revisions"] == 1
    assert health["counts"]["saved_views"] == 1
