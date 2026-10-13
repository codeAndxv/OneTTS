"""OneTTS 发音人音色管理 CLI 工具。

用法:
    uv run python -m cli.voice list [--provider edgetts] [--lang zh]
    uv run python -m cli.voice sync --provider edgetts
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from server.core.config import PROJECT_ROOT
from server.schemas.voice import VoiceInfo
from server.services.voice_service import VOICES_DATA_DIR, voice_service

logger = logging.getLogger("cli.voice")


async def sync_edgetts_voices(output_path: Path) -> int:
    """从微软 Edge-TTS 在线服务抓取最新全量发音人列表并生成 JSON 字典。"""
    import edge_tts

    print("[OneTTS CLI] 正在连接微软 Edge-TTS 在线服务拉取最新发音人清单...")
    voices_raw = await edge_tts.list_voices()
    print(f"[OneTTS CLI] 成功拉取到 {len(voices_raw)} 个发音人，正在结构化转换...")

    # 常见精选中文/英文发音人 ID 集合
    RECOMMENDED_IDS = {
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-YunxiNeural",
        "zh-CN-YunjianNeural",
        "zh-CN-XiaoyiNeural",
        "zh-CN-YunyangNeural",
        "zh-CN-liaoning-XiaobeiNeural",
        "zh-HK-HiuMaanNeural",
        "zh-TW-HsiaoChenNeural",
        "en-US-JennyNeural",
        "en-US-GuyNeural",
        "ja-JP-NanamiNeural",
        "ja-JP-KeitaNeural",
    }

    voice_items: list[dict] = []
    for item in voices_raw:
        short_name = item.get("ShortName", "")
        locale = item.get("Locale", "zh-CN")
        gender = item.get("Gender", "Neutral").lower()
        friendly_name = item.get("FriendlyName", short_name)

        is_rec = short_name in RECOMMENDED_IDS
        tags = ["在线", "EdgeTTS"]
        if is_rec:
            tags.append("精选推荐")
        if "liaoning" in short_name.lower():
            tags.append("东北话")
        if "shaanxi" in short_name.lower():
            tags.append("陕西话")

        voice_items.append({
            "id": short_name,
            "name": friendly_name.split("-")[-1].strip() if "-" in friendly_name else friendly_name,
            "provider": "edgetts",
            "gender": gender,
            "language": locale,
            "languages": [locale, locale.split("-")[0]],
            "category": "微软神经语音",
            "tags": tags,
            "styles": item.get("VoicePersonalities", []) or [],
            "description": f"微软官方 {locale} {gender} 语音",
            "preview_url": None,
            "is_recommended": is_rec,
            "is_clone": False,
        })

    # 将精选置顶，其余按语言与名称排序
    voice_items.sort(key=lambda x: (not x["is_recommended"], x["language"], x["id"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(voice_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OneTTS CLI] 同步成功！已保存至 {output_path.resolve()} (共 {len(voice_items)} 个音色)")
    return len(voice_items)


def handle_list(args):
    """打印音色列表概览。"""
    voices = voice_service.get_static_voices(
        provider=args.provider,
        language=args.lang,
        recommended_only=args.recommended,
    )

    print("\n" + "=" * 90)
    print(f"{'ID':<30} | {'名称':<20} | {'Provider':<10} | {'语言':<10} | {'性别':<8} | {'精选'}")
    print("-" * 90)
    for v in voices:
        rec_str = "★ 推荐" if v.is_recommended else "  -"
        print(f"{v.id:<30} | {v.name[:18]:<20} | {v.provider:<10} | {v.language:<10} | {v.gender:<8} | {rec_str}")
    print("=" * 90)
    print(f"总计: {len(voices)} 个音色\n")


def handle_sync(args):
    """同步指定 Provider 的音色。"""
    provider = args.provider.lower().strip()
    if provider == "edgetts":
        out_file = VOICES_DATA_DIR / "edgetts.json"
        asyncio.run(sync_edgetts_voices(out_file))
        voice_service.reload_cache()
    else:
        print(f"[OneTTS CLI] 暂不支持自动在线同步 Provider: {provider} (目前支持: edgetts)")


def main():
    parser = argparse.ArgumentParser(description="OneTTS 发音人音色管理 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list 子命令
    list_parser = subparsers.add_parser("list", help="查看可用音色列表")
    list_parser.add_argument("-p", "--provider", type=str, default=None, help="按 Provider 过滤")
    list_parser.add_argument("-l", "--lang", type=str, default=None, help="按语言代码过滤 (如 zh, en, ja)")
    list_parser.add_argument("-r", "--recommended", action="store_true", help="仅显示精选推荐音色")

    # sync 子命令
    sync_parser = subparsers.add_parser("sync", help="同步/生成指定 Provider 的音色字典")
    sync_parser.add_argument("-p", "--provider", type=str, required=True, help="目标 Provider (如 edgetts)")

    args = parser.parse_args()
    if args.command == "list":
        handle_list(args)
    elif args.command == "sync":
        handle_sync(args)


if __name__ == "__main__":
    main()
