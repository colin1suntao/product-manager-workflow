"""集成适配器包"""

from pm_workstation.integrations.adapters.base import (
    BaseIntegrationAdapter,
    SyncDataType,
    SyncItem,
    SyncResult,
)
from pm_workstation.integrations.adapters.registry import (
    auto_discover_adapters,
    get_adapter,
    list_registered_adapters,
    register_adapter,
)

__all__ = [
    "BaseIntegrationAdapter",
    "SyncResult",
    "SyncDataType",
    "SyncItem",
    "get_adapter",
    "register_adapter",
    "list_registered_adapters",
    "auto_discover_adapters",
]
