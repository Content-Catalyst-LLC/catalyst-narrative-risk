from flask import Flask, jsonify, request
from narrative_risk.service import build_narrative_risk_record


def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}, 200

    @app.post("/api/narrative-risk")
    def narrative_risk_api():
        payload = request.get_json(silent=True) or {}
        return jsonify(build_narrative_risk_record(payload))

    return app
