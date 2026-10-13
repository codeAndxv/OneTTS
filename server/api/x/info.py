"""OneTTS 系统与协议版本信息及 Provider 状态接口 (/v1/x/info, /v1/x/providers)。"""

from fastapi import APIRouter, Depends
from server.api.auth import get_api_key
from server.core.config import API_VERSION, app_config, settings

router = APIRouter(prefix="/v1/x", tags=["Info-Extended"])


@router.get("/info")
async def get_service_info():
    """返回 OneTTS 服务与接口协议版本信息 (/v1/x/info)。"""
    return {
        "service": "OneTTS",
        "app_version": settings.app_version,
        "api_version": API_VERSION,
        "status": "ok",
    }


@router.get("/providers", dependencies=[Depends(get_api_key)])
async def list_providers():
    """获取所有底层 TTS Provider 的配置与健康状态 (/v1/x/providers)。"""
    res = {}
    for name, cfg in app_config.providers.items():
        res[name] = {
            "enable": cfg.enable,
            "engine": cfg.engine,
            "default_voice": cfg.default_voice,
            "voice_aliases": cfg.voice_aliases,
        }
    return {
        "api_version": API_VERSION,
        "providers": res,
    }
