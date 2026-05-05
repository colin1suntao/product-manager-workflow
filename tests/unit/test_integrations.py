"""集成适配器测试"""

import json
import zipfile
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from pm_workstation.integrations.adapters.base import (
    BaseIntegrationAdapter,
    SyncDataType,
    SyncItem,
    SyncResult,
)
from pm_workstation.integrations.adapters.registry import (
    get_adapter,
    register_adapter,
    list_registered_adapters,
    auto_discover_adapters,
    _adapter_registry,
)
from pm_workstation.integrations.models import (
    IntegrationConfig,
    IntegrationType,
    SyncDirection,
    SyncStatus,
    SyncTask,
)

# Auto-discover all adapters
auto_discover_adapters()


@pytest.fixture
def jira_config():
    return IntegrationConfig(
        id="int-jira-001",
        name="My Jira",
        integration_type=IntegrationType.JIRA,
        api_endpoint="https://mycompany.atlassian.net",
        api_key="test-token",
    )


@pytest.fixture
def trello_config():
    return IntegrationConfig(
        id="int-trello-001",
        name="My Trello",
        integration_type=IntegrationType.TRELLO,
        api_key="test-key",
        api_secret="test-token",
        settings={"board_id": "board123", "list_id": "list456"},
    )


@pytest.fixture
def feishu_config():
    return IntegrationConfig(
        id="int-feishu-001",
        name="My Feishu",
        integration_type=IntegrationType.FEISHU,
        api_key="test-app-id",
        api_secret="test-app-secret",
        settings={"folder_token": "folder123"},
    )


@pytest.fixture
def figma_config():
    return IntegrationConfig(
        id="int-figma-001",
        name="My Figma",
        integration_type=IntegrationType.FIGMA,
        api_key="test-figma-token",
        settings={"file_key": "file123"},
    )


@pytest.fixture
def github_config():
    return IntegrationConfig(
        id="int-github-001",
        name="My GitHub",
        integration_type=IntegrationType.GITHUB,
        api_key="test-github-token",
        settings={"owner": "test-org", "repo": "test-repo"},
    )


@pytest.fixture
def gitlab_config():
    return IntegrationConfig(
        id="int-gitlab-001",
        name="My GitLab",
        integration_type=IntegrationType.GITLAB,
        api_key="test-gitlab-token",
        api_endpoint="https://gitlab.example.com",
        settings={"project_id": "12345"},
    )


@pytest.fixture
def sync_task():
    return SyncTask(
        id="sync-test-001",
        integration_id="int-test",
        workflow_id="wf-test-001",
        direction=SyncDirection.IMPORT,
        status=SyncStatus.PENDING,
    )


class TestAdapterRegistry:
    """适配器注册表测试"""

    def test_all_adapters_registered(self):
        expected_types = {
            IntegrationType.JIRA,
            IntegrationType.TRELLO,
            IntegrationType.FEISHU,
            IntegrationType.FIGMA,
            IntegrationType.SKETCH,
            IntegrationType.GITHUB,
            IntegrationType.GITLAB,
        }
        assert expected_types.issubset(set(_adapter_registry.keys()))

    def test_get_adapter_returns_instance(self, jira_config):
        adapter = get_adapter(jira_config)
        assert adapter is not None
        assert adapter.config == jira_config

    def test_get_adapter_unsupported_type(self):
        config = IntegrationConfig(
            id="int-custom",
            name="Custom",
            integration_type=IntegrationType.CUSTOM,
        )
        with pytest.raises(ValueError, match="No adapter registered"):
            get_adapter(config)

    def test_list_registered_adapters(self):
        adapters = list_registered_adapters()
        assert "jira" in adapters
        assert "github" in adapters
        assert "figma" in adapters


class TestBaseAdapter:
    """基础适配器测试"""

    def test_validate_config_valid(self, jira_config):
        adapter = get_adapter(jira_config)
        errors = adapter.validate_config()
        assert errors == []

    def test_validate_config_missing_name(self):
        config = IntegrationConfig(
            id="int-test",
            name="",
            integration_type=IntegrationType.JIRA,
            api_key="key",
        )
        adapter = get_adapter(config)
        errors = adapter.validate_config()
        assert len(errors) > 0

    def test_build_headers(self, jira_config):
        adapter = get_adapter(jira_config)
        headers = adapter._build_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token"

    def test_build_headers_no_api_key(self):
        config = IntegrationConfig(
            id="int-test",
            name="Test",
            integration_type=IntegrationType.JIRA,
            api_endpoint="https://example.com",
        )
        adapter = get_adapter(config)
        headers = adapter._build_headers()
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"


