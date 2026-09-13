"""Regression tests for API security and model behaviour."""

from fastapi.testclient import TestClient

import api


client = TestClient(api.app)


def test_security_headers_and_status():
    response = client.get("/security/status")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.json()["cors_allowlist"] is True


def test_empty_and_oversized_text_rejected():
    assert client.post("/predict", json={"text": ""}).status_code == 422
    assert client.post("/predict", json={"text": "x" * 5001}).status_code == 422


def test_bangla_threat_regression():
    response = client.post("/predict", json={"text": "toke mere felbo"})
    body = response.json()
    assert response.status_code == 200
    assert body["prediction"] == "Cyberbullying"
    assert body["category"] == "Threat"
    assert body["risk_level"] == "Critical"


def test_safe_text_regression():
    body = client.post("/predict", json={"text": "you are so cute"}).json()
    assert body["prediction"] == "Safe"


def test_context_and_sarcasm_metadata():
    body = client.post(
        "/predict", json={"text": "yeah right, what a genius /s", "context": "previous message"}
    ).json()
    assert body["context_used"] is True
    assert body["sarcasm_detected"] is True


def test_youtube_key_never_required_from_browser():
    assert "api_key" not in api.YouTubeProtectionRequest.model_json_schema()["properties"]
