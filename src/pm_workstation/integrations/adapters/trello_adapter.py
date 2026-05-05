"""Trello API 适配器

用于与 Trello 系统集成，支持看板、列表、卡片等数据的导入导出。
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

_TRELLO_LIST_STATUS_MAP = {
    "Backlog": "backlog",
    "To Do": "todo",
    "In Progress": "in_progress",
    "Review": "review",
    "Done": "done",
}


@register_adapter(IntegrationType.TRELLO)
class TrelloAdapter(BaseIntegrationAdapter):
    """Trello REST API 适配器"""

    @property
    def name(self) -> str:
        return "Trello"

    def authenticate(self) -> bool:
        if not HAS_HTTPX:
            return False

        board_id = self.config.settings.get("board_id", "")
        if not board_id:
            return False

        url = f"https://api.trello.com/1/boards/{board_id}"
        params = self._get_trello_params()
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(url, params=params)
                return response.status_code == 200
        except Exception as e:
            logger.error("Trello authentication failed: %s", e)
            return False

    def import_data(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())

        try:
            board_id = self.config.settings.get("board_id", "")
            if not board_id:
                result.error_message = "No board_id in config settings"
                return result

            cards = self._get_board_cards(board_id)
            lists_map = self._get_board_lists(board_id)

            items = []
            for card in cards:
                list_name = lists_map.get(card.get("idList", ""), "")
                status = _TRELLO_LIST_STATUS_MAP.get(list_name, list_name.lower())

                items.append(SyncItem(
                    external_id=card.get("id", ""),
                    data_type=SyncDataType.TASK,
                    title=card.get("name", ""),
                    description=card.get("desc", ""),
                    status=status,
                    url=f"https://trello.com/c/{card.get('shortLink', '')}",
                    raw_data=card,
                    created_at=self._parse_datetime(card.get("dateLastActivity")),
                ))

            result.items = items
            result.total_count = len(items)
            result.synced_count = len(items)
            result.success = True
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.error_message = f"Import failed: {str(e)}"
            logger.error("Trello import error: %s", e)

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
            list_id = self.config.settings.get("list_id", "")

            created_ids = []
            for item_data in items:
                card_id = self._create_card(
                    title=item_data.get("title", ""),
                    description=item_data.get("description", ""),
                    list_id=list_id,
                )
                if card_id:
                    created_ids.append(card_id)

            result.synced_count = len(created_ids)
            result.total_count = len(items)
            result.success = len(created_ids) == len(items)
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.error_message = f"Export failed: {str(e)}"
            logger.error("Trello export error: %s", e)

        return result

    def get_remote_status(self, task: SyncTask) -> SyncResult:
        if not task.workflow_id:
            return SyncResult(success=False, error_message="No workflow_id provided")

        try:
            import_result = self.import_data(task)
            filtered_items = [
                item for item in import_result.items
                if item.raw_data.get("labels") and
                any(label.get("name") == task.workflow_id for label in item.raw_data.get("labels", []))
            ]
            return SyncResult(
                success=True,
                items=filtered_items,
                total_count=len(filtered_items),
                synced_count=len(filtered_items),
                completed_at=datetime.utcnow(),
            )
        except Exception as e:
            return SyncResult(success=False, error_message=str(e))

    def _get_trello_params(self) -> dict:
        params = {"key": self.config.api_key}
        if self.config.api_secret:
            params["token"] = self.config.api_secret
        return params

    def _get_board_cards(self, board_id: str) -> list[dict]:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for Trello integration")

        url = f"https://api.trello.com/1/boards/{board_id}/cards"
        params = {**self._get_trello_params(), "fields": "all"}

        with httpx.Client(timeout=30) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    def _get_board_lists(self, board_id: str) -> dict[str, str]:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for Trello integration")

        url = f"https://api.trello.com/1/boards/{board_id}/lists"
        params = self._get_trello_params()

        with httpx.Client(timeout=30) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            lists = response.json()

        return {lst["id"]: lst["name"] for lst in lists}

    def _create_card(
        self,
        title: str,
        description: str,
        list_id: str = "",
    ) -> Optional[str]:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for Trello integration")

        url = "https://api.trello.com/1/cards"
        params = {
            **self._get_trello_params(),
            "name": title,
            "desc": description,
        }
        if list_id:
            params["idList"] = list_id

        with httpx.Client(timeout=30) as client:
            response = client.post(url, params=params)
            response.raise_for_status()
            data = response.json()

        return data.get("id")

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
