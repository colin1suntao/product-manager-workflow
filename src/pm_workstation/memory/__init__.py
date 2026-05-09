"""Memory Module - 长期记忆模块

为 AI Agent 提供跨越会话的长期记忆功能，包括 Soul 定义、用户偏好、经验记忆和反思学习。
"""

from .memory_manager import MemoryManager
from .memory_models import (
    AgentSoul,
    MemoryEntry,
    MemoryType,
    Reflection,
    UserPreference,
)
from .memory_retriever import MemoryRetriever
from .reflection_engine import ReflectionEngine
from .soul_manager import SoulManager

__all__ = [
    "AgentSoul",
    "MemoryEntry",
    "MemoryManager",
    "MemoryRetriever",
    "MemoryType",
    "Reflection",
    "ReflectionEngine",
    "SoulManager",
    "UserPreference",
]
