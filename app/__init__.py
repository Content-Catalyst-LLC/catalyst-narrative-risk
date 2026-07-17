"""Flask API for the canonical engine and persistent review workspaces."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request

from narrative_risk.contracts import contract_definition, controlled_vocabularies, current_method_snapshot, sha256_digest
from narrative_risk.integrations import import_catalyst_data_source, import_knowledge_library_source
from narrative_risk.migrations import (
    migrate_record, migrate_v1_0_1_record, migrate_v1_1_0_record, migrate_v1_2_0_record, migrate_v1_3_0_record, migrate_v1_4_0_record, migrate_v1_5_0_record, migrate_v1_6_0_record,
)
from narrative_risk.service import (
    VERSION,
    NarrativeRiskValidationError,
    build_narrative_risk_record,
    score_narrative_risk,
    validate_narrative_risk_record,
    verify_record_reproducibility,
)
from narrative_risk.workspaces import SQLiteCaseRepository


def _json_object():
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        raise NarrativeRiskValidationError("request body must be a JSON object")
    return payload


def _bad_request(error_code: str, exc: Exception):
    return jsonify({"error": error_code, "message": str(exc)}), 400


def _bool_query(name: str, default: bool = False) -> bool:
    raw = request.args.get(name)
    if raw is None:
        return default
    if raw.lower() in {"1", "true", "yes"}:
        return True
    if raw.lower() in {"0", "false", "no"}:
        return False
    raise NarrativeRiskValidationError(f"{name} must be true or false")


def _int_query(name: str, default: int) -> int:
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise NarrativeRiskValidationError(f"{name} must be an integer") from exc


def create_app(config: dict | None = None):
    app = Flask(__name__)
    default_db = os.environ.get(
        "CNRISK_DATABASE_PATH",
        str(Path(app.instance_path) / "catalyst-narrative-risk.sqlite3"),
    )
    app.config.update(NARRATIVE_RISK_DATABASE=default_db)
    if config:
        app.config.update(config)
    repository = SQLiteCaseRepository(app.config["NARRATIVE_RISK_DATABASE"])
    app.extensions["narrative_risk_repository"] = repository

    @app.get("/healthz")
    def healthz():
        return {
            "ok": True,
            "version": VERSION,
            "contract_id": "urn:catalyst:narrative-risk:contract:canonical",
            "contract_version": VERSION,
            "evidence_ledger": True,
            "persistent_cases": True,
            "narrative_mapping": True,
            "governance_workflow": True,
            "narrative_monitoring": True,
            "site_intelligence_handoff": True,
            "stakeholder_intelligence": True,
            "catalyst_canvas_handoff": True,
            "workspace": repository.health(),
        }, 200

    @app.get("/api/narrative-risk/contract")
    def narrative_risk_contract():
        return jsonify(contract_definition()), 200

    @app.get("/api/narrative-risk/vocabularies")
    def narrative_risk_vocabularies():
        return jsonify(controlled_vocabularies()), 200

    @app.get("/api/narrative-risk/methods/current")
    def narrative_risk_method():
        method = current_method_snapshot()
        return jsonify({"method_snapshot": method, "method_snapshot_sha256": sha256_digest(method)}), 200

    @app.post("/api/narrative-risk")
    def narrative_risk_api():
        try:
            record = build_narrative_risk_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_narrative_risk_input", exc)
        return jsonify(record), 200

    @app.post("/api/narrative-risk/ledger/analyze")
    def narrative_risk_ledger_analyze():
        try:
            analysis = score_narrative_risk(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_evidence_ledger_input", exc)
        return jsonify(analysis), 200

    @app.post("/api/narrative-risk/map/analyze")
    def narrative_risk_map_analyze():
        try:
            analysis = score_narrative_risk(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_narrative_map_input", exc)
        return jsonify({"narrative_map": analysis["narrative_map"], "interpretation": analysis["interpretation"]}), 200

    @app.post("/api/narrative-risk/verify")
    def narrative_risk_verify():
        try:
            record = _json_object()
            validate_narrative_risk_record(record)
            report = verify_record_reproducibility(record)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_narrative_risk_record", exc)
        return jsonify(report), 200

    @app.post("/api/narrative-risk/migrate")
    def narrative_risk_migrate_auto():
        try:
            migrated = migrate_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_legacy_narrative_risk_record", exc)
        return jsonify(migrated), 200

    @app.post("/api/narrative-risk/migrate/v1.0.1")
    def narrative_risk_migrate_v101():
        try:
            migrated = migrate_v1_0_1_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_legacy_narrative_risk_record", exc)
        return jsonify(migrated), 200

    @app.post("/api/narrative-risk/migrate/v1.1.0")
    def narrative_risk_migrate_v110():
        try:
            migrated = migrate_v1_1_0_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_legacy_narrative_risk_record", exc)
        return jsonify(migrated), 200

    @app.post("/api/narrative-risk/migrate/v1.2.0")
    def narrative_risk_migrate_v120():
        try:
            migrated = migrate_v1_2_0_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_legacy_narrative_risk_record", exc)
        return jsonify(migrated), 200

    @app.post("/api/narrative-risk/migrate/v1.3.0")
    def narrative_risk_migrate_v130():
        try:
            migrated = migrate_v1_3_0_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_legacy_narrative_risk_record", exc)
        return jsonify(migrated), 200

    @app.post("/api/narrative-risk/migrate/v1.4.0")
    def narrative_risk_migrate_v140():
        try:
            migrated = migrate_v1_4_0_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_legacy_narrative_risk_record", exc)
        return jsonify(migrated), 200


    @app.post("/api/narrative-risk/migrate/v1.5.0")
    def narrative_risk_migrate_v150():
        try:
            migrated = migrate_v1_5_0_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_legacy_narrative_risk_record", exc)
        return jsonify(migrated), 200

    @app.post("/api/narrative-risk/migrate/v1.6.0")
    def narrative_risk_migrate_v160():
        try:
            migrated = migrate_v1_6_0_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_legacy_narrative_risk_record", exc)
        return jsonify(migrated), 200

    @app.post("/api/narrative-risk/import/knowledge-library")
    def narrative_risk_import_knowledge_library():
        try:
            source = import_knowledge_library_source(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_knowledge_library_handoff", exc)
        return jsonify({"source": source}), 200

    @app.post("/api/narrative-risk/import/catalyst-data")
    def narrative_risk_import_catalyst_data():
        try:
            source = import_catalyst_data_source(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_catalyst_data_handoff", exc)
        return jsonify({"source": source}), 200

    @app.get("/api/narrative-risk/workspaces/health")
    def workspace_health():
        return jsonify(repository.health()), 200

    @app.post("/api/narrative-risk/cases")
    def create_case():
        try:
            payload = _json_object()
            allowed = {
                "title", "summary", "organization_id", "project_id", "status", "priority",
                "tags", "case_id", "created_at", "initial_payload", "created_by", "change_note",
            }
            unknown = sorted(set(payload) - allowed)
            if unknown:
                raise NarrativeRiskValidationError(f"unsupported case field(s): {', '.join(unknown)}")
            case = repository.create_case(**payload)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_case", exc)
        return jsonify(case), 201

    @app.get("/api/narrative-risk/cases")
    def list_cases():
        try:
            tags = [value.strip() for value in request.args.get("tags", "").split(",") if value.strip()]
            cases = repository.list_cases(
                query=request.args.get("query", ""),
                organization_id=request.args.get("organization_id"),
                project_id=request.args.get("project_id"),
                status=request.args.get("status"),
                priority=request.args.get("priority"),
                tags=tags,
                archived=_bool_query("archived", False),
                limit=_int_query("limit", 100),
                offset=_int_query("offset", 0),
            )
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_case_query", exc)
        return jsonify({"cases": cases, "count": len(cases)}), 200

    @app.get("/api/narrative-risk/cases/<case_id>")
    def get_case(case_id: str):
        try:
            case = repository.get_case(case_id, include_details=_bool_query("include_details", True))
        except NarrativeRiskValidationError as exc:
            return _bad_request("case_not_found", exc)
        return jsonify(case), 200

    @app.patch("/api/narrative-risk/cases/<case_id>")
    def update_case(case_id: str):
        try:
            case = repository.update_case(case_id, _json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_case_update", exc)
        return jsonify(case), 200

    @app.post("/api/narrative-risk/cases/<case_id>/archive")
    def archive_case(case_id: str):
        try:
            payload = request.get_json(silent=True) or {}
            if not isinstance(payload, dict):
                raise NarrativeRiskValidationError("request body must be a JSON object")
            case = repository.archive_case(case_id, archived_at=payload.get("archived_at"))
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_case_archive", exc)
        return jsonify(case), 200

    @app.post("/api/narrative-risk/cases/<case_id>/restore")
    def restore_case(case_id: str):
        try:
            case = repository.restore_case(case_id)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_case_restore", exc)
        return jsonify(case), 200

    @app.post("/api/narrative-risk/cases/<case_id>/revisions")
    def add_revision(case_id: str):
        try:
            payload = _json_object()
            allowed = {"record", "payload", "human_decision", "created_by", "change_note", "revision_id", "created_at"}
            unknown = sorted(set(payload) - allowed)
            if unknown:
                raise NarrativeRiskValidationError(f"unsupported revision field(s): {', '.join(unknown)}")
            revision = repository.add_revision(case_id, **payload)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_case_revision", exc)
        return jsonify(revision), 201

    @app.post("/api/narrative-risk/cases/<case_id>/reviews")
    def add_review(case_id: str):
        try:
            event = repository.add_review_event(case_id, **_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_review_event", exc)
        return jsonify(event), 201

    @app.get("/api/narrative-risk/cases/<case_id>/export")
    def export_case(case_id: str):
        try:
            bundle = repository.export_case_bundle(case_id, exported_at=request.args.get("exported_at"))
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_case_export", exc)
        return jsonify(bundle), 200

    @app.post("/api/narrative-risk/cases/import")
    def import_case():
        try:
            result = repository.import_case_bundle(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_case_bundle", exc)
        return jsonify(result), 201

    @app.post("/api/narrative-risk/review-templates")
    def create_review_template():
        try:
            template = repository.create_review_template(**_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_review_template", exc)
        return jsonify(template), 201

    @app.get("/api/narrative-risk/review-templates")
    def list_review_templates():
        try:
            active_raw = request.args.get("active")
            active = None if active_raw is None else _bool_query("active")
            templates = repository.list_review_templates(active=active)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_review_template_query", exc)
        return jsonify({"review_templates": templates, "count": len(templates)}), 200

    @app.post("/api/narrative-risk/cases/<case_id>/governance")
    def start_governance(case_id: str):
        try:
            workflow = repository.start_governance_workflow(case_id, **_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_governance_workflow", exc)
        return jsonify(workflow), 201

    @app.get("/api/narrative-risk/cases/<case_id>/governance")
    def get_case_governance(case_id: str):
        try:
            workflow = repository.get_case_governance_workflow(
                case_id, include_details=_bool_query("include_details", True), at=request.args.get("at")
            )
            if workflow is None:
                raise NarrativeRiskValidationError("case does not have a governance workflow")
        except NarrativeRiskValidationError as exc:
            return _bad_request("governance_workflow_not_found", exc)
        return jsonify(workflow), 200

    @app.post("/api/narrative-risk/governance/<workflow_id>/assignments")
    def create_review_assignment(workflow_id: str):
        try:
            assignment = repository.assign_reviewer(workflow_id, **_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_review_assignment", exc)
        return jsonify(assignment), 201

    @app.patch("/api/narrative-risk/governance/assignments/<assignment_id>")
    def update_review_assignment(assignment_id: str):
        try:
            assignment = repository.update_review_assignment_status(assignment_id, **_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_review_assignment_update", exc)
        return jsonify(assignment), 200

    @app.get("/api/narrative-risk/governance/queue")
    def governance_queue():
        try:
            queue = repository.governance_queue(reviewer_id=request.args.get("reviewer_id"), at=request.args.get("at"))
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_governance_queue", exc)
        return jsonify(queue), 200

    @app.post("/api/narrative-risk/governance/<workflow_id>/decisions")
    def create_governance_decision(workflow_id: str):
        try:
            decision = repository.add_governance_decision(workflow_id, **_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_governance_decision", exc)
        return jsonify(decision), 201

    @app.get("/api/narrative-risk/governance/reassessment-due")
    def governance_reassessment_due():
        try:
            workflows = repository.list_reassessment_due(at=request.args.get("at"))
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_reassessment_query", exc)
        return jsonify({"workflows": workflows, "count": len(workflows)}), 200


    @app.post("/api/narrative-risk/cases/<case_id>/stakeholders/actors")
    def add_stakeholder_actor(case_id: str):
        try: value = repository.add_stakeholder_actor(case_id, _json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_stakeholder_actor", exc)
        return jsonify(value), 201

    @app.get("/api/narrative-risk/cases/<case_id>/stakeholders/actors")
    def list_stakeholder_actors(case_id: str):
        try: values = repository.list_stakeholder_actors(case_id)
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_stakeholder_query", exc)
        return jsonify({"stakeholder_actors": values, "count": len(values)}), 200

    @app.post("/api/narrative-risk/cases/<case_id>/stakeholders/relationships")
    def add_stakeholder_relationship(case_id: str):
        try: value = repository.add_stakeholder_relationship(case_id, _json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_stakeholder_relationship", exc)
        return jsonify(value), 201

    @app.post("/api/narrative-risk/cases/<case_id>/stakeholders/incentives")
    def add_stakeholder_incentive(case_id: str):
        try: value = repository.add_stakeholder_incentive(case_id, _json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_stakeholder_incentive", exc)
        return jsonify(value), 201

    @app.post("/api/narrative-risk/cases/<case_id>/stakeholders/pressures")
    def add_stakeholder_pressure(case_id: str):
        try: value = repository.add_stakeholder_pressure(case_id, _json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_stakeholder_pressure", exc)
        return jsonify(value), 201

    @app.post("/api/narrative-risk/cases/<case_id>/stakeholders/consequences")
    def add_stakeholder_consequence(case_id: str):
        try: value = repository.add_stakeholder_consequence(case_id, _json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_stakeholder_consequence", exc)
        return jsonify(value), 201

    @app.get("/api/narrative-risk/cases/<case_id>/stakeholder-intelligence")
    def stakeholder_intelligence(case_id: str):
        try: value = repository.get_stakeholder_intelligence(case_id, generated_at=request.args.get("generated_at"))
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_stakeholder_intelligence", exc)
        return jsonify(value), 200

    @app.post("/api/narrative-risk/cases/<case_id>/import/catalyst-canvas")
    def import_catalyst_canvas(case_id: str):
        try: value = repository.import_catalyst_canvas_stakeholders(case_id, _json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_catalyst_canvas_handoff", exc)
        return jsonify(value), 201

    @app.post("/api/narrative-risk/cases/<case_id>/monitoring/snapshots")
    def capture_monitoring_snapshot(case_id: str):
        try:
            payload = request.get_json(silent=True) or {}
            if not isinstance(payload, dict):
                raise NarrativeRiskValidationError("request body must be a JSON object")
            snapshot = repository.capture_monitoring_snapshot(case_id, **payload)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_monitoring_snapshot", exc)
        return jsonify(snapshot), 201

    @app.get("/api/narrative-risk/cases/<case_id>/monitoring/snapshots")
    def list_monitoring_snapshots(case_id: str):
        try:
            values = repository.list_monitoring_snapshots(case_id)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_monitoring_snapshot_query", exc)
        return jsonify({"monitoring_snapshots": values, "count": len(values)}), 200

    @app.post("/api/narrative-risk/monitoring/compare")
    def compare_monitoring_snapshots_api():
        try:
            payload = _json_object()
            comparison = repository.compare_snapshots(
                payload.get("from_snapshot_id"), payload.get("to_snapshot_id"),
                compared_at=payload.get("compared_at"), comparison_id=payload.get("comparison_id"),
            )
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_monitoring_comparison", exc)
        return jsonify(comparison), 201

    @app.post("/api/narrative-risk/cases/<case_id>/watchlists")
    def create_watchlist(case_id: str):
        try:
            watch = repository.create_watchlist(case_id, **_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_watchlist", exc)
        return jsonify(watch), 201

    @app.get("/api/narrative-risk/cases/<case_id>/watchlists")
    def list_case_watchlists(case_id: str):
        try:
            values = repository.list_watchlists(case_id=case_id, status=request.args.get("status"))
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_watchlist_query", exc)
        return jsonify({"watchlists": values, "count": len(values)}), 200

    @app.patch("/api/narrative-risk/watchlists/<watch_id>")
    def update_watchlist(watch_id: str):
        try:
            watch = repository.update_watchlist(watch_id, _json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_watchlist_update", exc)
        return jsonify(watch), 200

    @app.post("/api/narrative-risk/watchlists/<watch_id>/check")
    def run_watchlist_check(watch_id: str):
        try:
            payload = request.get_json(silent=True) or {}
            if not isinstance(payload, dict):
                raise NarrativeRiskValidationError("request body must be a JSON object")
            result = repository.run_watchlist_check(watch_id, **payload)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_watchlist_check", exc)
        return jsonify(result), 200

    @app.get("/api/narrative-risk/monitoring/alerts")
    def list_monitoring_alerts():
        try:
            values = repository.list_monitoring_alerts(
                case_id=request.args.get("case_id"), watch_id=request.args.get("watch_id"),
                status=request.args.get("status"), severity=request.args.get("severity"),
            )
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_monitoring_alert_query", exc)
        return jsonify({"monitoring_alerts": values, "count": len(values)}), 200

    @app.patch("/api/narrative-risk/monitoring/alerts/<alert_id>")
    def update_monitoring_alert(alert_id: str):
        try:
            alert = repository.update_monitoring_alert_status(alert_id, **_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_monitoring_alert_update", exc)
        return jsonify(alert), 200

    @app.get("/api/narrative-risk/cases/<case_id>/timeline")
    def case_timeline(case_id: str):
        try:
            timeline = repository.case_timeline(case_id)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_case_timeline", exc)
        return jsonify(timeline), 200

    @app.post("/api/narrative-risk/monitoring/site-intelligence")
    def ingest_site_intelligence_event():
        try:
            result = repository.ingest_site_intelligence_event(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_site_intelligence_handoff", exc)
        return jsonify(result), 201

    @app.post("/api/narrative-risk/saved-views")
    def create_saved_view():
        try:
            view = repository.save_view(**_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_saved_view", exc)
        return jsonify(view), 201

    @app.get("/api/narrative-risk/saved-views")
    def list_saved_views():
        try:
            views = repository.list_saved_views(owner_id=request.args.get("owner_id"))
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_saved_view_query", exc)
        return jsonify({"saved_views": views, "count": len(views)}), 200

    return app
