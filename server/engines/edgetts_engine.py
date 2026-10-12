"""Edge-TTS 引擎适配器实现（基于微软 Azure 神经语音）。"""

import io
import logging
from typing import AsyncGenerator
import edge_tts

from server.engines.base import BaseTTSEngine, TTSContext, TTSResult
from server.schemas.voice import VoiceInfo
from server.utils.audio_encoder import encode_audio

logger = logging.getLogger(__name__)

# 系统预置常用优质音色清单
DEFAULT_EDGETTS_VOICES = [
    VoiceInfo(
        id="zh-CN-XiaoxiaoNeural",
        name="晓晓 (Xiaoxiao - 温暖女声)",
        provider="edgetts",
        language="zh-CN",
        gender="female",
        description="微软经典温暖自然女声，适合新闻、小说、助手",
    ),
    VoiceInfo(
        id="zh-CN-YunxiNeural",
        name="云希 (Yunxi - 活力男声)",
        provider="edgetts",
        language="zh-CN",
        gender="male",
        description="生动阳光男声，适合播客、旁白、视频解说",
    ),
    VoiceInfo(
        id="zh-CN-YunjianNeural",
        name="云健 (Yunjian - 影视解说男声)",
        provider="edgetts",
        language="zh-CN",
        gender="male",
        description="磁性沉稳男声，适合影视解说与纪录片",
    ),
    VoiceInfo(
        id="zh-CN-XiaoyiNeural",
        name="晓伊 (Xiaoyi - 亲切女声)",
        provider="edgetts",
        language="zh-CN",
        gender="female",
        description="生动自然女声，适合电台与日常对话",
    ),
    VoiceInfo(
        id="zh-CN-liaoning-XiaobeiNeural",
        name="小北 (Xiaobei - 东北方言女声)",
        provider="edgetts",
        language="zh-CN-liaoning",
        gender="female",
        description="生动幽默东北特色方言女声",
    ),
    VoiceInfo(
        id="zh-HK-HiuMaanNeural",
        name="曉曼 (HiuMaan - 粤语女声)",
        provider="edgetts",
        language="zh-HK",
        gender="female",
        description="标准香港粤语自然女声",
    ),
    VoiceInfo(
        id="zh-TW-HsiaoChenNeural",
        name="曉臻 (HsiaoChen - 台湾国语女声)",
        provider="edgetts",
        language="zh-TW",
        gender="female",
        description="标准台湾国语自然女声",
    ),
    VoiceInfo(
        id="en-US-JennyNeural",
        name="Jenny (US English Female)",
        provider="edgetts",
        language="en-US",
        gender="female",
        description="Standard US English female voice",
    ),
    VoiceInfo(
        id="en-US-GuyNeural",
        name="Guy (US English Male)",
        provider="edgetts",
        language="en-US",
        gender="male",
        description="Standard US English male voice",
    ),
    VoiceInfo(
        id="ja-JP-NanamiNeural",
        name="Nanami (七海 - 日本語女性)",
        provider="edgetts",
        language="ja-JP",
        gender="female",
        description="自然でクリアな日本語女性音声",
    ),
    VoiceInfo(
        id="ja-JP-KeitaNeural",
        name="Keita (圭太 - 日本語男性)",
        provider="edgetts",
        language="ja-JP",
        gender="male",
        description="落ち着きのある自然な日本語男性音声",
    ),
]


def _format_rate(speed: float) -> str:
    """将浮点语速转换为 Edge-TTS 期望的百分比字符串 (+20%, -10%)。"""
    percent = int(round((speed - 1.0) * 100))
    if percent >= 0:
        return f"+{percent}%"
    return f"{percent}%"


def _format_pitch(pitch: float) -> str:
    """将音高浮点偏移 (-50.0 ~ +50.0) 格式化为 Edge-TTS 期望的 '+10Hz' 或 '+5%'。"""
    val = int(round(pitch))
    if val >= 0:
        return f"+{val}Hz"
    return f"{val}Hz"


