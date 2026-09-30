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
    assert res == b"DUMMY_AUDIO"

    chunks = []
    async for chunk in engine.stream_synthesize("test", "dummy_v"):
        chunks.append(chunk)
    assert chunks == [b"CHUNK_1", b"CHUNK_2"]
