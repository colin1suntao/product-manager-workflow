"""Sketch 文件格式适配器

用于解析和导出 Sketch 文件格式（.sketch），支持页面、画板、组件等数据。
Sketch 文件本质上是 ZIP 压缩包，包含 JSON 格式的设计数据。
"""

import json
import logging
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from pm_workstation.integrations.adapters.base import (
    BaseIntegrationAdapter,
    SyncDataType,
    SyncItem,
    SyncResult,
)
from pm_workstation.integrations.adapters.registry import register_adapter
from pm_workstation.integrations.models import IntegrationType, SyncTask

logger = logging.getLogger(__name__)

_SKETCH_LAYER_TYPES = {
    "MSArtboardGroup": SyncDataType.PROTOTYPE,
    "MSSymbolMaster": SyncDataType.COMPONENT,
    "MSPage": SyncDataType.DOCUMENT,
    "MSLayerGroup": SyncDataType.PROTOTYPE,
}


@register_adapter(IntegrationType.SKETCH)
class SketchAdapter(BaseIntegrationAdapter):
    """Sketch 文件格式适配器

    解析 .sketch 文件（ZIP 格式），提取页面、画板、组件等数据。
    """

    @property
    def name(self) -> str:
        return "Sketch"

    def authenticate(self) -> bool:
        file_path = self.config.settings.get("file_path", "")
        if not file_path:
            return False
        return Path(file_path).exists()

    def import_data(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())

        try:
            file_path = self.config.settings.get("file_path", "")
            if not file_path:
                result.error_message = "No file_path in config settings"
                return result

            items = self._parse_sketch_file(file_path, data_types)

            result.items = items
            result.total_count = len(items)
            result.synced_count = len(items)
            result.success = True
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.error_message = f"Import failed: {str(e)}"
            logger.error("Sketch import error: %s", e)

        return result

    def export_data(
        self,
        task: SyncTask,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> SyncResult:
        result = SyncResult(success=False, started_at=datetime.utcnow())
        result.error_message = "Sketch export requires the Sketch application"
        return result

    def get_remote_status(self, task: SyncTask) -> SyncResult:
        file_path = self.config.settings.get("file_path", "")
        if not file_path or not Path(file_path).exists():
            return SyncResult(
                success=False,
                error_message=f"Sketch file not found: {file_path}",
            )

        try:
            stat = Path(file_path).stat()
            return SyncResult(
                success=True,
                total_count=1,
                synced_count=1,
                items=[
                    SyncItem(
                        external_id=file_path,
                        data_type=SyncDataType.DOCUMENT,
                        title=Path(file_path).name,
                        description="Sketch design file",
                        metadata={
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        },
                    )
                ],
                completed_at=datetime.utcnow(),
            )
        except Exception as e:
            return SyncResult(success=False, error_message=str(e))

    def _parse_sketch_file(
        self,
        file_path: str,
        data_types: Optional[list[SyncDataType]] = None,
    ) -> list[SyncItem]:
        items: list[SyncItem] = []

        with zipfile.ZipFile(file_path, "r") as zf:
            if "document.json" not in zf.namelist():
                raise ValueError("Invalid Sketch file: missing document.json")

            with zf.open("document.json") as f:
                document = json.loads(f.read())

            for page_info in document.get("pages", []):
                page_id = page_info.get("_ref", "")
                page_filename = f"{page_id}.json"

                if page_filename in zf.namelist():
                    with zf.open(page_filename) as f:
                        page_data = json.loads(f.read())

                    page_items = self._extract_items(
                        page_data, page_id, data_types
                    )
                    items.extend(page_items)

        return items

    def _extract_items(
        self,
        node: dict,
        page_id: str,
        data_types: Optional[list[SyncDataType]] = None,
        parent_path: str = "",
    ) -> list[SyncItem]:
        items: list[SyncItem] = []
        layer_type = node.get("_class", "")
        layer_name = node.get("name", "")
        current_path = f"{parent_path}/{layer_name}" if parent_path else layer_name

        sync_type = _SKETCH_LAYER_TYPES.get(layer_type)
        if sync_type and (not data_types or sync_type in data_types):
            items.append(SyncItem(
                external_id=node.get("do_objectID", ""),
                data_type=sync_type,
                title=layer_name,
                description=f"Sketch {layer_type}: {layer_name}",
                metadata={
                    "page_id": page_id,
                    "path": current_path,
                    "type": layer_type,
                },
                raw_data={"_class": layer_type, "name": layer_name},
            ))

        for child in node.get("layers", []):
            items.extend(self._extract_items(child, page_id, data_types, current_path))

        return items