class TestJiraAdapter:
    """Jira 适配器测试"""

    def test_name(self, jira_config):
        adapter = get_adapter(jira_config)
        assert adapter.name == "Jira"

    @patch("pm_workstation.integrations.adapters.jira_adapter.httpx")
    def test_authenticate_success(self, mock_httpx, jira_config):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        adapter = get_adapter(jira_config)
        assert adapter.authenticate() is True

    @patch("pm_workstation.integrations.adapters.jira_adapter.httpx")
    def test_authenticate_failure(self, mock_httpx, jira_config):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        adapter = get_adapter(jira_config)
        assert adapter.authenticate() is False

    @patch("pm_workstation.integrations.adapters.jira_adapter.httpx")
    def test_import_data(self, mock_httpx, jira_config, sync_task):
        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "issues": [
                {
                    "key": "PROJ-1",
                    "fields": {
                        "summary": "Test Issue",
                        "issuetype": {"name": "Story"},
                        "status": {"name": "To Do"},
                        "description": "Test description",
                        "created": "2024-01-01T00:00:00.000+0000",
                        "updated": "2024-01-02T00:00:00.000+0000",
                    },
                }
            ]
        }
        mock_client = MagicMock()
        mock_client.get.return_value = mock_search_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        adapter = get_adapter(jira_config)
        result = adapter.import_data(sync_task)

        assert result.success is True
        assert result.total_count == 1
        assert len(result.items) == 1
        assert result.items[0].external_id == "PROJ-1"
        assert result.items[0].data_type == SyncDataType.USER_STORY
        assert result.items[0].title == "Test Issue"

    @patch("pm_workstation.integrations.adapters.jira_adapter.httpx")
    def test_export_data(self, mock_httpx, jira_config, sync_task):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "PROJ-2", "id": "10001"}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        sync_task.source_data = {
            "items": [
                {
                    "title": "New Issue",
                    "description": "New description",
                    "issue_type": "Task",
                    "project_key": "PROJ",
                }
            ]
        }

        adapter = get_adapter(jira_config)
        result = adapter.export_data(sync_task)

        assert result.success is True
        assert result.synced_count == 1


class TestTrelloAdapter:
    """Trello 适配器测试"""

    def test_name(self, trello_config):
        adapter = get_adapter(trello_config)
        assert adapter.name == "Trello"

    @patch("pm_workstation.integrations.adapters.trello_adapter.httpx")
    def test_import_data(self, mock_httpx, trello_config, sync_task):
        mock_cards_response = MagicMock()
        mock_cards_response.status_code = 200
        mock_cards_response.json.return_value = [
            {
                "id": "card1",
                "name": "Test Card",
                "desc": "Card description",
                "idList": "list1",
                "shortLink": "abc123",
                "dateLastActivity": "2024-01-01T00:00:00.000Z",
            }
        ]
        mock_lists_response = MagicMock()
        mock_lists_response.status_code = 200
        mock_lists_response.json.return_value = [
            {"id": "list1", "name": "To Do"},
            {"id": "list2", "name": "Done"},
        ]

        mock_client = MagicMock()
        mock_client.get.side_effect = [mock_cards_response, mock_lists_response]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        adapter = get_adapter(trello_config)
        result = adapter.import_data(sync_task)

        assert result.success is True
        assert result.total_count == 1
        assert result.items[0].external_id == "card1"
        assert result.items[0].title == "Test Card"
        assert result.items[0].status == "todo"


