"""OneTTS 发音人音色与声音克隆资产管理路由 (/v1/x/voices)。"""

import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from server.api.auth import get_api_key
from server.schemas.tts_ext import VoiceCloneCreateResponse, VoiceCloneItem
from server.schemas.voice import VoiceListResponse
from server.services.clone_service import clone_service
from server.services.voice_service import voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/x/voices", tags=["Voices-Extended"], dependencies=[Depends(get_api_key)])

# ── 发音人音色探索 ──────────────────────────────────────────────────────────

@router.get("", response_model=VoiceListResponse)
async def list_voices(
    provider: str | None = Query(default=None, description="按提供商/引擎过滤 (如 edgetts, kokoro, doubao, clone)"),
    language: str | None = Query(default=None, description="按语言代码过滤 (如 zh, zh-CN, en, ja)"),
    gender: str | None = Query(default=None, description="按性别过滤: female, male, neutral"),
    recommended_only: bool = Query(default=False, description="仅返回精选推荐音色"),
):
    """获取系统当前发音人音色列表，支持语言、性别、推荐标签多维过滤 (/v1/x/voices)。"""
    voices = await voice_service.get_all_voices(
        provider=provider,
        language=language,
        gender=gender,
        recommended_only=recommended_only,
    )
    return VoiceListResponse(voices=voices, total=len(voices))


# ── 声音克隆资产管理 (/v1/x/voices/clones) ──────────────────────────────────

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
        logger.error("[x_voices] 注册声音失败: %s", e, exc_info=True)
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
