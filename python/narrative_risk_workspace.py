#!/usr/bin/env python3
"""Manage persistent Catalyst Narrative Risk cases from the command line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.workspaces import SQLiteCaseRepository


def read_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(value, path: str | None = None):
    content = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if path:
        Path(path).write_text(content, encoding="utf-8")
    else:
        print(content, end="")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--database", default="data/catalyst-narrative-risk.sqlite3")
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("init")
    create = commands.add_parser("create")
    create.add_argument("--title", required=True)
    create.add_argument("--summary", default="")
    create.add_argument("--organization-id")
    create.add_argument("--project-id")
    create.add_argument("--status", default="draft")
    create.add_argument("--priority", default="normal")
    create.add_argument("--tag", action="append", default=[])
    create.add_argument("--input")
    create.add_argument("--created-by")

    listing = commands.add_parser("list")
    listing.add_argument("--query", default="")
    listing.add_argument("--status")
    listing.add_argument("--priority")
    listing.add_argument("--tag", action="append", default=[])
    listing.add_argument("--archived", action="store_true")

    show = commands.add_parser("show")
    show.add_argument("case_id")
    show.add_argument("--details", action="store_true")

    revise = commands.add_parser("add-revision")
    revise.add_argument("case_id")
    revise.add_argument("--input", required=True)
    revise.add_argument("--record", action="store_true", help="Input is a canonical record rather than analytical input.")
    revise.add_argument("--created-by")
    revise.add_argument("--change-note", default="")

    review = commands.add_parser("add-review")
    review.add_argument("case_id")
    review.add_argument("--event-type", default="comment")
    review.add_argument("--revision-id")
    review.add_argument("--author-id")
    review.add_argument("--author-name")
    review.add_argument("--body", default="")

    archive = commands.add_parser("archive")
    archive.add_argument("case_id")
    restore = commands.add_parser("restore")
    restore.add_argument("case_id")

    export = commands.add_parser("export")
    export.add_argument("case_id")
    export.add_argument("--output", required=True)
    export.add_argument("--exported-at")

    import_cmd = commands.add_parser("import")
    import_cmd.add_argument("--input", required=True)

    verify = commands.add_parser("verify-bundle")
    verify.add_argument("--input", required=True)

    view = commands.add_parser("save-view")
    view.add_argument("--name", required=True)
    view.add_argument("--owner-id")
    view.add_argument("--filters", required=True, help="Path to a JSON filters object.")

    template = commands.add_parser("create-template")
    template.add_argument("--name")
    template.add_argument("--description")
    template.add_argument("--stages", help="Path to a JSON array of stage definitions.")
    template.add_argument("--default-due-days", type=int)
    template.add_argument("--escalation-days", type=int)
    template.add_argument("--created-by")
    template.add_argument("--actor-role", default="administrator")

    templates = commands.add_parser("list-templates")
    templates.add_argument("--active", choices=("true", "false", "all"), default="all")

    start = commands.add_parser("start-governance")
    start.add_argument("case_id")
    start.add_argument("--revision-id")
    start.add_argument("--template-id")
    start.add_argument("--template", help="Path to an inline template snapshot JSON object.")
    start.add_argument("--started-at")
    start.add_argument("--due-at")
    start.add_argument("--created-by")
    start.add_argument("--actor-role", default="administrator")

    assign = commands.add_parser("assign-review")
    assign.add_argument("workflow_id")
    assign.add_argument("--stage", required=True)
    assign.add_argument("--reviewer-id", required=True)
    assign.add_argument("--reviewer-name")
    assign.add_argument("--reviewer-role", required=True)
    assign.add_argument("--optional", action="store_true")
    assign.add_argument("--instructions", default="")
    assign.add_argument("--due-at")
    assign.add_argument("--created-by")
    assign.add_argument("--actor-role", default="administrator")

    assignment = commands.add_parser("assignment-status")
    assignment.add_argument("assignment_id")
    assignment.add_argument("--status", required=True)
    assignment.add_argument("--actor-id", required=True)
    assignment.add_argument("--actor-role", required=True)
    assignment.add_argument("--changed-at")

    decide = commands.add_parser("decide")
    decide.add_argument("workflow_id")
    decide.add_argument("--stage", required=True)
    decide.add_argument("--disposition", required=True)
    decide.add_argument("--decided-by", required=True)
    decide.add_argument("--decided-by-name")
    decide.add_argument("--decider-role", required=True)
    decide.add_argument("--rationale", required=True)
    decide.add_argument("--assignment-id")
    decide.add_argument("--condition", action="append", default=[])
    decide.add_argument("--required-wording", action="append", default=[])
    decide.add_argument("--publication-restriction", action="append", default=[])
    decide.add_argument("--disclosure", action="append", default=[])
    decide.add_argument("--valid-until")
    decide.add_argument("--reassessment-at")
    decide.add_argument("--supersedes-decision-id")
    decide.add_argument("--decided-at")

    queue = commands.add_parser("governance-queue")
    queue.add_argument("--reviewer-id")
    queue.add_argument("--at")

    due = commands.add_parser("reassessment-due")
    due.add_argument("--at")

    snapshot = commands.add_parser("capture-snapshot")
    snapshot.add_argument("case_id")
    snapshot.add_argument("--revision-id")
    snapshot.add_argument("--captured-at")
    snapshot.add_argument("--trigger", default="manual")

    compare = commands.add_parser("compare-snapshots")
    compare.add_argument("from_snapshot_id")
    compare.add_argument("to_snapshot_id")
    compare.add_argument("--compared-at")

    watch = commands.add_parser("create-watch")
    watch.add_argument("case_id")
    watch.add_argument("--name", required=True)
    watch.add_argument("--cadence", default="daily")
    watch.add_argument("--trigger-type", action="append", default=[])
    watch.add_argument("--source-id", action="append", default=[])
    watch.add_argument("--next-check-at")
    watch.add_argument("--created-by")
    watch.add_argument("--notes", default="")

    watches = commands.add_parser("list-watches")
    watches.add_argument("--case-id")
    watches.add_argument("--status")
    watches.add_argument("--due-at")

    check = commands.add_parser("check-watch")
    check.add_argument("watch_id")
    check.add_argument("--revision-id")
    check.add_argument("--checked-at")
    check.add_argument("--trigger", default="scheduled")

    alerts = commands.add_parser("list-alerts")
    alerts.add_argument("--case-id")
    alerts.add_argument("--watch-id")
    alerts.add_argument("--status")
    alerts.add_argument("--severity")

    alert_status = commands.add_parser("alert-status")
    alert_status.add_argument("alert_id")
    alert_status.add_argument("--status", required=True)
    alert_status.add_argument("--actor-id", required=True)
    alert_status.add_argument("--changed-at")

    timeline = commands.add_parser("timeline")
    timeline.add_argument("case_id")

    site = commands.add_parser("ingest-site-intelligence")
    site.add_argument("--input", required=True)
    site.add_argument("--ingested-at")

    for command in ("add-stakeholder-actor", "add-stakeholder-relationship", "add-stakeholder-incentive", "add-stakeholder-pressure", "add-stakeholder-consequence"):
        item = commands.add_parser(command); item.add_argument("case_id"); item.add_argument("--input", required=True)
    stakeholder_list = commands.add_parser("stakeholder-intelligence"); stakeholder_list.add_argument("case_id"); stakeholder_list.add_argument("--generated-at")
    canvas = commands.add_parser("import-catalyst-canvas"); canvas.add_argument("case_id"); canvas.add_argument("--input", required=True); canvas.add_argument("--imported-at")
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "verify-bundle":
        write_json(SQLiteCaseRepository.verify_bundle(read_json(args.input)))
        return 0

    repository = SQLiteCaseRepository(args.database)
    try:
        if args.command == "init":
            write_json(repository.health())
        elif args.command == "create":
            write_json(repository.create_case(
                title=args.title, summary=args.summary, organization_id=args.organization_id,
                project_id=args.project_id, status=args.status, priority=args.priority, tags=args.tag,
                initial_payload=read_json(args.input) if args.input else None, created_by=args.created_by,
            ))
        elif args.command == "list":
            cases = repository.list_cases(query=args.query, status=args.status, priority=args.priority, tags=args.tag, archived=args.archived)
            write_json({"cases": cases, "count": len(cases)})
        elif args.command == "show":
            write_json(repository.get_case(args.case_id, include_details=args.details))
        elif args.command == "add-revision":
            data = read_json(args.input)
            kwargs = {"record": data} if args.record else {"payload": data}
            write_json(repository.add_revision(args.case_id, created_by=args.created_by, change_note=args.change_note, **kwargs))
        elif args.command == "add-review":
            write_json(repository.add_review_event(
                args.case_id, event_type=args.event_type, revision_id=args.revision_id,
                author_id=args.author_id, author_name=args.author_name, body=args.body,
            ))
        elif args.command == "archive":
            write_json(repository.archive_case(args.case_id))
        elif args.command == "restore":
            write_json(repository.restore_case(args.case_id))
        elif args.command == "export":
            bundle = repository.export_case_bundle(args.case_id, exported_at=args.exported_at)
            write_json(bundle, args.output)
            print(f"Wrote {args.output}", file=sys.stderr)
        elif args.command == "import":
            write_json(repository.import_case_bundle(read_json(args.input)))
        elif args.command == "save-view":
            write_json(repository.save_view(name=args.name, owner_id=args.owner_id, filters=read_json(args.filters)))
        elif args.command == "create-template":
            write_json(repository.create_review_template(
                name=args.name, description=args.description,
                stages=read_json(args.stages) if args.stages else None,
                default_due_days=args.default_due_days, escalation_days=args.escalation_days,
                created_by=args.created_by, actor_role=args.actor_role,
            ))
        elif args.command == "list-templates":
            active = None if args.active == "all" else args.active == "true"
            values = repository.list_review_templates(active=active)
            write_json({"review_templates": values, "count": len(values)})
        elif args.command == "start-governance":
            write_json(repository.start_governance_workflow(
                args.case_id, revision_id=args.revision_id, template_id=args.template_id,
                template_snapshot=read_json(args.template) if args.template else None,
                started_at=args.started_at, due_at=args.due_at, created_by=args.created_by,
                actor_role=args.actor_role,
            ))
        elif args.command == "assign-review":
            write_json(repository.assign_reviewer(
                args.workflow_id, stage=args.stage, reviewer_id=args.reviewer_id,
                reviewer_name=args.reviewer_name, reviewer_role=args.reviewer_role,
                required=not args.optional, instructions=args.instructions, due_at=args.due_at,
                created_by=args.created_by, actor_role=args.actor_role,
            ))
        elif args.command == "assignment-status":
            write_json(repository.update_review_assignment_status(
                args.assignment_id, status=args.status, actor_id=args.actor_id,
                actor_role=args.actor_role, changed_at=args.changed_at,
            ))
        elif args.command == "decide":
            write_json(repository.add_governance_decision(
                args.workflow_id, stage=args.stage, disposition=args.disposition,
                decided_by=args.decided_by, decided_by_name=args.decided_by_name,
                decider_role=args.decider_role, rationale=args.rationale,
                assignment_id=args.assignment_id, conditions=args.condition,
                required_wording=args.required_wording,
                publication_restrictions=args.publication_restriction,
                disclosures=args.disclosure, valid_until=args.valid_until,
                reassessment_at=args.reassessment_at,
                supersedes_decision_id=args.supersedes_decision_id,
                decided_at=args.decided_at,
            ))
        elif args.command == "governance-queue":
            write_json(repository.governance_queue(reviewer_id=args.reviewer_id, at=args.at))
        elif args.command == "reassessment-due":
            values = repository.list_reassessment_due(at=args.at)
            write_json({"workflows": values, "count": len(values)})
        elif args.command == "capture-snapshot":
            write_json(repository.capture_monitoring_snapshot(
                args.case_id, revision_id=args.revision_id, captured_at=args.captured_at, trigger=args.trigger,
            ))
        elif args.command == "compare-snapshots":
            write_json(repository.compare_snapshots(
                args.from_snapshot_id, args.to_snapshot_id, compared_at=args.compared_at,
            ))
        elif args.command == "create-watch":
            write_json(repository.create_watchlist(
                args.case_id, name=args.name, cadence=args.cadence,
                trigger_types=args.trigger_type or None, source_ids=args.source_id,
                next_check_at=args.next_check_at, created_by=args.created_by, notes=args.notes,
            ))
        elif args.command == "list-watches":
            values = repository.list_watchlists(case_id=args.case_id, status=args.status, due_at=args.due_at)
            write_json({"watchlists": values, "count": len(values)})
        elif args.command == "check-watch":
            write_json(repository.run_watchlist_check(
                args.watch_id, revision_id=args.revision_id, checked_at=args.checked_at, trigger=args.trigger,
            ))
        elif args.command == "list-alerts":
            values = repository.list_monitoring_alerts(
                case_id=args.case_id, watch_id=args.watch_id, status=args.status, severity=args.severity,
            )
            write_json({"monitoring_alerts": values, "count": len(values)})
        elif args.command == "alert-status":
            write_json(repository.update_monitoring_alert_status(
                args.alert_id, status=args.status, actor_id=args.actor_id, changed_at=args.changed_at,
            ))
        elif args.command == "timeline":
            write_json(repository.case_timeline(args.case_id))
        elif args.command == "ingest-site-intelligence":
            write_json(repository.ingest_site_intelligence_event(read_json(args.input), ingested_at=args.ingested_at))
        elif args.command == "add-stakeholder-actor":
            write_json(repository.add_stakeholder_actor(args.case_id, read_json(args.input)))
        elif args.command == "add-stakeholder-relationship":
            write_json(repository.add_stakeholder_relationship(args.case_id, read_json(args.input)))
        elif args.command == "add-stakeholder-incentive":
            write_json(repository.add_stakeholder_incentive(args.case_id, read_json(args.input)))
        elif args.command == "add-stakeholder-pressure":
            write_json(repository.add_stakeholder_pressure(args.case_id, read_json(args.input)))
        elif args.command == "add-stakeholder-consequence":
            write_json(repository.add_stakeholder_consequence(args.case_id, read_json(args.input)))
        elif args.command == "stakeholder-intelligence":
            write_json(repository.get_stakeholder_intelligence(args.case_id, generated_at=args.generated_at))
        elif args.command == "import-catalyst-canvas":
            write_json(repository.import_catalyst_canvas_stakeholders(args.case_id, read_json(args.input), imported_at=args.imported_at))
        else:  # pragma: no cover
            raise AssertionError(args.command)
    finally:
        repository.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
