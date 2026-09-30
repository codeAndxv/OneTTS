"""OneTTS 命令行快速合成与测试工具。"""

import argparse
import asyncio
from pathlib import Path
from server.schemas.speech import SpeechRequest
from server.services.speech_service import speech_service


def main():
    parser = argparse.ArgumentParser(description="OneTTS 命令行语音合成工具")
    parser.add_argument("text", type=str, help="待朗读/合成的文本")
    parser.add_argument("-v", "--voice", type=str, default="alloy", help="目标音色 ID 或别名 (默认: alloy)")
    parser.add_argument("-m", "--model", type=str, default="edgetts", help="目标模型或引擎 (默认: edgetts)")
    parser.add_argument("-s", "--speed", type=float, default=1.0, help="语速倍率 (默认: 1.0)")
    parser.add_argument("-f", "--format", type=str, default="mp3", help="音频格式 (默认: mp3)")
    parser.add_argument("-o", "--output", type=str, default="output.mp3", help="输出音频文件路径")

    args = parser.parse_args()

    async def _run():
        print(f"[OneTTS] 正在合成文本: '{args.text}' (音色: {args.voice}, 引擎: {args.model})...")
        req = SpeechRequest(
            input=args.text,
            voice=args.voice,
            model=args.model,
            speed=args.speed,
            response_format=args.format,
        )
        audio = await speech_service.synthesize_speech(req)
        out_p = Path(args.output)
        out_p.write_bytes(audio)
        print(f"[OneTTS] 合成完成！已保存至: {out_p.resolve()} ({len(audio) / 1024:.1f} KB)")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
