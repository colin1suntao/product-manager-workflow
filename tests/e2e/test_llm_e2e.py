"""LLM 工作流端到端测试

测试完整的 LLM Provider 配置和工作流集成流程。
"""

import pytest
from httpx import ASGITransport, AsyncClient

from pm_workstation.api.app import create_app
from pm_workstation.auth.jwt import create_access_token
from pm_workstation.orchestrator.workflow_manager import WorkflowManager
from pm_workstation.llm.provider_store import _provider_store


@pytest.fixture
def app():
    app = create_app()
    app.state.workflow_manager = WorkflowManager()
    return app


@pytest.fixture
def auth_headers():
    token = create_access_token("test-user")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clear_store():
    from pm_workstation.api.routes.llm import _provider_store as api_store
    api_store._configs.clear()
    _provider_store._configs.clear()
    yield


@pytest.mark.asyncio
async def test_full_llm_workflow(app, auth_headers):
    """完整 LLM 工作流测试"""
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        # 1. 创建 LLM Provider
        provider_resp = await client.post("/api/v1/llm/providers", json={
            "name": "Test OpenAI",
            "provider_type": "openai",
            "api_key": "sk-test-key",
            "default_model": "gpt-4o",
        }, headers=auth_headers)
        assert provider_resp.status_code == 200
        provider_id = provider_resp.json()["id"]

        # 2. 列出 Providers
        list_resp = await client.get("/api/v1/llm/providers", headers=auth_headers)
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 1

        # 3. 设置默认 Provider
        default_resp = await client.post(f"/api/v1/llm/providers/{provider_id}/set-default", json={}, headers=auth_headers)
        assert default_resp.status_code == 200

        # 4. 启动工作流（不指定 LLM，使用默认）
        wf_resp = await client.post("/api/v1/workflows", json={
            "requirement_text": "我需要一个电商网站的登录页面",
        }, headers=auth_headers)
        assert wf_resp.status_code == 200
        assert wf_resp.json()["id"].startswith("wf-")


@pytest.mark.asyncio
async def test_provider_crud_operations(app, auth_headers):
    """Provider CRUD 操作测试"""
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        # Create
        create_resp = await client.post("/api/v1/llm/providers", json={
            "name": "Anthropic",
            "provider_type": "anthropic",
            "api_key": "sk-ant-test",
            "default_model": "claude-3-5-sonnet",
        }, headers=auth_headers)
        assert create_resp.status_code == 200
        provider_id = create_resp.json()["id"]

        # Update
        update_resp = await client.put(f"/api/v1/llm/providers/{provider_id}", json={
            "default_model": "claude-3-opus",
        }, headers=auth_headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["default_model"] == "claude-3-opus"

        # Delete
        delete_resp = await client.delete(f"/api/v1/llm/providers/{provider_id}", headers=auth_headers)
        assert delete_resp.status_code == 200

        # Verify deletion
        list_resp = await client.get("/api/v1/llm/providers", headers=auth_headers)
        assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_multiple_providers_with_default(app, auth_headers):
    """多个 Provider 和默认设置测试"""
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        # Create OpenAI
        openai_resp = await client.post("/api/v1/llm/providers", json={
            "name": "OpenAI",
            "provider_type": "openai",
            "api_key": "sk-openai",
            "default_model": "gpt-4o",
        }, headers=auth_headers)
        openai_id = openai_resp.json()["id"]

        # Create Anthropic
        anthropic_resp = await client.post("/api/v1/llm/providers", json={
            "name": "Anthropic",
            "provider_type": "anthropic",
            "api_key": "sk-ant",
            "default_model": "claude-3",
        }, headers=auth_headers)
        anthropic_id = anthropic_resp.json()["id"]

        # Verify OpenAI is default (first created)
        list_resp = await client.get("/api/v1/llm/providers", headers=auth_headers)
        providers = list_resp.json()["providers"]
        default_providers = [p for p in providers if p["is_default"]]
        assert len(default_providers) == 1
        assert default_providers[0]["id"] == openai_id

        # Change default to Anthropic
        await client.post(f"/api/v1/llm/providers/{anthropic_id}/set-default", json={}, headers=auth_headers)

        # Verify Anthropic is now default
        list_resp = await client.get("/api/v1/llm/providers", headers=auth_headers)
        providers = list_resp.json()["providers"]
        default_providers = [p for p in providers if p["is_default"]]
        assert len(default_providers) == 1
        assert default_providers[0]["id"] == anthropic_id
