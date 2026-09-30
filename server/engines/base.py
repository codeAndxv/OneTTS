"""TTS 引擎抽象基类。"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator
from server.schemas.voice import VoiceInfo


class BaseTTSEngine(ABC):
    """所有 TTS 引擎适配器的统一基类。"""

    def __init__(self, name: str, config: dict | None = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        response_format: str = "mp3",
    ) -> bytes:
        """全量合成文本并返回目标格式的完整音频二进制。"""
        pass

    @abstractmethod
    async def stream_synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        response_format: str = "mp3",
    ) -> AsyncGenerator[bytes, None]:
        """流式合成文本，逐块产生音频 Chunk。"""
        pass

    @abstractmethod
    def list_voices(self) -> list[VoiceInfo]:
        """获取该引擎当前支持的发音人列表。"""
        pass
