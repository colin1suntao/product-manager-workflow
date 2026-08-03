"""Memory Manager - 兼容层

从持久化记忆管理器导入，保持旧代码兼容性。
"""

from .persistent_manager import (
    PersistentMemoryManager as MemoryManager,  # noqa: F401
)
from .persistent_manager import (
    get_persistent_memory_manager as get_memory_manager,  # noqa: F401
)

