import sqlite3

import pytest

from narrative_risk.errors import NarrativeRiskValidationError
from narrative_risk.governance import default_template_payload, permissions_for_role, require_permission
from narrative_risk.workspaces import SQLiteCaseRepository

CASE_ID = "urn:uuid:60000000-0000-4000-8000-000000000001"
TEMPLATE_ID = "urn:uuid:60000000-0000-4000-8000-000000000002"
WORKFLOW_ID = "urn:uuid:60000000-0000-4000-8000-000000000003"


def repository(tmp_path):
    return SQLiteCaseRepository(tmp_path / "governance.sqlite3")


def create_case(repo):
    return repo.create_case(
        case_id=CASE_ID,
        title="Governed public claim",
        initial_payload={"claim": "The program improved public trust."},
        created_at="2026-07-17T12:00:00+00:00",
    )


def assign_and_decide(repo, workflow_id, stage, reviewer_id, role, *, disposition="approve", **decision):
    assignment = repo.assign_reviewer(
        workflow_id,
        stage=stage,
        reviewer_id=reviewer_id,
        reviewer_role=role,
        due_at="2026-07-25T12:00:00+00:00",
        created_at="2026-07-17T12:05:00+00:00",
    )
    result = repo.add_governance_decision(
        workflow_id,
        stage=stage,
        disposition=disposition,
        decided_by=reviewer_id,
        decider_role=role,
        assignment_id=assignment["assignment_id"],
        rationale=f"{stage} review completed.",
        decided_at=decision.pop("decided_at", "2026-07-17T13:00:00+00:00"),
        **decision,
    )
    return assignment, result


def test_governance_policy_enforces_role_permissions():
    assert "approve_final" in permissions_for_role("final_approver")
    assert "manage_templates" in permissions_for_role("administrator")
    assert "publish" not in permissions_for_role("reviewer")
    with pytest.raises(NarrativeRiskValidationError, match="does not have permission"):
        require_permission("observer", "comment")


def test_review_templates_are_versioned_validated_and_persistent(tmp_path):
    repo = repository(tmp_path)
    template = repo.create_review_template(
        template_id=TEMPLATE_ID,
        created_at="2026-07-17T12:00:00+00:00",
        created_by="admin:1",
    )
    assert template["name"] == default_template_payload()["name"]
    assert template["stages"][-1]["stage"] == "final"
    assert repo.get_review_template(TEMPLATE_ID) == template
    assert repo.list_review_templates(active=True) == [template]
    with pytest.raises(NarrativeRiskValidationError, match="canonical review-stage order"):
        repo.create_review_template(
            name="Invalid order",
            stages=[
                {"stage": "final", "required": True, "required_role": "final_approver", "instructions": ""},
                {"stage": "domain", "required": True, "required_role": "domain_reviewer", "instructions": ""},
            ],
        )
    with pytest.raises(NarrativeRiskValidationError, match="permission"):
        repo.create_review_template(name="Unauthorized", actor_role="reviewer")


def test_staged_workflow_assignments_decisions_conditions_and_publication(tmp_path):
    repo = repository(tmp_path)
    case = create_case(repo)
    workflow = repo.start_governance_workflow(
        case["case_id"], workflow_id=WORKFLOW_ID,
        started_at="2026-07-17T12:01:00+00:00", created_by="admin:1",
    )
    assert workflow["status"] == "active"
    assert workflow["current_stage"] == "intake"
    assert repo.get_case(CASE_ID)["status"] == "in_review"

    assign_and_decide(repo, WORKFLOW_ID, "intake", "reviewer:1", "reviewer")
    assert repo.get_governance_workflow(WORKFLOW_ID)["current_stage"] == "domain"
    assign_and_decide(repo, WORKFLOW_ID, "domain", "domain:1", "domain_reviewer")
    assign_and_decide(repo, WORKFLOW_ID, "editorial", "editor:1", "editorial_reviewer")

    # Optional stages may be explicitly waived without manufacturing assignments.
    repo.add_governance_decision(
        WORKFLOW_ID, stage="legal", disposition="waive", decided_by="admin:1",
        decider_role="administrator", rationale="No legal trigger was identified.",
        decided_at="2026-07-17T14:00:00+00:00",
    )
    repo.add_governance_decision(
        WORKFLOW_ID, stage="compliance", disposition="waive", decided_by="admin:1",
        decider_role="administrator", rationale="No regulated communication is involved.",
        decided_at="2026-07-17T14:05:00+00:00",
    )
    _, final = assign_and_decide(
        repo, WORKFLOW_ID, "final", "approver:1", "final_approver",
        disposition="approve_with_conditions",
        conditions=["Publish only with the reviewed evidence note."],
        required_wording=["Available evidence indicates"],
        publication_restrictions=["attribution_required", "disclosure_required"],
        disclosures=["The assessment reflects evidence available on July 17, 2026."],
        valid_until="2027-01-31T23:59:59+00:00",
        reassessment_at="2026-12-15T12:00:00+00:00",
        decided_at="2026-07-17T15:00:00+00:00",
    )
    assert final["disposition"] == "approve_with_conditions"
    governed = repo.get_governance_workflow(WORKFLOW_ID, include_details=True, at="2026-07-18T12:00:00+00:00")
    assert governed["status"] == "approved"
    assert governed["required_assignments_complete"] is True
    assert governed["publication_allowed"] is True
    assert governed["final_disposition"] == "approve_with_conditions"
    case = repo.get_case(CASE_ID)
    assert case["status"] == "approved"
    assert case["governance_decision_count"] == 6
    assert case["assignment_count"] == 4


