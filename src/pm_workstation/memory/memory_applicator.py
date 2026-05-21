"""Memory Applicator - 记忆应用器

将检索到的记忆注入到 Agent 上下文，支持 Token 限制、格式化。
"""

import logging

from .memory_retriever import MemoryRetriever, get_memory_retriever
from .persistent_models import (
    MemoryInjectionConfig,
    MemorySearchResult,
)

logger = logging.getLogger(__name__)


class MemoryApplicator:
    """记忆应用器

    将记忆注入 Agent 上下文：
    - 格式化为 Markdown 或 JSON
    - 控制 Token 数量
    - 按重要性排序
    """

    DEFAULT_CONFIG = MemoryInjectionConfig()

    def __init__(
        self,
        retriever: MemoryRetriever | None = None,
        config: MemoryInjectionConfig | None = None,
    ):
        self.retriever = retriever or get_memory_retriever()
        self.config = config or self.DEFAULT_CONFIG

    async def inject_to_context(
        self,
        context: dict,
        memories: list[MemorySearchResult],
        max_tokens: int | None = None,
    ) -> dict:
        """将记忆注入到 Agent 上下文

        Args:
            context: 原始上下文
            memories: 记忆列表
            max_tokens: 最大 Token 数

        Returns:
            dict: 增强的上下文
        """
        max_tokens = max_tokens or self.config.max_tokens

        truncated_memories = self._truncate_memories(memories, max_tokens)

        formatted_memories = await self.format_for_prompt(truncated_memories, self.config.format_type)

        context["injected_memories"] = formatted_memories
        context["memory_count"] = len(truncated_memories)
        context["memory_sources"] = [
            {
                "id": m.memory.id,
                "level": m.memory.level.value,
                "relevance": m.relevance_score,
            }
            for m in truncated_memories
        ]

        return context

    async def format_for_prompt(
        self,
        memories: list[MemorySearchResult],
        format_type: str = "markdown",
    ) -> str:
        """格式化记忆为提示词

        Args:
            memories: 记忆列表
            format_type: 格式类型

        Returns:
            str: 格式化的提示词
        """
        if not memories:
            return ""

        if format_type == "markdown":
            return self._format_as_markdown(memories)
        elif format_type == "json":
            return self._format_as_json(memories)
        elif format_type == "bullet_list":
            return self._format_as_bullet_list(memories)
        else:
            return self._format_as_markdown(memories)

    def _format_as_markdown(
        self,
        memories: list[MemorySearchResult],
    ) -> str:
        """格式化为 Markdown"""
        sections = []

        user_preferences = [m for m in memories if m.memory.level.value == "user_level"]
        project_memories = [m for m in memories if m.memory.level.value == "project_level"]
        session_memories = [m for m in memories if m.memory.level.value == "session_level"]

        if user_preferences:
            section = "## User Preferences\n\n"
            for m in user_preferences[:5]:
                section += f"- {m.memory.content}\n"
            sections.append(section)

        if project_memories:
            section = "## Project Context\n\n"
            for m in project_memories[:10]:
                section += f"- {m.memory.summary}: {m.memory.content[:100]}\n"
            sections.append(section)

        if session_memories:
            section = "## Session Context\n\n"
            for m in session_memories[:10]:
                section += f"- {m.memory.content[:80]}\n"
            sections.append(section)

        return "\n".join(sections)

    def _format_as_json(
        self,
        memories: list[MemorySearchResult],
    ) -> str:
        """格式化为 JSON"""
        import json

        data = {
            "memories": [
                {
                    "id": m.memory.id,
                    "level": m.memory.level.value,
                    "type": m.memory.memory_type,
                    "content": m.memory.content[:200],
                    "relevance": m.relevance_score,
                }
                for m in memories
            ]
        }

        return json.dumps(data, indent=2)

    def _format_as_bullet_list(
        self,
        memories: list[MemorySearchResult],
    ) -> str:
        """格式化为列表"""
        lines = []

        for m in memories:
            prefix = {
                "user_level": "[Pref]",
                "project_level": "[Project]",
                "session_level": "[Session]",
            }.get(m.memory.level.value, "[Memory]")

            lines.append(f"{prefix} {m.memory.content[:100]}")

        return "\n".join(lines)

    async def apply_preferences(
        self,
        preferences: list[MemorySearchResult],
        output_config: dict,
    ) -> dict:
        """应用偏好到输出配置

        Args:
            preferences: 偏好记忆列表
            output_config: 输出配置

        Returns:
            dict: 更新的配置
        """
        for pref in preferences:
            if pref.memory.memory_type == "preference":
                content = pref.memory.content

                if "output_language" in content:
                    if "zh-CN" in content:
                        output_config["language"] = "zh-CN"
                    elif "en" in content:
                        output_config["language"] = "en"

                if "detail_level" in content:
                    if "concise" in content:
                        output_config["detail_level"] = "concise"
                    elif "detailed" in content:
                        output_config["detail_level"] = "detailed"

                if "output_format" in content:
                    if "list" in content:
                        output_config["format"] = "list"
                    elif "table" in content:
                        output_config["format"] = "table"

        return output_config

    def _estimate_tokens(
        self,
        text: str,
    ) -> int:
        """估算 Token 数量

        简化估算：中文约 1.5 字/token，英文约 4 字/token
        """
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other_chars = len(text) - chinese_chars

        tokens = int(chinese_chars / 1.5 + other_chars / 4)

        return tokens

    def _truncate_memories(
        self,
        memories: list[MemorySearchResult],
        max_tokens: int,
    ) -> list[MemorySearchResult]:
        """截断记忆列表以符合 Token 限制

        Args:
            memories: 记忆列表
            max_tokens: 最大 Token 数

        Returns:
            list[MemorySearchResult]: 截断后的列表
        """
        truncated: list[MemorySearchResult] = []
        total_tokens: int = 0

        for memory in memories:
            content_tokens = self._estimate_tokens(memory.memory.content)

            if total_tokens + content_tokens > max_tokens:
                break

            if len(truncated) >= self.config.max_memories:
                break

            truncated.append(memory)
            total_tokens += content_tokens

        return truncated


_global_applicator: MemoryApplicator | None = None


def get_memory_applicator() -> MemoryApplicator:
    """获取全局记忆应用器实例"""
    global _global_applicator
    if _global_applicator is None:
        _global_applicator = MemoryApplicator()
    return _global_applicator
