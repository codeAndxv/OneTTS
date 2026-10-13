"""测试夹具快速加载器辅助模块。"""

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def get_fixture_path(category: str, filename: str) -> Path:
    """获取测试夹具文件的绝对路径。"""
    path = FIXTURES_DIR / category / filename
    if not path.exists():
        raise FileNotFoundError(f"测试夹具未找到: {path}")
    return path


def load_audio_fixture(filename: str = "en_speech_15s.wav") -> bytes:
    """加载测试音频文件二进制数据。"""
    path = get_fixture_path("audio", filename)
    return path.read_bytes()


def load_subtitle_fixture(filename: str = "sample_dubbing.srt") -> str:
    """加载测试字幕文本内容。"""
    path = get_fixture_path("subtitles", filename)
    return path.read_text(encoding="utf-8")


def load_text_fixture(filename: str = "sample_speech.txt") -> str:
    """加载文本测试素材。"""
    path = get_fixture_path("texts", filename)
    return path.read_text(encoding="utf-8")


def load_json_fixture(filename: str = "sample_drama.json") -> dict:
    """加载 JSON 结构化测试素材。"""
    path = get_fixture_path("texts", filename)
    return json.loads(path.read_text(encoding="utf-8"))
