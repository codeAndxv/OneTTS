"""OneTTS 全双工实时 WebSocket 语音流端点 (/v1/x/realtime)。"""

import base64
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.core.config import app_config
from server.engines.base import TTSContext
from server.engines.registry import get_engine
from server.services.voice_service import voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/x", tags=["Realtime-Extended"])


@router.websocket("/realtime")
async def realtime_tts_stream(websocket: WebSocket):
    """面向实时 AI Agent 的全双工流式 WebSocket 接口 (/v1/x/realtime)。"""
    await websocket.accept()

    query_params = websocket.query_params
    api_key = query_params.get("api_key") or websocket.headers.get("x-api-key")
    server_key = app_config.api_key.strip()
    if server_key and api_key != server_key:
        await websocket.close(code=1008, reason="Invalid API Key")
        return

    model_name = query_params.get("model", "edgetts")
    voice_name = query_params.get("voice", "alloy")
    response_format = query_params.get("format", "mp3")
    speed = float(query_params.get("speed", 1.0))

    provider_name, actual_voice = voice_service.resolve_voice(model_name, voice_name)
    engine = get_engine(provider_name)

    buffer_text = ""
    is_interrupted = False

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
            except json.JSONDecodeError:
                continue

            event_type = data.get("type")

            if event_type == "text.append":
                delta = data.get("delta", "")
                buffer_text += delta

                # 遇到自然断句标点立即触发生成
                if any(p in delta for p in ["。", "！", "？", "!", "?", "\n", "；", ";"]):
                    sentence = buffer_text.strip()
                    buffer_text = ""
                    if sentence:
                        await _stream_sentence(websocket, engine, sentence, actual_voice, speed, response_format)

            elif event_type == "text.flush":
                sentence = buffer_text.strip()
                buffer_text = ""
                if sentence:
                    await _stream_sentence(websocket, engine, sentence, actual_voice, speed, response_format)

            elif event_type == "interrupt":
                is_interrupted = True
                buffer_text = ""
                logger.info("[realtime_ws] 收到客户端打断指令")
                await websocket.send_json({"type": "interrupted"})

    except WebSocketDisconnect:
        logger.info("[realtime_ws] WebSocket 连接正常断开")
    except Exception as e:
        logger.error("[realtime_ws] 发生异常: %s", e)


async def _stream_sentence(
    ws: WebSocket,
    engine,
    text: str,
    voice: str,
    speed: float,
    response_format: str,
):
    """单句合成并流式回传事件。"""
    await ws.send_json({"type": "sentence.start", "text": text})

    ctx = TTSContext(
        text=text,
        voice=voice,
        speed=speed,
        response_format=response_format,
    )

    total_bytes = 0
    async for chunk in engine.stream_synthesize_with_context(ctx):
        if not chunk:
            continue
        total_bytes += len(chunk)
        b64_delta = base64.b64encode(chunk).decode("ascii")
        await ws.send_json({
            "type": "audio.delta",
            "delta_base64": b64_delta,
            "format": response_format,
        })

    await ws.send_json({"type": "sentence.end", "bytes_count": total_bytes})
