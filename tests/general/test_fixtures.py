"""测试预置测试资源（音频、字幕、文本、剧本）及其加载器。"""

import wave
import io
from tests.helpers.fixture_loader import (
    get_fixture_path,
    load_audio_fixture,
    load_json_fixture,
    load_subtitle_fixture,
    load_text_fixture,
)
from server.services.dubbing_service import parse_srt_to_cues


def test_audio_fixture_wav_validity():
    """验证 en_speech_15s.wav 是否为合法的 16kHz WAV 音频。"""
    audio_bytes = load_audio_fixture("en_speech_15s.wav")
    assert len(audio_bytes) > 400_000  # 约 469 KB

    bio = io.BytesIO(audio_bytes)
    with wave.open(bio, "rb") as wf:
        assert wf.getnchannels() == 1  # 单声道
        assert wf.getsampwidth() == 2  # 16-bit
        assert wf.getframerate() == 16000  # 16 kHz
        duration = wf.getnframes() / wf.getframerate()
        assert 14.0 <= duration <= 16.0  # 约 15 秒


def test_subtitle_fixture_cues_and_silence_gaps():
    """验证 sample_dubbing.srt 字幕解析及预置的静音留白。"""
    srt_content = load_subtitle_fixture("sample_dubbing.srt")
    assert "Narrator" in srt_content
    assert "Alice" in srt_content
    assert "Bob" in srt_content

    cues = parse_srt_to_cues(srt_content)
    assert len(cues) == 3

    # Cue 1: 0.5s ~ 2.5s
    assert cues[0].speaker == "Narrator"
    assert cues[0].start_seconds == 0.5
    assert cues[0].end_seconds == 2.5

    # Cue 2: 4.0s ~ 6.0s (与 Cue 1 之间留白 1.5s)
    assert cues[1].speaker == "Alice"
    assert cues[1].start_seconds == 4.0
    assert cues[1].end_seconds == 6.0
    gap1 = cues[1].start_seconds - cues[0].end_seconds
    assert abs(gap1 - 1.5) < 0.001

    # Cue 3: 8.0s ~ 10.5s (与 Cue 2 之间留白 2.0s)
    assert cues[2].speaker == "Bob"
    assert cues[2].start_seconds == 8.0
    assert cues[2].end_seconds == 10.5
    gap2 = cues[2].start_seconds - cues[1].end_seconds
    assert abs(gap2 - 2.0) < 0.001


def test_multilingual_vtt_fixture():
    """验证 sample_multilingual.vtt 字幕存在且格式正确。"""
    vtt = load_subtitle_fixture("sample_multilingual.vtt")
    assert vtt.startswith("WEBVTT")
    assert "Narrator" in vtt
    assert "Alice" in vtt
    assert "Bob" in vtt


def test_text_and_drama_fixtures():
    """验证文本台词与广播剧 JSON 格式。"""
    text = load_text_fixture("sample_speech.txt")
    assert len(text) > 50
    assert "rainbow" in text.lower()
    assert "sunlight" in text.lower()

    drama = load_json_fixture("sample_drama.json")
    assert drama["title"] == "Morning Standup Meeting"
    assert len(drama["dialogue"]) >= 4
    for line in drama["dialogue"]:
        assert "speaker" in line
        assert "voice" in line
        assert "text" in line
