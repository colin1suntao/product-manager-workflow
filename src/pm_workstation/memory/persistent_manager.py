"""Persistent Memory Manager - 持久化记忆管理器

协调记忆提取、存储、检索和应用的全流程管理。
"""

import logging

from .memory_applicator import MemoryApplicator, get_memory_applicator
from .memory_extractor import MemoryExtractor, get_memory_extractor
from .memory_retriever import MemoryRetriever, get_memory_retriever
from .persistent_models import (
    MemoryInjectionConfig,
    MemorySearchResult,
    PersistentMemoryEntry,
    PreferenceCategory,
    ProjectMemory,
    ProjectMemoryType,
    SessionMemory,
    SessionMemoryType,
    UserPreference,
)
from .persistent_store import PersistentMemoryStore, get_persistent_memory_store

logger = logging.getLogger(__name__)


class PersistentMemoryManager:
    """记忆管理器

    协调记忆生命周期：
    - 从工作流结果提取记忆
    - 从 Sandbox 执行提取记忆
    - 从对话历史提取记忆
    - 存储到持久化系统
    - 检索并注入到上下文
    """

    def __init__(
        self,
        store: PersistentMemoryStore | None = None,
        extractor: MemoryExtractor | None = None,
        retriever: MemoryRetriever | None = None,
        applicator: MemoryApplicator | None = None,
    ):
        self.store = store or get_persistent_memory_store()
        self.extractor = extractor or get_memory_extractor()
        self.retriever = retriever or get_memory_retriever()
        self.applicator = applicator or get_memory_applicator()

    async def process_workflow_result(
        self,
        workflow_execution: dict,
        user_id: str,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> list[PersistentMemoryEntry]:
        """处理工作流结果，提取并存储记忆

        Args:
            workflow_execution: 工作流执行结果
            user_id: 用户 ID
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            list[PersistentMemoryEntry]: 提取的记忆列表
        """
        memories = await self.extractor.extract_from_workflow(
            workflow_execution,
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
        )

        saved_memories = []
        for memory in memories:
            await self.store.save(memory)
            saved_memories.append(memory)

        logger.info(f"Processed workflow result, saved {len(saved_memories)} memories")

        return saved_memories

    async def process_sandbox_result(
        self,
        sandbox_execution: dict,
        user_id: str,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> list[PersistentMemoryEntry]:
        """处理 Sandbox 执行结果

        Args:
            sandbox_execution: Sandbox 执行结果
            user_id: 用户 ID
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            list[PersistentMemoryEntry]: 提取的记忆列表
        """
        memories = await self.extractor.extract_from_sandbox(
            sandbox_execution,
            user_id=user_id,
            session_id=session_id or "",
            project_id=project_id,
        )

        saved_memories = []
        for memory in memories:
            await self.store.save(memory)
            saved_memories.append(memory)

        logger.info(f"Processed sandbox result, saved {len(saved_memories)} memories")

        return saved_memories

    async def process_chat_message(
        self,
        message: dict,
        user_id: str,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> list[PersistentMemoryEntry]:
        """处理对话消息

        Args:
            message: 对话消息
            user_id: 用户 ID
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            list[PersistentMemoryEntry]: 提取的记忆列表
        """
        message_content = message.get("content", "")
        user_input = message.get("user_input", message_content)
        memories = await self.extractor.extract_from_chat(
            message=user_input,
            response=message_content,
            user_id=user_id,
            session_id=session_id or "",
            project_id=project_id,
        )

        saved_memories = []
        for memory in memories:
            await self.store.save(memory)
            saved_memories.append(memory)

        return saved_memories

    async def process_user_feedback(
        self,
        feedback: dict,
        user_id: str,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> list[PersistentMemoryEntry]:
        """处理用户反馈

        Args:
            feedback: 用户反馈
            user_id: 用户 ID
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            list[PersistentMemoryEntry]: 提取的记忆列表
        """
        feedback_content = feedback.get("comment", "")
        memory = await self.extractor.extract_from_feedback(
            feedback=feedback_content,
            user_id=user_id,
            session_id=session_id or "",
            project_id=project_id,
        )

        saved_memories = []
        if memory:
            await self.store.save(memory)
            saved_memories.append(memory)

        return saved_memories

    async def get_context_memories(
        self,
        user_id: str,
        session_id: str,
        project_id: str | None = None,
        context_keywords: list[str] | None = None,
        config: MemoryInjectionConfig | None = None,
    ) -> list[MemorySearchResult]:
        """获取上下文记忆

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            project_id: 项目 ID
            context_keywords: 上下文关键词
            config: 注入配置

        Returns:
            list[MemorySearchResult]: 检索的记忆列表
        """
        config = config or MemoryInjectionConfig()

        memories = await self.retriever.retrieve_for_session(
            user_id=user_id,
            session_id=session_id,
            project_id=project_id,
            context_keywords=context_keywords,
            max_memories=config.max_memories,
        )

        return memories

    async def inject_memories(
        self,
        context: dict,
        memories: list[MemorySearchResult],
        config: MemoryInjectionConfig | None = None,
    ) -> dict:
        """注入记忆到上下文

        Args:
            context: Agent 上下文
            memories: 记忆列表
            config: 注入配置

        Returns:
            dict: 增强的上下文
        """
        config = config or MemoryInjectionConfig()

        return await self.applicator.inject_to_context(
            context=context,
            memories=memories,
            max_tokens=config.max_tokens,
        )

    async def save_user_preference(
        self,
        user_id: str,
        key: str,
        value: str,
        category: str | None = None,
        confidence: float = 0.9,
    ) -> bool:
        """保存用户偏好

        Args:
            user_id: 用户 ID
            key: 偏好键
            value: 偏好值
            category: 分类
            confidence: 置信度

        Returns:
            bool: 是否成功
        """

        category_enum = None
        if category:
            try:
                category_enum = PreferenceCategory(category)
            except ValueError:
                category_enum = PreferenceCategory.WORKFLOW

        pref = UserPreference(
            user_id=user_id,
            key=key,
            value=value,
            category=category_enum or PreferenceCategory.WORKFLOW,
            confidence=confidence,
        )

        await self.store.save_user_preference(pref)

        logger.info(f"Saved user preference: {key}={value}")

        return True

    async def save_project_memory(
        self,
        project_id: str,
        user_id: str,
        title: str,
        content: str,
        memory_type: ProjectMemoryType = ProjectMemoryType.DECISION,
        importance: float = 0.7,
    ) -> ProjectMemory:
        """保存项目记忆

        Args:
            project_id: 项目 ID
            user_id: 用户 ID
            title: 标题
            content: 内容
            memory_type: 记忆类型
            importance: 重要性

        Returns:
            ProjectMemory: 项目记忆对象
        """
        memory = ProjectMemory(
            project_id=project_id,
            user_id=user_id,
            memory_type=memory_type,
            title=title,
            content=content,
            importance=importance,
        )

        await self.store.save_project_memory(memory)

        logger.info(f"Saved project memory: {title}")

        return memory

    async def save_session_memory(
        self,
        session_id: str,
        user_id: str,
        content: str,
        entities: list[str] | None = None,
        importance: float = 0.5,
    ) -> SessionMemory:
        """保存会话记忆

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            content: 内容
            entities: 实体列表
            importance: 重要性

        Returns:
            SessionMemory: 会话记忆对象
        """
        memory = SessionMemory(
            session_id=session_id,
            user_id=user_id,
            memory_type=SessionMemoryType.CONTEXT,
            content=content,
            entities=entities or [],
            importance=importance,
        )

        await self.store.save_session_memory(memory)

        logger.info(f"Saved session memory for session {session_id}")

        return memory

    async def archive_old_memories(
        self,
        user_id: str,
        days_threshold: int = 30,
    ) -> int:
        """归档旧记忆

        Args:
            user_id: 用户 ID
            days_threshold: 天数阈值

        Returns:
            int: 归档的记忆数量
        """
        count = await self.store.archive_old(days_threshold)

        logger.info(f"Archived {count} old memories")

        return count


_global_persistent_manager: PersistentMemoryManager | None = None


def get_persistent_memory_manager() -> PersistentMemoryManager:
    """获取全局持久化记忆管理器实例"""
    global _global_persistent_manager
    if _global_persistent_manager is None:
        _global_persistent_manager = PersistentMemoryManager()
    return _global_persistent_manager
