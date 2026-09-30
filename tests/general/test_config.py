"""测试配置加载。"""

from server.core.config import app_config


def test_config_loading():
    assert app_config.api_key == "onetts-test-key"
    assert app_config.tts_toolkit.cache.enable is True
    assert app_config.tts_toolkit.text_splitter.enable is True

    # 检查 edgetts provider
    assert "edgetts" in app_config.providers
    edgetts_cfg = app_config.get_provider_config("edgetts")
    assert edgetts_cfg.enable is True
    assert edgetts_cfg.engine == "edgetts"
    assert "alloy" in edgetts_cfg.voice_aliases
