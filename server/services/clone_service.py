"""声音克隆资产库管理服务。"""

import logging
import uuid
from pathlib import Path
from sqlalchemy import select, delete

from server.core.config import PROJECT_ROOT
from server.db.orm_models import VoiceCloneRecord
from server.db.session import async_session
from server.schemas.tts_ext import VoiceCloneCreateResponse, VoiceCloneItem

logger = logging.getLogger(__name__)

CLONES_DIR = PROJECT_ROOT / "data" / "outputs" / "clones"


class CloneService:
    """管理持久化声音克隆资产。"""

    def __init__(self):
        CLONES_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    async def register_clone(
        name: str,
        description: str | None,
        language: str,
        prompt_text: str | None,
        audio_bytes: bytes,
        filename: str = "sample.wav",
    ) -> VoiceCloneCreateResponse:
        """保存参考音频并注册持久化克隆声音。"""
        clone_id = f"clone_{uuid.uuid4().hex[:10]}"
        ext = Path(filename).suffix or ".wav"
        save_path = CLONES_DIR / f"{clone_id}{ext}"
        save_path.write_bytes(audio_bytes)

        sample_url = f"/v1/x/voices/clones/{clone_id}/sample"

        async with async_session() as session:
            record = VoiceCloneRecord(
                id=clone_id,
                name=name,
                description=description,
                language=language or "zh-CN",
                prompt_text=prompt_text,
                audio_path=str(save_path),
                sample_url=sample_url,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)

        logger.info("[clone_service] 成功注册克隆声音: %s (%s)", name, clone_id)
        return VoiceCloneCreateResponse(
            clone_voice_id=record.id,
            name=record.name,
            language=record.language,
            sample_url=sample_url,
            created_at=record.created_at.isoformat(),
        )

    @staticmethod
    async def list_clones() -> list[VoiceCloneItem]:
        """获取所有已保存的克隆音色。"""
        async with async_session() as session:
            result = await session.execute(select(VoiceCloneRecord).order_by(VoiceCloneRecord.created_at.desc()))
            records = result.scalars().all()

        return [
            VoiceCloneItem(
                id=r.id,
                name=r.name,
                description=r.description,
                language=r.language,
                prompt_text=r.prompt_text,
                sample_url=r.sample_url,
                created_at=r.created_at.isoformat(),
            )
            for r in records
        ]

    @staticmethod
    async def delete_clone(clone_id: str) -> bool:
        """删除指定的克隆音色及其物理音频文件。"""
        async with async_session() as session:
            result = await session.execute(select(VoiceCloneRecord).where(VoiceCloneRecord.id == clone_id))
            record = result.scalar_one_or_none()
            if not record:
                return False

            if record.audio_path:
                p = Path(record.audio_path)
                if p.exists():
                    try:
                        p.unlink()
                    except Exception as e:
                        logger.warning("删除克隆音频文件失败: %s, 错误: %s", p, e)

            await session.execute(delete(VoiceCloneRecord).where(VoiceCloneRecord.id == clone_id))
            await session.commit()
        return True

    @staticmethod
    async def get_clone_audio_bytes(clone_id: str) -> bytes | None:
        """获取克隆样本音频二进制。"""
        async with async_session() as session:
            result = await session.execute(select(VoiceCloneRecord).where(VoiceCloneRecord.id == clone_id))
            record = result.scalar_one_or_none()
            if not record or not record.audio_path:
                return None

        p = Path(record.audio_path)
        if p.exists():
            return p.read_bytes()
        return None

    @staticmethod
    async def get_clone_file_path(clone_id: str) -> Path | None:
        """获取克隆样本文件路径。"""
        async with async_session() as session:
            result = await session.execute(select(VoiceCloneRecord).where(VoiceCloneRecord.id == clone_id))
            record = result.scalar_one_or_none()
            if not record or not record.audio_path:
                return None

        p = Path(record.audio_path)
        return p if p.exists() else None


clone_service = CloneService()
