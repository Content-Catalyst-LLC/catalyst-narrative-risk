from flask import Flask, jsonify, request

from narrative_risk.contracts import contract_definition, current_method_snapshot, sha256_digest
from narrative_risk.migrations import migrate_v1_0_1_record
from narrative_risk.service import (
    VERSION,
    NarrativeRiskValidationError,
    build_narrative_risk_record,
    validate_narrative_risk_record,
    verify_record_reproducibility,
)


def _json_object():
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        raise NarrativeRiskValidationError("request body must be a JSON object")
    return payload


def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return {
            "ok": True,
            "version": VERSION,
            "contract_id": "urn:catalyst:narrative-risk:contract:canonical",
            "contract_version": VERSION,
        }, 200

    @app.get("/api/narrative-risk/contract")
    def narrative_risk_contract():
        return jsonify(contract_definition()), 200

    @app.get("/api/narrative-risk/methods/current")
    def narrative_risk_method():
        method = current_method_snapshot()
        return jsonify({"method_snapshot": method, "method_snapshot_sha256": sha256_digest(method)}), 200

    @app.post("/api/narrative-risk")
    def narrative_risk_api():
        try:
            record = build_narrative_risk_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return jsonify({"error": "invalid_narrative_risk_input", "message": str(exc)}), 400
        return jsonify(record), 200

    @app.post("/api/narrative-risk/verify")
    def narrative_risk_verify():
        try:
            record = _json_object()
            validate_narrative_risk_record(record)
            report = verify_record_reproducibility(record)
        except NarrativeRiskValidationError as exc:
            return jsonify({"error": "invalid_narrative_risk_record", "message": str(exc)}), 400
        return jsonify(report), 200

    @app.post("/api/narrative-risk/migrate/v1.0.1")
    def narrative_risk_migrate():
        try:
            migrated = migrate_v1_0_1_record(_json_object())
        except NarrativeRiskValidationError as exc:
            return jsonify({"error": "invalid_legacy_narrative_risk_record", "message": str(exc)}), 400
        return jsonify(migrated), 200

    return app
