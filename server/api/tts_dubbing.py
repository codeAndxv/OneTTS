"""字幕时间轴对齐配音 API 路由 (/v1/tts/dubbing)。"""

from fastapi import APIRouter, Depends, Response
from server.api.auth import verify_api_key
from server.schemas.tts_ext import TTSDubbingRequest, TTSDubbingResponse
from server.services.dubbing_service import dubbing_service

router = APIRouter(prefix="/v1/tts", tags=["TTS-Extended"])


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
async def create_dubbing(
    req: TTSDubbingRequest,
    _: str = Depends(verify_api_key),
):
    audio_bytes, resp = await dubbing_service.execute_dubbing(req)

    if req.output_mode == "audio":
        media_type = f"audio/{req.response_format}"
        if req.response_format == "wav":
            media_type = "audio/wav"
        elif req.response_format == "mp3":
            media_type = "audio/mpeg"
        return Response(content=audio_bytes, media_type=media_type)

    return resp
