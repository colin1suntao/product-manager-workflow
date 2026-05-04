"""存储工厂"""

from typing import Optional

from pm_workstation.config import settings
from pm_workstation.storage.base import StorageBackend


def get_storage(
    storage_type: Optional[str] = None,
    **kwargs,
) -> StorageBackend:
    """获取存储后端
    
    Args:
        storage_type: 存储类型 (local, minio, s3)
        **kwargs: 存储后端特定参数
        
    Returns:
        存储后端实例
    """
    storage_type = storage_type or settings.storage_type
    
    if storage_type == "local":
        from pm_workstation.storage.local import LocalStorage
        return LocalStorage(**kwargs)
    elif storage_type in ("minio", "s3"):
        from pm_workstation.storage.minio import MinIOStorage
        return MinIOStorage(**kwargs)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
