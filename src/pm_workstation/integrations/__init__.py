"""外部系统集成适配器模块

提供与外部系统（Jira, Figma, GitHub 等）的适配器抽象层和具体实现。
"""

from pm_workstation.integrations.adapters.base import (
    BaseIntegrationAdapter,
    SyncResult,
    SyncDataType,
)
from pm_workstation.integrations.adapters.registry import get_adapter
from pm_workstation.integrations.models import (
    IntegrationConfig,
    IntegrationType,
    SyncDirection,
    SyncStatus,
    SyncTask,
)
from pm_workstation.integrations.store import (
    IntegrationStore,
    SyncTaskStore,
    integration_store,
    sync_task_store,
)

__all__ = [
    "BaseIntegrationAdapter",
    "SyncResult",
    "SyncDataType",
    "IntegrationConfig",
    "IntegrationStore",
    "IntegrationType",
    "SyncDirection",
    "SyncStatus",
    "SyncTask",
    "SyncTaskStore",
    "get_adapter",
    "integration_store",
    "sync_task_store",
]
