"""音频时间轴缝合与静音填充器单元测试。"""

import io
import wave
import pytest
from server.utils.audio_stitcher import AudioStitcher, AudioTimelineTrack


def test_timeline_track_silence():
    track = AudioTimelineTrack(sample_rate=24000, channels=1, sample_width=2)
    assert track.current_duration_seconds == 0.0

    # 追加 1.5 秒静音
    track.append_silence(1.5)
    assert abs(track.current_duration_seconds - 1.5) < 0.001

    # 导出为 WAV
    wav_bytes = track.to_wav_bytes()
    assert wav_bytes.startswith(b"RIFF")
    with io.BytesIO(wav_bytes) as bio:
        with wave.open(bio, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 24000
            duration = wf.getnframes() / wf.getframerate()
            assert abs(duration - 1.5) < 0.001


def test_timeline_track_pad_to_timestamp():
    track = AudioTimelineTrack(sample_rate=24000)
    # 当前为 0 秒，填充到 2.0 秒
    track.pad_to_timestamp(2.0)
    assert abs(track.current_duration_seconds - 2.0) < 0.001

    # 再次填充到 1.5 秒（早于当前时间，不应回退或截断）
    track.pad_to_timestamp(1.5)
    assert abs(track.current_duration_seconds - 2.0) < 0.001

    # 填充到 3.5 秒
    track.pad_to_timestamp(3.5)
    assert abs(track.current_duration_seconds - 3.5) < 0.001


def test_timeline_track_append_wav():
    # 生成 1 秒的合成测试 WAV (24kHz 16-bit)
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"\x12\x34" * 24000)
    test_wav = bio.getvalue()

    track = AudioTimelineTrack(sample_rate=24000)
    # 先留白 1 秒
    track.append_silence(1.0)
    # 再追加 1 秒音频
    track.append_wav(test_wav)
    assert abs(track.current_duration_seconds - 2.0) < 0.001

    final_wav = track.to_wav_bytes()
    with io.BytesIO(final_wav) as bio_out:
        with wave.open(bio_out, "rb") as wf:
            assert wf.getnframes() == 48000


def test_audio_stitcher_generate_silence():
    silence_wav = AudioStitcher.generate_silence_wav(0.5, sample_rate=24000)
    assert silence_wav.startswith(b"RIFF")
    with io.BytesIO(silence_wav) as bio:
        with wave.open(bio, "rb") as wf:
            assert wf.getframerate() == 24000
            duration = wf.getnframes() / wf.getframerate()
            assert abs(duration - 0.5) < 0.001
