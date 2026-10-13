"""OneTTS 增强模型矩阵与能力详情接口 (/v1/x/models)。"""

from fastapi import APIRouter, Depends
from server.api.auth import get_api_key
from server.core.config import app_config

router = APIRouter(prefix="/v1/x/models", tags=["Models-Extended"], dependencies=[Depends(get_api_key)])


@router.get("")
async def list_extended_models():
    """获取所有模型矩阵与底层 Provider 详细能力矩阵 (/v1/x/models)。"""
    models = []
    # 1. 预设标准别名模型
    models.append({
        "id": "tts-1",
        "name": "OpenAI 标准别名",
        "engine": "auto",
        "enable": True,
        "type": "alias",
        "description": "自动路由到默认启用的 TTS 引擎",
    })
    models.append({
        "id": "tts-1-hd",
        "name": "OpenAI 高清别名",
        "engine": "auto",
        "enable": True,
        "type": "alias",
        "description": "自动路由到高音质 TTS 引擎",
    })

    # 2. 各 Provider 注册引擎
    for name, cfg in app_config.providers.items():
        if cfg.enable:
            models.append({
                "id": name,
                "name": f"{cfg.engine.upper()} 引擎",
                "engine": cfg.engine,
                "enable": cfg.enable,
                "preload": cfg.preload,
                "keep_alive": cfg.keep_alive,
                "categories": cfg.categories,
                "languages": cfg.languages,
                "default_voice": cfg.default_voice,
                "type": "engine",
                "description": f"{cfg.engine.upper()} 语音合成引擎",
            })

    return {
        "object": "list",
        "data": models,
        "total": len(models),
    }
