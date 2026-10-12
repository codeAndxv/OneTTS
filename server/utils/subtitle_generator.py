"""字幕生成与时间轴格式化工具 (SRT / VTT / Cues)。"""

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class SubtitleCue:
    """字幕条目单元。"""
    index: int
    text: str
    start_seconds: float
    end_seconds: float
    start_time: str  # "00:00:00,000"
    end_time: str    # "00:00:02,500"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def format_timestamp(seconds: float, delimiter: str = ",") -> str:
    """将秒数浮点数格式化为 HH:MM:SS,mmm (SRT) 或 HH:MM:SS.mmm (VTT)。"""
    if seconds < 0:
        seconds = 0.0

    total_millis = int(round(seconds * 1000))
    hours = total_millis // 3_600_000
    minutes = (total_millis % 3_600_000) // 60_000
    secs = (total_millis % 60_000) // 1000
    millis = total_millis % 1000

    return f"{hours:02d}:{minutes:02d}:{secs:02d}{delimiter}{millis:03d}"


def build_cues_from_sentences(
    sentences: list[str],
    durations: list[float],
    start_offset: float = 0.0,
) -> list[SubtitleCue]:
    """基于分句列表和各句时长生成 SubtitleCue 列表。"""
    cues: list[SubtitleCue] = []
    current_time = start_offset

    for i, (sentence, dur) in enumerate(zip(sentences, durations), start=1):
        seg_start = current_time
        seg_end = current_time + max(dur, 0.1)
        cues.append(
            SubtitleCue(
                index=i,
                text=sentence.strip(),
                start_seconds=round(seg_start, 3),
                end_seconds=round(seg_end, 3),
                start_time=format_timestamp(seg_start, ","),
                end_time=format_timestamp(seg_end, ","),
            )
        )
        current_time = seg_end

    return cues


def generate_srt(cues: list[SubtitleCue]) -> str:
    """由 SubtitleCue 列表生成标准 SRT 格式文本。"""
    blocks: list[str] = []
    for cue in cues:
        start_ts = format_timestamp(cue.start_seconds, ",")
        end_ts = format_timestamp(cue.end_seconds, ",")
        blocks.append(f"{cue.index}\n{start_ts} --> {end_ts}\n{cue.text}\n")
    return "\n".join(blocks)


def generate_vtt(cues: list[SubtitleCue]) -> str:
    """由 SubtitleCue 列表生成标准 WebVTT 格式文本。"""
    lines: list[str] = ["WEBVTT", ""]
    for cue in cues:
        start_ts = format_timestamp(cue.start_seconds, ".")
        end_ts = format_timestamp(cue.end_seconds, ".")
        lines.append(f"{cue.index}\n{start_ts} --> {end_ts}\n{cue.text}\n")
    return "\n".join(lines)
