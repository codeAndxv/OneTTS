"""OneTTS 异步长文与多角色演播任务路由 /v1/tts/tasks。"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from server.api.auth import get_api_key
from server.schemas.tts_ext import TTSTaskCreateRequest, TTSTaskDetailResponse
from server.services.task_service import task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/tts", tags=["tts_tasks"], dependencies=[Depends(get_api_key)])


@router.post("/tasks", response_model=TTSTaskDetailResponse)
async def create_tts_task(req: TTSTaskCreateRequest):
    """创建异步长文本/多角色演播任务。"""
    try:
        return await task_service.create_task(req)
    except Exception as e:
        logger.error("[tts_tasks] 创建任务失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/tasks", response_model=list[TTSTaskDetailResponse])
async def list_tts_tasks(
    status: str | None = Query(default=None, description="任务状态过滤: pending, running, completed, failed, cancelled"),
    limit: int = Query(default=50, ge=1, le=200, description="最大返回数量"),
):
    """获取任务列表。"""
    return await task_service.list_tasks(status=status, limit=limit)


@router.get("/tasks/{task_id}", response_model=TTSTaskDetailResponse)
async def get_tts_task(task_id: str):
    """获取指定任务的详细状态与进度。"""
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("/tasks/{task_id}/cancel")
async def cancel_tts_task(task_id: str):
    """取消排队或正在执行的异步任务。"""
    success = await task_service.cancel_task(task_id)
    return {"task_id": task_id, "cancelled": success}


@router.get("/tasks/{task_id}/download")
async def download_tts_task_asset(
    task_id: str,
    format: str = Query(default="audio", description="下载类型: 'audio' 单独音频文件, 'zip' 包含音频与字幕的压缩包"),
):
    """下载任务合成的音频产物或字幕打包文件。"""
    file_path, filename = await task_service.get_download_file(task_id, format_type=format)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="产物文件不存在或任务尚未执行完成")

    media_type = "application/zip" if format.lower() == "zip" else "application/octet-stream"
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
    )
