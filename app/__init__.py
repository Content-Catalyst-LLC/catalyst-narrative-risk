"""Flask API for the canonical engine and persistent review workspaces."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request

from narrative_risk.contracts import contract_definition, controlled_vocabularies, current_method_snapshot, sha256_digest
from narrative_risk.integrations import import_catalyst_data_source, import_knowledge_library_source
from narrative_risk.migrations import (
    migrate_record, migrate_v1_0_1_record, migrate_v1_1_0_record, migrate_v1_2_0_record, migrate_v1_3_0_record, migrate_v1_4_0_record, migrate_v1_5_0_record, migrate_v1_6_0_record, migrate_v1_7_0_record, migrate_v1_8_0_record, migrate_v1_9_0_record,
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
from narrative_risk.hardening import (
    audit_wordpress_accessibility, build_production_readiness_report,
    build_security_readiness_report,
)


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
    raw_origins = os.environ.get("NARRATIVE_RISK_ALLOWED_ORIGINS", "")
    app.config.update(
        NARRATIVE_RISK_DATABASE=default_db,
        NARRATIVE_RISK_ENVIRONMENT=os.environ.get("NARRATIVE_RISK_ENVIRONMENT", "development"),
        NARRATIVE_RISK_REQUIRE_API_KEY=os.environ.get("NARRATIVE_RISK_REQUIRE_API_KEY", "").lower() in {"1", "true", "yes"},
        NARRATIVE_RISK_ADMIN_TOKEN=os.environ.get("NARRATIVE_RISK_ADMIN_TOKEN"),
        NARRATIVE_RISK_ALLOWED_ORIGINS=[value.strip() for value in raw_origins.split(",") if value.strip()],
        NARRATIVE_RISK_ENFORCE_HTTPS=os.environ.get("NARRATIVE_RISK_ENFORCE_HTTPS", "").lower() in {"1", "true", "yes"},
        NARRATIVE_RISK_SECURE_HEADERS=True,
        NARRATIVE_RISK_BACKUP_DIRECTORY=os.environ.get("NARRATIVE_RISK_BACKUP_DIRECTORY"),
        NARRATIVE_RISK_RETENTION_POLICY_CONFIGURED=os.environ.get("NARRATIVE_RISK_RETENTION_POLICY_CONFIGURED", "").lower() in {"1", "true", "yes"},
        NARRATIVE_RISK_ENCRYPTION_AT_REST_ATTESTED=os.environ.get("NARRATIVE_RISK_ENCRYPTION_AT_REST_ATTESTED", "").lower() in {"1", "true", "yes"},
        MAX_CONTENT_LENGTH=int(os.environ.get("NARRATIVE_RISK_MAX_CONTENT_LENGTH", "1048576")),
        SESSION_COOKIE_SECURE=os.environ.get("NARRATIVE_RISK_SESSION_COOKIE_SECURE", "").lower() in {"1", "true", "yes"},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)
    repository = SQLiteCaseRepository(app.config["NARRATIVE_RISK_DATABASE"])
    app.extensions["narrative_risk_repository"] = repository

    def _security_config_snapshot():
        token = app.config.get("NARRATIVE_RISK_ADMIN_TOKEN") or ""
        try:
            retention_configured = bool(repository.list_privacy_policies(status="active"))
        except Exception:
            retention_configured = bool(app.config.get("NARRATIVE_RISK_RETENTION_POLICY_CONFIGURED"))
        return {
            "environment": app.config.get("NARRATIVE_RISK_ENVIRONMENT", "development"),
            "debug": bool(app.debug),
            "require_api_key": bool(app.config.get("NARRATIVE_RISK_REQUIRE_API_KEY")),
            "admin_token_length": len(token),
            "enforce_https": bool(app.config.get("NARRATIVE_RISK_ENFORCE_HTTPS")),
            "secure_headers": bool(app.config.get("NARRATIVE_RISK_SECURE_HEADERS", True)),
            "allowed_origins": list(app.config.get("NARRATIVE_RISK_ALLOWED_ORIGINS") or []),
            "max_content_length": int(app.config.get("MAX_CONTENT_LENGTH") or 0),
            "database_path": app.config.get("NARRATIVE_RISK_DATABASE"),
            "backup_directory": app.config.get("NARRATIVE_RISK_BACKUP_DIRECTORY"),
            "retention_policy_configured": retention_configured,
            "encryption_at_rest_attested": bool(app.config.get("NARRATIVE_RISK_ENCRYPTION_AT_REST_ATTESTED")),
            "cookie_secure": bool(app.config.get("SESSION_COOKIE_SECURE")),
        }

    @app.before_request
    def enforce_transport_and_content_type():
        if app.config.get("NARRATIVE_RISK_ENFORCE_HTTPS"):
            forwarded = request.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip().lower()
            if not request.is_secure and forwarded != "https":
                return jsonify({"error": "https_required", "message": "HTTPS is required"}), 400
        if request.method in {"POST", "PUT", "PATCH"} and request.path.startswith("/api/"):
            if request.content_length and request.content_length > int(app.config.get("MAX_CONTENT_LENGTH") or 0):
                return jsonify({"error": "request_too_large", "message": "Request body exceeds the configured limit"}), 413
            if request.content_length and not request.is_json:
                return jsonify({"error": "json_required", "message": "Content-Type: application/json is required"}), 415
        origin = request.headers.get("Origin")
        allowed = app.config.get("NARRATIVE_RISK_ALLOWED_ORIGINS") or []
        if origin and request.path.startswith("/api/") and allowed and origin not in allowed:
            return jsonify({"error": "origin_denied", "message": "Origin is not allowed"}), 403

    @app.after_request
    def harden_response(response):
        if app.config.get("NARRATIVE_RISK_SECURE_HEADERS", True):
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
            if request.is_secure or app.config.get("NARRATIVE_RISK_ENFORCE_HTTPS"):
                response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        origin = request.headers.get("Origin")
        allowed = app.config.get("NARRATIVE_RISK_ALLOWED_ORIGINS") or []
        if origin and origin in allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-CNRISK-Admin-Token, Idempotency-Key"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, OPTIONS"
        return response

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "request_too_large", "message": "Request body exceeds the configured limit"}), 413

    def require_scope(scope: str):
        if not app.config.get("NARRATIVE_RISK_REQUIRE_API_KEY"):
            return None
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "api_key_required", "message": "Authorization: Bearer API key is required"}), 401
        try:
            repository.authenticate_api_key(header[7:].strip(), scope)
        except NarrativeRiskValidationError as exc:
            status = 429 if "rate limit" in str(exc).lower() else 403
            return jsonify({"error": "api_key_denied", "message": str(exc)}), status
        return None

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
            "comparative_analysis": True,
            "publication_briefings": True,
            "public_embeds": True,
            "scoped_api_keys": True,
            "platform_publication_handoffs": True,
            "production_hardening": True,
            "privacy_retention": True,
            "verified_backups": True,
            "accessibility_audits": True,
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

    @app.post("/api/narrative-risk/migrate/v1.7.0")
    def narrative_risk_migrate_v170():
        try:
            migrated = migrate_v1_7_0_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_legacy_narrative_risk_record", exc)
        return jsonify(migrated), 200

    @app.post("/api/narrative-risk/migrate/v1.8.0")
    def narrative_risk_migrate_v180():
        try:
            migrated = migrate_v1_8_0_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_legacy_narrative_risk_record", exc)
        return jsonify(migrated), 200


    @app.post("/api/narrative-risk/migrate/v1.9.0")
    def narrative_risk_migrate_v190():
        try:
            migrated = migrate_v1_9_0_record(_json_object())
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

    @app.get("/api/narrative-risk/openapi.json")
    def narrative_risk_openapi():
        paths = {
            "/api/narrative-risk/cases/{case_id}/briefings": {"post": {"summary": "Create a governance-aware briefing", "security": [{"bearerAuth": ["publication:write"]}]}},
            "/api/narrative-risk/briefings/{briefing_id}/packages": {"post": {"summary": "Create a multi-format publication package", "security": [{"bearerAuth": ["publication:write"]}]}},
            "/api/narrative-risk/packages/{package_id}/artifacts/{format}": {"get": {"summary": "Read a publication artifact", "security": [{"bearerAuth": ["publication:read"]}]}},
            "/api/narrative-risk/packages/{package_id}/embeds": {"post": {"summary": "Create a public embed", "security": [{"bearerAuth": ["embeds:write"]}]}},
            "/api/narrative-risk/packages/{package_id}/handoffs": {"post": {"summary": "Create a platform publication handoff", "security": [{"bearerAuth": ["handoffs:write"]}]}},
        }
        return jsonify({"openapi": "3.1.0", "info": {"title": "Catalyst Narrative Risk API", "version": VERSION}, "paths": paths, "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}}}), 200

    @app.post("/api/narrative-risk/api-keys")
    def create_api_key():
        admin_token = app.config.get("NARRATIVE_RISK_ADMIN_TOKEN")
        if admin_token and request.headers.get("X-CNRISK-Admin-Token") != admin_token:
            return jsonify({"error": "admin_token_required", "message": "A valid administrator token is required"}), 403
        try:
            result = repository.create_api_key(**_json_object())
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_api_key", exc)
        return jsonify(result), 201

    @app.get("/api/narrative-risk/api-keys")
    def list_api_keys():
        denied = require_scope("admin")
        if denied: return denied
        return jsonify({"api_keys": repository.list_api_keys(), "count": len(repository.list_api_keys())}), 200

    @app.post("/api/narrative-risk/api-keys/<api_key_id>/revoke")
    def revoke_api_key(api_key_id: str):
        denied = require_scope("admin")
        if denied: return denied
        try:
            value = repository.revoke_api_key(api_key_id)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_api_key_revocation", exc)
        return jsonify(value), 200

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

    @app.post("/api/narrative-risk/cases/<case_id>/comparisons")
    def create_comparison_set(case_id: str):
        try: value = repository.create_comparison_set(case_id, _json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_comparison_set", exc)
        return jsonify(value), 201

    @app.get("/api/narrative-risk/cases/<case_id>/comparisons")
    def list_comparison_sets(case_id: str):
        try: values = repository.list_comparison_sets(case_id=case_id, status=request.args.get("status"))
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_comparison_query", exc)
        return jsonify({"comparison_sets": values, "count": len(values)}), 200

    @app.post("/api/narrative-risk/comparisons/<comparison_id>/evidence-matrix")
    def generate_comparative_evidence_matrix(comparison_id: str):
        try: value = repository.generate_comparative_evidence_matrix(comparison_id, **_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_comparative_evidence_matrix", exc)
        return jsonify(value), 201

    @app.post("/api/narrative-risk/comparisons/<comparison_id>/scenarios")
    def create_scenario(comparison_id: str):
        try: value = repository.create_scenario(comparison_id, _json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_scenario", exc)
        return jsonify(value), 201

    @app.get("/api/narrative-risk/comparisons/<comparison_id>/scenarios")
    def list_scenarios(comparison_id: str):
        try: values = repository.list_scenarios(comparison_id=comparison_id, status=request.args.get("status"))
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_scenario_query", exc)
        return jsonify({"scenarios": values, "count": len(values)}), 200

    @app.post("/api/narrative-risk/scenarios/<scenario_id>/evaluate")
    def evaluate_scenario_api(scenario_id: str):
        try: value = repository.evaluate_scenario(scenario_id, **_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_scenario_evaluation", exc)
        return jsonify(value), 201

    @app.post("/api/narrative-risk/comparisons/<comparison_id>/sensitivity")
    def run_comparative_sensitivity(comparison_id: str):
        try: value = repository.run_comparative_sensitivity(comparison_id, **_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_sensitivity_analysis", exc)
        return jsonify(value), 201

    @app.get("/api/narrative-risk/cases/<case_id>/comparative-portfolio")
    def comparative_portfolio(case_id: str):
        try: value = repository.get_comparative_portfolio(case_id, generated_at=request.args.get("generated_at"))
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_comparative_portfolio", exc)
        return jsonify(value), 200

    @app.post("/api/narrative-risk/comparisons/<comparison_id>/decision-studio-handoff")
    def decision_studio_handoff(comparison_id: str):
        try: value = repository.create_decision_studio_handoff(comparison_id, **_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_decision_studio_handoff", exc)
        return jsonify(value), 201

    @app.post("/api/narrative-risk/cases/<case_id>/briefings")
    def create_publication_briefing(case_id: str):
        denied = require_scope("publication:write")
        if denied: return denied
        try: value = repository.create_publication_briefing(case_id, **_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_publication_briefing", exc)
        return jsonify(value), 201

    @app.get("/api/narrative-risk/cases/<case_id>/briefings")
    def list_publication_briefings(case_id: str):
        denied = require_scope("publication:read")
        if denied: return denied
        try: values = repository.list_publication_briefings(case_id)
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_publication_query", exc)
        return jsonify({"publication_briefings": values, "count": len(values)}), 200

    @app.post("/api/narrative-risk/briefings/<briefing_id>/packages")
    def create_publication_package(briefing_id: str):
        denied = require_scope("publication:write")
        if denied: return denied
        try: value = repository.create_publication_package(briefing_id, **_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_publication_package", exc)
        return jsonify(value), 201

    @app.get("/api/narrative-risk/cases/<case_id>/publications")
    def list_publication_packages(case_id: str):
        denied = require_scope("publication:read")
        if denied: return denied
        try:
            values = repository.list_publication_packages(case_id, status=request.args.get("status"))
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_publication_query", exc)
        return jsonify({"publication_packages": values, "count": len(values)}), 200

    @app.get("/api/narrative-risk/cases/<case_id>/embeds")
    def list_public_embeds(case_id: str):
        denied = require_scope("embeds:read")
        if denied: return denied
        try:
            values = repository.list_public_embeds(case_id)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_embed_query", exc)
        return jsonify({"public_embeds": values, "count": len(values)}), 200

    @app.get("/api/narrative-risk/cases/<case_id>/publication-handoffs")
    def list_platform_handoffs(case_id: str):
        denied = require_scope("publication:read")
        if denied: return denied
        try:
            values = repository.list_platform_handoffs(case_id)
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_platform_handoff_query", exc)
        return jsonify({"platform_handoffs": values, "count": len(values)}), 200

    @app.patch("/api/narrative-risk/packages/<package_id>")
    def update_publication_package(package_id: str):
        denied = require_scope("publication:write")
        if denied: return denied
        try: value = repository.update_publication_package_status(package_id, **_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_publication_package_update", exc)
        return jsonify(value), 200

    @app.get("/api/narrative-risk/packages/<package_id>/artifacts/<format_name>")
    def get_publication_artifact(package_id: str, format_name: str):
        denied = require_scope("publication:read")
        if denied: return denied
        try: value = repository.get_publication_artifact(package_id, format_name)
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_publication_artifact", exc)
        return jsonify(value), 200

    @app.post("/api/narrative-risk/packages/<package_id>/embeds")
    def create_public_embed(package_id: str):
        denied = require_scope("embeds:write")
        if denied: return denied
        try: value = repository.create_public_embed(package_id, **_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_public_embed", exc)
        return jsonify(value), 201

    @app.get("/api/narrative-risk/embed/<slug>")
    def read_public_embed(slug: str):
        try:
            embed = repository.get_public_embed(slug)
            if embed["status"] != "active": raise NarrativeRiskValidationError("public embed is not active")
            package = repository.get_publication_package(embed["package_id"])
            artifact = next((item for item in package["artifacts"] if item["format"] == "html"), package["artifacts"][0])
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_public_embed", exc)
        return jsonify({"embed": embed, "artifact": artifact}), 200

    @app.post("/api/narrative-risk/packages/<package_id>/handoffs")
    def create_platform_handoff(package_id: str):
        denied = require_scope("handoffs:write")
        if denied: return denied
        try: value = repository.create_platform_handoff(package_id, **_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_platform_handoff", exc)
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

    @app.get("/api/narrative-risk/production/security")
    def production_security_report():
        denied = require_scope("admin")
        if denied: return denied
        return jsonify(build_security_readiness_report(_security_config_snapshot())), 200

    @app.get("/api/narrative-risk/production/database")
    def production_database_diagnostics():
        denied = require_scope("admin")
        if denied: return denied
        return jsonify(repository.database_diagnostics()), 200

    @app.get("/api/narrative-risk/production/accessibility")
    def production_accessibility_report():
        denied = require_scope("admin")
        if denied: return denied
        plugin_root = Path(__file__).resolve().parents[1] / "wordpress" / "catalyst-narrative-risk-demo"
        return jsonify(audit_wordpress_accessibility(plugin_root)), 200

    @app.get("/api/narrative-risk/production/performance")
    def production_performance_report():
        denied = require_scope("admin")
        if denied: return denied
        try:
            report = repository.performance_report(case_id=request.args.get("case_id"))
        except NarrativeRiskValidationError as exc:
            return _bad_request("invalid_performance_audit", exc)
        return jsonify(report), 200

    @app.get("/api/narrative-risk/production/readiness")
    def production_readiness_report():
        denied = require_scope("admin")
        if denied: return denied
        security = build_security_readiness_report(_security_config_snapshot())
        plugin_root = Path(__file__).resolve().parents[1] / "wordpress" / "catalyst-narrative-risk-demo"
        accessibility = audit_wordpress_accessibility(plugin_root)
        performance = repository.performance_report(case_id=request.args.get("case_id"))
        backup_verification = None
        manifests = repository.list_backup_manifests()
        if manifests:
            try: backup_verification = repository.verify_database_backup(manifests[0]["backup_id"])
            except NarrativeRiskValidationError: backup_verification = {"verified": False}
        report = build_production_readiness_report(
            security_report=security, accessibility_report=accessibility, performance_report=performance,
            database_diagnostics=repository.database_diagnostics(), backup_verification=backup_verification,
        )
        return jsonify(report), 200

    @app.post("/api/narrative-risk/privacy/policies")
    def create_privacy_policy():
        denied = require_scope("admin")
        if denied: return denied
        try: policy = repository.save_privacy_policy(_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_privacy_policy", exc)
        return jsonify(policy), 201

    @app.get("/api/narrative-risk/privacy/policies")
    def list_privacy_policies():
        denied = require_scope("admin")
        if denied: return denied
        try: values = repository.list_privacy_policies(status=request.args.get("status"))
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_privacy_policy_query", exc)
        return jsonify({"privacy_policies": values, "count": len(values)}), 200

    @app.post("/api/narrative-risk/cases/<case_id>/retention-assessments")
    def create_retention_assessment(case_id: str):
        denied = require_scope("admin")
        if denied: return denied
        try: assessment = repository.assess_case_retention(case_id, **_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_retention_assessment", exc)
        return jsonify(assessment), 201

    @app.get("/api/narrative-risk/cases/<case_id>/retention-assessments")
    def list_retention_assessments(case_id: str):
        denied = require_scope("admin")
        if denied: return denied
        try: values = repository.list_retention_assessments(case_id)
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_retention_assessment_query", exc)
        return jsonify({"retention_assessments": values, "count": len(values)}), 200

    @app.post("/api/narrative-risk/backups")
    def create_database_backup():
        denied = require_scope("admin")
        if denied: return denied
        try:
            payload = _json_object()
            destination = payload.pop("destination_path", None)
            if not destination: raise NarrativeRiskValidationError("destination_path is required")
            backup_dir = app.config.get("NARRATIVE_RISK_BACKUP_DIRECTORY")
            if backup_dir:
                requested = Path(destination).expanduser().resolve(); allowed_root = Path(backup_dir).expanduser().resolve()
                if allowed_root not in requested.parents:
                    raise NarrativeRiskValidationError("backup destination must be inside NARRATIVE_RISK_BACKUP_DIRECTORY")
            manifest = repository.create_database_backup(destination, **payload)
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_backup_request", exc)
        return jsonify(manifest), 201

    @app.get("/api/narrative-risk/backups")
    def list_database_backups():
        denied = require_scope("admin")
        if denied: return denied
        values = repository.list_backup_manifests()
        return jsonify({"backups": values, "count": len(values)}), 200

    @app.post("/api/narrative-risk/backups/<backup_id>/verify")
    def verify_database_backup(backup_id: str):
        denied = require_scope("admin")
        if denied: return denied
        try: report = repository.verify_database_backup(backup_id, **_json_object())
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_backup_verification", exc)
        return jsonify(report), 200

    @app.post("/api/narrative-risk/backups/<backup_id>/restore")
    def restore_database_backup(backup_id: str):
        denied = require_scope("admin")
        if denied: return denied
        try:
            payload = _json_object(); target = payload.pop("target_path", None)
            if not target: raise NarrativeRiskValidationError("target_path is required")
            if Path(target).expanduser().resolve() == Path(repository.database_path).expanduser().resolve():
                raise NarrativeRiskValidationError("in-place restore of the live database is not allowed")
            report = repository.restore_database_backup(backup_id, target, **payload)
        except NarrativeRiskValidationError as exc: return _bad_request("invalid_backup_restore", exc)
        return jsonify(report), 200

    return app
