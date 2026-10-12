"""OneTTS 专属声音克隆资产管理路由 /v1/tts/clones。"""

import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from server.api.auth import get_api_key
from server.schemas.tts_ext import VoiceCloneCreateResponse, VoiceCloneItem
from server.services.clone_service import clone_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/tts", tags=["tts_clones"], dependencies=[Depends(get_api_key)])


@router.post("/clones", response_model=VoiceCloneCreateResponse)
async def register_voice_clone(
    name: str = Form(..., description="克隆声音名称"),
    description: str | None = Form(default=None, description="说明与适用场景"),
    language: str = Form(default="zh-CN", description="语言代码"),
    prompt_text: str | None = Form(default=None, description="参考音频对应的台词文本"),
    file: UploadFile = File(..., description="5~15秒高品质清晰人声样本音频 (WAV/MP3)"),
):
    """注册并保存专属声音克隆资产。"""
    try:
        audio_bytes = await file.read()
        if not audio_bytes or len(audio_bytes) < 1024:
            raise HTTPException(status_code=400, detail="音频文件过小或无效")

        return await clone_service.register_clone(
            name=name,
            description=description,
            language=language,
            prompt_text=prompt_text,
            audio_bytes=audio_bytes,
            filename=file.filename or "sample.wav",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[tts_clones] 注册声音失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"注册声音失败: {str(e)}")


@router.get("/clones", response_model=list[VoiceCloneItem])
async def list_voice_clones():
    """获取所有已保存的克隆音色列表。"""
    return await clone_service.list_clones()


@router.delete("/clones/{clone_id}")
async def delete_voice_clone(clone_id: str):
    """删除指定的克隆音色资产。"""
    success = await clone_service.delete_clone(clone_id)
    if not success:
        raise HTTPException(status_code=404, detail="指定的克隆音色不存在")
    return {"clone_id": clone_id, "deleted": True}


@router.get("/clones/{clone_id}/sample")
async def get_clone_sample_audio(clone_id: str):
    """试听克隆原音样本。"""
    file_path = await clone_service.get_clone_file_path(clone_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="样本音频不存在")

    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        filename=file_path.name,
    )
