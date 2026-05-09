"""Chat Module - 会话交互模块

提供基于自然语言的会话交互功能，支持用户与主 Agent 进行对话式任务交互。
"""

from .chat_manager import ChatManager
from .chat_models import (
    Artifact,
    ChatMessage,
    ChatSession,
    CoordinatorResponse,
    IntentAnalysis,
    TaskPlan,
    TaskResult,
    TaskStatus,
)
from .task_router import TaskRouter

__all__ = [
    "ChatManager",
    "ChatMessage",
    "ChatSession",
    "CoordinatorResponse",
    "IntentAnalysis",
    "TaskPlan",
    "TaskResult",
    "TaskStatus",
    "TaskRouter",
    "Artifact",
]