def _format_volume(volume: float) -> str:
    """将音量倍率 (0.1 ~ 2.0) 格式化为百分比 (+0%, -20%)。"""
    percent = int(round((volume - 1.0) * 100))
    if percent >= 0:
        return f"+{percent}%"
    return f"{percent}%"


class EdgeTTSEngine(BaseTTSEngine):
    """Edge-TTS 引擎实现。"""

    def __init__(self, name: str = "edgetts", config: dict | None = None):
        super().__init__(name, config)
        self.default_voice = self.config.get("default_voice", "zh-CN-XiaoxiaoNeural")

    async def synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        response_format: str = "mp3",
    ) -> bytes:
        ctx = TTSContext(
            text=text,
            voice=voice,
            speed=speed,
            response_format=response_format,
        )
        res = await self.synthesize_with_context(ctx)
        return res.audio_bytes

    async def synthesize_with_context(self, ctx: TTSContext) -> TTSResult:
        target_voice = ctx.voice or self.default_voice
        rate_str = _format_rate(ctx.speed)
        pitch_str = _format_pitch(ctx.pitch)
        volume_str = _format_volume(ctx.volume)

        communicate = edge_tts.Communicate(
            ctx.text,
            target_voice,
            rate=rate_str,
            pitch=pitch_str,
            volume=volume_str,
        )
        audio_buffer = io.BytesIO()
        word_boundaries: list[dict] = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append(chunk)

        mp3_bytes = audio_buffer.getvalue()
        output_bytes = mp3_bytes
        if ctx.response_format.lower() != "mp3":
            output_bytes = encode_audio(mp3_bytes, target_format=ctx.response_format)

        duration_sec = 0.0
        if word_boundaries:
            last = word_boundaries[-1]
            duration_sec = round((last["offset"] + last["duration"]) / 10_000_000.0, 3)
        if duration_sec <= 0:
            duration_sec = max(round(len(ctx.text) / (4.0 * ctx.speed), 3), 0.5)

        cues = []
        srt_text = ""
        vtt_text = ""
        if ctx.with_subtitles:
            from server.utils.subtitle_generator import build_cues_from_sentences, generate_srt, generate_vtt
            from server.utils.text_splitter import split_text_into_sentences

            sentences = split_text_into_sentences(ctx.text)
            if sentences:
                total_chars = max(sum(len(s) for s in sentences), 1)
                durations = [(len(s) / total_chars) * duration_sec for s in sentences]
                cues = build_cues_from_sentences(sentences, durations)
                srt_text = generate_srt(cues)
                vtt_text = generate_vtt(cues)

        from server.engines.base import TTSResult
        return TTSResult(
            audio_bytes=output_bytes,
            format=ctx.response_format,
            duration_seconds=duration_sec,
            sample_rate=24000,
            subtitles=cues,
            srt_content=srt_text,
            vtt_content=vtt_text,
        )

    async def stream_synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        response_format: str = "mp3",
    ) -> AsyncGenerator[bytes, None]:
        ctx = TTSContext(
            text=text,
            voice=voice,
            speed=speed,
            response_format=response_format,
        )
        async for chunk in self.stream_synthesize_with_context(ctx):
            yield chunk

    async def stream_synthesize_with_context(
        self,
        ctx: TTSContext,
    ) -> AsyncGenerator[bytes, None]:
        target_voice = ctx.voice or self.default_voice
        rate_str = _format_rate(ctx.speed)
        pitch_str = _format_pitch(ctx.pitch)
        volume_str = _format_volume(ctx.volume)

        communicate = edge_tts.Communicate(
            ctx.text,
            target_voice,
            rate=rate_str,
            pitch=pitch_str,
            volume=volume_str,
        )
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                data = chunk["data"]
                if ctx.response_format.lower() == "mp3":
                    yield data
                else:
                    yield encode_audio(data, target_format=ctx.response_format)

    def list_voices(self) -> list[VoiceInfo]:
        return list(DEFAULT_EDGETTS_VOICES)
