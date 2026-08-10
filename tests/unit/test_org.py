"""测试组织管理 API"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from pm_workstation.api.app import create_app
from pm_workstation.orchestrator.workflow_manager import WorkflowManager


@pytest.fixture
def app():
    from sqlalchemy import create_engine

    from pm_workstation.auth.models import Base
    engine = create_engine("sqlite:///./pm_workstation.db")
    Base.metadata.create_all(engine)
    engine.dispose()
    app = create_app()
    app.state.workflow_manager = WorkflowManager()
    return app


@pytest_asyncio.fixture
async def auth_headers(app):
    """注册并登录，返回认证 headers"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        email = f"org-test-{uuid.uuid4().hex[:8]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "test-password-123"})
        login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "test-password-123"})
        token = login_resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_org_info(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/org/info", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "name" in data
        assert data["name"].endswith("的组织")


@pytest.mark.asyncio
async def test_org_update(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put("/api/v1/org/info", json={"name": "新组织名称"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "新组织名称"


@pytest.mark.asyncio
async def test_list_groups(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/org/groups", headers=auth_headers)
        assert resp.status_code == 200
        groups = resp.json()
        assert len(groups) >= 1
        assert groups[0]["name"] == "所有成员"


@pytest.mark.asyncio
async def test_create_group(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/org/groups", json={"name": "测试组", "description": "测试描述"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "测试组"
        assert data["description"] == "测试描述"


@pytest.mark.asyncio
async def test_delete_group(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/api/v1/org/groups", json={"name": "待删除组"}, headers=auth_headers)
        group_id = create_resp.json()["id"]

        delete_resp = await client.delete(f"/api/v1/org/groups/{group_id}", headers=auth_headers)
        assert delete_resp.status_code == 200

        list_resp = await client.get("/api/v1/org/groups", headers=auth_headers)
        group_ids = [g["id"] for g in list_resp.json()]
        assert group_id not in group_ids


@pytest.mark.asyncio
async def test_group_members(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/org/groups", headers=auth_headers)
        groups = resp.json()
        default_group_id = groups[0]["id"]

        members_resp = await client.get(f"/api/v1/org/groups/{default_group_id}/members", headers=auth_headers)
        assert members_resp.status_code == 200
        members = members_resp.json()
        assert len(members) >= 1


@pytest.mark.asyncio
async def test_get_my_menus(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/org/menus", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "menu_keys" in data
        assert len(data["menu_keys"]) > 0


@pytest.mark.asyncio
async def test_get_menu_registry(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/org/menus/registry", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "menus" in data
        assert len(data["menus"]) > 0


@pytest.mark.asyncio
async def test_unauthorized_access(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/org/info")
        assert resp.status_code == 401

        resp = await client.get("/api/v1/org/groups")
        assert resp.status_code == 401
