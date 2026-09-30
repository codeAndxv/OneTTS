"""长文本智能分句与切片工具。"""

import re
from server.core.config import app_config


def split_text_into_sentences(text: str, max_chars: int | None = None) -> list[str]:
    """将输入长文本按标点与自然句号切分为适宜流式 TTS 合成的句子片段。"""
    if not text or not text.strip():
        return []

    cfg = app_config.tts_toolkit.text_splitter
    if not cfg.enable:
        return [text.strip()]

    max_len = max_chars or cfg.max_chunk_chars
    delimiters = cfg.split_delimiters

    # 使用正则保留分隔符切分
    escaped_delims = re.escape(delimiters)
    pattern = f"([^﻿{escaped_delims}]+[{escaped_delims}]+)"

    raw_chunks = re.findall(pattern, text, flags=re.DOTALL)
    matched_len = sum(len(c) for c in raw_chunks)
    if matched_len < len(text):
        remaining = text[matched_len:].strip()
        if remaining:
            raw_chunks.append(remaining)

    if not raw_chunks:
        raw_chunks = [text.strip()]

    sentences: list[str] = []
    for chunk in raw_chunks:
        cleaned = chunk.strip()
        if not cleaned:
            continue
        if len(cleaned) > max_len:
            sub_chunks = [cleaned[i : i + max_len] for i in range(0, len(cleaned), max_len)]
            sentences.extend(sub_chunks)
        else:
            sentences.append(cleaned)

    return [s.strip() for s in sentences if s.strip()]
