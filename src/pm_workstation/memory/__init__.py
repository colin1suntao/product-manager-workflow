"""Memory System - 记忆系统

包含两个子系统：
1. 传统内存记忆：Agent Soul、反思记录、短期记忆
2. 持久化记忆：项目级、会话级、用户偏好长期存储
"""

__all__ = [
    # 传统内存记忆
    "AgentSoul",
    "MemoryEntry",
    "MemoryStats",
    "MemoryType",
    "Reflection",
    "LegacySearchResult",
    "LegacyUserPreference",
    "SoulManager",
    "ReflectionEngine",
    # 持久化记忆系统
    "MemoryApplicator",
    "get_memory_applicator",
    "MemoryExtractor",
    "get_memory_extractor",
    "MemoryRetriever",
    "get_memory_retriever",
    "PersistentMemoryManager",
    "get_persistent_memory_manager",
    "MemoryInjectionConfig",
    "MemoryLevel",
    "MemorySearchResult",
    "PersistentMemoryEntry",
    "ProjectMemory",
    "SessionMemory",
    "UserPreference",
    "PersistentMemoryStore",
    "get_persistent_memory_store",
    "ProjectMemoryType",
    "SessionMemoryType",
    "PreferenceCategory",
]

# 传统内存记忆
# 持久化记忆系统
from .memory_applicator import (
    MemoryApplicator as MemoryApplicator,
)
from .memory_applicator import (
    get_memory_applicator as get_memory_applicator,
)
from .memory_extractor import (
    MemoryExtractor as MemoryExtractor,
)
from .memory_extractor import (
    get_memory_extractor as get_memory_extractor,
)
from .memory_models import (
    AgentSoul as AgentSoul,
)
from .memory_models import (
    MemoryEntry as MemoryEntry,
)
from .memory_models import (
    MemorySearchResult as LegacySearchResult,
)
from .memory_models import (
    MemoryStats as MemoryStats,
)
from .memory_models import (
    MemoryType as MemoryType,
)
from .memory_models import (
    Reflection as Reflection,
)
from .memory_models import (
    UserPreference as LegacyUserPreference,
)
from .memory_retriever import (
    MemoryRetriever as MemoryRetriever,
)
from .memory_retriever import (
    get_memory_retriever as get_memory_retriever,
)
from .persistent_manager import (
    PersistentMemoryManager as PersistentMemoryManager,
)
from .persistent_manager import (
    get_persistent_memory_manager as get_persistent_memory_manager,
)
from .persistent_models import (
    MemoryInjectionConfig as MemoryInjectionConfig,
)
from .persistent_models import (
    MemoryLevel as MemoryLevel,
)
from .persistent_models import (
    MemorySearchResult as MemorySearchResult,
)
from .persistent_models import (
    PersistentMemoryEntry as PersistentMemoryEntry,
)
from .persistent_models import (
    PreferenceCategory as PreferenceCategory,
)
from .persistent_models import (
    ProjectMemory as ProjectMemory,
)
from .persistent_models import (
    ProjectMemoryType as ProjectMemoryType,
)
from .persistent_models import (
    SessionMemory as SessionMemory,
)
from .persistent_models import (
    SessionMemoryType as SessionMemoryType,
)
from .persistent_models import (
    UserPreference as UserPreference,
)
from .persistent_store import (
    PersistentMemoryStore as PersistentMemoryStore,
)
from .persistent_store import (
    get_persistent_memory_store as get_persistent_memory_store,
)
from .reflection_engine import ReflectionEngine as ReflectionEngine
from .soul_manager import SoulManager as SoulManager