class TestFigmaAdapter:
    """Figma 适配器测试"""

    def test_name(self, figma_config):
        adapter = get_adapter(figma_config)
        assert adapter.name == "Figma"

    @patch("pm_workstation.integrations.adapters.figma_adapter.httpx")
    def test_import_data(self, mock_httpx, figma_config, sync_task):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "document": {
                "id": "0:0",
                "name": "Design File",
                "type": "DOCUMENT",
                "children": [
                    {
                        "id": "0:1",
                        "name": "Page 1",
                        "type": "CANVAS",
                        "children": [
                            {
                                "id": "1:1",
                                "name": "Page",
                                "type": "FRAME",
                                "children": [
                                    {
                                        "id": "2:1",
                                        "name": "Button",
                                        "type": "COMPONENT",
                                        "children": [],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        }
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        adapter = get_adapter(figma_config)
        result = adapter.import_data(sync_task)

        assert result.success is True
        assert result.total_count > 0
        component_items = [
            i for i in result.items if i.data_type == SyncDataType.COMPONENT
        ]
        assert len(component_items) > 0
        assert component_items[0].title == "Button"

    def test_export_not_supported(self, figma_config, sync_task):
        adapter = get_adapter(figma_config)
        result = adapter.export_data(sync_task)
        assert result.success is False
        assert "read-only" in result.error_message


class TestGitHubAdapter:
    """GitHub 适配器测试"""

    def test_name(self, github_config):
        adapter = get_adapter(github_config)
        assert adapter.name == "GitHub"

    @patch("pm_workstation.integrations.adapters.github_adapter.httpx")
    def test_import_data(self, mock_httpx, github_config, sync_task):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "number": 1,
                "title": "Test Issue",
                "body": "Issue description",
                "state": "open",
                "html_url": "https://github.com/test-org/test-repo/issues/1",
                "labels": [{"name": "user-story"}],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        adapter = get_adapter(github_config)
        result = adapter.import_data(sync_task)

        assert result.success is True
        assert result.total_count == 1
        assert result.items[0].data_type == SyncDataType.USER_STORY
        assert result.items[0].external_id == "1"


class TestGitLabAdapter:
    """GitLab 适配器测试"""

    def test_name(self, gitlab_config):
        adapter = get_adapter(gitlab_config)
        assert adapter.name == "GitLab"

    @patch("pm_workstation.integrations.adapters.gitlab_adapter.httpx")
    def test_import_data(self, mock_httpx, gitlab_config, sync_task):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "iid": 42,
                "title": "GitLab Issue",
                "description": "Issue body",
                "state": "opened",
                "web_url": "https://gitlab.example.com/test/-/issues/42",
                "labels": ["feature"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        adapter = get_adapter(gitlab_config)
        result = adapter.import_data(sync_task)

        assert result.success is True
        assert result.total_count == 1
        assert result.items[0].data_type == SyncDataType.TASK
        assert result.items[0].external_id == "42"


class TestSketchAdapter:
    """Sketch 适配器测试"""

    @pytest.fixture
    def sketch_config(self, tmp_path):
        sketch_file = tmp_path / "test.sketch"
        document = {
            "pages": [{"_ref": "page-1"}],
        }
        page = {
            "_class": "MSPage",
            "name": "Page 1",
            "do_objectID": "page-1-uuid",
            "layers": [
                {
                    "_class": "MSArtboardGroup",
                    "name": "Login Screen",
                    "do_objectID": "artboard-1",
                    "layers": [
                        {
                            "_class": "MSSymbolMaster",
                            "name": "Primary Button",
                            "do_objectID": "symbol-1",
                            "layers": [],
                        }
                    ],
                }
            ],
        }

        with zipfile.ZipFile(sketch_file, "w") as zf:
            zf.writestr("document.json", json.dumps(document))
            zf.writestr("page-1.json", json.dumps(page))

        return IntegrationConfig(
            id="int-sketch-001",
            name="Test Sketch",
            integration_type=IntegrationType.SKETCH,
            settings={"file_path": str(sketch_file)},
        )

    def test_name(self, sketch_config):
        adapter = get_adapter(sketch_config)
        assert adapter.name == "Sketch"

    def test_authenticate(self, sketch_config):
        adapter = get_adapter(sketch_config)
        assert adapter.authenticate() is True

    def test_import_data(self, sketch_config, sync_task):
        adapter = get_adapter(sketch_config)
        result = adapter.import_data(sync_task)

        assert result.success is True
        assert result.total_count > 0

        types_found = {item.data_type for item in result.items}
        assert SyncDataType.PROTOTYPE in types_found
        assert SyncDataType.COMPONENT in types_found

    def test_get_remote_status(self, sketch_config):
        adapter = get_adapter(sketch_config)
        sync_task = SyncTask(
            id="sync-test",
            integration_id="int-sketch-001",
            direction=SyncDirection.IMPORT,
            status=SyncStatus.PENDING,
        )
        result = adapter.get_remote_status(sync_task)
        assert result.success is True
        assert result.total_count == 1
