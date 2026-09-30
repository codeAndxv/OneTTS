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
