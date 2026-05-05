"""集成适配器包"""

from pm_workstation.integrations.adapters.base import (
    BaseIntegrationAdapter,
    SyncResult,
    SyncDataType,
    SyncItem,
)
from pm_workstation.integrations.adapters.registry import (
    get_adapter,
    register_adapter,
    list_registered_adapters,
    auto_discover_adapters,
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
