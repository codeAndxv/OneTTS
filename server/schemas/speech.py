"""语音合成请求与响应 Schemas。"""

from typing import Literal
from pydantic import BaseModel, Field


class SpeechRequest(BaseModel):
    """OpenAI /v1/audio/speech 标准入参定义。"""

    model: str = Field(
        default="edgetts",
        description="TTS 模型标识，如 'tts-1', 'edgetts', 'kokoro'",
    )
    input: str = Field(
        ...,
        min_length=1,
        max_length=8192,
        description="待合成文本内容",
    )
    voice: str = Field(
        default="alloy",
        description="目标发音人音色 ID 或系统预设别名 (alloy, echo, zh-CN-XiaoxiaoNeural 等)",
    )
    response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = Field(
        default="mp3",
        description="音频输出编码格式，支持 mp3, opus, aac, flac, wav, pcm",
    )
    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="语速控制倍率，范围 0.25 ~ 4.0，默认 1.0",
    )
    stream: bool = Field(
        default=False,
        description="是否以 HTTP Chunked 数据流边生成边吐出音频",
    )
