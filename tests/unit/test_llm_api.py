"""LLM Provider API 测试"""

import pytest
from httpx import ASGITransport, AsyncClient

from pm_workstation.api.app import create_app
from pm_workstation.auth.jwt import create_access_token
from pm_workstation.api.routes.llm import _provider_store


@pytest.fixture
def app():
    app = create_app()
    app.state.workflow_manager = type("MockWM", (), {})()  # Mock workflow manager
    return app


@pytest.fixture
def auth_headers():
    token = create_access_token("test-user")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clear_store():
    """每个测试前清空 provider store"""
    _provider_store._configs.clear()
    yield


@pytest.mark.asyncio
async def test_create_provider(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.post("/api/v1/llm/providers", json={
            "name": "OpenAI",
            "provider_type": "openai",
            "api_key": "sk-test-key-123",
            "default_model": "gpt-4o",
        }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "OpenAI"
    assert data["is_default"] is True  # First config should be default


@pytest.mark.asyncio
async def test_list_providers(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        await client.post("/api/v1/llm/providers", json={
            "name": "OpenAI",
            "provider_type": "openai",
            "api_key": "sk-test-key",
            "default_model": "gpt-4o",
        }, headers=auth_headers)
        response = await client.get("/api/v1/llm/providers", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_update_provider(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        create_resp = await client.post("/api/v1/llm/providers", json={
            "name": "OpenAI",
            "provider_type": "openai",
            "api_key": "sk-test-key",
            "default_model": "gpt-4o",
        }, headers=auth_headers)
        provider_id = create_resp.json()["id"]

        response = await client.put(f"/api/v1/llm/providers/{provider_id}", json={
            "name": "OpenAI Updated",
        }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "OpenAI Updated"


@pytest.mark.asyncio
async def test_delete_provider(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        create_resp = await client.post("/api/v1/llm/providers", json={
            "name": "OpenAI",
            "provider_type": "openai",
            "api_key": "sk-test-key",
            "default_model": "gpt-4o",
        }, headers=auth_headers)
        provider_id = create_resp.json()["id"]

        response = await client.delete(f"/api/v1/llm/providers/{provider_id}", headers=auth_headers)
    assert response.status_code == 200
    assert "已删除" in response.json()["message"]


@pytest.mark.asyncio
async def test_set_default_provider(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        create_resp = await client.post("/api/v1/llm/providers", json={
            "name": "OpenAI",
            "provider_type": "openai",
            "api_key": "sk-test-key",
            "default_model": "gpt-4o",
        }, headers=auth_headers)
        provider_id = create_resp.json()["id"]

        # Create another provider
        await client.post("/api/v1/llm/providers", json={
            "name": "Anthropic",
            "provider_type": "anthropic",
            "api_key": "sk-ant-test-key",
            "default_model": "claude-3-5-sonnet",
        }, headers=auth_headers)

        response = await client.post(f"/api/v1/llm/providers/{provider_id}/set-default", json={}, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_custom_provider_requires_base_url(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.post("/api/v1/llm/providers", json={
            "name": "DeepSeek",
            "provider_type": "custom",
            "api_key": "sk-deepseek-key",
            "base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-chat",
        }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["provider_type"] == "custom"
