"""Figma REST API 适配器

用于与 Figma 设计工具集成，支持设计文件、组件、样式等数据的导入。
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


@register_adapter(IntegrationType.FIGMA)
class FigmaAdapter(BaseIntegrationAdapter):
    """Figma REST API 适配器

    支持 Figma 设计文件、组件库、样式等数据的导入。
    """

    @property
    def name(self) -> str:
        return "Figma"

    def authenticate(self) -> bool:
        if not HAS_HTTPX:
            return False

        url = "https://api.figma.com/v1/me"
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    url,
                    headers={"X-Figma-Token": self.config.api_key},
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("Figma authentication failed: %s", e)
            return False

    def import_data(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())

        try:
            file_key = self.config.settings.get("file_key", "")
            if not file_key:
                result.error_message = "No file_key in config settings"
                return result

            items = []
            if not data_types or SyncDataType.COMPONENT in data_types:
                components = self._get_components(file_key)
                items.extend(components)

            if not data_types or SyncDataType.PROTOTYPE in data_types:
                frames = self._get_frames(file_key)
                items.extend(frames)

            result.items = items
            result.total_count = len(items)
            result.synced_count = len(items)
            result.success = True
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.error_message = f"Import failed: {str(e)}"
            logger.error("Figma import error: %s", e)

        return result

    def export_data(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())
        result.error_message = "Figma API does not support export (read-only)"
        return result

    def get_remote_status(self, task: SyncTask) -> SyncResult:
        if not task.workflow_id:
            return SyncResult(success=False, error_message="No workflow_id provided")

        file_key = self.config.settings.get("file_key", "")
        if not file_key:
            return SyncResult(success=False, error_message="No file_key in config")

        try:
            file_info = self._get_file_info(file_key)
            return SyncResult(
                success=True,
                total_count=1,
                synced_count=1,
                items=[
                    SyncItem(
                        external_id=file_key,
                        data_type=SyncDataType.PROTOTYPE,
                        title=file_info.get("name", ""),
                        description="",
                        url=f"https://www.figma.com/file/{file_key}",
                        raw_data=file_info,
                    )
                ],
                completed_at=datetime.utcnow(),
            )
        except Exception as e:
            return SyncResult(success=False, error_message=str(e))

    def _get_file_info(self, file_key: str) -> dict:
        if not HAS_HTTPX:
            raise RuntimeError("httpx is required for Figma integration")

        url = f"https://api.figma.com/v1/files/{file_key}"
        headers = {"X-Figma-Token": self.config.api_key}

        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    def _get_components(self, file_key: str) -> list[SyncItem]:
        file_info = self._get_file_info(file_key)
        document = file_info.get("document", {})

        components = self._extract_components(document)
        items = []
        for comp in components:
            items.append(SyncItem(
                external_id=comp.get("id", ""),
                data_type=SyncDataType.COMPONENT,
                title=comp.get("name", ""),
                description=f"Figma component: {comp.get('name', '')}",
                url=f"https://www.figma.com/file/{file_key}?node-id={comp.get('id', '')}",
                raw_data=comp,
            ))
        return items

    def _get_frames(self, file_key: str) -> list[SyncItem]:
        file_info = self._get_file_info(file_key)
        document = file_info.get("document", {})

        frames = self._extract_frames(document)
        items = []
        for frame in frames:
            items.append(SyncItem(
                external_id=frame.get("id", ""),
                data_type=SyncDataType.PROTOTYPE,
                title=frame.get("name", ""),
                description=f"Figma frame: {frame.get('name', '')}",
                url=f"https://www.figma.com/file/{file_key}?node-id={frame.get('id', '')}",
                raw_data=frame,
            ))
        return items

    def _extract_components(self, node: dict, components: Optional[list] = None) -> list:
        if components is None:
            components = []

        if node.get("type") == "COMPONENT" or node.get("type") == "COMPONENT_SET":
            components.append(node)

        for child in node.get("children", []):
            self._extract_components(child, components)

        return components

    def _extract_frames(self, node: dict, frames: Optional[list] = None) -> list:
        if frames is None:
            frames = []

        if node.get("type") == "FRAME" and node.get("name", "").startswith("Page"):
            frames.append(node)

        for child in node.get("children", []):
            self._extract_frames(child, frames)

        return frames
