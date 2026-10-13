"""OneTTS 主服务入口。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from server.api.standard import (
    models as std_models,
    speech as std_speech,
)
from server.api.x import (
    audio as x_audio,
    info as x_info,
    models as x_models,
    realtime as x_realtime,
    tasks as x_tasks,
    voices as x_voices,
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

# ── 轨道一：OpenAI 标准兼容体系 (/v1) ───────────────────────────────────
# 统一语音合成 API (OpenAI /v1/audio/speech)
app.include_router(std_speech.router)

# 模型列表 API (OpenAI /v1/models, /v1/models/{model_id})
app.include_router(std_models.router)


# ── 轨道二：OneTTS 专属高级扩展体系 (/v1/x) ─────────────────────────────
# 高级语音合成与字幕配音 (/v1/x/audio/speech, /v1/x/audio/dubbing)
app.include_router(x_audio.router)

# 发音人音色与声音克隆资产 (/v1/x/voices, /v1/x/voices/clones)
app.include_router(x_voices.router)

# 异步长文演播与多角色剧本任务 (/v1/x/tasks)
app.include_router(x_tasks.router)

# 全双工实时流式推流 WebSocket (/v1/x/realtime)
app.include_router(x_realtime.router)

# 扩展模型矩阵能力详情 (/v1/x/models)
app.include_router(x_models.router)

# 服务协议版本与底层 Provider 状态 (/v1/x/info, /v1/x/providers)
app.include_router(x_info.router)



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
