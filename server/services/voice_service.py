"""音色与别名映射业务服务 (支持 data/voices/ 独立字典存储与多维过滤)。"""

import json
import logging
from pathlib import Path
from server.core.config import PROJECT_ROOT, app_config
from server.engines.registry import get_engine, list_available_providers
from server.schemas.voice import VoiceInfo
from server.services.clone_service import clone_service

logger = logging.getLogger(__name__)

VOICES_DATA_DIR = PROJECT_ROOT / "data" / "voices"

# OpenAI 官方 6 种标准音色在各底层引擎下的推荐映射 (代码层内置兜底，无需在 config.yaml 臃肿配置)
BUILTIN_OPENAI_VOICE_MAP: dict[str, dict[str, str]] = {
    "edgetts": {
        "alloy": "zh-CN-XiaoxiaoNeural",
        "nova": "zh-CN-XiaoyiNeural",
        "shimmer": "zh-CN-liaoning-XiaobeiNeural",
        "echo": "zh-CN-YunxiNeural",
        "fable": "zh-CN-YunjianNeural",
        "onyx": "zh-CN-YunyangNeural",
    },
    "doubao": {
        "alloy": "zh_female_shuangkuai",
        "nova": "zh_female_tianmei",
        "shimmer": "zh_female_cantonese",
        "echo": "zh_male_chunhou",
        "fable": "zh_male_dongbeikouyin",
        "onyx": "zh_male_chunhou",
    },
    "f5tts": {
        "alloy": "f5-chinese-female",
        "nova": "f5-chinese-female",
        "shimmer": "f5-chinese-female",
        "echo": "f5-chinese-male",
        "fable": "f5-chinese-male",
        "onyx": "f5-chinese-male",
    },
    "cosyvoice": {
        "alloy": "cosyvoice-chinese-female",
        "nova": "cosyvoice-chinese-female",
        "shimmer": "cosyvoice-chinese-female",
        "echo": "cosyvoice-chinese-male",
        "fable": "cosyvoice-chinese-male",
        "onyx": "cosyvoice-chinese-male",
    },
    "kokoro": {
        "alloy": "af_bella",
        "nova": "af_sarah",
        "shimmer": "af_nicole",
        "echo": "am_adam",
        "fable": "am_michael",
        "onyx": "am_eric",
    },
    "openai": {
        "alloy": "alloy",
        "echo": "echo",
        "fable": "fable",
        "onyx": "onyx",
        "nova": "nova",
        "shimmer": "shimmer",
    },
}


