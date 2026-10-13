"""/v1/tts/dubbing 字幕留白对齐配音接口单元测试。"""

import io
import wave
from unittest.mock import AsyncMock, patch
import pytest

from server.engines.base import TTSResult
from server.services.dubbing_service import parse_srt_to_cues
from tests.helpers.fixture_loader import load_subtitle_fixture

AUTH_HEADERS = {"Authorization": "Bearer onetts-test-key"}


def _create_mock_wav(duration_seconds: float = 1.0, sample_rate: int = 24000) -> bytes:
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        num_frames = int(duration_seconds * sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return bio.getvalue()


def test_parse_srt_to_cues():
    srt = """1
00:00:01,000 --> 00:00:03,000
[Alice] Hello world!

2
00:00:05,500 --> 00:00:07,000
Bob: Nice to meet you.
"""
    cues = parse_srt_to_cues(srt)
    assert len(cues) == 2
    assert cues[0].start_seconds == 1.0
    assert cues[0].end_seconds == 3.0
    assert cues[0].speaker == "Alice"
    assert cues[0].text == "Hello world!"

    assert cues[1].start_seconds == 5.5
    assert cues[1].end_seconds == 7.0
    assert cues[1].speaker == "Bob"
    assert cues[1].text == "Nice to meet you."


def test_dubbing_endpoint_json_mode(client):
    """测试 /v1/tts/dubbing 使用 JSON 返回模式。"""
    mock_wav = _create_mock_wav(1.0)
    mock_res = TTSResult(
        audio_bytes=mock_wav,
        format="wav",
        duration_seconds=1.0,
        sample_rate=24000,
    )

    with patch("server.engines.edgetts_engine.EdgeTTSEngine.synthesize_with_context", new_callable=AsyncMock) as mock_synth:
        mock_synth.return_value = mock_res

        payload = {
            "model": "edgetts",
            "default_voice": "zh-CN-XiaoxiaoNeural",
            "output_mode": "json",
            "response_format": "wav",
            "cues": [
                {"start_seconds": 1.0, "end_seconds": 2.5, "text": "第一句话"},
                {"start_seconds": 4.0, "end_seconds": 5.5, "text": "第二句话"},
            ]
        }
        resp = client.post("/v1/x/audio/dubbing", json=payload, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()

        assert "audio_base64" in data
        assert data["format"] == "wav"
        assert data["total_cues"] == 2
        assert data["silence_gaps_count"] >= 1
        assert data["total_duration_seconds"] >= 5.0


def test_dubbing_endpoint_srt_input(client):
    """测试 /v1/x/audio/dubbing 传入真实 SRT 夹具文本与角色映射。"""
    mock_wav = _create_mock_wav(1.0)
    mock_res = TTSResult(
        audio_bytes=mock_wav,
        format="wav",
        duration_seconds=1.0,
        sample_rate=24000,
    )

    with patch("server.engines.edgetts_engine.EdgeTTSEngine.synthesize_with_context", new_callable=AsyncMock) as mock_synth:
        mock_synth.return_value = mock_res

        srt_text = load_subtitle_fixture("sample_dubbing.srt")
        payload = {
            "model": "edgetts",
            "srt_content": srt_text,
            "voice_mapping": {
                "Narrator": "zh-CN-YunxiNeural",
                "Alice": "zh-CN-XiaoxiaoNeural",
                "Bob": "zh-CN-YunjianNeural",
            },
            "output_mode": "audio",
            "response_format": "wav",
        }
        resp = client.post("/v1/x/audio/dubbing", json=payload, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("audio/")
        assert resp.content.startswith(b"RIFF")
