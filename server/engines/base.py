"""TTS 引擎抽象基类与上下文数据模型。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

from server.schemas.voice import VoiceInfo
from server.utils.subtitle_generator import SubtitleCue


@dataclass
class TTSContext:
    """统一语音合成上下文参数包。"""

    text: str
    voice: str
    speed: float = 1.0
    pitch: float = 0.0  # 音高百分比微调 (-50.0 ~ +50.0)
    volume: float = 1.0  # 音量倍率 (0.1 ~ 2.0)
    language: str | None = None
    emotion: str | None = None
    prompt_audio_bytes: bytes | None = None
    prompt_text: str | None = None
    clone_voice_id: str | None = None
    with_subtitles: bool = False
    response_format: str = "mp3"
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class TTSResult:
    """全量合成输出载体。"""

    audio_bytes: bytes
    format: str = "mp3"
    duration_seconds: float = 0.0
    sample_rate: int = 24000
    subtitles: list[SubtitleCue] = field(default_factory=list)
    srt_content: str = ""
    vtt_content: str = ""


class BaseTTSEngine(ABC):
    """所有 TTS 引擎适配器的统一基类。"""

    def __init__(self, name: str, config: dict | None = None):
        self.name = name
        self.config = config or {}

    async def synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        response_format: str = "mp3",
    ) -> bytes:
        """保持向后兼容的简易合成接口。"""
        ctx = TTSContext(
            text=text,
            voice=voice,
            speed=speed,
            response_format=response_format,
        )
        result = await self.synthesize_with_context(ctx)
        return result.audio_bytes

    async def stream_synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        response_format: str = "mp3",
    ) -> AsyncGenerator[bytes, None]:
        """保持向后兼容的简易流式合成接口。"""
        ctx = TTSContext(
            text=text,
            voice=voice,
            speed=speed,
            response_format=response_format,
        )
        async for chunk in self.stream_synthesize_with_context(ctx):
            yield chunk

    async def synthesize_with_context(self, ctx: TTSContext) -> TTSResult:
        """带丰富上下文的高级合成接口（若子类重写了 synthesize，默认降级调用）。"""
        if type(self).synthesize != BaseTTSEngine.synthesize:
            audio_bytes = await self.synthesize(
                text=ctx.text,
                voice=ctx.voice,
                speed=ctx.speed,
                response_format=ctx.response_format,
            )
            return TTSResult(audio_bytes=audio_bytes, format=ctx.response_format)
        raise NotImplementedError(f"{self.__class__.__name__} 必须实现 synthesize 或 synthesize_with_context 至少之一")

    async def stream_synthesize_with_context(
        self,
        ctx: TTSContext,
    ) -> AsyncGenerator[bytes, None]:
        """带丰富上下文的高级流式合成接口（默认降级产出完整音频块）。"""
        res = await self.synthesize_with_context(ctx)
        yield res.audio_bytes

    @abstractmethod
    def list_voices(self) -> list[VoiceInfo]:
        """获取该引擎当前支持的发音人列表。"""
        pass
