"""测试 OpenAI 标准 /v1/models 与 OneTTS 扩展 /v1/x/models, /v1/x/info, /v1/x/providers 端点。"""


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


def test_retrieve_model_authorized(client):
    headers = {"Authorization": "Bearer onetts-test-key"}
    resp = client.get("/v1/models/tts-1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "tts-1"
    assert data["object"] == "model"

    # 测试不存在的模型
    resp_404 = client.get("/v1/models/non-existent-model", headers=headers)
    assert resp_404.status_code == 404


def test_extended_models_authorized(client):
    headers = {"Authorization": "Bearer onetts-test-key"}
    resp = client.get("/v1/x/models", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    assert data["total"] > 0
    ids = [m["id"] for m in data["data"]]
    assert "tts-1" in ids
    # 验证语言已完全下沉至音色字典，模型层不再包含 languages 字段
    for m in data["data"]:
        assert "languages" not in m


def test_info_authorized(client):
    resp = client.get("/v1/x/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "OneTTS"
    assert "api_version" in data
    assert data["status"] == "ok"


def test_providers_authorized(client):
    headers = {"X-API-Key": "onetts-test-key"}
    resp = client.get("/v1/x/providers", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "edgetts" in data["providers"]
