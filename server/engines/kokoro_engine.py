"""Kokoro ONNX 82M 轻量本地 TTS 引擎适配器。"""

import logging
from typing import AsyncGenerator
from server.engines.base import BaseTTSEngine
from server.schemas.voice import VoiceInfo

logger = logging.getLogger(__name__)

KOKORO_VOICES = [
    VoiceInfo(id="af_bella", name="Bella (US Female)", provider="kokoro", language="en-US", gender="female", description="Kokoro natural female"),
    VoiceInfo(id="am_adam", name="Adam (US Male)", provider="kokoro", language="en-US", gender="male", description="Kokoro natural male"),
    VoiceInfo(id="zf_xiaoyan", name="小燕 (Mandarin Female)", provider="kokoro", language="zh-CN", gender="female", description="Kokoro 中文女声"),
    VoiceInfo(id="zm_yifan", name="一凡 (Mandarin Male)", provider="kokoro", language="zh-CN", gender="male", description="Kokoro 中文男声"),
]


class KokoroEngine(BaseTTSEngine):
    """Kokoro-82M ONNX 引擎插槽。"""

    def __init__(self, name: str = "kokoro", config: dict | None = None):
        super().__init__(name, config)
        self.model_path = self.config.get("model_path", "")
        self.voices_path = self.config.get("voices_path", "")
        self._session = None

    async def synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        response_format: str = "mp3",
    ) -> bytes:
        raise NotImplementedError("Kokoro 引擎模型文件未下载或处于离线插槽模式。请在 config.yaml 中配置 model_path 或使用 edgetts 引擎。")

    async def stream_synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        response_format: str = "mp3",
    ) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError("Kokoro 引擎未激活。")
        yield b""  # pragma: no cover

    def list_voices(self) -> list[VoiceInfo]:
        return list(KOKORO_VOICES)
