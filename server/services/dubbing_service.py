"""
字幕时间轴配音与留白生成服务 (Dubbing Service)

Clean-room 独立设计与实现：
1. 解析标准 SRT 格式字幕（提取起止毫秒时间戳与说话人）；
2. 调度底层多 TTS 引擎逐句合成音频；
3. 计算字幕间留白间隔，精确插入纯净无声静音 PCM 块；
4. 结合 AudioTimelineTrack 实现零爆音无缝缝合；
5. 支持多角色音色映射 (Speaker-to-Voice Mapping) 与单句时间窗自适应。
"""

import base64
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from server.engines.base import TTSContext
from server.engines.registry import get_engine
from server.schemas.tts_ext import (
    TTSDubbingCueItem,
    TTSDubbingRequest,
    TTSDubbingResponse,
)
from server.services.voice_service import voice_service
from server.utils.audio_encoder import audio_encoder
from server.utils.audio_stitcher import AudioStitcher, AudioTimelineTrack

logger = logging.getLogger(__name__)

TIME_LINE_REGEX = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)
SPEAKER_PREFIX_REGEX = re.compile(r"^\[([^\]]+)\]\s*(.*)$|^([^：:\n]{1,16})[：:]\s*(.*)$")


def parse_timestamp_seconds(h: str, m: str, s: str, ms: str) -> float:
    """将时分秒毫秒转为秒数浮点数。"""
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt_to_cues(srt_content: str) -> list[TTSDubbingCueItem]:
    """解析标准 SRT 字幕纯文本为结构化字幕条目列表。"""
    if not srt_content:
        return []

    cues: list[TTSDubbingCueItem] = []
    blocks = re.split(r"\n\s*\n", srt_content.strip())

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue

        # 第一行可能是数字序号，也可能直接是时间轴
        time_line_idx = 1 if len(lines) >= 2 and TIME_LINE_REGEX.search(lines[1]) else 0
        time_match = TIME_LINE_REGEX.search(lines[time_line_idx])
        if not time_match:
            continue

        h1, m1, s1, ms1, h2, m2, s2, ms2 = time_match.groups()
        start_sec = parse_timestamp_seconds(h1, m1, s1, ms1)
        end_sec = parse_timestamp_seconds(h2, m2, s2, ms2)

        # 时间轴下方为字幕文本
        text_lines = lines[time_line_idx + 1 :]
        raw_text = " ".join(text_lines).strip()
        if not raw_text:
            continue

        # 检测说话人前缀，例如 "[Speaker 0] 你好" 或 "旁白: 你好"
        speaker: str | None = None
        clean_text = raw_text

        speaker_match = SPEAKER_PREFIX_REGEX.match(raw_text)
        if speaker_match:
            g1, g2, g3, g4 = speaker_match.groups()
            if g1:
                speaker = g1.strip()
                clean_text = g2.strip()
            elif g3:
                speaker = g3.strip()
                clean_text = g4.strip()

        cues.append(
            TTSDubbingCueItem(
                start_seconds=round(start_sec, 3),
                end_seconds=round(end_sec, 3),
                text=clean_text or raw_text,
                speaker=speaker,
            )
        )

    # 按照开始时间顺序排序
    cues.sort(key=lambda c: c.start_seconds)
    return cues


