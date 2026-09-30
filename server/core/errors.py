"""统一 OpenAI 格式错误处理体系。"""

from typing import Any
from fastapi.responses import JSONResponse


class OpenAIAPIException(Exception):
    """自定义 OpenAI 风格 API 异常。"""

    def __init__(
        self,
        status_code: int = 400,
        message: str = "Bad Request",
        error_type: str = "invalid_request_error",
        param: str | None = None,
        code: str | None = None,
        detail: Any = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.error_type = error_type
        self.param = param
        self.code = code
        self.detail = detail
        self.headers = headers


def get_default_error_type(status_code: int) -> str:
    if status_code in (401, 403):
        return "authentication_error"
    if status_code == 404:
        return "not_found_error"
    if status_code == 422 or status_code == 400:
        return "invalid_request_error"
    if status_code == 429:
        return "rate_limit_error"
    return "api_error"


def get_default_error_code(status_code: int) -> str:
    if status_code == 401:
        return "invalid_api_key"
    if status_code == 403:
        return "permission_denied"
    if status_code == 404:
        return "resource_not_found"
    if status_code == 422:
        return "validation_error"
    if status_code == 400:
        return "bad_request"
    if status_code >= 500:
        return "internal_error"
    return "error"


def build_openai_error_json_response(
    status_code: int,
    message: str,
    error_type: str | None = None,
    param: str | None = None,
    code: str | None = None,
    raw_detail: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error_payload: dict[str, Any] = {
        "message": message,
        "type": error_type or get_default_error_type(status_code),
        "param": param,
        "code": code or get_default_error_code(status_code),
    }
    content: dict[str, Any] = {
        "error": error_payload,
        "detail": raw_detail if raw_detail is not None else message,
    }
    return JSONResponse(status_code=status_code, content=content, headers=headers)
