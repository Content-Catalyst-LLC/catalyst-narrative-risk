from app import create_app


def test_api_returns_canonical_record():
    client = create_app().test_client()
    response = client.post("/api/narrative-risk", json={"claim": "API claim"})
    assert response.status_code == 200
    record = response.get_json()
    assert record["contract"]["contract_version"] == "1.1.0"
    assert record["method_snapshot"]["method_version"] == "1.1.0"
    assert record["human_decision"]["disposition"] == "undecided"


def test_api_exposes_contract_and_method_snapshot():
    client = create_app().test_client()
    contract = client.get("/api/narrative-risk/contract").get_json()
    method = client.get("/api/narrative-risk/methods/current").get_json()
    assert contract["contract_version"] == "1.1.0"
    assert method["method_snapshot"]["method_version"] == "1.1.0"
    assert len(method["method_snapshot_sha256"]) == 64


def test_api_verifies_generated_record():
    client = create_app().test_client()
    record = client.post("/api/narrative-risk", json={"claim": "Verify API claim"}).get_json()
    response = client.post("/api/narrative-risk/verify", json=record)
    assert response.status_code == 200
    assert response.get_json()["exact_match"] is True


def test_api_rejects_missing_claim_and_invalid_vocabulary():
    client = create_app().test_client()
    missing = client.post("/api/narrative-risk", json={})
    invalid = client.post("/api/narrative-risk", json={"claim": "x", "source_type": "made_up"})
    assert missing.status_code == 400
    assert missing.get_json()["message"] == "claim is required"
    assert invalid.status_code == 400
    assert invalid.get_json()["message"].startswith("source_type must be one of:")


def test_api_rejects_non_json_body():
    client = create_app().test_client()
    response = client.post("/api/narrative-risk", data="not-json", content_type="text/plain")
    assert response.status_code == 400
    assert response.get_json()["message"] == "request body must be a JSON object"
