"""音色探索与查询接口 GET /v1/audio/voices。"""

from fastapi import APIRouter, Depends
from server.api.auth import get_api_key
from server.schemas.voice import VoiceListResponse
from server.services.voice_service import voice_service

router = APIRouter(prefix="/v1/audio", tags=["voices"], dependencies=[Depends(get_api_key)])


@router.get("/voices", response_model=VoiceListResponse)
async def list_voices():
    """获取系统当前所有可用发音人音色列表。"""
    voices = voice_service.get_all_voices()
    return VoiceListResponse(voices=voices, total=len(voices))
