"""/v1/x/... 专属高级扩展 API 测试集。"""

import io
from unittest.mock import AsyncMock, patch
from server.engines.base import TTSResult
from server.utils.subtitle_generator import SubtitleCue
from tests.helpers.fixture_loader import load_audio_fixture, load_json_fixture

AUTH_HEADERS = {"Authorization": "Bearer onetts-test-key"}


def test_tts_generate_json_with_subtitles(client):
    """测试 /v1/x/audio/speech 结构化输出模式并带字幕。"""
    cues = [
        SubtitleCue(index=1, text="测试第一句", start_seconds=0.0, end_seconds=1.5, start_time="00:00:00,000", end_time="00:00:01,500"),
        SubtitleCue(index=2, text="测试第二句", start_seconds=1.5, end_seconds=3.0, start_time="00:00:01,500", end_time="00:00:03,000"),
    ]
    mock_res = TTSResult(
        audio_bytes=b"dummy_mp3_audio_data_1234567890",
        format="mp3",
        duration_seconds=3.0,
        sample_rate=24000,
        subtitles=cues,
        srt_content="1\n00:00:00,000 --> 00:00:01,500\n测试第一句\n",
        vtt_content="WEBVTT\n\n1\n00:00:00.000 --> 00:00:01.500\n测试第一句\n",
    )

    with patch("server.services.speech_service.SpeechService.synthesize_advanced", new_callable=AsyncMock) as mock_synth:
        mock_synth.return_value = mock_res
        payload = {
            "model": "edgetts",
            "text": "测试第一句。测试第二句。",
            "voice": "zh-CN-XiaoxiaoNeural",
            "response_format": "mp3",
            "with_subtitles": True,
            "output_mode": "json",
        }
        resp = client.post("/v1/x/audio/speech", json=payload, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()

        assert "audio_base64" in data
        assert len(data["audio_base64"]) > 0
        assert data["audio_format"] == "mp3"
        assert data["audio_duration_seconds"] == 3.0
        assert len(data["subtitles"]) == 2
        assert "srt_content" in data
        assert "vtt_content" in data


def test_tts_generate_audio_mode(client):
    """测试 /v1/x/audio/speech 直接返回音频二进制模式。"""
    mock_res = TTSResult(
        audio_bytes=b"raw_binary_audio_data_test_12345",
        format="mp3",
        duration_seconds=2.5,
    )
    with patch("server.services.speech_service.SpeechService.synthesize_advanced", new_callable=AsyncMock) as mock_synth:
        mock_synth.return_value = mock_res
        payload = {
            "model": "edgetts",
            "text": "测试直接返回音频模式。",
            "voice": "alloy",
            "response_format": "mp3",
            "with_subtitles": False,
            "output_mode": "audio",
        }
        resp = client.post("/v1/x/audio/speech", json=payload, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/mpeg"
        assert resp.content == b"raw_binary_audio_data_test_12345"
        assert resp.headers["x-audio-duration"] == "2.5"


def test_tts_tasks_lifecycle(client):
    """测试 /v1/x/tasks 异步长文本/剧本演播任务生命周期。"""
    create_payload = load_json_fixture("sample_drama.json")
    # 1. 创建任务
    create_resp = client.post("/v1/x/tasks", json=create_payload, headers=AUTH_HEADERS)
    assert create_resp.status_code == 200
    task_info = create_resp.json()
    task_id = task_info["task_id"]
    assert task_id.startswith("tts_task_")
    assert task_info["status"] in ("pending", "running", "completed")

    # 2. 查询列表
    list_resp = client.get("/v1/x/tasks", headers=AUTH_HEADERS)
    assert list_resp.status_code == 200
    tasks = list_resp.json()
    assert any(t["task_id"] == task_id for t in tasks)

    # 3. 查询单任务详情
    detail_resp = client.get(f"/v1/x/tasks/{task_id}", headers=AUTH_HEADERS)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["task_id"] == task_id

    # 4. 取消任务
    cancel_resp = client.post(f"/v1/x/tasks/{task_id}/cancel", headers=AUTH_HEADERS)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["cancelled"] is True


def test_tts_clones_crud(client):
    """测试 /v1/x/voices/clones 专属声音克隆资产注册、列表、试听与删除。"""
    sample_wav = load_audio_fixture("en_speech_15s.wav")

    # 1. 注册克隆声音
    files = {"file": ("test_voice.wav", io.BytesIO(sample_wav), "audio/wav")}
    data = {
        "name": "单元测试专属音色",
        "description": "用于 pytest 的声音资产",
        "language": "zh-CN",
        "prompt_text": "这是测试录音台词。",
    }
    reg_resp = client.post("/v1/x/voices/clones", data=data, files=files, headers=AUTH_HEADERS)
    assert reg_resp.status_code == 200
    clone_info = reg_resp.json()
    clone_id = clone_info["clone_voice_id"]
    assert clone_id.startswith("clone_")
    assert clone_info["name"] == "单元测试专属音色"

    # 2. 获取克隆声音列表
    list_resp = client.get("/v1/x/voices/clones", headers=AUTH_HEADERS)
    assert list_resp.status_code == 200
    clones = list_resp.json()
    assert any(c["id"] == clone_id for c in clones)

    # 3. 试听样本
    sample_resp = client.get(f"/v1/x/voices/clones/{clone_id}/sample", headers=AUTH_HEADERS)
    assert sample_resp.status_code == 200
    assert sample_resp.headers["content-type"] == "audio/wav"

    # 4. 删除克隆声音
    del_resp = client.delete(f"/v1/x/voices/clones/{clone_id}", headers=AUTH_HEADERS)
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True


def test_tts_realtime_websocket(client):
    """测试 /v1/x/realtime 全双工 WebSocket 接口连接与打断。"""
    with client.websocket_connect("/v1/x/realtime?api_key=onetts-test-key") as ws:
        # 发送打断指令
        ws.send_json({"type": "interrupt"})
        msg = ws.receive_json()
        assert msg["type"] == "interrupted"
