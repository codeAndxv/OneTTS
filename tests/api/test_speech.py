"""测试 /v1/audio/speech 核心语音合成端点。"""

from unittest.mock import AsyncMock, patch


def test_speech_unauthorized(client):
    payload = {
        "model": "tts-1",
        "input": "测试语音合成",
        "voice": "alloy",
    }
    resp = client.post("/v1/audio/speech", json=payload)
    assert resp.status_code == 401
    assert "error" in resp.json()


def test_speech_validation_error(client):
    headers = {"Authorization": "Bearer onetts-test-key"}
    # 缺少 input 必填字段
    resp = client.post("/v1/audio/speech", json={"model": "tts-1"}, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "validation_error"


@patch("server.services.speech_service.SpeechService.synthesize_speech", new_callable=AsyncMock)
def test_speech_synthesize_success(mock_synth, client):
    mock_synth.return_value = b"FAKE_MP3_AUDIO_BYTES"
    headers = {"Authorization": "Bearer onetts-test-key"}
    payload = {
        "model": "tts-1",
        "input": "欢迎使用 OneTTS！",
        "voice": "alloy",
        "response_format": "mp3",
    }
    resp = client.post("/v1/audio/speech", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content == b"FAKE_MP3_AUDIO_BYTES"


@patch("server.services.speech_service.SpeechService.stream_speech")
def test_speech_streaming_success(mock_stream, client):
    async def _mock_gen(req):
        yield b"CHUNK_A"
        yield b"CHUNK_B"

    mock_stream.side_effect = _mock_gen
    headers = {"Authorization": "Bearer onetts-test-key"}
    payload = {
        "model": "tts-1",
        "input": "流式合成测试。",
        "voice": "alloy",
        "response_format": "wav",
        "stream": True,
    }
    resp = client.post("/v1/audio/speech", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    assert resp.content == b"CHUNK_ACHUNK_B"
