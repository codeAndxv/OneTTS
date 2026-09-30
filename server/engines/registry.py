"""TTS 引擎注册表与生命周期工厂。"""

import logging
from typing import Type
from server.core.config import app_config
from server.engines.base import BaseTTSEngine
from server.engines.edgetts_engine import EdgeTTSEngine
from server.engines.openai_engine import OpenAITTSEngine
from server.engines.kokoro_engine import KokoroEngine

logger = logging.getLogger(__name__)

_ENGINE_CLASSES: dict[str, Type[BaseTTSEngine]] = {
    "edgetts": EdgeTTSEngine,
    "openai": OpenAITTSEngine,
    "kokoro": KokoroEngine,
}

_ACTIVE_INSTANCES: dict[str, BaseTTSEngine] = {}


def register_engine_class(engine_type: str, engine_cls: Type[BaseTTSEngine]) -> None:
    _ENGINE_CLASSES[engine_type] = engine_cls


def get_engine(provider_name: str) -> BaseTTSEngine:
    """按 provider 名称获取或延迟初始化引擎实例。"""
    if provider_name in _ACTIVE_INSTANCES:
        return _ACTIVE_INSTANCES[provider_name]

    if provider_name not in app_config.providers:
        # 如果传入的是通用的 tts-1 / tts-1-hd，默认路由至首个启用的引擎或 edgetts
        if provider_name in ("tts-1", "tts-1-hd"):
            # 找到第一个启用的 provider
            for name, cfg in app_config.providers.items():
                if cfg.enable:
                    return get_engine(name)
            return get_engine("edgetts")
        raise ValueError(f"未找到配置的 TTS Provider: {provider_name}")

    cfg = app_config.providers[provider_name]
    engine_type = cfg.engine

    if engine_type not in _ENGINE_CLASSES:
        raise ValueError(f"不支持的 TTS 引擎类型: {engine_type}")

    instance = _ENGINE_CLASSES[engine_type](name=provider_name, config=cfg.raw_config)
    _ACTIVE_INSTANCES[provider_name] = instance
    logger.info("已成功初始化 TTS 引擎实例: %s (%s)", provider_name, engine_type)
    return instance


def list_available_providers() -> list[str]:
    """列出当前已启用且可用的 Provider 名称。"""
    return [name for name, cfg in app_config.providers.items() if cfg.enable]
