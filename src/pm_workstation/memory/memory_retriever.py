"""Memory Retriever - 记忆检索器

根据当前上下文检索相关记忆，支持关键词搜索、层级过滤、相关性排序。
"""

import logging
import re
from datetime import datetime, timedelta

from .persistent_models import (
    MemoryInjectionConfig,
    MemoryLevel,
    MemorySearchResult,
    PersistentMemoryEntry,
    ProjectMemory,
    SessionMemory,
    UserPreference,
)
from .persistent_store import PersistentMemoryStore, get_persistent_memory_store

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """记忆检索器

    检索相关记忆：
    - 用户偏好（长期）
    - 项目记忆（项目级）
    - 会话记忆（当前会话）
    - 关键词匹配
    """

    DEFAULT_CONFIG = MemoryInjectionConfig()

    def __init__(
        self,
        store: PersistentMemoryStore | None = None,
        config: MemoryInjectionConfig | None = None,
    ):
        self.store = store or get_persistent_memory_store()
        self.config = config or self.DEFAULT_CONFIG

    async def retrieve_for_session(
        self,
        user_id: str,
        session_id: str,
        project_id: str | None = None,
        context_keywords: list[str] | None = None,
        max_memories: int = 20,
    ) -> list[MemorySearchResult]:
        """为会话检索相关记忆

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            project_id: 项目 ID
            context_keywords: 上下文关键词
            max_memories: 最大记忆数量

        Returns:
            list[MemorySearchResult]: 检索结果列表
        """
        results = []

        if self.config.include_user_preferences:
            user_prefs = await self.store.get_user_preferences(user_id)
            for pref in user_prefs:
                memory = PersistentMemoryEntry(
                    id=pref.id,
                    user_id=pref.user_id,
                    level=MemoryLevel.USER,
                    memory_type="preference",
                    content=f"{pref.key}: {pref.value}",
                    summary=f"Preference: {pref.key}",
                    keywords=[pref.key],
                    importance=0.9,
                    confidence=pref.confidence,
                    source_type="preference",
                )

                results.append(MemorySearchResult(
                    memory=memory,
                    relevance_score=0.95,
                    match_reason="User preference",
                    matched_keywords=[pref.key],
                ))

        if project_id and self.config.include_project_memories:
            project_memories = await self.store.get_project_memories(project_id)
            for proj_mem in project_memories:
                memory = PersistentMemoryEntry(
                    id=proj_mem.id,
                    user_id=proj_mem.user_id,
                    project_id=proj_mem.project_id,
                    level=MemoryLevel.PROJECT,
                    memory_type=proj_mem.memory_type.value,
                    content=proj_mem.content,
                    summary=proj_mem.title,
                    keywords=self._extract_keywords(proj_mem.content),
                    importance=proj_mem.importance,
                    confidence=0.85,
                    source_type="project",
                )

                relevance = 0.8

                if context_keywords:
                    relevance = self._compute_relevance(memory, context_keywords)

                if relevance >= self.config.min_importance:
                    results.append(MemorySearchResult(
                        memory=memory,
                        relevance_score=relevance,
                        match_reason="Project memory",
                        matched_keywords=context_keywords or [],
                    ))

        if self.config.include_session_memories:
            session_memories = await self.store.get_session_memories(session_id)
            for sess_mem in session_memories:
                memory = PersistentMemoryEntry(
                    id=sess_mem.id,
                    user_id=sess_mem.user_id,
                    session_id=sess_mem.session_id,
                    level=MemoryLevel.SESSION,
                    memory_type=sess_mem.memory_type.value,
                    content=sess_mem.content,
                    summary="Session context",
                    keywords=sess_mem.entities + self._extract_keywords(sess_mem.content),
                    importance=sess_mem.importance,
                    confidence=0.8,
                    source_type="session",
                )

                relevance = 0.7

                if context_keywords:
                    relevance = self._compute_relevance(memory, context_keywords)

                if relevance >= self.config.min_importance:
                    results.append(MemorySearchResult(
                        memory=memory,
                        relevance_score=relevance,
                        match_reason="Session memory",
                        matched_keywords=context_keywords or [],
                    ))

        if context_keywords:
            search_results = await self.store.search(
                query=" ".join(context_keywords),
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                limit=max_memories,
            )

            seen_ids = {r.memory.id for r in results}
            for sr in search_results:
                if sr.memory.id not in seen_ids:
                    seen_ids.add(sr.memory.id)
                    results.append(sr)

        results = self._rank_memories(results)

        return results[:max_memories]

    async def retrieve_user_preferences(
        self,
        user_id: str,
        category: str | None = None,
    ) -> list[UserPreference]:
        """检索用户偏好

        Args:
            user_id: 用户 ID
            category: 偏好类别

        Returns:
            list[UserPreference]: 偏好列表
        """
        return await self.store.get_user_preferences(user_id, category)

    async def retrieve_project_memories(
        self,
        project_id: str,
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[ProjectMemory]:
        """检索项目记忆

        Args:
            project_id: 项目 ID
            memory_type: 记忆类型
            limit: 最大数量

        Returns:
            list[ProjectMemory]: 项目记忆列表
        """
        memories = await self.store.get_project_memories(project_id, memory_type)

        memories.sort(key=lambda m: m.importance, reverse=True)

        return memories[:limit]

    async def retrieve_session_memories(
        self,
        session_id: str,
        recent_hours: int = 24,
    ) -> list[SessionMemory]:
        """检索会话记忆

        Args:
            session_id: 会话 ID
            recent_hours: 最近小时数

        Returns:
            list[SessionMemory]: 会话记忆列表
        """
        memories = await self.store.get_session_memories(session_id)

        if recent_hours:
            threshold = datetime.now() - timedelta(hours=recent_hours)
            memories = [m for m in memories if m.created_at >= threshold]

        memories.sort(key=lambda m: m.importance, reverse=True)

        return memories

    async def search_by_keywords(
        self,
        keywords: list[str],
        user_id: str,
        project_id: str | None = None,
        limit: int = 20,
    ) -> list[MemorySearchResult]:
        """关键词搜索

        Args:
            keywords: 关键词列表
            user_id: 用户 ID
            project_id: 项目 ID
            limit: 最大数量

        Returns:
            list[MemorySearchResult]: 搜索结果
        """
        query = " ".join(keywords)

        return await self.store.search(
            query=query,
            user_id=user_id,
            project_id=project_id,
            limit=limit,
        )

    def _compute_relevance(
        self,
        memory: PersistentMemoryEntry,
        keywords: list[str],
    ) -> float:
        """计算相关性

        Args:
            memory: 记忆
            keywords: 关键词

        Returns:
            float: 相关性评分
        """
        if not keywords:
            return memory.importance

        matched_count = 0
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in memory.keywords:
                matched_count += 2
            elif keyword_lower in memory.content.lower():
                matched_count += 1

        keyword_score = matched_count / (len(keywords) * 2) if keywords else 0

        recency_score: float = 0.0
        if memory.last_accessed:
            hours_since_access = (datetime.now() - memory.last_accessed).total_seconds() / 3600
            recency_score = max(0, 1 - hours_since_access / 168) * 0.1

        importance_score = memory.importance

        relevance = (
            keyword_score * 0.5 +
            importance_score * 0.4 +
            recency_score
        )

        return min(relevance, 1.0)

    def _rank_memories(
        self,
        memories: list[MemorySearchResult],
    ) -> list[MemorySearchResult]:
        """排序记忆

        Args:
            memories: 记忆列表

        Returns:
            list[MemorySearchResult]: 排序后的列表
        """
        def rank_key(result: MemorySearchResult) -> tuple:
            level_priority = {
                MemoryLevel.USER: 3,
                MemoryLevel.PROJECT: 2,
                MemoryLevel.SESSION: 1,
                MemoryLevel.ARCHIVED: 0,
            }

            level_score = level_priority.get(result.memory.level, 0)

            relevance_score = result.relevance_score

            importance_score = result.memory.importance

            return (-level_score, -relevance_score, -importance_score)

        sorted_memories = sorted(memories, key=rank_key)

        return sorted_memories

    def _extract_keywords(
        self,
        text: str,
    ) -> list[str]:
        """提取关键词"""
        words = re.findall(r"\b\w{3,}\b", text.lower())

        stopwords = {"the", "and", "for", "with", "this", "that", "from", "to", "is", "are", "was", "were", "的", "是", "在", "有"}

        keywords = [w for w in words if w not in stopwords]

        return keywords[:10]


_global_retriever: MemoryRetriever | None = None


def get_memory_retriever() -> MemoryRetriever:
    """获取全局记忆检索器实例"""
    global _global_retriever
    if _global_retriever is None:
        _global_retriever = MemoryRetriever()
    return _global_retriever
