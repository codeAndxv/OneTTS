"""测试 /v1/audio/voices 端点。"""

def test_voices_unauthorized(client):
    resp = client.get("/v1/audio/voices")
    assert resp.status_code == 401


def test_voices_authorized(client):
    headers = {"Authorization": "Bearer onetts-test-key"}
    resp = client.get("/v1/audio/voices", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    voice_ids = [v["id"] for v in data["voices"]]
    assert "zh-CN-XiaoxiaoNeural" in voice_ids
