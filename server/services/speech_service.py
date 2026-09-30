"""语音合成核心调度与编排服务。"""

import logging
from typing import AsyncGenerator

from server.core.cache import cache_manager
from server.engines.registry import get_engine
from server.schemas.speech import SpeechRequest
from server.services.voice_service import voice_service
from server.utils.text_splitter import split_text_into_sentences

logger = logging.getLogger(__name__)


class SpeechService:
    """语音合成服务。"""

    @staticmethod
    async def synthesize_speech(req: SpeechRequest) -> bytes:
        """全量合成语音，带缓存拦截。"""
        provider_name, actual_voice = voice_service.resolve_voice(req.model, req.voice)
        cache_key = cache_manager.compute_cache_key(
            provider=provider_name,
            voice=actual_voice,
            text=req.input,
            speed=req.speed,
            response_format=req.response_format,
        )

        # 1. 命中缓存直接返回
        cached_audio = cache_manager.get(cache_key, req.response_format)
        if cached_audio is not None:
            logger.debug("[cache_hit] Key: %s", cache_key)
            return cached_audio

        # 2. 调用底层引擎合成
        engine = get_engine(provider_name)
        audio_bytes = await engine.synthesize(
            text=req.input,
            voice=actual_voice,
            speed=req.speed,
            response_format=req.response_format,
        )

        # 3. 异步/安全回填缓存
        cache_manager.put(cache_key, req.response_format, audio_bytes)
        return audio_bytes

    @staticmethod
    async def stream_speech(req: SpeechRequest) -> AsyncGenerator[bytes, None]:
        """流式合成音频，支持长文本分句流式预热。"""
        provider_name, actual_voice = voice_service.resolve_voice(req.model, req.voice)
        engine = get_engine(provider_name)

        sentences = split_text_into_sentences(req.input)
        if not sentences:
            return

        # 如果单句且文本简短，直接使用引擎流式
        if len(sentences) == 1:
            async for chunk in engine.stream_synthesize(
                text=sentences[0],
                voice=actual_voice,
                speed=req.speed,
                response_format=req.response_format,
            ):
                yield chunk
            return

        # 多句按流水线依次流式合成并持续吐出 Chunk
        for sentence in sentences:
            async for chunk in engine.stream_synthesize(
                text=sentence,
                voice=actual_voice,
                speed=req.speed,
                response_format=req.response_format,
            ):
                yield chunk


speech_service = SpeechService()
