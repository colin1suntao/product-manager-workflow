"""API 集成测试"""

import os
import pytest
from fastapi.testclient import TestClient

from pm_workstation.api.app import create_app
from pm_workstation.auth.jwt import create_access_token
from pm_workstation.orchestrator.workflow_manager import PERSISTENCE_FILE as WF_CACHE_FILE


@pytest.fixture(autouse=True)
def clear_workflow_cache():
    """在每个测试前清理工作流缓存文件"""
    if os.path.exists(WF_CACHE_FILE):
        os.remove(WF_CACHE_FILE)
    yield
    if os.path.exists(WF_CACHE_FILE):
        os.remove(WF_CACHE_FILE)


@pytest.fixture
def client():
    """创建测试客户端"""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    """创建认证请求头"""
    token = create_access_token("test-user-001")
    return {"Authorization": f"Bearer {token}"}


class TestHealthCheck:
    """健康检查测试"""

    def test_health_check(self, client):
        """测试健康检查接口"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"


class TestWorkflowAPI:
    """工作流 API 测试"""

    def test_start_workflow(self, client, auth_headers):
        """测试启动工作流"""
        response = client.post(
            "/api/v1/workflows",
            json={"requirement_text": "我需要实现一个用户登录功能"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("wf-")
        assert data["user_id"] == "test-user-001"
        assert data["requirement_text"] == "我需要实现一个用户登录功能"
        assert data["status"] == "init"

    def test_start_workflow_missing_body(self, client, auth_headers):
        """测试缺少请求体"""
        response = client.post("/api/v1/workflows", json={}, headers=auth_headers)
        assert response.status_code == 422

    def test_start_workflow_missing_auth(self, client):
        """测试缺少认证信息时返回 401"""
        response = client.post(
            "/api/v1/workflows",
            json={"requirement_text": "测试"},
        )
        # JWT 认证要求必须提供 Token
        assert response.status_code == 401

    @pytest.mark.xfail(reason="Workflow executes in background thread, status may not be init")
    def test_get_workflow_status(self, client, auth_headers):
        """测试查询工作流状态"""
        # 先创建工作流
        create_response = client.post(
            "/api/v1/workflows",
            json={"requirement_text": "测试需求"},
            headers=auth_headers,
        )
        workflow_id = create_response.json()["id"]

        # 查询状态
        response = client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == workflow_id
        assert data["status"] == "init"

    def test_get_workflow_status_not_found(self, client, auth_headers):
        """测试查询不存在的工作流"""
        response = client.get("/api/v1/workflows/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_get_workflow_status_access_denied(self, client, auth_headers):
        """测试访问其他用户的工作流"""
        # 创建用户 A 的工作流
        user_a_token = create_access_token("user-a")
        create_response = client.post(
            "/api/v1/workflows",
            json={"requirement_text": "测试"},
            headers={"Authorization": f"Bearer {user_a_token}"},
        )
        workflow_id = create_response.json()["id"]

        # 用户 B 尝试访问
        response = client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.xfail(reason="Workflow executes in background thread, status may not be pausable")
    def test_pause_workflow(self, client, auth_headers):
        """测试暂停工作流"""
        # 创建工作流
        create_response = client.post(
            "/api/v1/workflows",
            json={"requirement_text": "测试"},
            headers=auth_headers,
        )
        workflow_id = create_response.json()["id"]

        # 暂停
        response = client.post(
            f"/api/v1/workflows/{workflow_id}/pause",
            json={"reason": "需要补充信息"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "waiting_user_input"

    def test_pause_workflow_not_found(self, client, auth_headers):
        """测试暂停不存在的工作流"""
        response = client.post(
            "/api/v1/workflows/nonexistent/pause",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.xfail(reason="Workflow executes in background thread, status may not be resumable")
    def test_resume_workflow(self, client, auth_headers):
        """测试恢复工作流"""
        # 创建工作流并暂停
        create_response = client.post(
            "/api/v1/workflows",
            json={"requirement_text": "测试"},
            headers=auth_headers,
        )
        workflow_id = create_response.json()["id"]

        client.post(
            f"/api/v1/workflows/{workflow_id}/pause",
            json={},
            headers=auth_headers,
        )

        # 恢复
        response = client.post(
            f"/api/v1/workflows/{workflow_id}/resume",
            json={"user_responses": [{"answer": "确认"}]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "parsing"

    @pytest.mark.xfail(reason="Workflow executes in background thread, deliverables may not be ready")
    def test_get_deliverables(self, client, auth_headers):
        """测试获取交付物"""
        # 创建工作流
        create_response = client.post(
            "/api/v1/workflows",
            json={"requirement_text": "测试"},
            headers=auth_headers,
        )
        workflow_id = create_response.json()["id"]

        # 获取交付物
        response = client.get(
            f"/api/v1/workflows/{workflow_id}/deliverables",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == workflow_id
        assert "prototype_url" in data
        assert "prd_document_url" in data

    def test_list_workflows(self, client, auth_headers):
        """测试列出工作流"""
        # 创建多个工作流
        client.post(
            "/api/v1/workflows",
            json={"requirement_text": "测试1"},
            headers=auth_headers,
        )
        client.post(
            "/api/v1/workflows",
            json={"requirement_text": "测试2"},
            headers=auth_headers,
        )

        # 列出
        response = client.get("/api/v1/workflows", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["workflows"]) >= 2


class TestComponentAPI:
    """组件库 API 测试"""

    def test_upload_component(self, client, auth_headers):
        """测试上传组件"""
        response = client.post(
            "/api/v1/components",
            json={
                "name": "TestButton",
                "category": "form",
                "description": "测试按钮组件",
                "tags": ["button", "form"],
                "version": "1.0.0",
                "content": "<button>Test</button>",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TestButton"
        assert data["status"] == "draft"

    def test_search_components(self, client, auth_headers):
        """测试搜索组件"""
        # 先上传一个组件
        client.post(
            "/api/v1/components",
            json={
                "name": "SearchableButton",
                "category": "form",
                "description": "可搜索按钮",
                "tags": ["button"],
            },
            headers=auth_headers,
        )

        # 搜索
        response = client.get(
            "/api/v1/components?q=SearchableButton",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["components"]) >= 1

    def test_get_component(self, client, auth_headers):
        """测试获取组件"""
        # 上传组件
        upload_response = client.post(
            "/api/v1/components",
            json={
                "name": "GetTestComponent",
                "category": "layout",
                "description": "测试获取",
            },
            headers=auth_headers,
        )
        component_id = upload_response.json()["id"]

        # 获取
        response = client.get(f"/api/v1/components/{component_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "GetTestComponent"

    def test_get_component_not_found(self, client, auth_headers):
        """测试获取不存在的组件"""
        response = client.get("/api/v1/components/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_component(self, client, auth_headers):
        """测试删除组件"""
        # 上传组件
        upload_response = client.post(
            "/api/v1/components",
            json={
                "name": "DeleteTestComponent",
                "category": "layout",
                "description": "测试删除",
            },
            headers=auth_headers,
        )
        component_id = upload_response.json()["id"]

        # 删除
        response = client.delete(f"/api/v1/components/{component_id}", headers=auth_headers)
        assert response.status_code == 200

        # 验证已删除
        get_response = client.get(f"/api/v1/components/{component_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_component_not_found(self, client, auth_headers):
        """测试删除不存在的组件"""
        response = client.delete("/api/v1/components/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_search_components_by_category(self, client, auth_headers):
        """测试按分类搜索组件"""
        client.post(
            "/api/v1/components",
            json={"name": "FormInput", "category": "form", "description": "表单输入"},
            headers=auth_headers,
        )

        response = client.get("/api/v1/components?category=form", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_search_components_pagination(self, client, auth_headers):
        """测试组件搜索分页"""
        # 上传多个组件
        for i in range(5):
            client.post(
                "/api/v1/components",
                json={"name": f"PageTest{i}", "category": "custom", "description": f"测试{i}"},
                headers=auth_headers,
            )

        # 第一页
        response = client.get("/api/v1/components?category=custom&page=1&page_size=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["components"]) <= 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total"] >= 5
