"""底层 TTS Provider 状态查询接口 GET /v1/providers。"""

from fastapi import APIRouter, Depends
from server.api.auth import get_api_key
from server.core.config import app_config

router = APIRouter(prefix="/v1", tags=["providers"], dependencies=[Depends(get_api_key)])


@router.get("/providers")
async def list_providers():
    """获取所有底层 TTS Provider 的配置与健康状态。"""
    res = {}
    for name, cfg in app_config.providers.items():
        res[name] = {
            "enable": cfg.enable,
            "engine": cfg.engine,
            "default_voice": cfg.default_voice,
            "voice_aliases": cfg.voice_aliases,
        }
    return {"providers": res}
