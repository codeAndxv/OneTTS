"""
CosyVoice 语音合成与零样本声音克隆引擎 (CosyVoice 2/3)。

基于阿里通义实验室 CosyVoice 开源大模型架构：
1. 原生支持 3~5 秒参考音频零样本声音克隆 (Zero-Shot Voice Cloning)；
2. 跨语种音色迁移（中文、英语、日语、粤语、韩语）；
3. 丰富的细粒度情感控制 (happy, sad, angry, excited, whisper 等)；
4. 支持本地 Python 运行时或 HTTP 微服务 API 两种接入模式。
"""

import asyncio
import io
import logging
from typing import AsyncGenerator

import httpx

from server.engines.base import BaseTTSEngine, TTSContext, TTSResult
from server.schemas.voice import VoiceInfo
from server.utils.audio_encoder import audio_encoder

logger = logging.getLogger(__name__)

COSYVOICE_PRESET_VOICES = [
    VoiceInfo(
        id="cosyvoice-chinese-female",
        name="Cosy-温柔女声",
        provider="cosyvoice",
        language="zh-CN",
        gender="female",
        description="阿里 CosyVoice 高清自适应女声",
    ),
    VoiceInfo(
        id="cosyvoice-chinese-male",
        name="Cosy-磁性男声",
        provider="cosyvoice",
        language="zh-CN",
        gender="male",
        description="阿里 CosyVoice 稳重专业男声",
    ),
    VoiceInfo(
        id="cosyvoice-clone",
        name="Cosy-声音克隆 (Clone Mode)",
        provider="cosyvoice",
        language="multilingual",
        gender="unknown",
        description="基于上传参考音频的零样本瞬时音色克隆",
    ),
]


class CosyVoiceEngine(BaseTTSEngine):
    """阿里 CosyVoice 大模型 TTS 适配器。"""

    def __init__(self, name: str = "cosyvoice", config: dict | None = None):
        super().__init__(name, config)
        self.default_voice = self.config.get("default_voice", "cosyvoice-chinese-female")
        self.api_url = self.config.get("api_url", "http://127.0.0.1:9233")
        self.model_dir = self.config.get("model_dir", None)
        self._local_model = None

    def list_voices(self) -> list[VoiceInfo]:
        """返回 CosyVoice 预置音色与克隆模式项。"""
        return COSYVOICE_PRESET_VOICES

    def _get_local_model(self):
        """懒加载本地 CosyVoice 运行时。"""
        if self._local_model is not None:
            return self._local_model

        try:
            from cosyvoice.cli.cosyvoice import CosyVoice
        except ImportError as e:
            err_msg = (
                "\n" + "=" * 70 + "\n"
                "[cosyvoice] 未安装 cosyvoice 依赖库，且未配置远程 api_url。\n"
                "推荐使用以下方式之一：\n"
                "  1. 启动独立 CosyVoice API 服务并在 config.yaml 中配置 api_url: http://localhost:9233\n"
                "  2. 安装本地依赖: pip install cosyvoice torchaudio\n"
                + "=" * 70
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg) from e

        model_path = self.model_dir or "pretrained_models/CosyVoice-300M"
        logger.info("[cosyvoice] 正在加载本地 CosyVoice 模型: %s", model_path)
        self._local_model = CosyVoice(model_path)
        return self._local_model

    async def synthesize_with_context(self, ctx: TTSContext) -> TTSResult:
        """执行带克隆与情感上下文的合成。"""
        # 1. 优先尝试通过 HTTP API 访问部署好的 CosyVoice 微服务
        if self.api_url:
            try:
                return await self._synthesize_via_api(ctx)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(
                    "[cosyvoice] API 节点无法连接 (%s): %s，尝试降级本地模型",
                    self.api_url, e,
                )

        # 2. 尝试使用本地 Python 运行时
        loop = asyncio.get_running_loop()

        def _infer():
            model = self._get_local_model()
            # 如果有 prompt 参考音频，走 zero-shot 克隆模式
            if ctx.prompt_audio_bytes and ctx.prompt_text:
                output = model.inference_zero_shot(
                    ctx.text,
                    ctx.prompt_text,
                    ctx.prompt_audio_bytes,
                    stream=False,
                    speed=ctx.speed,
                )
            else:
                # 预置音色合成
                output = model.inference_sft(
                    ctx.text,
                    ctx.voice or "中文女",
                    stream=False,
                    speed=ctx.speed,
                )
            return output

        output = await loop.run_in_executor(None, _infer)
        # 将采样数据转为 WAV
        import torchaudio
        bio = io.BytesIO()
        torchaudio.save(bio, output["tts_speech"], 22050, format="wav")
        wav_bytes = bio.getvalue()

        output_bytes = wav_bytes
        if ctx.response_format.lower() != "wav":
            output_bytes = audio_encoder.encode(wav_bytes, "wav", ctx.response_format)

        return TTSResult(
            audio_bytes=output_bytes,
            format=ctx.response_format,
            duration_seconds=round(len(wav_bytes) / 44100.0, 3),
            sample_rate=22050,
        )

    async def _synthesize_via_api(self, ctx: TTSContext) -> TTSResult:
        """通过标准 HTTP API 与 CosyVoice 服务交互。"""
        endpoint = f"{self.api_url.rstrip('/')}/api/tts"
        payload = {
            "text": ctx.text,
            "voice": ctx.voice,
            "speed": ctx.speed,
            "emotion": ctx.emotion,
            "prompt_text": ctx.prompt_text,
        }
        files = {}
        if ctx.prompt_audio_bytes:
            files["prompt_audio"] = ("prompt.wav", ctx.prompt_audio_bytes, "audio/wav")

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(endpoint, data=payload, files=files if files else None)
            resp.raise_for_status()
            wav_bytes = resp.content

        output_bytes = wav_bytes
        if ctx.response_format.lower() != "wav":
            output_bytes = audio_encoder.encode(wav_bytes, "wav", ctx.response_format)

        duration = round(len(wav_bytes) / 48000.0, 3)
        return TTSResult(
            audio_bytes=output_bytes,
            format=ctx.response_format,
            duration_seconds=duration,
            sample_rate=24000,
        )

    async def stream_synthesize_with_context(
        self,
        ctx: TTSContext,
    ) -> AsyncGenerator[bytes, None]:
        res = await self.synthesize_with_context(ctx)
        yield res.audio_bytes
