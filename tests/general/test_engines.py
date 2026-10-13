"""测试 TTS 引擎注册与工厂机制。"""

import pytest
from server.engines.base import BaseTTSEngine
from server.engines.registry import get_engine, list_available_providers, register_engine_class
from server.schemas.voice import VoiceInfo


class DummyEngine(BaseTTSEngine):
    async def synthesize(self, text, voice, speed=1.0, response_format="mp3"):
        return b"DUMMY_AUDIO"

    async def stream_synthesize(self, text, voice, speed=1.0, response_format="mp3"):
        yield b"CHUNK_1"
        yield b"CHUNK_2"

    def list_voices(self):
        return [VoiceInfo(id="dummy_v", name="Dummy Voice", provider="dummy")]


def test_registry_and_dummy_engine():
    register_engine_class("dummy", DummyEngine)
    # 动态注入一个 provider 配置
    from server.core.config import app_config, EngineConfig
    app_config.providers["dummy_prov"] = EngineConfig("dummy_prov", {"enable": True, "engine": "dummy"})

    engine = get_engine("dummy_prov")
    assert isinstance(engine, DummyEngine)
    assert len(engine.list_voices()) == 1


@pytest.mark.asyncio
async def test_dummy_synthesize():
    engine = get_engine("dummy_prov")
    res = await engine.synthesize("test", "dummy_v")
    chunks = []
    async for chunk in engine.stream_synthesize("test", "dummy_v"):
        chunks.append(chunk)
    assert chunks == [b"CHUNK_1", b"CHUNK_2"]


def test_cosyvoice_engine_voices():
    from server.engines.cosyvoice_engine import CosyVoiceEngine
    engine = CosyVoiceEngine("cosyvoice", {"default_voice": "cosyvoice-chinese-female"})
    voices = engine.list_voices()
    assert len(voices) >= 2
    voice_ids = [v.id for v in voices]
    assert "cosyvoice-chinese-female" in voice_ids
    assert "cosyvoice-clone" in voice_ids


def test_f5tts_engine_voices_and_synthesis():
    """测试 F5-TTS 引擎发音人列表、声音克隆参数构造与合成。"""
    from server.engines.f5tts_engine import F5TTSEngine
    from server.engines.base import TTSContext
    import asyncio

    engine = F5TTSEngine("f5tts", {"default_voice": "f5-chinese-female"})
    voices = engine.list_voices()
    assert len(voices) >= 3
    voice_ids = [v.id for v in voices]
    assert "f5-chinese-female" in voice_ids
    assert "f5-chinese-male" in voice_ids
    assert "f5-clone" in voice_ids

    # 测试带参考音频的零样本声音克隆合成与字幕
    ctx = TTSContext(
        text="Hello world, testing F5-TTS voice cloning.",
        voice="f5-clone",
        prompt_audio_bytes=b"RIFF" + b"\x00" * 2000,
        prompt_text="Sample reference speech",
        with_subtitles=True,
        response_format="wav",
    )
    result = asyncio.run(engine.synthesize_with_context(ctx))
    assert len(result.audio_bytes) > 0
    assert result.format == "wav"
    assert result.duration_seconds > 0
    assert len(result.subtitles) > 0
    assert len(result.srt_content) > 0


def test_doubao_engine_voices_and_synthesis():
    """测试火山引擎 / 豆包语音合成大模型发音人与合成。"""
    from server.engines.doubao_engine import DoubaoEngine
    from server.engines.base import TTSContext
    import asyncio

    engine = DoubaoEngine("doubao", {
        "appid": "mock_appid",
        "access_token": "mock_token",
        "default_voice": "zh_female_shuangkuai",
    })
    voices = engine.list_voices()
    assert len(voices) >= 5
    voice_ids = [v.id for v in voices]
    assert "zh_female_shuangkuai" in voice_ids
    assert "zh_male_chunhou" in voice_ids
    assert "zh_male_dongbeikouyin" in voice_ids

    ctx = TTSContext(
        text="欢迎使用豆包语音大模型合成能力。",
        voice="zh_female_shuangkuai",
        with_subtitles=True,
        response_format="mp3",
    )
    result = asyncio.run(engine.synthesize_with_context(ctx))
    assert len(result.audio_bytes) > 0
    assert result.format == "mp3"
    assert result.duration_seconds > 0
    assert len(result.subtitles) > 0


def test_engine_registry_contains_f5_and_doubao():
    """验证注册表中已收录 f5tts 与 doubao。"""
    from server.engines.registry import _ENGINE_CLASSES
    from server.engines.f5tts_engine import F5TTSEngine
    from server.engines.doubao_engine import DoubaoEngine

    assert _ENGINE_CLASSES["f5tts"] is F5TTSEngine
    assert _ENGINE_CLASSES["doubao"] is DoubaoEngine
