"""配置加载与管理。"""

from pathlib import Path
from typing import Any
import yaml
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def parse_keep_alive_seconds(val: Any, default: int = 600) -> int:
    """将 keep_alive 配置解析为秒数。

    支持：
    - 整数/浮点数：如 -1 (常驻), 0 (用完即焚), 600 (600秒)
    - 字符串时长：如 "10m" (600), "1h" (3600), "30s" (30), "-1", "0"
    """
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip().lower()
    if not s:
        return default
    if s in ("-1", "forever", "always", "permanent"):
        return -1
    if s in ("0", "0s", "immediate", "none"):
        return 0
    try:
        if s.endswith("ms"):
            return max(0, int(float(s[:-2]) / 1000))
        if s.endswith("s"):
            return int(float(s[:-1]))
        if s.endswith("m"):
            return int(float(s[:-1]) * 60)
        if s.endswith("h"):
            return int(float(s[:-1]) * 3600)
        return int(float(s))
    except ValueError:
        return default


class ModelManagerConfig:
    """全局模型生命周期管理配置（Ollama 风格 keep_alive + LRU 容量上限）。"""

    def __init__(self, data: dict | None = None):
        data = data or {}
        self.default_keep_alive: int = parse_keep_alive_seconds(
            data.get("default_keep_alive", data.get("keep_alive", 600)),
            default=600,
        )
        raw_max = data.get("max_loaded_models", 2)
        self.max_loaded_models: int = int(raw_max) if raw_max is not None else 2
        self.cleanup_interval: int = max(5, int(data.get("cleanup_interval", 30)))


class CacheConfig:
    def __init__(self, data: dict | None = None):
        data = data or {}
        self.enable: bool = bool(data.get("enable", True))
        self.cache_dir: str = str(data.get("cache_dir", "data/outputs/cache"))
        self.max_cache_size_mb: int = int(data.get("max_cache_size_mb", 1024))


class TextSplitterConfig:
    def __init__(self, data: dict | None = None):
        data = data or {}
        self.enable: bool = bool(data.get("enable", True))
        self.max_chunk_chars: int = int(data.get("max_chunk_chars", 80))
        self.split_delimiters: str = str(data.get("split_delimiters", "。！？!?；;\n"))


class TTSToolkitConfig:
    def __init__(self, data: dict | None = None):
        data = data or {}
        self.cache = CacheConfig(data.get("cache", {}))
        self.text_splitter = TextSplitterConfig(data.get("text_splitter", {}))


DRIVER_ALIAS_MAP: dict[str, str] = {
    "edge-tts": "edgetts",
    "openai-compatible": "openai",
    "f5-tts": "f5tts",
    "cosy-voice": "cosyvoice",
}


class EngineConfig:
    """TTS 模型/Provider 配置项，标准支持 load 与 capabilities 分层。"""

    def __init__(
        self,
        name: str,
        data: dict | None = None,
        is_cloud: bool = False,
        provider_group: str | None = None,
    ):
        data = data or {}
        self.name = name
        self.provider_group = provider_group or name
        self.raw_config: dict[str, Any] = data
        self.is_cloud = is_cloud
        self.type = "cloud" if is_cloud else data.get("type", "local")

        load_conf = data.get("load", {}) if isinstance(data.get("load"), dict) else {}
        caps_conf = data.get("capabilities", {}) if isinstance(data.get("capabilities"), dict) else {}
        self.load: dict[str, Any] = load_conf
        self.capabilities: dict[str, Any] = caps_conf

        def _get_val(key: str, default: Any = None) -> Any:
            if key in load_conf:
                return load_conf[key]
            if key in caps_conf:
                return caps_conf[key]
            return data.get(key, default)

        self.enable: bool = bool(data.get("enable", True))
        raw_driver = data.get("driver") or data.get("engine") or name
        self.driver: str = raw_driver
        self.engine: str = DRIVER_ALIAS_MAP.get(raw_driver, raw_driver)

        # 默认生命周期策略：云端/Web免卸载 keep_alive = -1，本地模型按配置
        if is_cloud or self.type == "cloud":
            self.preload: bool = bool(data.get("preload", True))
            self.keep_alive: int = -1
        else:
            self.preload: bool = bool(data.get("preload", False))
            self.keep_alive: int = parse_keep_alive_seconds(data.get("keep_alive", 600))

        # 音色与能力属性
        self.default_voice: str = _get_val("default_voice", "")
        self.voice_aliases: dict[str, str] = _get_val("voice_aliases", {}) or {}
        self.categories: list[str] = _get_val("categories", []) or []
        langs_val = _get_val("languages", "")
        if isinstance(langs_val, str):
            self.languages: list[str] = [s.strip() for s in langs_val.split(",") if s.strip()]
        else:
            self.languages = list(langs_val or [])

        voices_val = _get_val("voices", None)
        if isinstance(voices_val, list):
            self.voices: list[str] | None = [str(v).strip() for v in voices_val if str(v).strip()]
        else:
            self.voices: list[str] | None = None

        # 加载参数便捷映射
        self.api_url: str = _get_val("api_url", "")
        self.base_url: str = _get_val("base_url", "")
        self.api_key: str = _get_val("api_key", "")
        self.appid: str = _get_val("appid", "")
        self.access_token: str = _get_val("access_token", "")
        self.cluster: str = _get_val("cluster", "volcano_tts")
        self.remote_name: str = _get_val("remote_name", name)
        self.models: list[str] = _get_val("models", []) or []
        self.model_path: str = _get_val("model_path", "")
        self.voices_path: str = _get_val("voices_path", "")
        self.device: str = _get_val("device", "cpu")

        # 组合配置字典：确保引擎适配器开箱即用读取 load 与 capabilities 中参数
        combined = dict(data)
        combined.update(load_conf)
        combined.update(caps_conf)
        self.combined_config: dict[str, Any] = combined


