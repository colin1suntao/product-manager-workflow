from fastapi import APIRouter, Depends, HTTPException

from pm_workstation.api.dependencies import get_db_session
from pm_workstation.auth.dependencies import get_current_user_info
from pm_workstation.auth.models import UserInfo, UserResponse
from pm_workstation.auth.org_models import (
    MENU_REGISTRY,
    GroupMemberResponse,
    MenuPermissionBatchUpdate,
    MenuPermissionResponse,
    OrganizationResponse,
    UserGroupCreate,
    UserGroupResponse,
    UserGroupUpdate,
    UserPermissionsResponse,
)
from pm_workstation.auth.org_store import OrgStore
from pm_workstation.auth.user_store import UserStore

router = APIRouter(prefix="/org", tags=["组织管理"])


def _require_admin(current_user: UserInfo):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")


@router.get("/info", response_model=OrganizationResponse, summary="获取组织信息")
async def get_org_info(
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    if not current_user.org_id:
        raise HTTPException(status_code=404, detail="用户未关联组织")
    org_store = OrgStore(db_session)
    org = await org_store.get_org(current_user.org_id)
    if not org:
        raise HTTPException(status_code=404, detail="组织不存在")
    return org


@router.put("/info", response_model=OrganizationResponse, summary="更新组织信息")
async def update_org_info(
    data: dict,
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    _require_admin(current_user)
    if not current_user.org_id:
        raise HTTPException(status_code=404, detail="用户未关联组织")
    org_store = OrgStore(db_session)
    org = await org_store.update_org(current_user.org_id, data.get("name", ""))
    if not org:
        raise HTTPException(status_code=404, detail="组织不存在")
    return org


@router.get("/users", response_model=list[UserResponse], summary="获取组织成员列表")
async def list_org_users(
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    if not current_user.org_id:
        raise HTTPException(status_code=404, detail="用户未关联组织")
    org_store = OrgStore(db_session)
    users = await org_store.get_org_users(current_user.org_id)
    return [UserResponse.model_validate(u) for u in users]


@router.get("/groups", response_model=list[UserGroupResponse], summary="获取用户组列表")
async def list_groups(
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    if not current_user.org_id:
        raise HTTPException(status_code=404, detail="用户未关联组织")
    org_store = OrgStore(db_session)
    groups = await org_store.list_groups(current_user.org_id)
    result = []
    for g in groups:
        count = await org_store.get_member_count(g.id)
        group_resp = UserGroupResponse.model_validate(g)
        group_resp.member_count = count
        result.append(group_resp)
    return result


@router.post("/groups", response_model=UserGroupResponse, summary="创建用户组")
async def create_group(
    data: UserGroupCreate,
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    _require_admin(current_user)
    if not current_user.org_id:
        raise HTTPException(status_code=404, detail="用户未关联组织")
    org_store = OrgStore(db_session)
    group = await org_store.create_group(current_user.org_id, data.name, data.description)
    await org_store.init_default_permissions(group.id)
    return UserGroupResponse.model_validate(group)


@router.put("/groups/{group_id}", response_model=UserGroupResponse, summary="更新用户组")
async def update_group(
    group_id: str,
    data: UserGroupUpdate,
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    _require_admin(current_user)
    org_store = OrgStore(db_session)
    group = await org_store.update_group(group_id, data.name, data.description)
    if not group:
        raise HTTPException(status_code=404, detail="用户组不存在")
    return UserGroupResponse.model_validate(group)


@router.delete("/groups/{group_id}", summary="删除用户组")
async def delete_group(
    group_id: str,
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    _require_admin(current_user)
    org_store = OrgStore(db_session)
    success = await org_store.delete_group(group_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户组不存在")
    return {"message": "用户组已删除"}


@router.get("/groups/{group_id}/members", response_model=list[GroupMemberResponse], summary="获取组成员列表")
async def list_group_members(
    group_id: str,
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    org_store = OrgStore(db_session)
    members = await org_store.list_members(group_id)
    user_store = UserStore(db_session)
    result = []
    for m in members:
        user = await user_store.find_by_id(m.user_id)
        result.append(GroupMemberResponse(
            id=m.id,
            user_id=m.user_id,
            email=user.email if user else "",
            username=user.username if user else "",
            created_at=m.created_at,
        ))
    return result


@router.post("/groups/{group_id}/members", summary="添加组成员")
async def add_group_member(
    group_id: str,
    data: dict,
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    _require_admin(current_user)
    user_id = data.get("user_id", "")
    if not user_id:
        raise HTTPException(status_code=400, detail="请提供 user_id")
    org_store = OrgStore(db_session)
    member = await org_store.add_member(group_id, user_id)
    return {"message": "成员已添加", "id": member.id}


@router.delete("/groups/{group_id}/members/{user_id}", summary="移除组成员")
async def remove_group_member(
    group_id: str,
    user_id: str,
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    _require_admin(current_user)
    org_store = OrgStore(db_session)
    success = await org_store.remove_member(group_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="成员不存在")
    return {"message": "成员已移除"}


@router.get("/groups/{group_id}/permissions", response_model=list[MenuPermissionResponse], summary="获取用户组菜单权限")
async def get_group_permissions(
    group_id: str,
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    org_store = OrgStore(db_session)
    perms = await org_store.get_group_permissions(group_id)
    return [MenuPermissionResponse.model_validate(p) for p in perms]


@router.put("/groups/{group_id}/permissions", response_model=list[MenuPermissionResponse], summary="批量设置用户组菜单权限")
async def set_group_permissions(
    group_id: str,
    data: MenuPermissionBatchUpdate,
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    _require_admin(current_user)
    org_store = OrgStore(db_session)
    perms = await org_store.set_permissions_batch(
        group_id,
        [(p.menu_key, p.can_access) for p in data.permissions],
    )
    return [MenuPermissionResponse.model_validate(p) for p in perms]


@router.get("/menus", response_model=UserPermissionsResponse, summary="获取当前用户的有效菜单权限")
async def get_my_menus(
    current_user: UserInfo = Depends(get_current_user_info),
    db_session=Depends(get_db_session),
):
    if not current_user.org_id:
        return UserPermissionsResponse(menu_keys=[])
    org_store = OrgStore(db_session)
    if current_user.role == "admin":
        from pm_workstation.auth.org_models import ALL_MENU_KEYS
        return UserPermissionsResponse(menu_keys=list(ALL_MENU_KEYS))
    menu_keys = await org_store.get_user_effective_menu_keys(current_user.org_id, current_user.id)
    return UserPermissionsResponse(menu_keys=menu_keys)


@router.get("/menus/registry", summary="获取菜单注册表")
async def get_menu_registry():
    return {"menus": MENU_REGISTRY}
