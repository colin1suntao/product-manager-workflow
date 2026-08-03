"""JWT 工具模块

提供 JWT Token 的签发、解码和验证功能。
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from pm_workstation.config import settings


def create_access_token(user_id: str) -> str:
    """创建 Access Token

    Args:
        user_id: 用户唯一标识

    Returns:
        JWT Access Token 字符串
    """
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": expire,
    }

    return str(jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """创建 Refresh Token

    Args:
        user_id: 用户唯一标识

    Returns:
        (token, jti) 元组，jti 用于 Token 撤销
    """
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    jti = str(uuid.uuid4())

    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


def decode_token(token: str, secret: str | None = None) -> dict[str, Any]:
    """解码 JWT Token

    Args:
        token: JWT Token 字符串
        secret: 密钥，默认使用配置中的 jwt_secret_key

    Returns:
        Token Payload 字典

    Raises:
        JWTError: Token 无效或已过期
    """
    result = jwt.decode(token, secret or settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    return result if isinstance(result, dict) else {}


def verify_access_token(token: str) -> dict[str, Any]:
    """验证 Access Token

    Args:
        token: JWT Access Token 字符串

    Returns:
        Token Payload 字典

    Raises:
        ValueError: Token 无效、过期或类型不正确
    """
    try:
        payload = decode_token(token)
    except JWTError:
        raise ValueError("无效的认证令牌")

    if payload.get("type") != "access":
        raise ValueError("无效的认证令牌类型")

    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    """验证 Refresh Token

    Args:
        token: JWT Refresh Token 字符串

    Returns:
        Token Payload 字典

    Raises:
        ValueError: Token 无效、过期或类型不正确
    """
    try:
        payload = decode_token(token)
    except JWTError:
        raise ValueError("无效的刷新令牌")

    if payload.get("type") != "refresh":
        raise ValueError("无效的刷新令牌类型")

    return payload
