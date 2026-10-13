"""OneTTS 专属高级语音合成与字幕配音路由 (/v1/x/audio)。"""

import base64
import logging
from fastapi import APIRouter, Depends, HTTPException, Response

from server.api.auth import get_api_key
from server.schemas.tts_ext import (
    SubtitleCueItem,
    TTSDubbingRequest,
    TTSDubbingResponse,
    TTSGenerateRequest,
    TTSGenerateResponse,
)
from server.services.dubbing_service import dubbing_service
from server.services.speech_service import speech_service
from server.utils.audio_encoder import get_mime_type

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/x/audio", tags=["Audio-Extended"], dependencies=[Depends(get_api_key)])


@router.post("/speech")
async def generate_advanced_speech(req: TTSGenerateRequest):
    """高级语音合成端点 (/v1/x/audio/speech)：支持字幕、音高音量、语种与音色克隆。"""
    try:
        res = await speech_service.synthesize_advanced(req)
    except Exception as e:
        logger.error("[x_audio] 合成失败: %s", e, exc_info=True)
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


@router.post(
    "/dubbing",
    response_model=TTSDubbingResponse,
    summary="字幕时间轴对齐配音 (带自然留白空间)",
    description=(
        "接收带有起止毫秒时间戳的字幕条目列表 (cues) 或原始 SRT 文本，"
        "逐句合成配音，并在句子之间精确填充纯净无声留白 (Silence Gaps)，"
        "生成与原字幕/原视频绝对时间对齐的完整同步音轨。"
    ),
)
async def create_dubbing(req: TTSDubbingRequest):
    """字幕时间对齐配音端点 (/v1/x/audio/dubbing)。"""
    audio_bytes, resp = await dubbing_service.execute_dubbing(req)

    if req.output_mode == "audio":
        media_type = f"audio/{req.response_format}"
        if req.response_format == "wav":
            media_type = "audio/wav"
        elif req.response_format == "mp3":
            media_type = "audio/mpeg"
        return Response(content=audio_bytes, media_type=media_type)

    return resp
