"""OpenAI 兼容模型列表接口 GET /v1/models。"""

from fastapi import APIRouter, Depends
from server.api.auth import get_api_key
from server.core.config import app_config
from server.schemas.model import ModelCard, ModelListResponse

router = APIRouter(prefix="/v1", tags=["models"], dependencies=[Depends(get_api_key)])


@router.get("/models", response_model=ModelListResponse)
async def list_models():
    """获取所有已启用的 TTS 模型列表。"""
    cards: list[ModelCard] = [
        ModelCard(
            id="tts-1",
            description="OpenAI 标准 TTS 别名 (自动路由至默认引擎)",
            provider="auto",
        ),
        ModelCard(
            id="tts-1-hd",
            description="OpenAI 高清 TTS 别名 (自动路由至默认引擎)",
            provider="auto",
        ),
    ]

    for name, cfg in app_config.providers.items():
        if cfg.enable:
            cards.append(
                ModelCard(
                    id=name,
                    description=f"{cfg.engine.upper()} TTS 引擎",
                    provider=cfg.engine,
                )
            )

    return ModelListResponse(data=cards)
