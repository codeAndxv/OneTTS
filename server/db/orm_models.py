"""数据库 ORM 模型。"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from server.db.base import Base


def _utc_now():
    return datetime.now(timezone.utc)


class VoiceRecord(Base):
    """音色实体模型。"""

    __tablename__ = "voices"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    voice_id = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    provider = Column(String(64), nullable=False, index=True)
    language = Column(String(32), default="zh-CN")
    gender = Column(String(16), default="neutral")
    preview_url = Column(String(256), nullable=True)
    description = Column(Text, nullable=True)
    is_custom = Column(Integer, default=0)  # 0: 系统内置, 1: 用户克隆
    created_at = Column(DateTime, default=_utc_now)


class SynthesisLog(Base):
    """合成请求历史日志。"""

    __tablename__ = "synthesis_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(64), nullable=False)
    model = Column(String(64), nullable=False)
    voice = Column(String(128), nullable=False)
    text_length = Column(Integer, default=0)
    speed = Column(Float, default=1.0)
    response_format = Column(String(16), default="mp3")
    duration_sec = Column(Float, default=0.0)
    cached = Column(Integer, default=0)  # 0: 实时合成, 1: 命中缓存
    created_at = Column(DateTime, default=_utc_now)


class TTSTaskRecord(Base):
    """异步长文与多角色演播任务表。"""

    __tablename__ = "tts_tasks"

    id = Column(String(64), primary_key=True, default=lambda: f"tts_task_{uuid.uuid4().hex[:12]}")
    title = Column(String(256), nullable=False)
    model = Column(String(64), nullable=False)
    voice = Column(String(128), nullable=False)
    status = Column(String(32), default="pending", index=True)  # pending, running, completed, failed, cancelled
    progress = Column(Float, default=0.0)
    total_segments = Column(Integer, default=0)
    completed_segments = Column(Integer, default=0)
    dialogue_json = Column(Text, nullable=True)
    audio_path = Column(String(512), nullable=True)
    srt_path = Column(String(512), nullable=True)
    duration_seconds = Column(Float, default=0.0)
    webhook_url = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)


class VoiceCloneRecord(Base):
    """持久化克隆声音资产库。"""

    __tablename__ = "voice_clones"

    id = Column(String(64), primary_key=True, default=lambda: f"clone_{uuid.uuid4().hex[:10]}")
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    language = Column(String(32), default="zh-CN")
    prompt_text = Column(Text, nullable=True)
    audio_path = Column(String(512), nullable=False)
    sample_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=_utc_now)

