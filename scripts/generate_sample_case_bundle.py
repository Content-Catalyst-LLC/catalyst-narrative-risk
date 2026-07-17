#!/usr/bin/env python3
"""Generate the canonical v1.8.0 governed, monitored, stakeholder-aware comparative case bundle."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile

from narrative_risk.workspaces import SQLiteCaseRepository

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "urn:uuid:70000000-0000-4000-8000-000000000001"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    payload = load(ROOT / "data/sample_narrative_risk_input.json")
    with tempfile.TemporaryDirectory() as tmp:
        repo = SQLiteCaseRepository(Path(tmp) / "sample.sqlite3")
        repo.create_case(
            case_id=CASE_ID,
            title="Comparative public-impact narrative",
            summary="Governed, monitored, stakeholder-aware comparison of competing public-impact narratives.",
            status="in_review",
            priority="high",
            tags=["release", "comparative-narratives", "scenario-analysis"],
            initial_payload=payload,
            created_at="2026-07-17T12:00:00+00:00",
            created_by="release-suite",
        )
        revisions = repo.list_revisions(CASE_ID)
        first_snapshot = repo.capture_monitoring_snapshot(
            CASE_ID, revision_id=revisions[0]["revision_id"], captured_at="2026-07-17T12:30:00+00:00", trigger="revision_created"
        )

        alternative = deepcopy(payload)
        alternative["claim"] = "The pilot may have reduced energy use, but attribution remains uncertain and affordability effects require further review."
        alternative["claims"][0]["text"] = alternative["claim"]
        alternative["narrative_nodes"][0]["text"] = alternative["claim"]
        alternative["uncertainty"] = "high"
        alternative["narrative_volatility"] = "high"
        alternative["stakeholder_pressure"] = "high"
        alternative["consequences"] = "critical"
        repo.add_revision(
            CASE_ID,
            payload=alternative,
            created_at="2026-07-17T13:00:00+00:00",
            created_by="release-suite",
            change_note="Added a qualified attribution and affordability frame.",
        )
        revisions = repo.list_revisions(CASE_ID)
        second_snapshot = repo.capture_monitoring_snapshot(
            CASE_ID, revision_id=revisions[1]["revision_id"], captured_at="2026-07-17T13:30:00+00:00", trigger="revision_created"
        )
        repo.compare_snapshots(first_snapshot["snapshot_id"], second_snapshot["snapshot_id"], compared_at="2026-07-17T13:31:00+00:00")
        repo.add_review_event(
            CASE_ID,
            event_type="comment",
            author_id="release-suite",
            body="Comparative narrative, evidence, governance, and scenario review fixture.",
            created_at="2026-07-17T13:35:00+00:00",
        )

        template = repo.create_review_template(
            name="Comparative release governance template",
            created_by="release-suite",
            created_at="2026-07-17T14:00:00+00:00",
            actor_role="administrator",
        )
        workflow = repo.start_governance_workflow(
            CASE_ID,
            template_id=template["template_id"],
            started_at="2026-07-17T14:05:00+00:00",
            due_at="2026-07-31T14:05:00+00:00",
            created_by="release-suite",
            actor_role="administrator",
        )
        assignments = {}
        for stage, reviewer, role in (
            ("intake", "intake-reviewer", "reviewer"),
            ("domain", "domain-reviewer", "domain_reviewer"),
            ("editorial", "editorial-reviewer", "editorial_reviewer"),
            ("final", "final-approver", "final_approver"),
        ):
            assignments[stage] = repo.assign_reviewer(
                workflow["workflow_id"], stage=stage, reviewer_id=reviewer, reviewer_role=role,
                due_at="2026-07-24T17:00:00+00:00", created_at="2026-07-17T14:10:00+00:00",
                created_by="release-suite", actor_role="administrator",
            )
        for index, (stage, reviewer, role) in enumerate((
            ("intake", "intake-reviewer", "reviewer"),
            ("domain", "domain-reviewer", "domain_reviewer"),
            ("editorial", "editorial-reviewer", "editorial_reviewer"),
        ), start=1):
            repo.add_governance_decision(
                workflow["workflow_id"], stage=stage, disposition="approve",
                assignment_id=assignments[stage]["assignment_id"], decided_by=reviewer,
                decider_role=role, rationale=f"{stage} comparative review passed.",
                decided_at=f"2026-07-17T{14+index:02d}:00:00+00:00",
            )
        repo.add_governance_decision(
            workflow["workflow_id"], stage="legal", disposition="waive", decided_by="release-suite",
            decider_role="administrator", rationale="No separate legal trigger in the sample fixture.",
            decided_at="2026-07-17T18:00:00+00:00",
        )
        repo.add_governance_decision(
            workflow["workflow_id"], stage="compliance", disposition="waive", decided_by="release-suite",
            decider_role="administrator", rationale="No regulated communication in the sample fixture.",
            decided_at="2026-07-17T18:05:00+00:00",
        )
        repo.add_governance_decision(
            workflow["workflow_id"], stage="final", disposition="approve_with_conditions",
            assignment_id=assignments["final"]["assignment_id"], decided_by="final-approver",
            decider_role="final_approver", rationale="Comparative publication is permitted with explicit controls.",
            conditions=["Preserve the advisory method boundary and publish the competing frame."],
            required_wording=["Available evidence indicates; alternative attribution remains possible."],
            publication_restrictions=["attribution_required", "disclosure_required"],
            disclosures=["Scenarios are explicit assumption tests and do not certify truth."],
            valid_until="2027-01-17T23:59:59+00:00",
            reassessment_at="2026-10-17T12:00:00+00:00",
            decided_at="2026-07-17T18:10:00+00:00",
        )

        watch = repo.create_watchlist(
            CASE_ID, name="Comparative narrative watch", cadence="daily",
            trigger_types=["source_stale", "material_change", "reassessment_due", "approval_expired"],
            created_at="2026-07-17T18:20:00+00:00", updated_at="2026-07-17T18:20:00+00:00",
            created_by="release-suite",
        )
        repo.run_watchlist_check(watch["watch_id"], checked_at="2028-07-18T12:00:00+00:00")

        site_event = load(ROOT / "data/handoffs/site_intelligence_monitoring_event.json")
        site_event["case_id"] = CASE_ID
        repo.ingest_site_intelligence_event(site_event, ingested_at="2026-07-20T12:01:00+00:00")

        canvas = load(ROOT / "data/handoffs/catalyst_canvas_stakeholder_handoff.json")
        imported = repo.import_catalyst_canvas_stakeholders(CASE_ID, canvas, imported_at="2026-07-17T18:30:00+00:00")
        actors = imported["actors"]
        funder = next(item for item in actors if item.get("external_id", "").endswith(":funder"))
        evaluator = next(item for item in actors if item.get("external_id", "").endswith(":evaluator"))
        community = next(item for item in actors if item.get("external_id", "").endswith(":community"))
        repo.add_stakeholder_incentive(CASE_ID, {
            "actor_id": funder["actor_id"], "incentive_type": "reputational",
            "description": "Demonstrate measurable public impact.", "magnitude": "high",
            "alignment": "mixed", "disclosed": True, "conflict_status": "potential",
            "created_at": "2026-07-17T18:35:00+00:00",
        })
        repo.add_stakeholder_pressure(CASE_ID, {
            "actor_id": evaluator["actor_id"], "source_actor_id": funder["actor_id"],
            "pressure_type": "deadline", "description": "Publish before board review.",
            "intensity": "critical", "time_horizon": "immediate", "status": "active",
            "created_at": "2026-07-17T18:36:00+00:00",
        })
        repo.add_stakeholder_consequence(CASE_ID, {
            "actor_id": community["actor_id"], "impact_type": "financial", "direction": "mixed",
            "severity": "high", "description": "Overstatement could distort affordability expectations.",
            "mitigation": "Publish confidence limits and measurement dates.",
            "created_at": "2026-07-17T18:37:00+00:00",
        })

        comparison = repo.create_comparison_set(CASE_ID, {
            "title": "Measured reduction versus qualified attribution",
            "description": "Compare the audited performance frame with a cautious attribution and affordability frame.",
            "status": "active", "comparison_mode": "revision",
            "members": [
                {"label": "Audited performance", "revision_id": revisions[0]["revision_id"], "record_id": revisions[0]["record_id"], "frame": "Measured performance", "assumptions": ["Weather normalization is valid"]},
                {"label": "Qualified attribution", "revision_id": revisions[1]["revision_id"], "record_id": revisions[1]["record_id"], "frame": "Attribution and affordability uncertainty", "assumptions": ["Unobserved factors may contribute"]},
            ],
            "created_at": "2026-07-17T19:00:00+00:00", "updated_at": "2026-07-17T19:00:00+00:00", "created_by": "release-suite",
        })
        repo.generate_comparative_evidence_matrix(comparison["comparison_id"], generated_at="2026-07-17T19:05:00+00:00")
        scenarios = []
        for name, scenario_type, assumptions, overrides, at in (
            ("Best case", "best_case", ["Audited reductions persist"], {"uncertainty": "low", "evidence_strength": "strong", "consequences": "low"}, "2026-07-17T19:10:00+00:00"),
            ("Worst case", "worst_case", ["Attribution fails and consequences escalate"], {"uncertainty": "high", "evidence_strength": "weak", "consequences": "critical", "stakeholder_pressure": "high"}, "2026-07-17T19:15:00+00:00"),
            ("Counterfactual without primary evidence", "counterfactual", ["Primary measurements are unavailable"], {"source_count": 0, "evidence_strength": "unclear", "uncertainty": "high"}, "2026-07-17T19:20:00+00:00"),
            ("Adversarial public challenge", "adversarial", ["Public scrutiny and competing explanations increase"], {"narrative_volatility": "high", "stakeholder_pressure": "high", "uncertainty": "high"}, "2026-07-17T19:25:00+00:00"),
        ):
            scenario = repo.create_scenario(comparison["comparison_id"], {
                "name": name, "scenario_type": scenario_type, "description": "Explicit comparative release scenario.",
                "assumptions": assumptions, "parameter_overrides": overrides, "status": "active",
                "created_at": at, "updated_at": at, "created_by": "release-suite",
            })
            repo.evaluate_scenario(scenario["scenario_id"], generated_at=at)
            scenarios.append(scenario)
        repo.run_comparative_sensitivity(
            comparison["comparison_id"],
            dimensions=["evidence_strength", "uncertainty", "consequences", "stakeholder_pressure"],
            generated_at="2026-07-17T19:30:00+00:00",
        )
        repo.create_decision_studio_handoff(
            comparison["comparison_id"], selected_scenario_ids=[item["scenario_id"] for item in scenarios],
            generated_at="2026-07-17T19:35:00+00:00",
        )

        bundle = repo.export_case_bundle(CASE_ID, exported_at="2026-07-17T19:40:00+00:00")
        output = ROOT / "outputs/sample_case_bundle.json"
        output.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        repo.close()
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
