"""OpenAI 兼容语音合成接口 POST /v1/audio/speech。"""

import logging
from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse

from server.api.auth import get_api_key
from server.schemas.speech import SpeechRequest
from server.services.speech_service import speech_service
from server.utils.audio_encoder import get_mime_type

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/audio", tags=["audio"], dependencies=[Depends(get_api_key)])


@router.post("/speech")
async def create_speech(req: SpeechRequest):
    """OpenAI /v1/audio/speech 标准语音合成端点。"""
    mime_type = get_mime_type(req.response_format)

    # 1. 流式响应分支
    if req.stream:
        return StreamingResponse(
            speech_service.stream_speech(req),
            media_type=mime_type,
            headers={
                "Content-Disposition": f'inline; filename="speech.{req.response_format}"',
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
        )

    # 2. 全量响应分支
    audio_bytes = await speech_service.synthesize_speech(req)
    return Response(
        content=audio_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="speech.{req.response_format}"',
            "Content-Length": str(len(audio_bytes)),
        },
    )
