"""飞书开放平台 API 适配器

用于与飞书（Lark）系统集成，支持文档、任务、多维表格等数据的导入导出。
"""

import logging
from datetime import datetime

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


@register_adapter(IntegrationType.FEISHU)
class FeishuAdapter(BaseIntegrationAdapter):
    """飞书开放平台 API 适配器

    支持飞书文档、任务、多维表格等数据同步。
    """

    @property
    def name(self) -> str:
        return "飞书"

    def authenticate(self) -> bool:
        if not HAS_HTTPX:
            return False

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.config.api_key,
            "app_secret": self.config.api_secret,
        }
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(url, json=payload)
                data = response.json()
                if data.get("code") == 0:
                    self.config.settings["tenant_access_token"] = data.get(
                        "tenant_access_token", ""
                    )
                    return True
                return False
        except Exception as e:
            logger.error("Feishu authentication failed: %s", e)
            return False

    def import_data(
        self,
        task: SyncTask,
        data_types: list[SyncDataType] | None = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())

        try:
            token = self.config.settings.get("tenant_access_token", "")
            if not token:
                result.error_message = "No tenant_access_token, call authenticate() first"
                return result

            items = []
            if not data_types or SyncDataType.DOCUMENT in data_types:
                docs = self._list_documents(token)
                items.extend(docs)

            if not data_types or SyncDataType.TASK in data_types:
                tasks = self._list_tasks(token)
                items.extend(tasks)

            result.items = items
            result.total_count = len(items)
            result.synced_count = len(items)
            result.success = True
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.error_message = f"Import failed: {str(e)}"
            logger.error("Feishu import error: %s", e)

        return result

    def export_data(
        self,
        task: SyncTask,
        data_types: list[SyncDataType] | None = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())

        try:
            token = self.config.settings.get("tenant_access_token", "")
            if not token:
                result.error_message = "No tenant_access_token, call authenticate() first"
                return result

            source_data = task.source_data or {}
            items = source_data.get("items", [])
            created_count = 0

            for item_data in items:
                if item_data.get("data_type") == SyncDataType.DOCUMENT.value:
                    doc_id = self._create_document(token, item_data)
                    if doc_id:
                        created_count += 1
                elif item_data.get("data_type") == SyncDataType.TASK.value:
                    task_id = self._create_task(token, item_data)
                    if task_id:
                        created_count += 1

            result.synced_count = created_count
            result.total_count = len(items)
            result.success = created_count == len(items)
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.error_message = f"Export failed: {str(e)}"
            logger.error("Feishu export error: %s", e)

        return result

    def get_remote_status(self, task: SyncTask) -> SyncResult:
        if not task.workflow_id:
            return SyncResult(success=False, error_message="No workflow_id provided")

        try:
            token = self.config.settings.get("tenant_access_token", "")
            if not token:
                return SyncResult(success=False, error_message="No access token")

            items = self._list_documents(token, title_filter=task.workflow_id)
            return SyncResult(
                success=True,
                items=items,
                total_count=len(items),
                synced_count=len(items),
                completed_at=datetime.utcnow(),
            )
        except Exception as e:
            return SyncResult(success=False, error_message=str(e))

    def _list_documents(
        self,
        token: str,
        title_filter: str | None = None,
    ) -> list[SyncItem]:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for Feishu integration")

        url = "https://open.feishu.cn/open-apis/drive/v1/files"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"folder_token": self.config.settings.get("folder_token", "")}

        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

            items = []
            for file_info in data.get("data", {}).get("items", []):
                if title_filter and title_filter.lower() not in file_info.get("name", "").lower():
                    continue

                items.append(SyncItem(
                    external_id=file_info.get("token", ""),
                    data_type=SyncDataType.DOCUMENT,
                    title=file_info.get("name", ""),
                    description="",
                    url=file_info.get("url", ""),
                    raw_data=file_info,
                ))
            return items
        except Exception as e:
            logger.warning("Failed to list Feishu documents: %s", e)
            return []

    def _list_tasks(self, token: str) -> list[SyncItem]:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for Feishu integration")

        url = "https://open.feishu.cn/open-apis/task/v2/tasks"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            items = []
            for task_info in data.get("data", {}).get("items", []):
                items.append(SyncItem(
                    external_id=task_info.get("gid", ""),
                    data_type=SyncDataType.TASK,
                    title=task_info.get("title", ""),
                    description=task_info.get("description", ""),
                    status=task_info.get("status", ""),
                    raw_data=task_info,
                ))
            return items
        except Exception as e:
            logger.warning("Failed to list Feishu tasks: %s", e)
            return []

    def _create_document(self, token: str, item_data: dict) -> str | None:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for Feishu integration")

        url = "https://open.feishu.cn/open-apis/docx/v1/documents"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "title": item_data.get("title", ""),
            "folder_token": self.config.settings.get("folder_token", ""),
        }

        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("data", {}).get("document", {}).get("document_id")
        except Exception as e:
            logger.error("Failed to create Feishu document: %s", e)
            return None

    def _create_task(self, token: str, item_data: dict) -> str | None:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for Feishu integration")

        url = "https://open.feishu.cn/open-apis/task/v2/tasks"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "title": item_data.get("title", ""),
            "description": item_data.get("description", ""),
        }

        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("data", {}).get("task", {}).get("gid")
        except Exception as e:
            logger.error("Failed to create Feishu task: %s", e)
            return None
