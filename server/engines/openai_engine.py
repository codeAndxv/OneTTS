"""OpenAI TTS 官方/第三方兼容接口转发引擎。"""

import logging
from typing import AsyncGenerator
import httpx

from server.engines.base import BaseTTSEngine, TTSContext, TTSResult
from server.schemas.voice import VoiceInfo

logger = logging.getLogger(__name__)

OPENAI_VOICES = [
    VoiceInfo(id="alloy", name="Alloy", provider="openai", language="multi", gender="neutral", description="OpenAI Alloy voice"),
    VoiceInfo(id="echo", name="Echo", provider="openai", language="multi", gender="male", description="OpenAI Echo voice"),
    VoiceInfo(id="fable", name="Fable", provider="openai", language="multi", gender="male", description="OpenAI Fable voice"),
    VoiceInfo(id="onyx", name="Onyx", provider="openai", language="multi", gender="male", description="OpenAI Onyx voice"),
    VoiceInfo(id="nova", name="Nova", provider="openai", language="multi", gender="female", description="OpenAI Nova voice"),
    VoiceInfo(id="shimmer", name="Shimmer", provider="openai", language="multi", gender="female", description="OpenAI Shimmer voice"),
]


class OpenAITTSEngine(BaseTTSEngine):
    """OpenAI 协议中继引擎。"""

    def __init__(self, name: str = "openai", config: dict | None = None):
        super().__init__(name, config)
        self.base_url = (self.config.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = self.config.get("api_key") or ""
        self.default_model = (self.config.get("models") or ["tts-1"])[0]

    async def synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        response_format: str = "mp3",
    ) -> bytes:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.default_model,
            "input": text,
            "voice": voice or "alloy",
            "response_format": response_format,
            "speed": speed,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/audio/speech", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.content

    async def synthesize_with_context(self, ctx: TTSContext) -> TTSResult:
        audio_bytes = await self.synthesize(
            text=ctx.text,
            voice=ctx.voice,
            speed=ctx.speed,
            response_format=ctx.response_format,
        )
        dur = max(round(len(ctx.text) / (4.0 * ctx.speed), 3), 0.5)
        cues = []
        srt_text = ""
        vtt_text = ""
        if ctx.with_subtitles:
            from server.utils.subtitle_generator import build_cues_from_sentences, generate_srt, generate_vtt
            from server.utils.text_splitter import split_text_into_sentences

            sentences = split_text_into_sentences(ctx.text)
            if sentences:
                total_chars = max(sum(len(s) for s in sentences), 1)
                durations = [(len(s) / total_chars) * dur for s in sentences]
                cues = build_cues_from_sentences(sentences, durations)
                srt_text = generate_srt(cues)
                vtt_text = generate_vtt(cues)

        return TTSResult(
            audio_bytes=audio_bytes,
            format=ctx.response_format,
            duration_seconds=dur,
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
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.default_model,
            "input": text,
            "voice": voice or "alloy",
            "response_format": response_format,
            "speed": speed,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{self.base_url}/audio/speech", json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes():
                    yield chunk

    def list_voices(self) -> list[VoiceInfo]:
        return list(OPENAI_VOICES)
