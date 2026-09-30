"""API 认证与 Key 校验。"""

from fastapi import Header, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from server.core.config import app_config

security = HTTPBearer(auto_error=False)


async def get_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    x_api_key: str | None = Header(None, alias="x-api-key"),
) -> str:
    """提取并校验 API Key (支持 Authorization: Bearer <key> 及 X-API-Key)。"""
    server_key = app_config.api_key.strip()
    # 如果服务端未配置任何 key，则放行
    if not server_key:
        return ""

    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials.strip()
    elif x_api_key:
        token = x_api_key.strip()

    if not token or token != server_key:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Incorrect API key provided or missing Authorization header.",
                "type": "invalid_request_error",
                "param": None,
                "code": "invalid_api_key",
            },
        )
    return token
