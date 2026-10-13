"""音色管理数据模型 (Voice Schemas)。"""

from pydantic import BaseModel, Field


class VoiceInfo(BaseModel):
    """发音人音色元数据模型。"""

    id: str = Field(..., description="唯一音色 ID (如 zh-CN-XiaoxiaoNeural, alloy, af_bella)")
    name: str = Field(..., description="音色显示名称 (如 晓晓, Alloy)")
    provider: str = Field(..., description="所属引擎/提供商标识 (edgetts, kokoro, doubao 等)")
    gender: str = Field(default="neutral", description="发音人性别: female, male, neutral")
    language: str = Field(default="zh-CN", description="主要语言代码 (如 zh-CN, en-US, ja-JP)")
    languages: list[str] = Field(default_factory=list, description="支持的多语言代码列表")
    category: str | None = Field(default=None, description="场景分类 (如通用, 新闻, 情感, 方言, 动漫, 助手)")
    tags: list[str] = Field(default_factory=list, description="场景与特性标签 (如 [\"新闻\", \"小说\", \"温柔\"])")
    styles: list[str] = Field(default_factory=list, description="支持的情感或语气风格列表 (如 [\"cheerful\", \"sad\"])")
    description: str | None = Field(default=None, description="音色特点介绍")
    preview_url: str | None = Field(default=None, description="试听音频 URL 或本地相对路径")
    is_recommended: bool = Field(default=False, description="是否精选推荐 (置顶展示)")
    is_clone: bool = Field(default=False, description="是否为声音克隆自定义音色")


class VoiceListResponse(BaseModel):
    """发音人列表响应模型。"""

    voices: list[VoiceInfo]
    total: int