class VoiceService:
    """音色别名解析、数据字典加载与多引擎音色汇总。"""

    def __init__(self):
        self._cache: dict[str, list[VoiceInfo]] = {}

    def reload_cache(self) -> None:
        """清空并重置内存缓存。"""
        self._cache.clear()
        logger.info("[voice_service] 已清空音色内存缓存")

    def get_provider_voices(self, provider_name: str) -> list[VoiceInfo]:
        """获取指定 Provider 的音色列表 (优先从 data/voices/{provider}.json 加载，具备引擎代码兜底与 YAML 白名单过滤)。"""
        if provider_name in self._cache:
            return list(self._cache[provider_name])

        voices: list[VoiceInfo] = []
        json_path = VOICES_DATA_DIR / f"{provider_name}.json"

        # 1. 尝试从独立 JSON 数据字典文件加载
        if json_path.exists():
            try:
                content = json_path.read_text(encoding="utf-8")
                raw_items = json.loads(content)
                if isinstance(raw_items, list):
                    for item in raw_items:
                        try:
                            voices.append(VoiceInfo(**item))
                        except Exception as parse_err:
                            logger.warning("[voice_service] 解析音色项失败: %s (%s)", item, parse_err)
            except Exception as e:
                logger.error("[voice_service] 读取音色字典 %s 失败: %s", json_path, e)

        # 2. 如果 JSON 不存在或解析为空，平滑回退到引擎代码自带的内置清单
        if not voices:
            try:
                engine = get_engine(provider_name)
                voices = list(engine.list_voices())
            except Exception as e:
                logger.warning("[voice_service] 从引擎 [%s] 获取兜底音色失败: %s", provider_name, e)

        # 3. 检查 config.yaml 中是否配置了显式白名单过滤
        cfg = app_config.providers.get(provider_name)
        if cfg and getattr(cfg, "voices", None):
            whitelist = set(cfg.voices)
            filtered = [v for v in voices if v.id in whitelist]
            if filtered:
                voices = filtered

        # 4. 写入单例内存缓存
        self._cache[provider_name] = voices
        return list(voices)

    def get_static_voices(
        self,
        provider: str | None = None,
        language: str | None = None,
        gender: str | None = None,
        recommended_only: bool = False,
    ) -> list[VoiceInfo]:
        """同步获取所有静态发音人音色（不包含数据库中的克隆音色）。"""
        target_providers = [provider] if provider else list_available_providers()
        results: list[VoiceInfo] = []

        for p_name in target_providers:
            try:
                results.extend(self.get_provider_voices(p_name))
            except Exception as e:
                logger.warning("获取 Provider [%s] 静态音色失败: %s", p_name, e)

        return self._apply_filters(results, language=language, gender=gender, recommended_only=recommended_only)

    async def get_all_voices(
        self,
        provider: str | None = None,
        language: str | None = None,
        gender: str | None = None,
        recommended_only: bool = False,
        include_clones: bool = True,
    ) -> list[VoiceInfo]:
        """异步获取所有可用发音人音色（聚合并包含用户声音克隆资产，支持多维过滤）。"""
        results = self.get_static_voices(
            provider=provider,
            language=language,
            gender=gender,
            recommended_only=recommended_only,
        )

        # 聚合声音克隆资产 (当未限制特定非 clone 引擎时)
        if include_clones and (provider is None or provider in ("clone", "clones", "custom")):
            try:
                clones = await clone_service.list_clones()
                for c in clones:
                    results.append(
                        VoiceInfo(
                            id=c.id,
                            name=c.name,
                            provider="clone",
                            gender="neutral",
                            language=c.language or "zh-CN",
                            languages=[c.language] if c.language else ["zh-CN"],
                            category="声音克隆",
                            tags=["克隆", "自定义", "个人专属"],
                            styles=[],
                            description=c.description or "用户专属声音克隆资产",
                            preview_url=c.sample_url,
                            is_recommended=True,
                            is_clone=True,
                        )
                    )
            except Exception as e:
                logger.warning("[voice_service] 聚合克隆音色失败: %s", e)

        return self._apply_filters(results, language=language, gender=gender, recommended_only=recommended_only)

    @staticmethod
    def _apply_filters(
        voices: list[VoiceInfo],
        language: str | None = None,
        gender: str | None = None,
        recommended_only: bool = False,
    ) -> list[VoiceInfo]:
        """应用条件过滤。"""
        filtered = voices

        if recommended_only:
            filtered = [v for v in filtered if v.is_recommended]

        if gender:
            g_target = gender.strip().lower()
            filtered = [v for v in filtered if v.gender.lower() == g_target]

        if language:
            lang_target = language.strip().lower()
            filtered = [
                v for v in filtered
                if lang_target in v.language.lower()
                or any(lang_target in l.lower() for l in v.languages)
            ]

        return filtered

    @staticmethod
    def resolve_voice(provider_name: str, voice_input: str) -> tuple[str, str]:
        """解析音色别名，返回 (实际provider, 实际底层voice_id)。"""
        target_provider = provider_name
        if target_provider in ("tts-1", "tts-1-hd"):
            enabled = list_available_providers()
            target_provider = enabled[0] if enabled else "edgetts"

        if target_provider not in app_config.providers:
            target_provider = "edgetts"

        cfg = app_config.providers[target_provider]
        voice_lower = (voice_input or "").lower().strip()

        # 1. 优先检查用户在 config.yaml 中显式自定义的 voice_aliases
        user_aliases = cfg.voice_aliases or {}
        if voice_lower in user_aliases:
            return target_provider, user_aliases[voice_lower]

        # 2. 检查代码层内置的 OpenAI 6 种标准音色映射 (零配置开箱即用)
        builtin_map = BUILTIN_OPENAI_VOICE_MAP.get(cfg.engine, BUILTIN_OPENAI_VOICE_MAP.get(target_provider, {}))
        if voice_lower in builtin_map:
            return target_provider, builtin_map[voice_lower]

        # 3. 如果客户端传了真实音色 ID，保持原值
        if voice_input and voice_input.strip():
            return target_provider, voice_input.strip()

        # 4. 兜底默认音色
        actual_voice = cfg.default_voice or "zh-CN-XiaoxiaoNeural"
        return target_provider, actual_voice


voice_service = VoiceService()