def test_final_approval_requires_required_stage_assignments(tmp_path):
    repo = repository(tmp_path)
    case = create_case(repo)
    workflow = repo.start_governance_workflow(case["case_id"])
    # Administrator can move through stages, but required stages cannot be decided without assignments.
    with pytest.raises(NarrativeRiskValidationError, match="requires a review assignment"):
        repo.add_governance_decision(
            workflow["workflow_id"], stage="intake", disposition="approve",
            decided_by="admin:1", decider_role="administrator", rationale="Attempted bypass.",
        )


def test_revision_and_rejection_decisions_block_or_close_workflow(tmp_path):
    repo = repository(tmp_path)
    case = create_case(repo)
    workflow = repo.start_governance_workflow(case["case_id"])
    assignment, decision = assign_and_decide(
        repo, workflow["workflow_id"], "intake", "reviewer:1", "reviewer", disposition="revise"
    )
    assert decision["disposition"] == "revise"
    assert repo.get_governance_workflow(workflow["workflow_id"])["status"] == "changes_required"
    assert repo.get_review_assignment(assignment["assignment_id"])["status"] == "completed"


def test_expiration_reassessment_and_blocking_restrictions_disable_publication(tmp_path):
    repo = repository(tmp_path)
    case = create_case(repo)
    compact = {
        "name": "Compact approval",
        "description": "Final approval only.",
        "stages": [{"stage": "final", "required": True, "required_role": "final_approver", "instructions": "Final review."}],
        "default_due_days": 7,
        "escalation_days": 1,
    }
    workflow = repo.start_governance_workflow(case["case_id"], template_snapshot=compact)
    assign_and_decide(
        repo, workflow["workflow_id"], "final", "approver:1", "final_approver",
        publication_restrictions=["internal_only"],
        valid_until="2026-08-01T00:00:00+00:00",
        reassessment_at="2026-07-25T00:00:00+00:00",
        decided_at="2026-07-18T00:00:00+00:00",
    )
    before = repo.get_governance_workflow(workflow["workflow_id"], at="2026-07-20T00:00:00+00:00")
    assert before["status"] == "approved"
    assert before["publication_allowed"] is False
    due = repo.get_governance_workflow(workflow["workflow_id"], at="2026-07-26T00:00:00+00:00")
    assert "reassessment_due" in due["governance_flags"]
    expired = repo.get_governance_workflow(workflow["workflow_id"], at="2026-08-02T00:00:00+00:00")
    assert expired["status"] == "expired"
    assert "approval_expired" in expired["governance_flags"]
    assert repo.list_reassessment_due(at="2026-08-02T00:00:00+00:00")[0]["workflow_id"] == workflow["workflow_id"]


def test_governance_decisions_are_append_only_and_queue_surfaces_overdue(tmp_path):
    repo = repository(tmp_path)
    case = create_case(repo)
    workflow = repo.start_governance_workflow(case["case_id"])
    assignment = repo.assign_reviewer(
        workflow["workflow_id"], stage="intake", reviewer_id="reviewer:1", reviewer_role="reviewer",
        due_at="2026-07-18T00:00:00+00:00",
    )
    queue = repo.governance_queue(reviewer_id="reviewer:1", at="2026-07-19T00:00:00+00:00")
    assert queue["queues"]["overdue"][0]["assignment_id"] == assignment["assignment_id"]
    decision = repo.add_governance_decision(
        workflow["workflow_id"], stage="intake", disposition="approve", decided_by="reviewer:1",
        decider_role="reviewer", assignment_id=assignment["assignment_id"], rationale="Reviewed.",
    )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with repo._transaction() as connection:
            connection.execute("UPDATE governance_decisions SET rationale='changed' WHERE decision_id=?", (decision["decision_id"],))


def test_case_bundle_round_trip_preserves_governance_records(tmp_path):
    source = SQLiteCaseRepository(tmp_path / "source.sqlite3")
    case = create_case(source)
    compact = {
        "name": "Final-only",
        "description": "Portable governed decision.",
        "stages": [{"stage": "final", "required": True, "required_role": "final_approver", "instructions": "Final review."}],
        "default_due_days": 7,
        "escalation_days": 1,
    }
    workflow = source.start_governance_workflow(case["case_id"], template_snapshot=compact)
    assign_and_decide(
        source, workflow["workflow_id"], "final", "approver:1", "final_approver",
        valid_until="2027-01-01T00:00:00+00:00", reassessment_at="2026-12-01T00:00:00+00:00",
    )
    bundle = source.export_case_bundle(CASE_ID, exported_at="2026-07-20T00:00:00+00:00")
    assert bundle["governance_workflow"]["status"] == "approved"
    assert len(bundle["review_assignments"]) == 1
    assert len(bundle["governance_decisions"]) == 1
    assert SQLiteCaseRepository.verify_bundle(bundle)["governance_case_ids_match"] is True

    target = SQLiteCaseRepository(tmp_path / "target.sqlite3")
    imported = target.import_case_bundle(bundle)
    assert imported["case"]["governance_workflow"]["final_disposition"] == "approve"
    assert target.export_case_bundle(CASE_ID, exported_at=bundle["exported_at"]) == bundle
