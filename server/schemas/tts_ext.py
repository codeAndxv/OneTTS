"""OneTTS 专属高级扩展体系 Schemas (/v1/tts/...)。"""

from typing import Literal
from pydantic import BaseModel, Field


class SubtitleCueItem(BaseModel):
    """单条字幕/时间轴信息。"""

    index: int = Field(..., description="字幕序号，从 1 开始")
    text: str = Field(..., description="字幕文本")
    start_time: str = Field(..., description="起始时间格式，如 '00:00:01,200'")
    end_time: str = Field(..., description="结束时间格式，如 '00:00:03,500'")
    start_seconds: float = Field(..., description="起始秒数浮点数")
    end_seconds: float = Field(..., description="结束秒数浮点数")


class TTSGenerateRequest(BaseModel):
    """/v1/tts/generate 高级语音合成入参定义。"""

    model: str = Field(
        default="edgetts",
        description="目标 TTS 引擎或模型标识 (如 'edgetts', 'kokoro', 'openai')",
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=65536,
        description="待合成的文本内容",
    )
    voice: str = Field(
        default="alloy",
        description="目标发音人或别名 (如 'zh-CN-XiaoxiaoNeural', 'alloy')",
    )
    response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = Field(
        default="mp3",
        description="音频输出编码格式",
    )
    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="语速倍率，默认 1.0 (0.25 ~ 4.0)",
    )
    pitch: float = Field(
        default=0.0,
        ge=-50.0,
        le=50.0,
        description="音高微调百分比 (-50.0 ~ +50.0)，默认 0.0",
    )
    volume: float = Field(
        default=1.0,
        ge=0.1,
        le=2.0,
        description="音量倍率 (0.1 ~ 2.0)，默认 1.0",
    )
    language: str | None = Field(
        default=None,
        description="指定目标语种代码 (如 'zh', 'en', 'ja', 'yue')",
    )
    emotion: str | None = Field(
        default="neutral",
        description="情感风格 (如 'neutral', 'happy', 'sad', 'angry', 'whisper', 'storytelling')",
    )
    prompt_audio: str | None = Field(
        default=None,
        description="零样本克隆参考音频 (支持公开 HTTP URL 或 Base64 字符串)",
    )
    prompt_text: str | None = Field(
        default=None,
        description="零样本克隆参考音频对应的台词内容",
    )
    clone_voice_id: str | None = Field(
        default=None,
        description="已注册的专属克隆音色 ID",
    )
    with_subtitles: bool = Field(
        default=True,
        description="是否同步生成高精度句级/词级字幕与 SRT/VTT 文件",
    )
    output_mode: Literal["json", "audio"] = Field(
        default="json",
        description="返回模式：'json' 返回结构化元数据与 Base64 音频；'audio' 直接流式返回音频二进制",
    )


class TTSGenerateResponse(BaseModel):
    """/v1/tts/generate 结构化响应实体。"""

    audio_base64: str = Field(..., description="音频文件的 Base64 编码数据")
    audio_format: str = Field(default="mp3", description="音频文件格式")
    audio_duration_seconds: float = Field(default=0.0, description="合成音频总时长（秒）")
    sample_rate: int = Field(default=24000, description="音频采样率")
    subtitles: list[SubtitleCueItem] = Field(default_factory=list, description="字幕条目列表")
    srt_content: str = Field(default="", description="标准 SRT 格式字幕纯文本")
    vtt_content: str = Field(default="", description="标准 WebVTT 格式字幕纯文本")


class TTSDialogueSegment(BaseModel):
    """多角色剧本对话分段。"""

    speaker: str | None = Field(default=None, description="角色名或发音人代号 (如 '旁白', '角色A')")
    voice: str | None = Field(default=None, description="专属发音人或音色")
    text: str = Field(..., min_length=1, description="角色对应台词段落")


class TTSTaskCreateRequest(BaseModel):
    """/v1/tts/tasks 异步任务创建请求。"""

    title: str = Field(default="TTS 长文本合成任务", description="任务标题")
    model: str = Field(default="edgetts", description="TTS 模型标识")
    default_voice: str = Field(default="alloy", description="默认音色")
    response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = Field(
        default="mp3",
        description="合成产物音频格式",
    )
    speed: float = Field(default=1.0, ge=0.25, le=4.0, description="默认语速")
    pitch: float = Field(default=0.0, ge=-50.0, le=50.0, description="默认音高")
    volume: float = Field(default=1.0, ge=0.1, le=2.0, description="默认音量")
    with_subtitles: bool = Field(default=True, description="是否同时生成配套字幕")
    text: str | None = Field(default=None, description="单篇长文本全文 (与 dialogue 二选一)")
    dialogue: list[TTSDialogueSegment] | None = Field(default=None, description="多角色剧本分段数组")
    webhook_url: str | None = Field(default=None, description="任务完成后的 Webhook 通知地址")


class TTSTaskDetailResponse(BaseModel):
    """/v1/tts/tasks/{id} 任务详情与进度。"""

    task_id: str
    title: str
    model: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    progress: float = Field(default=0.0, description="任务进度百分比 0.0 ~ 100.0")
    total_segments: int = 0
    completed_segments: int = 0
    duration_seconds: float = 0.0
    audio_url: str | None = None
    srt_url: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str


class VoiceCloneCreateResponse(BaseModel):
    """/v1/tts/clones 注册音色响应。"""

    clone_voice_id: str
    name: str
    language: str
    sample_url: str | None = None
    created_at: str


class VoiceCloneItem(BaseModel):
    """声音克隆库列表项。"""

    id: str
    name: str
    description: str | None = None
    language: str = "zh-CN"
    prompt_text: str | None = None
    sample_url: str | None = None
    created_at: str
