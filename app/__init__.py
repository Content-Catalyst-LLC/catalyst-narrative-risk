from flask import Flask, jsonify, request

from narrative_risk.contracts import contract_definition, controlled_vocabularies, current_method_snapshot, sha256_digest
from narrative_risk.integrations import import_catalyst_data_source, import_knowledge_library_source
from narrative_risk.migrations import migrate_record, migrate_v1_0_1_record, migrate_v1_1_0_record
from narrative_risk.service import (
    VERSION,
    NarrativeRiskValidationError,
    build_narrative_risk_record,
    score_narrative_risk,
    validate_narrative_risk_record,
    verify_record_reproducibility,
)


def _json_object():
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        raise NarrativeRiskValidationError("request body must be a JSON object")
    return payload


def _bad_request(error_code: str, exc: Exception):
    return jsonify({"error": error_code, "message": str(exc)}), 400


def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return {
            "ok": True,
            "version": VERSION,
            "contract_id": "urn:catalyst:narrative-risk:contract:canonical",
            "contract_version": VERSION,
            "evidence_ledger": True,
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

    return app
