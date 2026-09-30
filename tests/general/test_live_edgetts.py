"""Edge-TTS 真实网络调用集成测试 (带 @pytest.mark.integration 标记)。"""

import pytest
from server.engines.edgetts_engine import EdgeTTSEngine


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_edgetts_synthesis():
    engine = EdgeTTSEngine()
    audio = await engine.synthesize("你好，OneTTS！", voice="zh-CN-XiaoxiaoNeural", speed=1.0)
    assert len(audio) > 1000  # 真实生成的 MP3 数据


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_edgetts_streaming():
    engine = EdgeTTSEngine()
    chunks = []
    async for chunk in engine.stream_synthesize("流式测试语音。", voice="zh-CN-YunxiNeural", speed=1.1):
        chunks.append(chunk)
    assert len(chunks) > 0
    total_len = sum(len(c) for c in chunks)
    assert total_len > 1000
