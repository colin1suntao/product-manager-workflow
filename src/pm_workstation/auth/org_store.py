import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pm_workstation.auth.models import User
from pm_workstation.auth.org_models import (
    ALL_MENU_KEYS,
    GroupMember,
    MenuPermission,
    Organization,
    UserGroup,
)


def filter_accessible_keys(allowed_keys: set[str]) -> set[str]:
    """级联过滤：若父菜单 key 不被允许，则其子 key（`parent.child`）也不应被允许"""
    accessible: set[str] = set()
    for key in allowed_keys:
        parts = key.split(".")
        parent_allowed = all(
            ".".join(parts[:i]) in allowed_keys for i in range(1, len(parts))
        )
        if parent_allowed:
            accessible.add(key)
    return accessible


class OrgStore:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # --- 组织 ---

    async def create_org(self, name: str, owner_id: str) -> Organization:
        org = Organization(
            id=str(uuid.uuid4()),
            name=name,
            owner_id=owner_id,
        )
        self.db.add(org)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def get_org(self, org_id: str) -> Organization | None:
        stmt = select(Organization).where(Organization.id == org_id)
        result = await self.db.execute(stmt)
        return cast(Organization | None, result.scalar_one_or_none())

    async def get_org_by_owner(self, owner_id: str) -> Organization | None:
        stmt = select(Organization).where(Organization.owner_id == owner_id)
        result = await self.db.execute(stmt)
        return cast(Organization | None, result.scalar_one_or_none())

    async def update_org(self, org_id: str, name: str) -> Organization | None:
        org = await self.get_org(org_id)
        if not org:
            return None
        org.name = name
        await self.db.commit()
        await self.db.refresh(org)
        return org

    # --- 用户组 ---

    async def create_group(self, org_id: str, name: str, description: str | None = None) -> UserGroup:
        group = UserGroup(
            id=str(uuid.uuid4()),
            org_id=org_id,
            name=name,
            description=description,
        )
        self.db.add(group)
        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def get_group(self, group_id: str) -> UserGroup | None:
        stmt = select(UserGroup).where(UserGroup.id == group_id)
        result = await self.db.execute(stmt)
        return cast(UserGroup | None, result.scalar_one_or_none())

    async def list_groups(self, org_id: str) -> list[UserGroup]:
        stmt = select(UserGroup).where(UserGroup.org_id == org_id).order_by(UserGroup.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_group(self, group_id: str, name: str | None = None, description: str | None = None) -> UserGroup | None:
        group = await self.get_group(group_id)
        if not group:
            return None
        if name is not None:
            group.name = name
        if description is not None:
            group.description = description
        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def delete_group(self, group_id: str) -> bool:
        group = await self.get_group(group_id)
        if not group:
            return False
        await self.db.delete(group)
        await self.db.commit()
        return True

    async def get_member_count(self, group_id: str) -> int:
        stmt = select(GroupMember).where(GroupMember.group_id == group_id)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

    # --- 组成员 ---

    async def add_member(self, group_id: str, user_id: str) -> GroupMember:
        member = GroupMember(
            id=str(uuid.uuid4()),
            group_id=group_id,
            user_id=user_id,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(self, group_id: str, user_id: str) -> bool:
        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        member = result.scalar_one_or_none()
        if not member:
            return False
        await self.db.delete(member)
        await self.db.commit()
        return True

    async def list_members(self, group_id: str) -> list[GroupMember]:
        stmt = select(GroupMember).where(GroupMember.group_id == group_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_groups(self, org_id: str, user_id: str) -> list[UserGroup]:
        stmt = (
            select(UserGroup)
            .join(GroupMember, UserGroup.id == GroupMember.group_id)
            .where(UserGroup.org_id == org_id, GroupMember.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_org_users(self, org_id: str) -> list[User]:
        stmt = select(User).where(User.org_id == org_id).order_by(User.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # --- 菜单权限 ---

    async def set_permission(self, group_id: str, menu_key: str, can_access: bool) -> MenuPermission:
        stmt = select(MenuPermission).where(
            MenuPermission.group_id == group_id,
            MenuPermission.menu_key == menu_key,
        )
        result = await self.db.execute(stmt)
        perm = result.scalar_one_or_none()
        if perm:
            perm.can_access = can_access
        else:
            perm = MenuPermission(
                id=str(uuid.uuid4()),
                group_id=group_id,
                menu_key=menu_key,
                can_access=can_access,
            )
            self.db.add(perm)
        await self.db.commit()
        return cast(MenuPermission, perm)

    async def set_permissions_batch(self, group_id: str, permissions: list[tuple[str, bool]]) -> list[MenuPermission]:
        results = []
        for menu_key, can_access in permissions:
            perm = await self.set_permission(group_id, menu_key, can_access)
            results.append(perm)
        return results

    async def get_group_permissions(self, group_id: str) -> list[MenuPermission]:
        stmt = select(MenuPermission).where(MenuPermission.group_id == group_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_effective_menu_keys(self, org_id: str, user_id: str) -> list[str]:
        """获取用户对所有菜单的有效权限（deny by default，组成员取并集）"""
        groups = await self.get_user_groups(org_id, user_id)
        if not groups:
            return []

        group_ids = [g.id for g in groups]
        stmt = select(MenuPermission).where(MenuPermission.group_id.in_(group_ids))
        result = await self.db.execute(stmt)
        perms = list(result.scalars().all())

        allowed_keys: set[str] = set()
        for p in perms:
            if p.can_access:
                allowed_keys.add(p.menu_key)

        return sorted(filter_accessible_keys(allowed_keys))

    async def init_default_permissions(self, group_id: str) -> int:
        """为新建组初始化所有菜单的默认权限"""
        for key in ALL_MENU_KEYS:
            perm = MenuPermission(
                id=str(uuid.uuid4()),
                group_id=group_id,
                menu_key=key,
                can_access=True,
            )
            self.db.add(perm)
        await self.db.commit()
        return len(ALL_MENU_KEYS)
