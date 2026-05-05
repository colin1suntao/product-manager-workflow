"""GitHub API 适配器

用于与 GitHub 平台集成，支持 Issues、Pull Requests、Repository 等数据的导入导出。
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

_GITHUB_LABEL_TYPE_MAP = {
    "requirement": SyncDataType.REQUIREMENT,
    "user-story": SyncDataType.USER_STORY,
    "epic": SyncDataType.EPIC,
    "task": SyncDataType.TASK,
    "bug": SyncDataType.TASK,
    "enhancement": SyncDataType.TASK,
    "documentation": SyncDataType.DOCUMENT,
}


@register_adapter(IntegrationType.GITHUB)
class GitHubAdapter(BaseIntegrationAdapter):
    """GitHub REST API 适配器

    支持 GitHub Issues、Pull Requests、Repository 数据同步。
    """

    @property
    def name(self) -> str:
        return "GitHub"

    def authenticate(self) -> bool:
        if not HAS_HTTPX:
            return False

        url = f"{self._api_base}/user"
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    url,
                    headers=self._build_github_headers(),
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("GitHub authentication failed: %s", e)
            return False

    def import_data(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())

        try:
            owner = self.config.settings.get("owner", "")
            repo = self.config.settings.get("repo", "")
            if not owner or not repo:
                result.error_message = "Missing owner or repo in config settings"
                return result

            items = []
            issues = self._list_issues(owner, repo)

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
            logger.error("GitHub import error: %s", e)

        return result

    def export_data(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())

        try:
            owner = self.config.settings.get("owner", "")
            repo = self.config.settings.get("repo", "")
            if not owner or not repo:
                result.error_message = "Missing owner or repo in config settings"
                return result

            source_data = task.source_data or {}
            items = source_data.get("items", [])
            created_ids = []

            for item_data in items:
                issue_url = self._create_issue(owner, repo, item_data)
                if issue_url:
                    created_ids.append(issue_url)

            result.synced_count = len(created_ids)
            result.total_count = len(items)
            result.success = len(created_ids) == len(items)
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.error_message = f"Export failed: {str(e)}"
            logger.error("GitHub export error: %s", e)

        return result

    def get_remote_status(self, task: SyncTask) -> SyncResult:
        if not task.workflow_id:
            return SyncResult(success=False, error_message="No workflow_id provided")

        try:
            owner = self.config.settings.get("owner", "")
            repo = self.config.settings.get("repo", "")
            if not owner or not repo:
                return SyncResult(success=False, error_message="Missing owner or repo")

            issues = self._list_issues(owner, repo, labels=task.workflow_id)
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
            return f"{self.config.api_endpoint}/api/v3"
        return "https://api.github.com"

    def _build_github_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _list_issues(
        self,
        owner: str,
        repo: str,
        labels: Optional[str] = None,
        state: str = "all",
    ) -> list[dict]:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for GitHub integration")

        url = f"{self._api_base}/repos/{owner}/{repo}/issues"
        params = {"state": state, "per_page": 100}
        if labels:
            params["labels"] = labels

        with httpx.Client(timeout=30) as client:
            response = client.get(
                url,
                headers=self._build_github_headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def _parse_issue(
        self,
        issue: dict,
        data_types: Optional[list[SyncDataType]],
    ) -> Optional[SyncItem]:
        labels = [lbl.get("name", "").lower() for lbl in issue.get("labels", [])]

        data_type = SyncDataType.TASK
        for label in labels:
            if label in _GITHUB_LABEL_TYPE_MAP:
                data_type = _GITHUB_LABEL_TYPE_MAP[label]
                break

        if data_types and data_type not in data_types:
            return None

        return SyncItem(
            external_id=str(issue.get("number", "")),
            data_type=data_type,
            title=issue.get("title", ""),
            description=issue.get("body", "") or "",
            status=issue.get("state", ""),
            url=issue.get("html_url", ""),
            raw_data=issue,
            created_at=self._parse_datetime(issue.get("created_at")),
            updated_at=self._parse_datetime(issue.get("updated_at")),
            metadata={"labels": labels},
        )

    def _create_issue(
        self,
        owner: str,
        repo: str,
        item_data: dict,
    ) -> Optional[str]:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for GitHub integration")

        url = f"{self._api_base}/repos/{owner}/{repo}/issues"
        payload = {
            "title": item_data.get("title", ""),
            "body": item_data.get("description", ""),
        }

        if item_data.get("labels"):
            payload["labels"] = item_data["labels"]

        with httpx.Client(timeout=30) as client:
            response = client.post(
                url,
                headers=self._build_github_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return data.get("html_url")

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
