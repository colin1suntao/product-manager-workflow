import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from pm_workstation.auth.models import Base


class Organization(Base):
    """组织数据库模型"""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class UserGroup(Base):
    """用户组数据库模型"""

    __tablename__ = "user_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class GroupMember(Base):
    """组成员数据库模型"""

    __tablename__ = "group_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_groups.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class MenuPermission(Base):
    """菜单权限数据库模型"""

    __tablename__ = "menu_permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_groups.id"), nullable=False, index=True)
    menu_key: Mapped[str] = mapped_column(String(100), nullable=False)
    can_access: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


# --- Pydantic 模型 ---

class OrganizationCreate(BaseModel):
    name: str


class OrganizationResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserGroupCreate(BaseModel):
    name: str
    description: str | None = None


class UserGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class UserGroupResponse(BaseModel):
    id: str
    org_id: str
    name: str
    description: str | None = None
    created_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class GroupMemberResponse(BaseModel):
    id: str
    user_id: str
    email: str = ""
    username: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class MenuPermissionCreate(BaseModel):
    menu_key: str
    can_access: bool = True


class MenuPermissionResponse(BaseModel):
    id: str
    group_id: str
    menu_key: str
    can_access: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MenuPermissionBatchUpdate(BaseModel):
    permissions: list[MenuPermissionCreate]


class UserPermissionsResponse(BaseModel):
    """用户的有效菜单权限"""
    menu_keys: list[str]


# 菜单注册表
MENU_REGISTRY: list[dict] = [
    {"key": "chat", "label": "AI 会话", "icon": "💬", "href": "/chat"},
    {
        "key": "workflows", "label": "工作流管理", "icon": "📊", "href": "/workflows",
        "children": [
            {"key": "workflows.requirements", "label": "需求输入", "icon": "📝", "href": "/requirements"},
            {"key": "workflows.list", "label": "工作流列表", "icon": "📋", "href": "/workflows"},
            {"key": "workflows.prototypes", "label": "原型预览", "icon": "🎨", "href": "/prototypes"},
            {"key": "workflows.documents", "label": "文档查看", "icon": "📄", "href": "/documents"},
            {"key": "workflows.reports", "label": "校验报告", "icon": "✅", "href": "/reports"},
        ],
    },
    {"key": "market-research", "label": "市场调研", "icon": "🔍", "href": "/market-research"},
    {"key": "channels", "label": "渠道接入", "icon": "📡", "href": "/channels"},
    {"key": "usage", "label": "模型用量", "icon": "📈", "href": "/usage"},
    {"key": "skills", "label": "PM Skills", "icon": "🎯", "href": "/skills"},
    {"key": "knowledge-base", "label": "知识库", "icon": "📚", "href": "/knowledge-base"},
    {"key": "component-library", "label": "组件库", "icon": "🧩", "href": "/component-library"},
    {
        "key": "settings", "label": "系统设置", "icon": "⚙️", "href": "/settings",
        "children": [
            {"key": "settings.memory", "label": "记忆管理", "icon": "🧠", "href": "/memory"},
            {"key": "settings.integrations", "label": "集成配置", "icon": "🔗", "href": "/integrations"},
            {"key": "settings.llm", "label": "供应商配置", "icon": "🤖", "href": "/settings/llm"},
        ],
    },
    {
        "key": "org", "label": "组织管理", "icon": "🏢", "href": "/org",
        "children": [
            {"key": "org.groups", "label": "用户组管理", "icon": "👥", "href": "/org/groups"},
            {"key": "org.permissions", "label": "权限设置", "icon": "🔐", "href": "/org/permissions"},
        ],
    },
]

ALL_MENU_KEYS: list[str] = []
for item in MENU_REGISTRY:
    ALL_MENU_KEYS.append(item["key"])
    for child in item.get("children", []):
        ALL_MENU_KEYS.append(child["key"])
