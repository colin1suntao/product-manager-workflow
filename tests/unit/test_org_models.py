"""组织管理单元测试"""
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pm_workstation.auth.models import Base, User, UserRole
from pm_workstation.auth.org_models import (
    ALL_MENU_KEYS,
    MENU_REGISTRY,
    GroupMember,
    MenuPermission,
    Organization,
    UserGroup,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def org(db_session: Session) -> Organization:
    org = Organization(id=str(uuid.uuid4()), name="测试组织", owner_id="owner-1")
    db_session.add(org)
    db_session.commit()
    return org


@pytest.fixture
def user(db_session: Session) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="admin@test.com",
        username="admin",
        password_hash="hash",
        role=UserRole.admin,
    )
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def group(db_session: Session, org: Organization) -> UserGroup:
    g = UserGroup(id=str(uuid.uuid4()), org_id=org.id, name="所有成员", description="默认组")
    db_session.add(g)
    db_session.commit()
    return g


class TestOrgModels:
    def test_create_organization(self, db_session: Session):
        org = Organization(id=str(uuid.uuid4()), name="新组织", owner_id="user-1")
        db_session.add(org)
        db_session.commit()
        assert org.id is not None
        assert org.name == "新组织"

    def test_create_user_group(self, db_session: Session, org: Organization):
        group = UserGroup(id=str(uuid.uuid4()), org_id=org.id, name="产品组", description="产品团队")
        db_session.add(group)
        db_session.commit()
        assert group.name == "产品组"
        assert group.description == "产品团队"

    def test_add_group_member(self, db_session: Session, group: UserGroup, user: User):
        member = GroupMember(id=str(uuid.uuid4()), group_id=group.id, user_id=user.id)
        db_session.add(member)
        db_session.commit()
        assert member.group_id == group.id
        assert member.user_id == user.id

    def test_create_menu_permission(self, db_session: Session, group: UserGroup):
        perm = MenuPermission(
            id=str(uuid.uuid4()),
            group_id=group.id,
            menu_key="chat",
            can_access=True,
        )
        db_session.add(perm)
        db_session.commit()
        assert perm.menu_key == "chat"
        assert perm.can_access is True

    def test_menu_permission_deny(self, db_session: Session, group: UserGroup):
        perm = MenuPermission(
            id=str(uuid.uuid4()),
            group_id=group.id,
            menu_key="settings",
            can_access=False,
        )
        db_session.add(perm)
        db_session.commit()
        assert perm.can_access is False

    def test_all_menu_keys_defined(self):
        assert len(ALL_MENU_KEYS) > 0
        assert "chat" in ALL_MENU_KEYS
        assert "workflows" in ALL_MENU_KEYS
        assert "settings" in ALL_MENU_KEYS
        assert "org" in ALL_MENU_KEYS
        assert "workflows.requirements" in ALL_MENU_KEYS
        assert "settings.llm" in ALL_MENU_KEYS

    def test_menu_registry_structure(self):
        top_level_keys = [item["key"] for item in MENU_REGISTRY]
        assert "chat" in top_level_keys
        assert "workflows" in top_level_keys
        assert "org" in top_level_keys

        workflows = next(item for item in MENU_REGISTRY if item["key"] == "workflows")
        assert "children" in workflows
        child_keys = [c["key"] for c in workflows["children"]]
        assert "workflows.requirements" in child_keys
        assert "workflows.list" in child_keys

    def test_multiple_groups_same_org(self, db_session: Session, org: Organization):
        g1 = UserGroup(id=str(uuid.uuid4()), org_id=org.id, name="组A")
        g2 = UserGroup(id=str(uuid.uuid4()), org_id=org.id, name="组B")
        db_session.add_all([g1, g2])
        db_session.commit()
        assert g1.org_id == g2.org_id

    def test_user_role_enum(self):
        assert UserRole.admin.value == "admin"
        assert UserRole.member.value == "member"

    def test_user_org_relationship(self, db_session: Session, org: Organization, user: User):
        user.org_id = org.id
        user.role = UserRole.admin
        db_session.commit()
        db_session.refresh(user)
        assert user.org_id == org.id
        assert user.role == UserRole.admin

    def test_group_member_cascade(self, db_session: Session, group: UserGroup, user: User):
        member = GroupMember(id=str(uuid.uuid4()), group_id=group.id, user_id=user.id)
        db_session.add(member)
        db_session.commit()
        found = db_session.query(GroupMember).filter_by(group_id=group.id).all()
        assert len(found) == 1
        assert found[0].user_id == user.id

    def test_menu_permission_parent_cascade(self):
        allowed = {"chat", "market-research", "workflows", "workflows.list"}
        from pm_workstation.auth.org_store import filter_accessible_keys
        accessible = filter_accessible_keys(allowed)
        assert "workflows" in accessible
        assert "workflows.list" in accessible

        allowed_denied = {"chat", "market-research"}
        accessible2 = filter_accessible_keys(allowed_denied)
        assert "chat" in accessible2
        assert "market-research" in accessible2
        assert "workflows" not in accessible2
        assert "workflows.list" not in accessible2

    def test_menu_permission_deep_cascade(self):
        allowed = {"settings", "settings.llm", "settings.memory"}
        from pm_workstation.auth.org_store import filter_accessible_keys
        accessible = filter_accessible_keys(allowed)
        assert "settings" in accessible
        assert "settings.llm" in accessible
        assert "settings.memory" in accessible

        allowed_no_parent = {"settings.llm"}
        accessible2 = filter_accessible_keys(allowed_no_parent)
        assert "settings.llm" not in accessible2
        assert "settings" not in accessible2

    def test_menu_permission_partial_deny(self):
        allowed = {"chat", "workflows", "workflows.requirements"}
        from pm_workstation.auth.org_store import filter_accessible_keys
        accessible = filter_accessible_keys(allowed)
        assert "chat" in accessible
        assert "workflows" in accessible
        assert "workflows.requirements" in accessible
        assert "settings" not in accessible
