"""音色与别名映射业务服务。"""

import logging
from server.core.config import app_config
from server.engines.registry import get_engine, list_available_providers
from server.schemas.voice import VoiceInfo

logger = logging.getLogger(__name__)


class VoiceService:
    """音色别名解析与多引擎音色汇总。"""

    @staticmethod
    def resolve_voice(provider_name: str, voice_input: str) -> tuple[str, str]:
        """解析音色别名，返回 (实际provider, 实际底层voice_id)。"""
        # 1. 检查 provider
        target_provider = provider_name
        if target_provider in ("tts-1", "tts-1-hd"):
            # 查找启用的 provider
            enabled = list_available_providers()
            target_provider = enabled[0] if enabled else "edgetts"

        if target_provider not in app_config.providers:
            target_provider = "edgetts"

        cfg = app_config.providers[target_provider]

        # 2. 检查音色别名映射 (alloy -> zh-CN-XiaoxiaoNeural 等)
        aliases = cfg.voice_aliases or {}
        voice_lower = voice_input.lower().strip()
        actual_voice = aliases.get(voice_lower, voice_input)

        # 3. 兜底默认音色
        if not actual_voice:
            actual_voice = cfg.default_voice or "zh-CN-XiaoxiaoNeural"

        return target_provider, actual_voice

    @staticmethod
    def get_all_voices() -> list[VoiceInfo]:
        """获取所有可用引擎的音色汇总。"""
        voices: list[VoiceInfo] = []
        for p_name in list_available_providers():
            try:
                engine = get_engine(p_name)
                voices.extend(engine.list_voices())
            except Exception as e:
                logger.warning("获取 Provider [%s] 音色列表失败: %s", p_name, e)
        return voices


voice_service = VoiceService()
