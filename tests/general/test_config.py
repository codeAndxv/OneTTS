"""测试现代 local-models 与 cloud-providers 配置加载、多模型展平与别名映射。"""

import tempfile
from pathlib import Path
import yaml

from server.core.config import AppConfig, EngineConfig, app_config


def test_config_loading():
    assert app_config.api_key == "onetts-test-key"
    assert app_config.model_manager.default_keep_alive == 600
    assert app_config.tts_toolkit.cache.enable is True
    assert app_config.tts_toolkit.text_splitter.enable is True

    # 检查从 cloud-providers 展平注入的 edgetts 规范分层
    assert "edgetts" in app_config.providers
    edgetts_cfg = app_config.get_provider_config("edgetts")
    assert edgetts_cfg.enable is True
    assert edgetts_cfg.driver == "edgetts"
    assert edgetts_cfg.engine == "edgetts"
    assert edgetts_cfg.is_cloud is True
    assert edgetts_cfg.keep_alive == -1
    assert "PresetTTS" in edgetts_cfg.categories
    assert "zh" in edgetts_cfg.languages
    assert "en" in edgetts_cfg.languages
    assert edgetts_cfg.default_voice == "zh-CN-XiaoxiaoNeural"


def test_local_models_and_cloud_providers_parsing():
    sample_yaml = {
        "api_key": "test-key-123",
        "model_manager": {
            "default_keep_alive": 300,
            "max_loaded_models": 3,
        },
        "TTS-Toolkit": {
            "cache": {"enable": True},
            "text_splitter": {"enable": False},
        },
        "local-models": {
            "my-kokoro": {
                "enable": True,
                "driver": "kokoro",
                "preload": False,
                "keep_alive": 300,
                "load": {
                    "model_path": "data/models/kokoro-v0_19.onnx",
                    "device": "cpu",
                },
                "capabilities": {
                    "categories": ["LocalTTS", "OnnxTTS"],
                    "languages": ["zh", "en"],
                    "default_voice": "af_bella",
                },
            },
        },
        "cloud-providers": {
            "openai-official": {
                "enable": True,
                "driver": "openai-compatible",
                "connection": {
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-secret-abc",
                    "timeout": 20,
                },
                "models": [
                    {
                        "id": "tts-1",
                        "remote_name": "tts-1",
                        "capabilities": {
                            "categories": ["CloudTTS"],
                            "languages": ["zh", "en"],
                            "default_voice": "alloy",
                        },
                    },
                    {
                        "id": "tts-1-hd",
                        "remote_name": "tts-1-hd",
                        "capabilities": {
                            "categories": ["CloudTTS"],
                            "languages": ["zh", "en"],
                            "default_voice": "nova",
                        },
                    },
                ],
            },
            "disabled-cloud": {
                "enable": False,
                "driver": "doubao",
                "connection": {"api_key": "dummy"},
                "models": [{"id": "should-not-exist"}],
            },
        },
    }

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(sample_yaml, f)
        cfg_path = Path(f.name)

    try:
        cfg = AppConfig(cfg_path)

        # 1. 本地模型验证
        assert "my-kokoro" in cfg.local_models
        assert "my-kokoro" in cfg.providers
        kokoro_cfg = cfg.providers["my-kokoro"]
        assert kokoro_cfg.driver == "kokoro"
        assert kokoro_cfg.engine == "kokoro"
        assert kokoro_cfg.is_cloud is False
        assert kokoro_cfg.model_path == "data/models/kokoro-v0_19.onnx"
        assert kokoro_cfg.default_voice == "af_bella"

        # 2. 云端多模型展平验证
        assert "tts-1" in cfg.providers
        assert "tts-1-hd" in cfg.providers
        assert "should-not-exist" not in cfg.providers

        t1_cfg = cfg.providers["tts-1"]
        assert t1_cfg.driver == "openai-compatible"
        assert t1_cfg.engine == "openai"
        assert t1_cfg.is_cloud is True
        assert t1_cfg.api_key == "sk-secret-abc"
        assert t1_cfg.base_url == "https://api.openai.com/v1"
        assert t1_cfg.remote_name == "tts-1"
        assert t1_cfg.default_voice == "alloy"

        t1hd_cfg = cfg.providers["tts-1-hd"]
        assert t1hd_cfg.default_voice == "nova"

        # 3. 短名与安全查找
        assert cfg.get_provider_config("tts-1").name == "tts-1"

    finally:
        cfg_path.unlink(missing_ok=True)


def test_driver_alias_mapping():
    c1 = EngineConfig("test-edge", {"driver": "edge-tts"})
    assert c1.driver == "edge-tts"
    assert c1.engine == "edgetts"

    c2 = EngineConfig("test-f5", {"driver": "f5-tts"})
    assert c2.driver == "f5-tts"
    assert c2.engine == "f5tts"

    c3 = EngineConfig("test-cosy", {"driver": "cosy-voice"})
    assert c3.driver == "cosy-voice"
    assert c3.engine == "cosyvoice"


def test_categories_and_auto_language_deduction():
    # 1. 省略 categories 与 languages 时的自动推导
    c_edge = EngineConfig("test-edge", {"driver": "edgetts"})
    assert c_edge.categories == ["PresetTTS"]
    assert "zh" in c_edge.languages
    assert "en" in c_edge.languages
    assert "ja" in c_edge.languages

    # 2. 显式指定 VoiceCloneTTS 与特定语言
    c_f5 = EngineConfig(
        "test-f5",
        {
            "driver": "f5tts",
            "capabilities": {
                "categories": ["VoiceCloneTTS"],
                "languages": "zh, en",
            },
        },
    )
    assert c_f5.categories == ["VoiceCloneTTS"]
    assert c_f5.languages == ["zh", "en"]

