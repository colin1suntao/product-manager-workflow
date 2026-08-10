"""认证依赖注入

提供 FastAPI 依赖项，用于验证 JWT Token 并提取当前用户。
"""


from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from pm_workstation.auth.jwt import verify_access_token
from pm_workstation.auth.models import UserInfo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> str:
    """获取当前认证用户的 ID

    Args:
        token: OAuth2 Bearer Token

    Returns:
        用户 ID

    Raises:
        HTTPException: 认证失败时抛出 401
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_access_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    return str(user_id) if user_id is not None else ""


async def get_current_user_info(token: str | None = Depends(oauth2_scheme)) -> UserInfo:
    """获取当前认证用户的完整信息（从 JWT 解码，无需查库）

    Returns:
        UserInfo 对象（id, email, username, org_id, role）
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_access_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserInfo(
        id=str(payload.get("sub", "")),
        email=str(payload.get("email", "")),
        username=str(payload.get("username", "")),
        org_id=str(payload.get("org_id", "")),
        role=str(payload.get("role", "member")),
    )


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
) -> str | None:
    """可选的当前用户（允许匿名访问）

    用于需要支持匿名访问的端点。
    """
    if not token:
        return None

    try:
        payload = verify_access_token(token)
        sub = payload.get("sub")
        return str(sub) if sub is not None else None
    except ValueError:
        return None
