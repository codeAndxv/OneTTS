"""测试 /v1/x/voices 发音人音色端点及多维过滤。"""


def test_voices_unauthorized(client):
    resp = client.get("/v1/x/voices")
    assert resp.status_code == 401


def test_voices_authorized(client):
    headers = {"Authorization": "Bearer onetts-test-key"}
    resp = client.get("/v1/x/voices", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    voice_ids = [v["id"] for v in data["voices"]]
    assert "zh-CN-XiaoxiaoNeural" in voice_ids

    # 校验新富元数据结构
    first = data["voices"][0]
    assert "tags" in first
    assert "styles" in first
    assert "category" in first
    assert "is_recommended" in first
    assert "is_clone" in first


def test_voices_filter_by_gender(client):
    headers = {"Authorization": "Bearer onetts-test-key"}
    resp = client.get("/v1/x/voices?gender=female", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for v in data["voices"]:
        assert v["gender"] == "female"


def test_voices_filter_by_language(client):
    headers = {"Authorization": "Bearer onetts-test-key"}
    resp = client.get("/v1/x/voices?language=zh", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for v in data["voices"]:
        assert "zh" in v["language"].lower() or any("zh" in l.lower() for l in v["languages"])


def test_voices_filter_by_recommended(client):
    headers = {"Authorization": "Bearer onetts-test-key"}
    resp = client.get("/v1/x/voices?recommended_only=true", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for v in data["voices"]:
        assert v["is_recommended"] is True
