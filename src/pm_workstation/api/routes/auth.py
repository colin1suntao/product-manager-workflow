"""认证 API 路由

提供用户注册、登录、Token 刷新、登出和密码修改功能。
"""


from fastapi import APIRouter, Depends, HTTPException

from pm_workstation.api.dependencies import get_db_session
from pm_workstation.auth.dependencies import get_current_user, get_current_user_info
from pm_workstation.auth.jwt import create_access_token, create_refresh_token, verify_refresh_token
from pm_workstation.auth.models import (
    LoginRequest,
    PasswordChange,
    TokenPair,
    UserCreate,
    UserInfo,
    UserResponse,
    UserRole,
)
from pm_workstation.auth.org_store import OrgStore
from pm_workstation.auth.user_store import UserStore, verify_password

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(user_data: UserCreate, db_session=Depends(get_db_session)) -> UserResponse:
    """注册新用户（自动创建组织+默认用户组+全量菜单权限）"""
    store = UserStore(db_session)

    existing = await store.find_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = await store.create_user(user_data.email, user_data.password, user_data.username)
    user.username = user_data.username or user.email.split("@")[0]
    user_id = user.id
    username = user.username

    org_store = OrgStore(db_session)
    org = await org_store.create_org(name=f"{username}的组织", owner_id=user_id)
    org_id = org.id
    user.org_id = org_id
    user.role = UserRole.admin

    default_group = await org_store.create_group(org_id=org_id, name="所有成员", description="默认用户组，包含所有成员")
    await org_store.add_member(default_group.id, user_id)
    await org_store.init_default_permissions(default_group.id)

    await db_session.commit()
    await db_session.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenPair, summary="用户登录")
async def login(request: LoginRequest, db_session=Depends(get_db_session)) -> TokenPair:
    """用户登录并获取 Token 对"""
    store = UserStore(db_session)
    user = await store.find_by_email(request.email)

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    access_token = create_access_token(
        user_id=user.id,
        org_id=user.org_id or "",
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        username=user.username or "",
    )
    refresh_token, _ = create_refresh_token(
        user_id=user.id,
        org_id=user.org_id or "",
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,
    )


@router.post("/refresh", summary="刷新 Access Token")
async def refresh_token(request_data: dict, db_session=Depends(get_db_session)):
    """使用 Refresh Token 获取新的 Access Token"""
    refresh_token_str = request_data.get("refresh_token", "")
    if not refresh_token_str:
        raise HTTPException(status_code=401, detail="未提供刷新令牌")

    try:
        payload = verify_refresh_token(refresh_token_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="无效的刷新令牌")

    user_id = payload["sub"]
    org_id = payload.get("org_id", "")
    role = payload.get("role", "member")

    store = UserStore(db_session)
    user = await store.find_by_id(user_id)

    new_access_token = create_access_token(
        user_id=user_id,
        org_id=org_id,
        role=role,
        username=user.username if user else "",
    )
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 900,
    }


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_me(
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
) -> UserInfo:
    """获取当前登录用户信息"""
    store = UserStore(db_session)
    user = await store.find_by_id(current_user.id)
    if user:
        return UserInfo(
            id=user.id,
            email=user.email,
            username=user.username or "",
            org_id=user.org_id or "",
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
        )
    return current_user


@router.post("/logout", summary="用户登出")
async def logout(request_data: dict):
    """登出并使 Refresh Token 失效"""
    refresh_token_str = request_data.get("refresh_token", "")
    if not refresh_token_str:
        raise HTTPException(status_code=401, detail="未提供刷新令牌")

    try:
        payload = verify_refresh_token(refresh_token_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="无效的刷新令牌")

    jti = payload["jti"]
    expires_at = payload["exp"]

    from pm_workstation.auth.token_store import token_store
    await token_store.revoke_token(jti, expires_at)

    return {"message": "登出成功"}


@router.post("/password", summary="修改密码")
async def change_password(
    password_data: PasswordChange,
    user_id: str = Depends(get_current_user),
    db_session=Depends(get_db_session),
):
    """修改当前用户密码"""
    store = UserStore(db_session)
    user = await store.find_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not verify_password(password_data.old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="旧密码不正确")

    await store.update_password(user_id, password_data.new_password)

    # 使所有已签发的 Refresh Token 失效
    from pm_workstation.auth.token_store import token_store
    await token_store.revoke_token("all", 0)  # 简化实现

    return {"message": "密码修改成功"}
