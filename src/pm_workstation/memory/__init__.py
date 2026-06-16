"""Memory System - 三层记忆架构

Short-term Memory (STM)  - 短期记忆: 当前会话窗口，Token 预算管理
Working Memory (WM)     - 工作记忆: 任务驱动，用户可手动添加
Long-term Memory (LTM)  - 长期记忆: 持久化 CRUD + 自动提取
"""

__all__ = [
    # 三层记忆架构（新）
    "LayeredMemoryManager",
    "get_layered_memory_manager",
    "ShortTermMemory",
    "WorkingMemory",
    "LongTermMemoryEntry",
    "LongTermCategory",
    "MemoryPriority",
    "MemoryLayer",
    "MemoryRetrievalQuery",
    "MemorySystemStats",
    # 传统内存记忆（兼容）
    "AgentSoul",
    "MemoryEntry",
    "MemoryStats",
    "MemoryType",
    "Reflection",
    "LegacySearchResult",
    "LegacyUserPreference",
    "SoulManager",
    "ReflectionEngine",
    # 持久化记忆系统（兼容）
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

# 三层记忆架构（新）
from .layered_manager import LayeredMemoryManager as LayeredMemoryManager
from .layered_manager import get_layered_memory_manager as get_layered_memory_manager
from .layered_models import LongTermCategory as LongTermCategory
from .layered_models import LongTermMemoryEntry as LongTermMemoryEntry
from .layered_models import MemoryLayer as MemoryLayer
from .layered_models import MemoryPriority as MemoryPriority
from .layered_models import MemoryRetrievalQuery as MemoryRetrievalQuery
from .layered_models import MemorySystemStats as MemorySystemStats
from .layered_models import ShortTermMemory as ShortTermMemory
from .layered_models import WorkingMemory as WorkingMemory

# 传统内存记忆
from .memory_models import AgentSoul as AgentSoul
from .memory_models import MemoryEntry as MemoryEntry
from .memory_models import MemorySearchResult as LegacySearchResult
from .memory_models import MemoryStats as MemoryStats
from .memory_models import MemoryType as MemoryType
from .memory_models import Reflection as Reflection
from .memory_models import UserPreference as LegacyUserPreference
from .reflection_engine import ReflectionEngine as ReflectionEngine
from .soul_manager import SoulManager as SoulManager

# 持久化记忆系统（兼容）
from .memory_applicator import MemoryApplicator as MemoryApplicator
from .memory_applicator import get_memory_applicator as get_memory_applicator
from .memory_extractor import MemoryExtractor as MemoryExtractor
from .memory_extractor import get_memory_extractor as get_memory_extractor
from .memory_retriever import MemoryRetriever as MemoryRetriever
from .memory_retriever import get_memory_retriever as get_memory_retriever
from .memory_manager import MemoryManager as MemoryManager
from .memory_manager import get_memory_manager as get_memory_manager
from .persistent_manager import PersistentMemoryManager as PersistentMemoryManager
from .persistent_manager import get_persistent_memory_manager as get_persistent_memory_manager
from .persistent_models import MemoryInjectionConfig as MemoryInjectionConfig
from .persistent_models import MemoryLevel as MemoryLevel
from .persistent_models import MemorySearchResult as MemorySearchResult
from .persistent_models import PersistentMemoryEntry as PersistentMemoryEntry
from .persistent_models import PreferenceCategory as PreferenceCategory
from .persistent_models import ProjectMemory as ProjectMemory
from .persistent_models import ProjectMemoryType as ProjectMemoryType
from .persistent_models import SessionMemory as SessionMemory
from .persistent_models import SessionMemoryType as SessionMemoryType
from .persistent_models import UserPreference as UserPreference
from .persistent_store import PersistentMemoryStore as PersistentMemoryStore
from .persistent_store import get_persistent_memory_store as get_persistent_memory_store

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
