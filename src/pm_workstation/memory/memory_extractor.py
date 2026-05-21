"""Memory Extractor - 记忆提取器

从 Workflow、Sandbox、Chat 等执行结果中自动提取有价值记忆。
"""

import logging
import re

from .persistent_models import (
    MemoryExtractionRule,
    MemoryLevel,
    PersistentMemoryEntry,
    PreferenceCategory,
    UserPreference,
)
from .persistent_store import PersistentMemoryStore, get_persistent_memory_store

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """记忆提取器

    从各种执行结果中自动提取记忆：
    - Workflow 执行 -> 项目决策、模式
    - Sandbox 执行 -> 代码模式、工具使用
    - Chat 对话 -> 实体、上下文
    - User feedback -> 用户偏好
    """

    DEFAULT_RULES = [
        MemoryExtractionRule(
            name="workflow_success",
            source_type="workflow",
            trigger_conditions={"status": "completed"},
            extract_patterns=["decision", "pattern", "artifact"],
            default_level=MemoryLevel.PROJECT,
            default_importance=0.7,
        ),
        MemoryExtractionRule(
            name="workflow_failure",
            source_type="workflow",
            trigger_conditions={"status": "failed"},
            extract_patterns=["error_lesson"],
            default_level=MemoryLevel.SESSION,
            default_importance=0.6,
        ),
        MemoryExtractionRule(
            name="sandbox_success",
            source_type="sandbox",
            trigger_conditions={"status": "completed"},
            extract_patterns=["pattern", "artifact"],
            default_level=MemoryLevel.SESSION,
            default_importance=0.5,
        ),
        MemoryExtractionRule(
            name="tool_failure",
            source_type="tool",
            trigger_conditions={"success": False},
            extract_patterns=["error_lesson"],
            default_level=MemoryLevel.SESSION,
            default_importance=0.6,
        ),
        MemoryExtractionRule(
            name="user_explicit_preference",
            source_type="chat",
            trigger_conditions={"contains_preference_keywords": True},
            extract_patterns=["preference"],
            default_level=MemoryLevel.USER,
            default_importance=0.9,
        ),
    ]

    PREFERENCE_KEYWORDS = [
        "请", "希望", "偏好", "喜欢", "习惯",
        "please", "prefer", "like", "always",
        "每次", "always", "总是", "要",
    ]

    PROJECT_DECISION_PATTERNS = [
        r"使用\s+(\w+)\s+作为",
        r"选择\s+(\w+)",
        r"采用\s+(\w+)\s+方案",
        r"决定\s+",
        r"框架\s+是",
        r"后端\s+用",
        r"前端\s+用",
    ]

    ENTITY_PATTERNS = [
        r"用户\s+(\w+)",
        r"页面\s+(\w+)",
        r"功能\s+(\w+)",
        r"模块\s+(\w+)",
        r"文件\s+(\w+)",
    ]

    def __init__(
        self,
        store: PersistentMemoryStore | None = None,
        rules: list[MemoryExtractionRule] | None = None,
    ):
        self.store = store or get_persistent_memory_store()
        self.rules = rules or self.DEFAULT_RULES

    async def extract_from_workflow(
        self,
        workflow_result: dict,
        user_id: str,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> list[PersistentMemoryEntry]:
        """从 Workflow 执行结果提取记忆

        Args:
            workflow_result: Workflow 执行结果
            user_id: 用户 ID
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            list[PersistentMemoryEntry]: 提取的记忆列表
        """
        memories = []

        status = workflow_result.get("status", "")
        workflow_name = workflow_result.get("workflow_name", "")
        steps_results = workflow_result.get("steps_results", [])
        workflow_result.get("artifacts", [])
        error_message = workflow_result.get("error_message")

        if status == "completed":
            if project_id:
                for step in steps_results:
                    if step.get("status") == "completed" and step.get("artifacts"):
                        memory = PersistentMemoryEntry(
                            user_id=user_id,
                            project_id=project_id,
                            session_id=session_id,
                            level=MemoryLevel.PROJECT,
                            memory_type="workflow_artifact",
                            content=f"Workflow '{workflow_name}' step '{step.get('step_name')}' generated artifacts",
                            summary=f"Workflow step artifact: {step.get('step_name')}",
                            keywords=[workflow_name, step.get("step_name", ""), "artifact"],
                            importance=0.7,
                            confidence=0.9,
                            source_type="workflow",
                            source_id=workflow_result.get("execution_id", ""),
                            context={
                                "workflow_name": workflow_name,
                                "step_name": step.get("step_name"),
                                "artifacts": step.get("artifacts", []),
                            },
                        )
                        memories.append(memory)

            if project_id and workflow_name:
                decisions = self._extract_decisions(str(workflow_result))
                for decision in decisions:
                    memory = PersistentMemoryEntry(
                        user_id=user_id,
                        project_id=project_id,
                        level=MemoryLevel.PROJECT,
                        memory_type="decision",
                        content=decision,
                        summary=f"Workflow decision: {decision[:50]}",
                        keywords=self._extract_keywords(decision),
                        importance=0.8,
                        confidence=0.85,
                        source_type="workflow",
                        source_id=workflow_result.get("execution_id", ""),
                    )
                    memories.append(memory)

        elif status == "failed" and error_message:
            memory = PersistentMemoryEntry(
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                level=MemoryLevel.SESSION,
                memory_type="error_lesson",
                content=f"Workflow '{workflow_name}' failed: {error_message}",
                summary=f"Workflow failure: {workflow_name}",
                keywords=["error", workflow_name, "failure"],
                importance=0.6,
                confidence=0.9,
                source_type="workflow",
                source_id=workflow_result.get("execution_id", ""),
                context={
                    "error_message": error_message,
                    "workflow_name": workflow_name,
                },
            )
            memories.append(memory)

        return memories

    async def extract_from_sandbox(
        self,
        sandbox_summary: dict,
        user_id: str,
        session_id: str,
        project_id: str | None = None,
    ) -> list[PersistentMemoryEntry]:
        """从 Sandbox 执行结果提取记忆

        Args:
            sandbox_summary: Sandbox 执行摘要
            user_id: 用户 ID
            session_id: 会话 ID
            project_id: 项目 ID

        Returns:
            list[PersistentMemoryEntry]: 提取的记忆列表
        """
        memories = []

        sandbox_summary.get("status", "")
        tool_results = sandbox_summary.get("tool_results", [])
        sandbox_summary.get("artifacts_count", 0)
        execution_id = sandbox_summary.get("execution_id", "")

        for tool_result in tool_results:
            tool_name = tool_result.get("tool_name", "")
            success = tool_result.get("success", False)
            tool_result.get("output", "")
            files_created = tool_result.get("files_created", [])

            if success and files_created:
                memory = PersistentMemoryEntry(
                    user_id=user_id,
                    project_id=project_id,
                    session_id=session_id,
                    level=MemoryLevel.SESSION,
                    memory_type="tool_artifact",
                    content=f"Tool '{tool_name}' created files: {files_created}",
                    summary=f"Tool execution: {tool_name}",
                    keywords=[tool_name, "artifact", "sandbox"],
                    importance=0.5,
                    confidence=0.85,
                    source_type="sandbox",
                    source_id=execution_id,
                    context={
                        "tool_name": tool_name,
                        "files_created": files_created,
                    },
                )
                memories.append(memory)

            elif not success:
                error = tool_result.get("error", "Unknown error")
                memory = PersistentMemoryEntry(
                    user_id=user_id,
                    project_id=project_id,
                    session_id=session_id,
                    level=MemoryLevel.SESSION,
                    memory_type="tool_error",
                    content=f"Tool '{tool_name}' failed: {error}",
                    summary=f"Tool failure: {tool_name}",
                    keywords=["error", tool_name, "sandbox"],
                    importance=0.6,
                    confidence=0.9,
                    source_type="sandbox",
                    source_id=execution_id,
                    context={
                        "tool_name": tool_name,
                        "error": error,
                    },
                )
                memories.append(memory)

        return memories

    async def extract_from_chat(
        self,
        message: str,
        response: str,
        user_id: str,
        session_id: str,
        project_id: str | None = None,
    ) -> list[PersistentMemoryEntry]:
        """从对话提取记忆

        Args:
            message: 用户消息
            response: AI 回复
            user_id: 用户 ID
            session_id: 会话 ID
            project_id: 项目 ID

        Returns:
            list[PersistentMemoryEntry]: 提取的记忆列表
        """
        memories = []

        entities = self._extract_entities(message + " " + response)
        if entities:
            memory = PersistentMemoryEntry(
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                level=MemoryLevel.SESSION,
                memory_type="entity",
                content=f"Entities mentioned in conversation: {entities}",
                summary="Conversation entities",
                keywords=entities,
                importance=0.5,
                confidence=0.8,
                source_type="chat",
                source_id=session_id,
                context={
                    "entities": entities,
                    "message_preview": message[:100],
                },
            )
            memories.append(memory)

        context_summary = self._summarize_context(message, response)
        if context_summary:
            memory = PersistentMemoryEntry(
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                level=MemoryLevel.SESSION,
                memory_type="context",
                content=context_summary,
                summary="Conversation context",
                keywords=self._extract_keywords(context_summary),
                importance=0.4,
                confidence=0.75,
                source_type="chat",
                source_id=session_id,
            )
            memories.append(memory)

        preferences = self._extract_preferences(message)
        for pref in preferences:
            memory = PersistentMemoryEntry(
                user_id=user_id,
                level=MemoryLevel.USER,
                memory_type="preference",
                content=f"User preference: {pref['key']} = {pref['value']}",
                summary=f"Preference: {pref['key']}",
                keywords=["preference", pref["key"]],
                importance=0.9,
                confidence=0.95,
                source_type="chat",
                source_id=session_id,
                context=pref,
            )
            memories.append(memory)

        return memories

    async def extract_from_feedback(
        self,
        feedback: str,
        user_id: str,
        session_id: str | None = None,
        project_id: str | None = None,
    ) -> PersistentMemoryEntry | None:
        """从用户反馈提取记忆

        Args:
            feedback: 用户反馈
            user_id: 用户 ID
            session_id: 会话 ID
            project_id: 项目 ID

        Returns:
            Optional[PersistentMemoryEntry]: 提取的记忆
        """
        feedback_lower = feedback.lower()

        is_positive = any(word in feedback_lower for word in ["好", "不错", "满意", "great", "good", "thanks"])
        is_negative = any(word in feedback_lower for word in ["不好", "错误", "不满意", "bad", "wrong", "issue"])
        is_correction = any(word in feedback_lower for word in ["应该", "要", "改成", "should", "need", "change"])

        if is_correction:
            memory_type = "user_correction"
            importance = 0.8
        elif is_negative:
            memory_type = "feedback_negative"
            importance = 0.7
        elif is_positive:
            memory_type = "feedback_positive"
            importance = 0.5
        else:
            memory_type = "feedback_general"
            importance = 0.6

        memory = PersistentMemoryEntry(
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            level=MemoryLevel.SESSION if session_id else MemoryLevel.USER,
            memory_type=memory_type,
            content=feedback,
            summary=f"User feedback: {feedback[:50]}",
            keywords=self._extract_keywords(feedback),
            importance=importance,
            confidence=0.9,
            source_type="feedback",
            source_id=session_id or "",
            context={
                "feedback_type": memory_type,
                "is_positive": is_positive,
                "is_negative": is_negative,
                "is_correction": is_correction,
            },
        )

        return memory

    async def extract_from_user_input(
        self,
        user_input: str,
        user_id: str,
    ) -> UserPreference | None:
        """从用户输入提取偏好

        Args:
            user_input: 用户输入
            user_id: 用户 ID

        Returns:
            Optional[UserPreference]: 提取的偏好
        """
        input_lower = user_input.lower()

        if not any(kw in input_lower for kw in self.PREFERENCE_KEYWORDS):
            return None

        language_patterns = [
            (r"用中文", "zh-CN"),
            (r"用英文", "en"),
            (r"in chinese", "zh-CN"),
            (r"in english", "en"),
        ]

        for pattern, value in language_patterns:
            if re.search(pattern, input_lower):
                return UserPreference(
                    user_id=user_id,
                    category=PreferenceCategory.LANGUAGE,
                    key="output_language",
                    value=value,
                    description=f"User prefers {value} output",
                    confidence=0.9,
                    learned_from=["explicit"],
                )

        format_patterns = [
            (r"列表形式", "list"),
            (r"表格", "table"),
            (r"表格形式", "table"),
            (r"详细", "detailed"),
            (r"简洁", "concise"),
            (r"简短", "concise"),
        ]

        for pattern, value in format_patterns:
            if re.search(pattern, input_lower):
                return UserPreference(
                    user_id=user_id,
                    category=PreferenceCategory.OUTPUT_FORMAT,
                    key="output_format",
                    value=value,
                    description=f"User prefers {value} format",
                    confidence=0.85,
                    learned_from=["explicit"],
                )

        return None

    def _extract_entities(
        self,
        text: str,
    ) -> list[str]:
        """提取实体"""
        entities = []

        for pattern in self.ENTITY_PATTERNS:
            matches = re.findall(pattern, text)
            entities.extend(matches)

        return entities[:10]

    def _extract_decisions(
        self,
        text: str,
    ) -> list[str]:
        """提取决策"""
        decisions = []

        for pattern in self.PROJECT_DECISION_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                decisions.append(f"Decision: use {match}")

        return decisions

    def _extract_keywords(
        self,
        text: str,
    ) -> list[str]:
        """提取关键词"""
        words = re.findall(r"\b\w{3,}\b", text.lower())

        stopwords = {"the", "and", "for", "with", "this", "that", "from", "to", "is", "are", "was", "were"}

        keywords = [w for w in words if w not in stopwords]

        return keywords[:10]

    def _extract_preferences(
        self,
        text: str,
    ) -> list[dict]:
        """提取偏好"""
        preferences = []

        text_lower = text.lower()

        if "中文" in text_lower or "用中文" in text_lower:
            preferences.append({
                "key": "output_language",
                "value": "zh-CN",
                "category": "language",
            })

        if "英文" in text_lower or "用英文" in text_lower:
            preferences.append({
                "key": "output_language",
                "value": "en",
                "category": "language",
            })

        if "简洁" in text_lower or "简短" in text_lower:
            preferences.append({
                "key": "detail_level",
                "value": "concise",
                "category": "detail",
            })

        if "详细" in text_lower:
            preferences.append({
                "key": "detail_level",
                "value": "detailed",
                "category": "detail",
            })

        return preferences

    def _summarize_context(
        self,
        message: str,
        response: str,
    ) -> str | None:
        """总结对话上下文"""
        combined = message + " " + response

        if len(combined) > 200:
            return combined[:200] + "..."

        return combined

    def _classify_level(
        self,
        source_type: str,
        context: dict,
    ) -> MemoryLevel:
        """分类记忆层级"""
        if source_type in ["workflow", "project"]:
            if context.get("project_id"):
                return MemoryLevel.PROJECT

        if source_type in ["chat", "sandbox"]:
            if context.get("session_id"):
                return MemoryLevel.SESSION

        if source_type in ["feedback", "preference"]:
            return MemoryLevel.USER

        return MemoryLevel.SESSION

    def _compute_importance(
        self,
        source_type: str,
        context: dict,
    ) -> float:
        """计算重要性"""
        base_importance = {
            "workflow": 0.7,
            "sandbox": 0.5,
            "chat": 0.4,
            "feedback": 0.6,
            "preference": 0.9,
        }

        importance = base_importance.get(source_type, 0.5)

        if context.get("is_error"):
            importance += 0.1

        if context.get("is_decision"):
            importance += 0.15

        if context.get("is_correction"):
            importance += 0.2

        return min(importance, 1.0)


_global_extractor: MemoryExtractor | None = None


def get_memory_extractor() -> MemoryExtractor:
    """获取全局记忆提取器实例"""
    global _global_extractor
    if _global_extractor is None:
        _global_extractor = MemoryExtractor()
    return _global_extractor
