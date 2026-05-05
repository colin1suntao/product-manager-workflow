"""集成配置 API 集成测试"""

import pytest
from fastapi.testclient import TestClient

from pm_workstation.api.app import create_app
from pm_workstation.auth.jwt import create_access_token


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


class TestIntegrationConfigAPI:
    """集成配置 API 测试"""

    def test_create_integration_config(self, client, auth_headers):
        """测试创建集成配置"""
        response = client.post(
            "/api/v1/integrations/configs",
            json={
                "name": "My Jira",
                "integration_type": "jira",
                "api_endpoint": "https://jira.example.com",
                "api_key": "test-api-key",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("int-")
        assert data["name"] == "My Jira"
        assert data["integration_type"] == "jira"
        assert data["enabled"] is True

    def test_create_integration_config_invalid_type(self, client, auth_headers):
        """测试创建集成配置 - 无效类型"""
        response = client.post(
            "/api/v1/integrations/configs",
            json={
                "name": "Invalid",
                "integration_type": "invalid_type",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_list_integration_configs(self, client, auth_headers):
        """测试列出集成配置"""
        # 创建配置
        client.post(
            "/api/v1/integrations/configs",
            json={"name": "Config1", "integration_type": "jira"},
            headers=auth_headers,
        )
        client.post(
            "/api/v1/integrations/configs",
            json={"name": "Config2", "integration_type": "figma"},
            headers=auth_headers,
        )

        # 列出
        response = client.get("/api/v1/integrations/configs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

    def test_list_integration_configs_by_type(self, client, auth_headers):
        """测试按类型过滤集成配置"""
        client.post(
            "/api/v1/integrations/configs",
            json={"name": "JiraConfig", "integration_type": "jira"},
            headers=auth_headers,
        )
        client.post(
            "/api/v1/integrations/configs",
            json={"name": "FigmaConfig", "integration_type": "figma"},
            headers=auth_headers,
        )

        response = client.get(
            "/api/v1/integrations/configs?integration_type=jira",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert all(c["integration_type"] == "jira" for c in data["configs"])

    def test_get_integration_config(self, client, auth_headers):
        """测试获取集成配置"""
        create_response = client.post(
            "/api/v1/integrations/configs",
            json={"name": "GetTest", "integration_type": "github"},
            headers=auth_headers,
        )
        config_id = create_response.json()["id"]

        response = client.get(
            f"/api/v1/integrations/configs/{config_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == config_id
        assert data["name"] == "GetTest"

    def test_get_integration_config_not_found(self, client, auth_headers):
        """测试获取不存在的集成配置"""
        response = client.get(
            "/api/v1/integrations/configs/nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_update_integration_config(self, client, auth_headers):
        """测试更新集成配置"""
        create_response = client.post(
            "/api/v1/integrations/configs",
            json={"name": "UpdateTest", "integration_type": "gitlab", "enabled": True},
            headers=auth_headers,
        )
        config_id = create_response.json()["id"]

        response = client.put(
            f"/api/v1/integrations/configs/{config_id}",
            json={
                "name": "UpdatedName",
                "integration_type": "gitlab",
                "enabled": False,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "UpdatedName"
        assert data["enabled"] is False

    def test_delete_integration_config(self, client, auth_headers):
        """测试删除集成配置"""
        create_response = client.post(
            "/api/v1/integrations/configs",
            json={"name": "DeleteTest", "integration_type": "trello"},
            headers=auth_headers,
        )
        config_id = create_response.json()["id"]

        response = client.delete(
            f"/api/v1/integrations/configs/{config_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # 验证已删除
        get_response = client.get(
            f"/api/v1/integrations/configs/{config_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    def test_delete_integration_config_not_found(self, client, auth_headers):
        """测试删除不存在的集成配置"""
        response = client.delete(
            "/api/v1/integrations/configs/nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestSyncTaskAPI:
    """同步任务 API 测试"""

    def _create_config(self, client, auth_headers) -> str:
        """辅助方法：创建集成配置"""
        response = client.post(
            "/api/v1/integrations/configs",
            json={"name": "SyncTestConfig", "integration_type": "jira"},
            headers=auth_headers,
        )
        return response.json()["id"]

    def test_create_sync_task(self, client, auth_headers):
        """测试创建同步任务"""
        config_id = self._create_config(client, auth_headers)

        response = client.post(
            f"/api/v1/integrations/configs/{config_id}/sync-tasks",
            json={
                "direction": "import",
                "workflow_id": "wf-test-001",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("sync-")
        assert data["integration_id"] == config_id
        assert data["direction"] == "import"
        assert data["status"] == "pending"

    def test_create_sync_task_config_not_found(self, client, auth_headers):
        """测试为不存在的配置创建同步任务"""
        response = client.post(
            "/api/v1/integrations/configs/nonexistent/sync-tasks",
            json={"direction": "import"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_create_sync_task_disabled_config(self, client, auth_headers):
        """测试为禁用的配置创建同步任务"""
        create_response = client.post(
            "/api/v1/integrations/configs",
            json={"name": "DisabledConfig", "integration_type": "jira", "enabled": False},
            headers=auth_headers,
        )
        config_id = create_response.json()["id"]

        response = client.post(
            f"/api/v1/integrations/configs/{config_id}/sync-tasks",
            json={"direction": "import"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_create_sync_task_invalid_direction(self, client, auth_headers):
        """测试创建同步任务 - 无效方向"""
        config_id = self._create_config(client, auth_headers)

        response = client.post(
            f"/api/v1/integrations/configs/{config_id}/sync-tasks",
            json={"direction": "invalid"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_list_sync_tasks(self, client, auth_headers):
        """测试列出同步任务"""
        config_id = self._create_config(client, auth_headers)

        # 创建多个任务
        client.post(
            f"/api/v1/integrations/configs/{config_id}/sync-tasks",
            json={"direction": "import"},
            headers=auth_headers,
        )
        client.post(
            f"/api/v1/integrations/configs/{config_id}/sync-tasks",
            json={"direction": "export"},
            headers=auth_headers,
        )

        response = client.get(
            f"/api/v1/integrations/sync-tasks?integration_id={config_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

    def test_list_sync_tasks_by_status(self, client, auth_headers):
        """测试按状态过滤同步任务"""
        config_id = self._create_config(client, auth_headers)

        client.post(
            f"/api/v1/integrations/configs/{config_id}/sync-tasks",
            json={"direction": "import"},
            headers=auth_headers,
        )

        response = client.get(
            "/api/v1/integrations/sync-tasks?status=pending",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert all(t["status"] == "pending" for t in data["tasks"])

    def test_get_sync_task(self, client, auth_headers):
        """测试获取同步任务"""
        config_id = self._create_config(client, auth_headers)

        create_response = client.post(
            f"/api/v1/integrations/configs/{config_id}/sync-tasks",
            json={"direction": "import", "workflow_id": "wf-test"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        response = client.get(
            f"/api/v1/integrations/sync-tasks/{task_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["integration_id"] == config_id
        assert data["workflow_id"] == "wf-test"

    def test_get_sync_task_not_found(self, client, auth_headers):
        """测试获取不存在的同步任务"""
        response = client.get(
            "/api/v1/integrations/sync-tasks/nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_cancel_sync_task(self, client, auth_headers):
        """测试取消同步任务"""
        config_id = self._create_config(client, auth_headers)

        create_response = client.post(
            f"/api/v1/integrations/configs/{config_id}/sync-tasks",
            json={"direction": "import"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        response = client.post(
            f"/api/v1/integrations/sync-tasks/{task_id}/cancel",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # 验证状态
        get_response = client.get(
            f"/api/v1/integrations/sync-tasks/{task_id}",
            headers=auth_headers,
        )
        assert get_response.json()["status"] == "cancelled"

    def test_cancel_sync_task_not_found(self, client, auth_headers):
        """测试取消不存在的同步任务"""
        response = client.post(
            "/api/v1/integrations/sync-tasks/nonexistent/cancel",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 400
