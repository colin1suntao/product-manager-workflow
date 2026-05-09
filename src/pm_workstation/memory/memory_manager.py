"""Memory Manager - 记忆管理器

管理用户的记忆存储、检索和更新。
"""

import logging
from datetime import datetime
from typing import Optional

from .memory_models import MemoryEntry, MemorySearchResult, MemoryStats, MemoryType

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器

    提供记忆的 CRUD 操作和搜索功能，使用内存存储（生产环境应使用数据库）。
    """

    def __init__(self):
        self._memories: dict[str, MemoryEntry] = {}

    async def add_memory(self, memory: MemoryEntry) -> MemoryEntry:
        """添加记忆

        Args:
            memory: 记忆条目

        Returns:
            添加的记忆
        """
        self._memories[memory.id] = memory
        logger.info(f"Added memory {memory.id} for user {memory.user_id}")
        return memory

    async def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """获取记忆详情

        Args:
            memory_id: 记忆 ID

        Returns:
            记忆条目，如果不存在返回 None
        """
        memory = self._memories.get(memory_id)
        if memory:
            memory.last_accessed = datetime.now()
            memory.access_count += 1
        return memory

    async def list_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[list[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MemoryEntry]:
        """列出用户的记忆

        Args:
            user_id: 用户 ID
            memory_type: 记忆类型筛选
            tags: 标签筛选
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            记忆列表
        """
        memories = [
            m for m in self._memories.values()
            if m.user_id == user_id
        ]

        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]

        if tags:
            memories = [m for m in memories if any(tag in m.tags for tag in tags)]

        # 按创建时间倒序排列
        memories.sort(key=lambda m: m.created_at, reverse=True)

        return memories[offset:offset + limit]

    async def update_memory(self, memory_id: str, updates: dict) -> Optional[MemoryEntry]:
        """更新记忆

        Args:
            memory_id: 记忆 ID
            updates: 要更新的字段

        Returns:
            更新后的记忆，如果不存在返回 None
        """
        memory = self._memories.get(memory_id)
        if not memory:
            return None

        for key, value in updates.items():
            if hasattr(memory, key) and key not in ("id", "user_id", "created_at"):
                setattr(memory, key, value)

        memory.updated_at = datetime.now()
        return memory

    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆

        Args:
            memory_id: 记忆 ID

        Returns:
            是否删除成功
        """
        if memory_id not in self._memories:
            return False

        del self._memories[memory_id]
        logger.info(f"Deleted memory {memory_id}")
        return True

    async def search_memories(
        self,
        user_id: str,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
    ) -> list[MemorySearchResult]:
        """搜索记忆

        Args:
            user_id: 用户 ID
            query: 搜索关键词
            memory_type: 记忆类型筛选
            limit: 返回数量限制

        Returns:
            搜索结果列表
        """
        results = []
        query_lower = query.lower()

        for memory in self._memories.values():
            if memory.user_id != user_id:
                continue

            if memory_type and memory.memory_type != memory_type:
                continue

            # 计算相关性
            relevance = self._calculate_relevance(memory, query_lower)
            if relevance > 0:
                results.append(MemorySearchResult(
                    memory=memory,
                    relevance_score=relevance,
                    match_reason=self._get_match_reason(memory, query_lower),
                ))

        # 按相关性排序
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        return results[:limit]

    async def get_relevant_memories(
        self,
        user_id: str,
        context: str,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """获取与上下文相关的记忆

        Args:
            user_id: 用户 ID
            context: 上下文文本
            limit: 返回数量限制

        Returns:
            相关记忆列表
        """
        search_results = await self.search_memories(
            user_id=user_id,
            query=context,
            limit=limit,
        )

        memories = []
        for result in search_results:
            memory = result.memory
            memory.last_accessed = datetime.now()
            memory.access_count += 1
            memories.append(memory)

        return memories

    async def get_stats(self, user_id: str) -> MemoryStats:
        """获取用户记忆统计

        Args:
            user_id: 用户 ID

        Returns:
            记忆统计信息
        """
        user_memories = [
            m for m in self._memories.values()
            if m.user_id == user_id
        ]

        by_type = {}
        for m in user_memories:
            type_name = m.memory_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        # 统计标签
        tag_counts: dict[str, int] = {}
        for m in user_memories:
            for tag in m.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return MemoryStats(
            total_memories=len(user_memories),
            by_type=by_type,
            top_tags=top_tags,
        )

    async def record_task_result(
        self,
        user_id: str,
        task_id: str,
        task_type: str,
        success: bool,
        details: str,
        error_message: Optional[str] = None,
    ) -> MemoryEntry:
        """记录任务结果为记忆

        Args:
            user_id: 用户 ID
            task_id: 任务 ID
            task_type: 任务类型
            success: 是否成功
            details: 任务详情
            error_message: 错误信息（失败时）

        Returns:
            创建的记忆条目
        """
        if success:
            memory_type = MemoryType.EXPERIENCE
            summary = f"成功完成 {task_type} 任务"
            tags = ["success", task_type]
            importance = 0.6
        else:
            memory_type = MemoryType.MISTAKE
            summary = f"{task_type} 任务失败: {error_message or '未知错误'}"
            tags = ["failure", task_type, "error"]
            importance = 0.8  # 错误更重要，需要记住

        memory = MemoryEntry(
            user_id=user_id,
            memory_type=memory_type,
            content=details,
            summary=summary,
            tags=tags,
            importance=importance,
            source=task_id,
            context={"task_type": task_type, "success": success},
        )

        return await self.add_memory(memory)

    def _calculate_relevance(self, memory: MemoryEntry, query: str) -> float:
        """计算记忆与查询的相关性

        Args:
            memory: 记忆条目
            query: 查询关键词（小写）

        Returns:
            相关性评分 0-1
        """
        score = 0.0

        # 摘要匹配
        if query in memory.summary.lower():
            score += 0.4

        # 内容匹配
        if query in memory.content.lower():
            score += 0.3

        # 标签匹配
        for tag in memory.tags:
            if query in tag.lower():
                score += 0.2
                break

        # 重要性加权
        score *= (0.5 + memory.importance * 0.5)

        return min(score, 1.0)

    def _get_match_reason(self, memory: MemoryEntry, query: str) -> str:
        """获取匹配原因

        Args:
            memory: 记忆条目
            query: 查询关键词（小写）

        Returns:
            匹配原因描述
        """
        reasons = []

        if query in memory.summary.lower():
            reasons.append("摘要匹配")
        if query in memory.content.lower():
            reasons.append("内容匹配")
        for tag in memory.tags:
            if query in tag.lower():
                reasons.append(f"标签匹配: {tag}")
                break

        return ", ".join(reasons) if reasons else "相关性匹配"
