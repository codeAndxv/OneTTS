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


class EngineConfig:
    """TTS Provider 配置项，标准支持 load 与 properties 分层。"""

    def __init__(self, name: str, data: dict | None = None):
        data = data or {}
        self.name = name
        self.raw_config: dict[str, Any] = data

        load_conf = data.get("load", {}) if isinstance(data.get("load"), dict) else {}
        props_conf = data.get("properties", {}) if isinstance(data.get("properties"), dict) else {}
        self.load: dict[str, Any] = load_conf
        self.properties: dict[str, Any] = props_conf

        def _get_val(key: str, default: Any = None) -> Any:
            if key in load_conf:
                return load_conf[key]
            if key in props_conf:
                return props_conf[key]
            return data.get(key, default)

        self.enable: bool = bool(data.get("enable", data.get("enabled", True)))
        self.engine: str = data.get("engine", name)
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
        self.models: list[str] = _get_val("models", []) or []
        self.model_path: str = _get_val("model_path", "")
        self.voices_path: str = _get_val("voices_path", "")
        self.device: str = _get_val("device", "cpu")

        # 组合配置字典：确保引擎适配器开箱即用读取 load 与 properties 中参数
        combined = dict(data)
        combined.update(load_conf)
        combined.update(props_conf)
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
        raw_toolkit = self._data.get("TTS-Toolkit", self._data.get("tts_toolkit", {}))
        self.tts_toolkit = TTSToolkitConfig(raw_toolkit)

        # TTS Providers 配置
        self.providers: dict[str, EngineConfig] = {}
        for name, prov_conf in self._data.get("TTS-Providers", {}).items():
            self.providers[name] = EngineConfig(name, prov_conf)

    def get_provider_config(self, name: str) -> EngineConfig:
        if name in self.providers:
            return self.providers[name]
        raise ValueError(f"未知 TTS Provider: {name}，当前可用: {list(self.providers)}")


class Settings(BaseSettings):
    app_name: str = "OneTTS"
    app_version: str = "0.1.0"
    api_version: str = "0.1.0"
    debug: bool = False


settings = Settings()
app_config = AppConfig()
API_VERSION = settings.api_version
