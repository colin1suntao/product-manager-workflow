"""GitLab API 适配器

用于与 GitLab 平台集成，支持 Issues、Merge Requests、Epics 等数据的导入导出。
"""

import logging
from datetime import datetime
from typing import Optional

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
from pm_workstation.integrations.models import IntegrationType, SyncTask

logger = logging.getLogger(__name__)

_GITLAB_LABEL_TYPE_MAP = {
    "requirement": SyncDataType.REQUIREMENT,
    "user story": SyncDataType.USER_STORY,
    "epic": SyncDataType.EPIC,
    "task": SyncDataType.TASK,
    "bug": SyncDataType.TASK,
    "feature": SyncDataType.TASK,
    "documentation": SyncDataType.DOCUMENT,
}


@register_adapter(IntegrationType.GITLAB)
class GitLabAdapter(BaseIntegrationAdapter):
    """GitLab REST API 适配器

    支持 GitLab Issues、Merge Requests、Epics 数据同步。
    """

    @property
    def name(self) -> str:
        return "GitLab"

    def authenticate(self) -> bool:
        if not HAS_HTTPX:
            return False

        url = f"{self._api_base}/api/v4/user"
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    url,
                    headers=self._build_gitlab_headers(),
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("GitLab authentication failed: %s", e)
            return False

    def import_data(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())

        try:
            project_id = self.config.settings.get("project_id", "")
            if not project_id:
                result.error_message = "Missing project_id in config settings"
                return result

            items = []
            issues = self._list_issues(project_id)

            for issue in issues:
                item = self._parse_issue(issue, data_types)
                if item:
                    items.append(item)

            result.items = items
            result.total_count = len(items)
            result.synced_count = len(items)
            result.success = True
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.error_message = f"Import failed: {str(e)}"
            logger.error("GitLab import error: %s", e)

        return result

    def export_data(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())

        try:
            project_id = self.config.settings.get("project_id", "")
            if not project_id:
                result.error_message = "Missing project_id in config settings"
                return result

            source_data = task.source_data or {}
            items = source_data.get("items", [])
            created_ids = []

            for item_data in items:
                issue_url = self._create_issue(project_id, item_data)
                if issue_url:
                    created_ids.append(issue_url)

            result.synced_count = len(created_ids)
            result.total_count = len(items)
            result.success = len(created_ids) == len(items)
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.error_message = f"Export failed: {str(e)}"
            logger.error("GitLab export error: %s", e)

        return result

    def get_remote_status(self, task: SyncTask) -> SyncResult:
        if not task.workflow_id:
            return SyncResult(success=False, error_message="No workflow_id provided")

        try:
            project_id = self.config.settings.get("project_id", "")
            if not project_id:
                return SyncResult(success=False, error_message="Missing project_id")

            issues = self._list_issues(project_id, labels=task.workflow_id)
            items = []
            for issue in issues:
                item = self._parse_issue(issue, None)
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
            return SyncResult(success=False, error_message=str(e))

    @property
    def _api_base(self) -> str:
        if self.config.api_endpoint:
            return self.config.api_endpoint
        return "https://gitlab.com"

    def _build_gitlab_headers(self) -> dict[str, str]:
        headers = {}
        if self.config.api_key:
            headers["PRIVATE-TOKEN"] = self.config.api_key
        return headers

    def _list_issues(
        self,
        project_id: str,
        labels: Optional[str] = None,
        state: str = "all",
    ) -> list[dict]:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for GitLab integration")

        url = f"{self._api_base}/api/v4/projects/{project_id}/issues"
        params = {"state": state, "per_page": 100}
        if labels:
            params["labels"] = labels

        with httpx.Client(timeout=30) as client:
            response = client.get(
                url,
                headers=self._build_gitlab_headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def _parse_issue(
        self,
        issue: dict,
        data_types: Optional[list[SyncDataType]],
    ) -> Optional[SyncItem]:
        labels = [lbl.lower() for lbl in issue.get("labels", [])]

        data_type = SyncDataType.TASK
        for label in labels:
            if label in _GITLAB_LABEL_TYPE_MAP:
                data_type = _GITLAB_LABEL_TYPE_MAP[label]
                break

        if data_types and data_type not in data_types:
            return None

        return SyncItem(
            external_id=str(issue.get("iid", "")),
            data_type=data_type,
            title=issue.get("title", ""),
            description=issue.get("description", "") or "",
            status=issue.get("state", ""),
            url=issue.get("web_url", ""),
            raw_data=issue,
            created_at=self._parse_datetime(issue.get("created_at")),
            updated_at=self._parse_datetime(issue.get("updated_at")),
            metadata={"labels": labels},
        )

    def _create_issue(
        self,
        project_id: str,
        item_data: dict,
    ) -> Optional[str]:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for GitLab integration")

        url = f"{self._api_base}/api/v4/projects/{project_id}/issues"
        payload = {
            "title": item_data.get("title", ""),
            "description": item_data.get("description", ""),
        }

        if item_data.get("labels"):
            payload["labels"] = ",".join(item_data["labels"])

        with httpx.Client(timeout=30) as client:
            response = client.post(
                url,
                headers=self._build_gitlab_headers(),
                data=payload,
            )
            response.raise_for_status()
            data = response.json()

        return data.get("web_url")

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
