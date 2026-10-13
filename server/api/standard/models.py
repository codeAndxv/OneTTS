"""OpenAI 兼容标准模型列表接口 (GET /v1/models, GET /v1/models/{model_id})。"""

from fastapi import APIRouter, Depends
from server.api.auth import get_api_key
from server.core.config import app_config
from server.core.errors import OpenAIAPIException
from server.schemas.model import ModelCard, ModelListResponse

router = APIRouter(prefix="/v1/models", tags=["Models-Standard"], dependencies=[Depends(get_api_key)])


def _build_model_cards() -> list[ModelCard]:
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
    return cards


@router.get("", response_model=ModelListResponse)
async def list_models():
    """获取所有已启用的 TTS 模型列表 (兼容 OpenAI GET /v1/models)。"""
    return ModelListResponse(data=_build_model_cards())


@router.get("/{model_id}", response_model=ModelCard)
async def get_model(model_id: str):
    """获取指定模型详情 (兼容 OpenAI GET /v1/models/{model_id})。"""
    cards = _build_model_cards()
    for card in cards:
        if card.id == model_id:
            return card
    raise OpenAIAPIException(
        status_code=404,
        message=f"The model '{model_id}' does not exist.",
        error_type="invalid_request_error",
        param="model",
        code="model_not_found",
    )
