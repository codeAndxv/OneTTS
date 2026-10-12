"""OneTTS 主服务入口。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from server.api import (
    model,
    provider,
    speech,
    tts_clones,
    tts_generate,
    tts_realtime,
    tts_tasks,
    voices,
)
from server.core.config import settings
from server.core.errors import (
    OpenAIAPIException,
    build_openai_error_json_response,
    get_default_error_code,
    get_default_error_type,
)
from server.db.session import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("onetts")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务生命周期管理。"""
    logger.info("OneTTS 正在启动...")
    await init_db()
    yield
    logger.info("OneTTS 正在关闭...")


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 轨道一：OpenAI 标准兼容体系 ───────────────────────────────────
# 统一语音合成 API (OpenAI /v1/audio/speech)
app.include_router(speech.router)

# 音色管理与查询 API (/v1/audio/voices)
app.include_router(voices.router)

# 模型列表 API (OpenAI /v1/models)
app.include_router(model.router)

# Provider 信息 API (/v1/providers)
app.include_router(provider.router)


# ── 轨道二：OneTTS 专属高级扩展体系 (/v1/tts/...) ─────────────────
# 高级结构化合成与字幕导出 (/v1/tts/generate)
app.include_router(tts_generate.router)

# 异步长文演播与多角色剧本任务 (/v1/tts/tasks)
app.include_router(tts_tasks.router)

# 声音克隆与专属声音资产库 (/v1/tts/clones)
app.include_router(tts_clones.router)

# 全双工实时流式推流 WebSocket (/v1/tts/realtime)
app.include_router(tts_realtime.router)



# ── 全局错误拦截器 ──────────────────────────────────────────────

@app.exception_handler(OpenAIAPIException)
async def openai_api_exception_handler(request: Request, exc: OpenAIAPIException):
    return build_openai_error_json_response(
        status_code=exc.status_code,
        message=exc.message,
        error_type=exc.error_type,
        param=exc.param,
        code=exc.code,
        raw_detail=exc.detail,
        headers=exc.headers,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", str(exc.detail))
        error_type = exc.detail.get("type", get_default_error_type(exc.status_code))
        param = exc.detail.get("param")
        code = exc.detail.get("code", get_default_error_code(exc.status_code))
        raw_detail = exc.detail
    else:
        message = str(exc.detail)
        error_type = get_default_error_type(exc.status_code)
        param = None
        code = get_default_error_code(exc.status_code)
        raw_detail = exc.detail

    return build_openai_error_json_response(
        status_code=exc.status_code,
        message=message,
        error_type=error_type,
        param=param,
        code=code,
        raw_detail=raw_detail,
        headers=exc.headers,
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return build_openai_error_json_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        error_type=get_default_error_type(exc.status_code),
        param=None,
        code=get_default_error_code(exc.status_code),
        raw_detail=exc.detail,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = "; ".join(f"{'.'.join(str(loc) for loc in e.get('loc', []))}: {e.get('msg', '')}" for e in errors)
    first_param = None
    if errors:
        loc = errors[0].get("loc", [])
        if len(loc) > 1:
            first_param = str(loc[-1])
        elif len(loc) == 1:
            first_param = str(loc[0])

    return build_openai_error_json_response(
        status_code=400,
        message=message,
        error_type="invalid_request_error",
        param=first_param,
        code="validation_error",
        raw_detail=errors,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("[unhandled_exception] %s: %s", request.url.path, exc)
    return build_openai_error_json_response(
        status_code=500,
        message=f"Internal Server Error: {str(exc)}",
        error_type="api_error",
        param=None,
        code="internal_error",
        raw_detail=str(exc),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "OneTTS"}
