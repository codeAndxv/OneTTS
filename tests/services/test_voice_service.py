"""测试 VoiceService 音色数据字典加载、内存缓存、双层兜底与白名单过滤。"""

import pytest
from server.schemas.voice import VoiceInfo
from server.services.voice_service import VoiceService, voice_service


def test_voice_service_cache_and_reload():
    # 测试加载与缓存
    voice_service.reload_cache()
    v1 = voice_service.get_provider_voices("edgetts")
    assert len(v1) > 0
    # 再次获取应当直接从缓存返回同一数据
    v2 = voice_service.get_provider_voices("edgetts")
    assert len(v1) == len(v2)

    # 重载缓存
    voice_service.reload_cache()
    assert len(voice_service._cache) == 0


def test_voice_service_filter_helpers():
    sample_voices = [
        VoiceInfo(
            id="v1",
            name="Voice 1",
            provider="test",
            gender="female",
            language="zh-CN",
            languages=["zh-CN", "zh"],
            is_recommended=True,
        ),
        VoiceInfo(
            id="v2",
            name="Voice 2",
            provider="test",
            gender="male",
            language="en-US",
            languages=["en-US", "en"],
            is_recommended=False,
        ),
    ]

    # 测试推荐过滤
    recs = VoiceService._apply_filters(sample_voices, recommended_only=True)
    assert len(recs) == 1
    assert recs[0].id == "v1"

    # 测试性别过滤
    males = VoiceService._apply_filters(sample_voices, gender="male")
    assert len(males) == 1
    assert males[0].id == "v2"

    # 测试语言过滤
    zh_voices = VoiceService._apply_filters(sample_voices, language="zh")
    assert len(zh_voices) == 1
    assert zh_voices[0].id == "v1"


def test_voice_service_resolve_voice():
    # 测试 OpenAI 标准音色别名解析
    p, v = voice_service.resolve_voice("edgetts", "alloy")
    assert p == "edgetts"
    assert v == "zh-CN-XiaoxiaoNeural"

    # 测试直接传真实音色
    p2, v2 = voice_service.resolve_voice("edgetts", "en-US-JennyNeural")
    assert p2 == "edgetts"
    assert v2 == "en-US-JennyNeural"
