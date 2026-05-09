"""Memory Retriever - 记忆检索器

负责检索与当前上下文相关的记忆。
"""

import logging
from typing import Optional

from .memory_manager import MemoryManager
from .memory_models import MemoryEntry, MemoryType

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """记忆检索器

    根据上下文检索相关记忆，并构建记忆提示词。
    """

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    async def retrieve_for_context(
        self,
        user_id: str,
        context: str,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """为上下文检索相关记忆

        Args:
            user_id: 用户 ID
            context: 上下文文本
            limit: 返回数量限制

        Returns:
            相关记忆列表
        """
        return await self.memory_manager.get_relevant_memories(
            user_id=user_id,
            context=context,
            limit=limit,
        )

    async def build_memory_prompt(
        self,
        user_id: str,
        context: str,
    ) -> str:
        """构建记忆提示词

        Args:
            user_id: 用户 ID
            context: 上下文文本

        Returns:
            记忆提示词
        """
        memories = await self.retrieve_for_context(user_id, context)

        if not memories:
            return ""

        parts = ["## 相关历史记忆\n"]

        for i, memory in enumerate(memories, 1):
            type_label = self._get_type_label(memory.memory_type)
            parts.append(f"{i}. [{type_label}] {memory.summary}")

        parts.append("\n请参考以上历史经验来完成当前任务。")

        return "\n".join(parts)

    async def get_user_preferences_prompt(self, user_id: str) -> str:
        """获取用户偏好提示词

        Args:
            user_id: 用户 ID

        Returns:
            偏好提示词
        """
        from .memory_models import UserPreference

        # 获取用户的所有偏好
        preferences = await self.memory_manager.list_memories(
            user_id=user_id,
            memory_type=MemoryType.PREFERENCE,
        )

        if not preferences:
            return ""

        parts = ["## 用户偏好\n"]

        for pref in preferences:
            parts.append(f"- {pref.summary}: {pref.content}")

        return "\n".join(parts)

    def _get_type_label(self, memory_type: MemoryType) -> str:
        """获取记忆类型的中文标签

        Args:
            memory_type: 记忆类型

        Returns:
            中文标签
        """
        labels = {
            MemoryType.SOUL: "Soul",
            MemoryType.PREFERENCE: "偏好",
            MemoryType.EXPERIENCE: "经验",
            MemoryType.MISTAKE: "教训",
            MemoryType.LEARNING: "学习",
            MemoryType.USER_FEEDBACK: "反馈",
        }
        return labels.get(memory_type, "记忆")
