from app import create_app


def test_api_returns_valid_record():
    client = create_app().test_client()
    response = client.post("/api/narrative-risk", json={"claim": "API claim"})
    assert response.status_code == 200
    assert response.get_json()["method_version"] == "1.0.1"


def test_api_rejects_missing_claim():
    client = create_app().test_client()
    response = client.post("/api/narrative-risk", json={})
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "invalid_narrative_risk_input",
        "message": "claim is required",
    }


def test_api_rejects_non_json_body():
    client = create_app().test_client()
    response = client.post("/api/narrative-risk", data="not-json", content_type="text/plain")
    assert response.status_code == 400
