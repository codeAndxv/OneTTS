"""OneTTS 专属高级语音合成接口 POST /v1/tts/generate。"""

import base64
import logging
from fastapi import APIRouter, Depends, HTTPException, Response

from server.api.auth import get_api_key
from server.schemas.tts_ext import TTSGenerateRequest, TTSGenerateResponse, SubtitleCueItem
from server.services.speech_service import speech_service
from server.utils.audio_encoder import get_mime_type

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/tts", tags=["tts_ext"], dependencies=[Depends(get_api_key)])


@router.post("/generate")
async def generate_advanced_speech(req: TTSGenerateRequest):
    """高级语音合成端点：支持字幕、音高音量、语种与音色克隆。"""
    try:
        res = await speech_service.synthesize_advanced(req)
    except Exception as e:
        logger.error("[tts_generate] 合成失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS 合成失败: {str(e)}")

    mime_type = get_mime_type(res.format)

    # 1. 直接流式返回音频二进制模式
    if req.output_mode == "audio":
        headers = {
            "Content-Disposition": f'inline; filename="speech.{res.format}"',
            "Content-Length": str(len(res.audio_bytes)),
            "X-Audio-Duration": str(res.duration_seconds),
        }
        return Response(content=res.audio_bytes, media_type=mime_type, headers=headers)

    # 2. 结构化 JSON 返回模式 (携带 Base64 音频与对齐字幕)
    audio_b64 = base64.b64encode(res.audio_bytes).decode("ascii")
    subtitles = [
        SubtitleCueItem(
            index=c.index,
            text=c.text,
            start_time=c.start_time,
            end_time=c.end_time,
            start_seconds=c.start_seconds,
            end_seconds=c.end_seconds,
        )
        for c in res.subtitles
    ]

    return TTSGenerateResponse(
        audio_base64=audio_b64,
        audio_format=res.format,
        audio_duration_seconds=res.duration_seconds,
        sample_rate=res.sample_rate,
        subtitles=subtitles,
        srt_content=res.srt_content,
        vtt_content=res.vtt_content,
    )
