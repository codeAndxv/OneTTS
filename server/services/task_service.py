"""长文本与多角色异步演播任务调度服务。"""

import asyncio
import json
import logging
import uuid
import zipfile
from pathlib import Path
from typing import Any
import httpx
from sqlalchemy import select, update

from server.core.config import PROJECT_ROOT
from server.db.orm_models import TTSTaskRecord
from server.db.session import async_session
from server.engines.base import TTSContext
from server.engines.registry import get_engine
from server.schemas.tts_ext import TTSTaskCreateRequest, TTSTaskDetailResponse
from server.services.voice_service import voice_service
from server.utils.subtitle_generator import SubtitleCue, generate_srt, generate_vtt, format_timestamp
from server.utils.text_splitter import split_text_into_sentences

logger = logging.getLogger(__name__)

TASKS_DIR = PROJECT_ROOT / "data" / "outputs" / "tasks"


class TaskService:
    """管理异步长文本与多角色演播任务。"""

    def __init__(self):
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        self._cancelled_tasks: set[str] = set()

    async def create_task(self, req: TTSTaskCreateRequest) -> TTSTaskDetailResponse:
        """创建并入队异步长文/剧本任务。"""
        task_id = f"tts_task_{uuid.uuid4().hex[:12]}"

        # 1. 解析任务分段 (优先剧本 dialogue，兜底单篇长文本切句)
        segments: list[dict[str, Any]] = []
        if req.dialogue:
            for item in req.dialogue:
                if item.text and item.text.strip():
                    segments.append({
                        "speaker": item.speaker or "默认",
                        "voice": item.voice or req.default_voice,
                        "text": item.text.strip(),
                    })
        elif req.text:
            raw_sentences = split_text_into_sentences(req.text)
            for s in raw_sentences:
                segments.append({
                    "speaker": "默认",
                    "voice": req.default_voice,
                    "text": s,
                })

        if not segments:
            segments = [{"speaker": "默认", "voice": req.default_voice, "text": "无文本内容"}]

        async with async_session() as session:
            record = TTSTaskRecord(
                id=task_id,
                title=req.title,
                model=req.model,
                voice=req.default_voice,
                status="pending",
                progress=0.0,
                total_segments=len(segments),
                completed_segments=0,
                dialogue_json=json.dumps(segments, ensure_ascii=False),
                webhook_url=req.webhook_url,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)

        # 异步启动后台合成处理协程
        asyncio.create_task(self._process_task(task_id, segments, req))

        return self._to_detail_response(record)

    async def _process_task(
        self,
        task_id: str,
        segments: list[dict[str, Any]],
        req: TTSTaskCreateRequest,
    ):
        """后台异步执行多段合成、音轨拼接与字幕生成。"""
        logger.info("[task_worker] 开始执行任务: %s (%d 个段落)", task_id, len(segments))

        async with async_session() as session:
            await session.execute(
                update(TTSTaskRecord)
                .where(TTSTaskRecord.id == task_id)
                .values(status="running")
            )
            await session.commit()

        audio_parts: list[bytes] = []
        combined_cues: list[SubtitleCue] = []
        current_time_offset = 0.0

        try:
            for idx, seg in enumerate(segments, start=1):
                # 检查是否已被用户手动取消
                if task_id in self._cancelled_tasks:
                    logger.info("[task_worker] 任务 %s 已被用户取消", task_id)
                    self._cancelled_tasks.discard(task_id)
                    async with async_session() as session:
                        await session.execute(
                            update(TTSTaskRecord)
                            .where(TTSTaskRecord.id == task_id)
                            .values(status="cancelled", error_message="Task cancelled by user")
                        )
                        await session.commit()
                    return

                provider_name, actual_voice = voice_service.resolve_voice(req.model, seg["voice"])
                engine = get_engine(provider_name)

                ctx = TTSContext(
                    text=seg["text"],
                    voice=actual_voice,
                    speed=req.speed,
                    pitch=req.pitch,
                    volume=req.volume,
                    with_subtitles=req.with_subtitles,
                    response_format=req.response_format,
                )

                res = await engine.synthesize_with_context(ctx)
                audio_parts.append(res.audio_bytes)

                # 累加字幕时间轴
                seg_duration = max(res.duration_seconds, 0.5)
                seg_start = current_time_offset
                seg_end = current_time_offset + seg_duration

                combined_cues.append(
                    SubtitleCue(
                        index=idx,
                        text=f"[{seg['speaker']}] {seg['text']}" if seg["speaker"] != "默认" else seg["text"],
                        start_seconds=round(seg_start, 3),
                        end_seconds=round(seg_end, 3),
                        start_time=format_timestamp(seg_start, ","),
                        end_time=format_timestamp(seg_end, ","),
                    )
                )
                current_time_offset = seg_end

                # 更新进度
                progress = round(100.0 * idx / len(segments), 1)
                async with async_session() as session:
                    await session.execute(
                        update(TTSTaskRecord)
                        .where(TTSTaskRecord.id == task_id)
                        .values(completed_segments=idx, progress=progress)
                    )
                    await session.commit()

            # 合并产物落盘
            final_audio = b"".join(audio_parts)
            audio_filename = f"{task_id}.{req.response_format}"
            audio_path = TASKS_DIR / audio_filename
            audio_path.write_bytes(final_audio)

            srt_path_str: str | None = None
            if req.with_subtitles:
                srt_content = generate_srt(combined_cues)
                srt_path = TASKS_DIR / f"{task_id}.srt"
                srt_path.write_text(srt_content, encoding="utf-8")
                srt_path_str = str(srt_path)

            total_duration = round(current_time_offset, 2)

            async with async_session() as session:
                await session.execute(
                    update(TTSTaskRecord)
                    .where(TTSTaskRecord.id == task_id)
                    .values(
                        status="completed",
                        progress=100.0,
                        audio_path=str(audio_path),
                        srt_path=srt_path_str,
                        duration_seconds=total_duration,
                    )
                )
                await session.commit()

            logger.info("[task_worker] 任务 %s 执行完成, 总时长: %.2f 秒", task_id, total_duration)

            # Webhook 回调通知
            if req.webhook_url:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        await client.post(
                            req.webhook_url,
                            json={"task_id": task_id, "status": "completed", "duration": total_duration},
                        )
                except Exception as e:
                    logger.warning("[task_worker] Webhook 通知失败: %s", e)

        except Exception as e:
            logger.error("[task_worker] 任务 %s 执行失败: %s", task_id, e, exc_info=True)
            async with async_session() as session:
                await session.execute(
                    update(TTSTaskRecord)
                    .where(TTSTaskRecord.id == task_id)
                    .values(status="failed", error_message=str(e))
                )
                await session.commit()

    async def get_task(self, task_id: str) -> TTSTaskDetailResponse | None:
        """获取单个任务详情。"""
        async with async_session() as session:
            result = await session.execute(select(TTSTaskRecord).where(TTSTaskRecord.id == task_id))
            record = result.scalar_one_or_none()
            if not record:
                return None
            return self._to_detail_response(record)

    async def list_tasks(self, status: str | None = None, limit: int = 50) -> list[TTSTaskDetailResponse]:
        """获取任务列表。"""
        async with async_session() as session:
            stmt = select(TTSTaskRecord).order_by(TTSTaskRecord.created_at.desc()).limit(limit)
            if status:
                stmt = stmt.where(TTSTaskRecord.status == status)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [self._to_detail_response(r) for r in records]

    async def cancel_task(self, task_id: str) -> bool:
        """标记取消任务。"""
        self._cancelled_tasks.add(task_id)
        async with async_session() as session:
            await session.execute(
                update(TTSTaskRecord)
                .where(TTSTaskRecord.id == task_id, TTSTaskRecord.status == "pending")
                .values(status="cancelled", error_message="Cancelled by user before running")
            )
            await session.commit()
        return True

    async def get_download_file(self, task_id: str, format_type: str = "audio") -> tuple[Path | None, str]:
        """获取产物下载路径与文件名（支持单独音频或打包 ZIP）。"""
        async with async_session() as session:
            result = await session.execute(select(TTSTaskRecord).where(TTSTaskRecord.id == task_id))
            record = result.scalar_one_or_none()
            if not record or record.status != "completed" or not record.audio_path:
                return None, ""

        audio_p = Path(record.audio_path)
        if not audio_p.exists():
            return None, ""

        if format_type.lower() == "zip":
            zip_p = TASKS_DIR / f"{task_id}_bundle.zip"
            with zipfile.ZipFile(zip_p, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(audio_p, arcname=audio_p.name)
                if record.srt_path:
                    srt_p = Path(record.srt_path)
                    if srt_p.exists():
                        zf.write(srt_p, arcname=srt_p.name)
            return zip_p, f"{record.title or task_id}.zip"

        return audio_p, audio_p.name

    @staticmethod
    def _to_detail_response(r: TTSTaskRecord) -> TTSTaskDetailResponse:
        return TTSTaskDetailResponse(
            task_id=r.id,
            title=r.title,
            model=r.model,
            status=r.status,  # type: ignore
            progress=r.progress or 0.0,
            total_segments=r.total_segments or 0,
            completed_segments=r.completed_segments or 0,
            duration_seconds=r.duration_seconds or 0.0,
            audio_url=f"/v1/tts/tasks/{r.id}/download?format=audio" if r.audio_path else None,
            srt_url=f"/v1/tts/tasks/{r.id}/download?format=zip" if r.srt_path else None,
            error_message=r.error_message,
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else "",
        )


task_service = TaskService()
