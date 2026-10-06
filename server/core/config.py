"""配置加载与管理。"""

from pathlib import Path
from typing import Any
import yaml
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


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
    def __init__(self, name: str, data: dict):
        self.name = name
        self.enable: bool = bool(data.get("enable", True))
        self.engine: str = data.get("engine", name)
        self.default_voice: str = data.get("default_voice", "")
        self.voice_aliases: dict[str, str] = data.get("voice_aliases", {})
        self.base_url: str = data.get("base_url", "")
        self.api_key: str = data.get("api_key", "")
        self.models: list[str] = data.get("models", [])
        self.model_path: str = data.get("model_path", "")
        self.voices_path: str = data.get("voices_path", "")
        self.raw_config: dict[str, Any] = data


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

