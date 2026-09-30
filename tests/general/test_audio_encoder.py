"""测试音频转码与编码工具。"""

import numpy as np
from server.utils.audio_encoder import encode_audio, get_mime_type, pcm_to_wav


def test_mime_types():
    assert get_mime_type("mp3") == "audio/mpeg"
    assert get_mime_type("wav") == "audio/wav"
    assert get_mime_type("pcm") == "audio/pcm"
    assert get_mime_type("flac") == "audio/flac"
    assert get_mime_type("opus") == "audio/opus"


def test_pcm_to_wav():
    raw_pcm = np.zeros(24000, dtype=np.int16).tobytes()
    wav_bytes = pcm_to_wav(raw_pcm, sample_rate=24000)
    assert len(wav_bytes) > len(raw_pcm)
    assert wav_bytes.startswith(b"RIFF")
    assert b"WAVE" in wav_bytes[:16]


def test_encode_audio_numpy_and_bytes():
    data = np.zeros(16000, dtype=np.float32)
    wav_out = encode_audio(data, target_format="wav", sample_rate=16000)
    assert wav_out.startswith(b"RIFF")

    pcm_out = encode_audio(data, target_format="pcm", sample_rate=16000)
    assert len(pcm_out) == 32000  # 16000 samples * 2 bytes
