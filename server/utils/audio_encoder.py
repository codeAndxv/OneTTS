"""音频格式转码与封装工具。"""

import io
import wave
import numpy as np
import soundfile as sf


FORMAT_MIME_MAP = {
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
}


def get_mime_type(response_format: str) -> str:
    """获取指定格式的 Content-Type MIME。"""
    return FORMAT_MIME_MAP.get(response_format.lower(), "audio/mpeg")


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """将裸 PCM (int16) 字节流打包为带标准 RIFF 头的 WAV 格式。"""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


def encode_audio(
    audio_data: bytes | np.ndarray,
    target_format: str = "mp3",
    sample_rate: int = 24000,
) -> bytes:
    """将 PCM 或 numpy 音频数据编码为目标格式字节流。"""
    fmt = target_format.lower().strip()
    if fmt == "pcm":
        if isinstance(audio_data, np.ndarray):
            # 将 float32 转为 int16 裸字节
            if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
                audio_data = np.clip(audio_data, -1.0, 1.0)
                audio_data = (audio_data * 32767).astype(np.int16)
            return audio_data.tobytes()
        return audio_data

    if fmt == "wav":
        if isinstance(audio_data, bytes):
            return pcm_to_wav(audio_data, sample_rate=sample_rate)
        # numpy array
        buf = io.BytesIO()
        sf.write(buf, audio_data, sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    # 其他格式 (mp3, flac, ogg/opus) 使用 soundfile 写入
    if isinstance(audio_data, bytes):
        # 假定为 int16 裸 PCM
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
    else:
        audio_np = audio_data

    buf = io.BytesIO()
    if fmt == "flac":
        sf.write(buf, audio_np, sample_rate, format="FLAC")
        return buf.getvalue()
    elif fmt == "ogg" or fmt == "opus":
        sf.write(buf, audio_np, sample_rate, format="OGG")
        return buf.getvalue()
    elif fmt == "mp3":
        # 如果 soundfile 支持 MP3 写入直接使用，否则转为 WAV
        try:
            sf.write(buf, audio_np, sample_rate, format="MP3")
            return buf.getvalue()
        except Exception:
            # 降级返回 WAV 或原始字节
            return pcm_to_wav(
                audio_np.tobytes() if isinstance(audio_np, np.ndarray) else audio_data,
                sample_rate=sample_rate,
            )

    return pcm_to_wav(audio_data if isinstance(audio_data, bytes) else audio_data.tobytes(), sample_rate)


class AudioEncoder:
    """统一音频格式转码适配器。"""

    @staticmethod
    def encode(
        audio_data: bytes | np.ndarray,
        source_format: str = "wav",
        target_format: str = "mp3",
        sample_rate: int = 24000,
    ) -> bytes:
        """从源格式或原始采样转码至目标格式。"""
        if target_format.lower() == source_format.lower() and isinstance(audio_data, bytes):
            return audio_data

        if source_format.lower() == "wav" and isinstance(audio_data, bytes):
            try:
                with io.BytesIO(audio_data) as bio:
                    data, sr = sf.read(bio, dtype="int16")
                    return encode_audio(data, target_format=target_format, sample_rate=sr)
            except Exception:
                pass

        return encode_audio(audio_data, target_format=target_format, sample_rate=sample_rate)

    @staticmethod
    def generate_silence_wav(duration_seconds: float = 1.0, sample_rate: int = 24000) -> bytes:
        """生成指定时长的合法标准静音 WAV 数据。"""
        num_frames = int(max(0.1, duration_seconds) * sample_rate)
        pcm_bytes = b"\x00\x00" * num_frames
        return pcm_to_wav(pcm_bytes, sample_rate=sample_rate)

    @staticmethod
    def convert_audio(audio_bytes: bytes, from_fmt: str, to_fmt: str) -> bytes:
        """便捷音频格式转换接口。"""
        return AudioEncoder.encode(audio_bytes, source_format=from_fmt, target_format=to_fmt)


audio_encoder = AudioEncoder()
