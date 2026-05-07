"""Auth API 路由测试"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from pm_workstation.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def unique_email():
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


@pytest.mark.asyncio
async def test_register_new_user(app, unique_email):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "password123",
        })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == unique_email
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json={
            "email": "dup@example.com",
            "password": "password123",
        })
        response = await client.post("/api/v1/auth/register", json={
            "email": "dup@example.com",
            "password": "password456",
        })
    assert response.status_code == 400
    assert "邮箱已被注册" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_short_password(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={
            "email": "short@example.com",
            "password": "123",
        })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json={
            "email": "login@example.com",
            "password": "password123",
        })
        response = await client.post("/api/v1/auth/login", json={
            "email": "login@example.com",
            "password": "password123",
        })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json={
            "email": "wrong@example.com",
            "password": "password123",
        })
        response = await client.post("/api/v1/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword",
        })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json={
            "email": "refresh@example.com",
            "password": "password123",
        })
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "refresh@example.com",
            "password": "password123",
        })
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_logout(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json={
            "email": "logout@example.com",
            "password": "password123",
        })
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "logout@example.com",
            "password": "password123",
        })
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh_token,
        })
    assert response.status_code == 200
    assert "登出成功" in response.json()["message"]
