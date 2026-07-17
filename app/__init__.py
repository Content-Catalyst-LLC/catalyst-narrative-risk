from flask import Flask, jsonify, request

from narrative_risk.service import (
    VERSION,
    NarrativeRiskValidationError,
    build_narrative_risk_record,
    validate_narrative_risk_record,
)


def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "version": VERSION}, 200

    @app.post("/api/narrative-risk")
    def narrative_risk_api():
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({
                "error": "invalid_narrative_risk_input",
                "message": "request body must be a JSON object",
            }), 400
        try:
            record = build_narrative_risk_record(payload)
            validate_narrative_risk_record(record)
        except NarrativeRiskValidationError as exc:
            return jsonify({
                "error": "invalid_narrative_risk_input",
                "message": str(exc),
            }), 400
        return jsonify(record), 200

    return app