class DubbingService:
    """字幕绝对时间轴对齐配音引擎。"""

    def __init__(self):
        pass

    async def execute_dubbing(
        self,
        req: TTSDubbingRequest,
    ) -> tuple[bytes, TTSDubbingResponse]:
        """执行字幕配音全流程并返回 (音频二进制, 响应体)。"""
        # 1. 获取字幕条目 (优先 cues，其次解析 srt_content)
        cues = req.cues
        if not cues and req.srt_content:
            cues = parse_srt_to_cues(req.srt_content)

        if not cues:
            # 兜底：空字幕生成 1 秒静音
            silence_wav = AudioStitcher.generate_silence_wav(1.0)
            resp = TTSDubbingResponse(
                audio_base64=base64.b64encode(silence_wav).decode("ascii"),
                format=req.response_format,
                total_duration_seconds=1.0,
                total_cues=0,
                silence_gaps_count=0,
                total_silence_duration=1.0,
            )
            return silence_wav, resp

        # 2. 初始化时间轴轨道 (24kHz 16-bit 单声道)
        track = AudioStitcher.create_track(sample_rate=24000)
        silence_gaps_count = 0
        total_silence_duration = 0.0

        for cue in cues:
            # 2.1 检查前置留白：如果当前轨道时长小于该字幕起始时间，插入纯净静音留白
            current_time = track.current_duration_seconds
            gap = cue.start_seconds - current_time

            if gap > 0.01:
                track.append_silence(gap)
                silence_gaps_count += 1
                total_silence_duration += gap

            # 2.2 确定发音人音色
            target_voice = cue.voice
            if not target_voice and cue.speaker and req.voice_mapping:
                target_voice = req.voice_mapping.get(cue.speaker)
            if not target_voice:
                target_voice = req.default_voice

            provider_name, actual_voice = voice_service.resolve_voice(req.model, target_voice)
            engine = get_engine(provider_name)

            # 2.3 合成单句音频
            ctx = TTSContext(
                text=cue.text,
                voice=actual_voice,
                speed=req.speed,
                pitch=req.pitch,
                volume=req.volume,
                response_format="wav",
            )
            result = await engine.synthesize_with_context(ctx)

            # 2.4 计算时长与时间窗口
            window_duration = max(0.2, cue.end_seconds - cue.start_seconds)
            audio_duration = result.duration_seconds
            if audio_duration <= 0.001 and result.audio_bytes:
                # 预估时长 (24kHz, 16bit, mono: 每秒 48000 字节)
                audio_duration = max(0.1, len(result.audio_bytes) / 48000.0)

            # 如果单句超出预留窗口且开启了自动加速 (auto_speedup)
            processed_wav = result.audio_bytes
            if req.auto_speedup and audio_duration > (window_duration * 1.15):
                ratio = audio_duration / window_duration
                # 安全加速上限不超过 2.0x
                speed_ratio = min(ratio, 2.0)
                try:
                    processed_wav = self._atempo_speedup(processed_wav, speed_ratio)
                except Exception as e:
                    logger.warning("[dubbing] 音频加速失败，保持原音频: %s", e)

            # 2.5 将该句音频追加到时间轴
            track.append_wav(processed_wav)

            # 2.6 如果配音比字幕窗口短，在尾部填充静音补满当前字幕时间
            if track.current_duration_seconds < cue.end_seconds:
                pad_duration = cue.end_seconds - track.current_duration_seconds
                if pad_duration > 0.01:
                    track.append_silence(pad_duration)
                    total_silence_duration += pad_duration

        final_wav = track.to_wav_bytes()
        final_duration = round(track.current_duration_seconds, 2)

        # 根据用户选择导出对应格式
        final_audio_bytes = final_wav
        if req.response_format == "mp3":
            try:
                final_audio_bytes = audio_encoder.encode(final_wav, "wav", "mp3")
            except Exception as e:
                logger.warning("[dubbing] 转 MP3 降级为 WAV: %s", e)

        resp = TTSDubbingResponse(
            audio_base64=base64.b64encode(final_audio_bytes).decode("ascii"),
            format=req.response_format,
            total_duration_seconds=final_duration,
            total_cues=len(cues),
            silence_gaps_count=silence_gaps_count,
            total_silence_duration=round(total_silence_duration, 2),
        )

        return final_audio_bytes, resp

    def _atempo_speedup(self, wav_bytes: bytes, speed_ratio: float) -> bytes:
        """调用 ffmpeg atempo 滤镜进行保频加速。"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as in_tmp:
            in_tmp.write(wav_bytes)
            in_path = Path(in_tmp.name)

        out_path = in_path.with_suffix(".speed.wav")
        try:
            cmd = [
                "ffmpeg", "-y", "-i", str(in_path),
                "-filter:a", f"atempo={speed_ratio:.2f}",
                "-ar", "24000", "-ac", "1",
                str(out_path)
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return out_path.read_bytes()
        finally:
            in_path.unlink(missing_ok=True)
            out_path.unlink(missing_ok=True)


dubbing_service = DubbingService()
