"""测试配置加载。"""

from server.core.config import app_config


def test_config_loading():
    assert app_config.api_key == "onetts-test-key"
    assert app_config.model_manager.default_keep_alive == 600
    assert app_config.tts_toolkit.cache.enable is True
    assert app_config.tts_toolkit.text_splitter.enable is True

    # 检查 edgetts provider 规范分层
    assert "edgetts" in app_config.providers
    edgetts_cfg = app_config.get_provider_config("edgetts")
    assert edgetts_cfg.enable is True
    assert edgetts_cfg.engine == "edgetts"
    assert edgetts_cfg.preload is True
    assert edgetts_cfg.keep_alive == -1
    assert "WebTTS" in edgetts_cfg.categories
    assert "zh" in edgetts_cfg.languages
    assert edgetts_cfg.default_voice == "zh-CN-XiaoxiaoNeural"
