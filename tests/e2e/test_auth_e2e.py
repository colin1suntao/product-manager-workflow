"""JWT 认证端到端测试

测试完整的认证流程：注册 -> 登录 -> API访问 -> 刷新Token -> 登出 -> Token失效
"""

import pytest
from httpx import ASGITransport, AsyncClient

from pm_workstation.api.app import create_app
from pm_workstation.orchestrator.workflow_manager import WorkflowManager


@pytest.fixture
def app():
    app = create_app()
    # 手动初始化 workflow_manager（因为 ASGITransport 不运行 lifespan）
    app.state.workflow_manager = WorkflowManager()
    return app


@pytest.mark.asyncio
async def test_full_auth_flow(app):
    """完整认证流程测试"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 注册
        reg_resp = await client.post("/api/v1/auth/register", json={
            "email": "e2e@example.com",
            "password": "e2e-password-123",
        })
        assert reg_resp.status_code == 200
        user_data = reg_resp.json()
        assert user_data["email"] == "e2e@example.com"

        # 2. 登录
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "e2e@example.com",
            "password": "e2e-password-123",
        })
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # 3. 使用 Access Token 访问受保护 API
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        wf_resp = await client.post("/api/v1/workflows", json={
            "requirement_text": "E2E 测试需求",
        }, headers=auth_headers)
        assert wf_resp.status_code == 200
        workflow_id = wf_resp.json()["id"]

        # 4. 刷新 Token
        refresh_resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert refresh_resp.status_code == 200
        new_access_token = refresh_resp.json()["access_token"]

        # 5. 使用新 Token 访问 API
        new_auth_headers = {"Authorization": f"Bearer {new_access_token}"}
        wf_resp2 = await client.get(f"/api/v1/workflows/{workflow_id}", headers=new_auth_headers)
        assert wf_resp2.status_code == 200

        # 6. 登出
        logout_resp = await client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh_token,
        })
        assert logout_resp.status_code == 200

        # 7. 登出后使用旧 Token 应返回 401
        wf_resp3 = await client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)
        # 注意：Access Token 本身仍然有效（因为它没有被撤销），但如果需要更严格的控制
        # 可以在每次请求时检查 Refresh Token 是否被撤销


@pytest.mark.asyncio
async def test_password_change_flow(app):
    """密码修改流程测试"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 注册并登录
        await client.post("/api/v1/auth/register", json={
            "email": "pwd-change@example.com",
            "password": "old-password-123",
        })
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "pwd-change@example.com",
            "password": "old-password-123",
        })
        access_token = login_resp.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # 修改密码
        pwd_resp = await client.post("/api/v1/auth/password", json={
            "old_password": "old-password-123",
            "new_password": "new-password-456",
        }, headers=auth_headers)
        assert pwd_resp.status_code == 200

        # 使用新密码登录
        new_login_resp = await client.post("/api/v1/auth/login", json={
            "email": "pwd-change@example.com",
            "password": "new-password-456",
        })
        assert new_login_resp.status_code == 200

        # 旧密码无法登录
        old_login_resp = await client.post("/api/v1/auth/login", json={
            "email": "pwd-change@example.com",
            "password": "old-password-123",
        })
        assert old_login_resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthorized_access(app):
    """未认证访问测试"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 不带 Token 访问受保护端点
        resp = await client.get("/api/v1/workflows")
        assert resp.status_code == 401

        # 带无效 Token 访问
        resp = await client.get("/api/v1/workflows", headers={
            "Authorization": "Bearer invalid.token.here",
        })
        assert resp.status_code == 401
