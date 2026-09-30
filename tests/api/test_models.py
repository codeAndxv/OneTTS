"""测试 /v1/models 与 /v1/providers 端点。"""

def test_models_unauthorized(client):
    resp = client.get("/v1/models")
    assert resp.status_code == 401
    assert "error" in resp.json()


def test_models_authorized(client):
    headers = {"Authorization": "Bearer onetts-test-key"}
    resp = client.get("/v1/models", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    ids = [m["id"] for m in data["data"]]
    assert "tts-1" in ids
    assert "edgetts" in ids


def test_providers_authorized(client):
    headers = {"X-API-Key": "onetts-test-key"}
    resp = client.get("/v1/providers", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "edgetts" in data["providers"]
