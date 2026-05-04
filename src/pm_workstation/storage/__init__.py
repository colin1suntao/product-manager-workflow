"""存储层模块"""

from pm_workstation.storage.base import StorageBackend, StorageObject
from pm_workstation.storage.factory import get_storage
from pm_workstation.storage.local import LocalStorage
from pm_workstation.storage.minio import MinIOStorage

__all__ = [
    "StorageBackend",
    "StorageObject",
    "get_storage",
    "LocalStorage",
    "MinIOStorage",
]
