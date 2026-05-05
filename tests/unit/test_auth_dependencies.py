"""Auth 依赖注入测试"""

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from pm_workstation.auth.dependencies import get_current_user, get_current_user_optional
from pm_workstation.auth.jwt import create_access_token


@pytest.fixture
def app():
    test_app = FastAPI()

    @test_app.get("/protected")
    async def protected(user_id: str = Depends(get_current_user)):
        return {"user_id": user_id}

    @test_app.get("/optional")
    async def optional(user_id: str = Depends(get_current_user_optional)):
        return {"user_id": user_id}

    return test_app


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(app):
    token = create_access_token("user-123")
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["user_id"] == "user-123"


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.get("/protected")
    assert response.status_code == 401
    assert "未提供认证令牌" in response.json()["detail"]


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.get("/protected", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_optional_endpoint_with_token(app):
    token = create_access_token("user-456")
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.get("/optional", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["user_id"] == "user-456"


@pytest.mark.asyncio
async def test_optional_endpoint_without_token(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.get("/optional")
    assert response.status_code == 200
    assert response.json()["user_id"] is None


@pytest.mark.asyncio
async def test_protected_endpoint_with_wrong_token_type(app):
    from pm_workstation.auth.jwt import create_refresh_token
    token, _ = create_refresh_token("user-wrong-type")
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "无效的认证令牌类型" in response.json()["detail"]
