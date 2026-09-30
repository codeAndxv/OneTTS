"""音色管理 Schemas。"""

from pydantic import BaseModel, Field


class VoiceInfo(BaseModel):
    id: str = Field(..., description="唯一音色 ID")
    name: str = Field(..., description="音色名称")
    provider: str = Field(..., description="所属 Provider/引擎")
    language: str = Field(default="zh-CN", description="支持的主要语言/地区代码")
    gender: str = Field(default="neutral", description="性别分类: female, male, neutral")
    preview_url: str | None = Field(default=None, description="试听样本音频链接")
    description: str | None = Field(default=None, description="音色特点描述")
    is_custom: bool = Field(default=False, description="是否为用户克隆音色")


class VoiceListResponse(BaseModel):
    voices: list[VoiceInfo]
    total: int