class AppConfig:
    def __init__(self, config_path: str | Path | None = None):
        config_path = config_path or PROJECT_ROOT / "config.yaml"
        if not Path(config_path).exists():
            self._data = {}
        else:
            with open(config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}

        # API Key 配置
        self.api_key: str = self._data.get("api_key", "")

        # 模型生命周期管理
        self.model_manager = ModelManagerConfig(self._data.get("model_manager", {}))

        # TTS Toolkit 配置
        raw_toolkit = self._data.get("TTS-Toolkit", {})
        self.tts_toolkit = TTSToolkitConfig(raw_toolkit)

        # TTS 模型配置 (纯粹现代架构：local-models + cloud-providers)
        self.providers: dict[str, EngineConfig] = {}
        self.local_models: dict[str, EngineConfig] = {}
        self.cloud_providers: dict[str, dict[str, Any]] = {}

        # 1. 解析本地模型 (local-models)
        raw_local = self._data.get("local-models", {})
        if isinstance(raw_local, dict):
            for model_id, model_conf in raw_local.items():
                if not isinstance(model_conf, dict):
                    continue
                cfg = EngineConfig(model_id, model_conf, is_cloud=False)
                self.local_models[model_id] = cfg
                self.providers[model_id] = cfg

        # 2. 解析云端服务商 (cloud-providers) 并自动多模型展平
        raw_cloud = self._data.get("cloud-providers", {})
        if isinstance(raw_cloud, dict):
            for prov_name, prov_conf in raw_cloud.items():
                if not isinstance(prov_conf, dict):
                    continue
                self.cloud_providers[prov_name] = prov_conf
                if not prov_conf.get("enable", True):
                    continue

                driver = prov_conf.get("driver") or prov_conf.get("engine", "openai")
                conn = prov_conf.get("connection", {}) if isinstance(prov_conf.get("connection"), dict) else {}
                models_list = prov_conf.get("models", [])

                for m in models_list:
                    if isinstance(m, str):
                        m_id = m
                        m_conf = {}
                    elif isinstance(m, dict):
                        m_id = m.get("id") or m.get("name")
                        m_conf = m
                    else:
                        continue

                    if not m_id:
                        continue

                    # 展平构建单模型配置
                    merged_conf: dict[str, Any] = {
                        "enable": True,
                        "driver": driver,
                        "type": "cloud",
                        "provider": prov_name,
                    }
                    merged_conf.update(conn)
                    merged_conf.update(m_conf)
                    if "capabilities" in m_conf:
                        merged_conf["capabilities"] = m_conf["capabilities"]

                    cfg = EngineConfig(m_id, merged_conf, is_cloud=True, provider_group=prov_name)
                    self.providers[m_id] = cfg

    def get_provider_config(self, name: str) -> EngineConfig:
        if name in self.providers:
            return self.providers[name]
        # 支持去除命名空间前缀或按短名查找
        short_name = name.split("/")[-1]
        for k, v in self.providers.items():
            if k == short_name or k.split("/")[-1] == short_name:
                return v
        raise ValueError(f"未知 TTS Provider / 模型: {name}，当前可用: {list(self.providers)}")


class Settings(BaseSettings):
    app_name: str = "OneTTS"
    app_version: str = "0.1.0"
    api_version: str = "0.1.0"
    debug: bool = False


settings = Settings()
app_config = AppConfig()
API_VERSION = settings.api_version
