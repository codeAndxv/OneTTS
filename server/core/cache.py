"""TTS 合成音频智能缓存管理。"""

import hashlib
import logging
from pathlib import Path

from server.core.config import PROJECT_ROOT, app_config

logger = logging.getLogger(__name__)


class TTSCacheManager:
    """管理合成音频的落盘与命中缓存。"""

    def __init__(self):
        self.config = app_config.tts_toolkit.cache
        cache_p = Path(self.config.cache_dir)
        self.cache_dir = cache_p if cache_p.is_absolute() else PROJECT_ROOT / cache_p
        if self.config.enable:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_cache_key(
        provider: str,
        voice: str,
        text: str,
        speed: float,
        response_format: str,
    ) -> str:
        """生成唯一哈希缓存 Key。"""
        raw = f"{provider}:{voice}:{text.strip()}:{speed:.2f}:{response_format.lower()}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, cache_key: str, response_format: str) -> bytes | None:
        """获取缓存的音频字节流。"""
        if not self.config.enable:
            return None
        file_path = self.cache_dir / f"{cache_key}.{response_format.lower()}"
        if file_path.exists():
            try:
                return file_path.read_bytes()
            except Exception as e:
                logger.warning("读取缓存文件失败: %s, 错误: %s", file_path, e)
        return None

    def put(self, cache_key: str, response_format: str, audio_bytes: bytes) -> None:
        """异步/安全写入缓存。"""
        if not self.config.enable or not audio_bytes:
            return
        file_path = self.cache_dir / f"{cache_key}.{response_format.lower()}"
        try:
            file_path.write_bytes(audio_bytes)
        except Exception as e:
            logger.warning("写入缓存文件失败: %s, 错误: %s", file_path, e)


cache_manager = TTSCacheManager()
