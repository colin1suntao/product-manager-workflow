"""Jira API 适配器

用于与 Atlassian Jira 系统集成，支持需求、任务、用户故事等数据的导入导出。
"""

import logging
from datetime import datetime
from typing import Any, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from pm_workstation.integrations.adapters.base import (
    BaseIntegrationAdapter,
    SyncDataType,
    SyncItem,
    SyncResult,
)
from pm_workstation.integrations.adapters.registry import register_adapter
from pm_workstation.integrations.models import IntegrationType, SyncDirection, SyncTask

logger = logging.getLogger(__name__)

_JIRA_ISSUE_TYPE_MAP = {
    "Story": SyncDataType.USER_STORY,
    "Epic": SyncDataType.EPIC,
    "Task": SyncDataType.TASK,
    "Sub-task": SyncDataType.TASK,
    "Bug": SyncDataType.TASK,
}

_JIRA_STATUS_MAP = {
    "To Do": "todo",
    "In Progress": "in_progress",
    "Done": "done",
    "Backlog": "backlog",
    "Selected for Development": "selected",
}


@register_adapter(IntegrationType.JIRA)
class JiraAdapter(BaseIntegrationAdapter):
    """Jira REST API 适配器

    支持 Jira Cloud 和 Jira Server/Data Center。
    """

    @property
    def name(self) -> str:
        return "Jira"

    def authenticate(self) -> bool:
        if not HAS_HTTPX:
            logger.error("httpx is required for Jira integration")
            return False

        url = f"{self.config.api_endpoint}/rest/api/3/myself"
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(url, headers=self._build_headers())
                return response.status_code == 200
        except Exception as e:
            logger.error("Jira authentication failed: %s", e)
            return False

    def import_data(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())

        try:
            jql = self._build_jql(task, data_types)
            issues = self._search_issues(jql)

            items = []
            for issue in issues:
                item = self._parse_issue(issue)
                if item:
                    items.append(item)

            result.items = items
            result.total_count = len(items)
            result.synced_count = len(items)
            result.success = True
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.error_message = f"Import failed: {str(e)}"
            logger.error("Jira import error: %s", e)

        return result

    def export_data(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())

        try:
            source_data = task.source_data or {}
            items = source_data.get("items", [])

            created_ids = []
            for item_data in items:
                issue_id = self._create_issue(item_data)
                if issue_id:
                    created_ids.append(issue_id)

            result.synced_count = len(created_ids)
            result.total_count = len(items)
            result.success = len(created_ids) == len(items)
            result.completed_at = datetime.utcnow()
            result.items = [
                SyncItem(
                    external_id=issue_id,
                    data_type=SyncDataType.TASK,
                    title="Exported issue",
                    description="",
                    url=f"{self.config.api_endpoint}/browse/{issue_id}",
                )
                for issue_id in created_ids
            ]

        except Exception as e:
            result.error_message = f"Export failed: {str(e)}"
            logger.error("Jira export error: %s", e)

        return result

    def get_remote_status(self, task: SyncTask) -> SyncResult:
        if not task.workflow_id:
            return SyncResult(
                success=False,
                error_message="No workflow_id provided",
            )

        jql = f'labels = "{task.workflow_id}"'
        try:
            issues = self._search_issues(jql)
            items = []
            for issue in issues:
                item = self._parse_issue(issue)
                if item:
                    items.append(item)

            return SyncResult(
                success=True,
                items=items,
                total_count=len(items),
                synced_count=len(items),
                completed_at=datetime.utcnow(),
            )
        except Exception as e:
            return SyncResult(
                success=False,
                error_message=f"Status check failed: {str(e)}",
            )

    def _build_jql(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> str:
        parts = []

        if task.workflow_id:
            parts.append(f'labels = "{task.workflow_id}"')

        if data_types:
            jira_types = []
            for dt in data_types:
                for jira_type, sync_type in _JIRA_ISSUE_TYPE_MAP.items():
                    if sync_type == dt:
                        jira_types.append(jira_type)
            if jira_types:
                type_str = " OR ".join(f'issuetype = "{t}"' for t in jira_types)
                parts.append(f"({type_str})")

        return " AND ".join(parts) if parts else "ORDER BY updated DESC"

    def _search_issues(self, jql: str, max_results: int = 100) -> list[dict]:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for Jira integration")

        url = f"{self.config.api_endpoint}/rest/api/3/search"
        params = {"jql": jql, "maxResults": max_results}

        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=self._build_headers(), params=params)
            response.raise_for_status()
            data = response.json()

        return data.get("issues", [])

    def _parse_issue(self, issue: dict) -> Optional[SyncItem]:
        try:
            fields = issue.get("fields", {})
            issue_type = fields.get("issuetype", {}).get("name", "")
            data_type = _JIRA_ISSUE_TYPE_MAP.get(issue_type, SyncDataType.TASK)

            status_name = fields.get("status", {}).get("name", "")
            status = _JIRA_STATUS_MAP.get(status_name, status_name.lower().replace(" ", "_"))

            return SyncItem(
                external_id=issue.get("key", ""),
                data_type=data_type,
                title=fields.get("summary", ""),
                description=fields.get("description", "") or "",
                status=status,
                url=f"{self.config.api_endpoint}/browse/{issue.get('key', '')}",
                raw_data=issue,
                created_at=self._parse_datetime(fields.get("created")),
                updated_at=self._parse_datetime(fields.get("updated")),
            )
        except Exception as e:
            logger.warning("Failed to parse Jira issue: %s", e)
            return None

    def _create_issue(self, item_data: dict) -> Optional[str]:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for Jira integration")

        url = f"{self.config.api_endpoint}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {"key": item_data.get("project_key", "PROJ")},
                "summary": item_data.get("title", ""),
                "description": item_data.get("description", ""),
                "issuetype": {"name": item_data.get("issue_type", "Task")},
            }
        }

        if item_data.get("labels"):
            payload["fields"]["labels"] = item_data["labels"]

        with httpx.Client(timeout=30) as client:
            response = client.post(url, headers=self._build_headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        return data.get("key")

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
