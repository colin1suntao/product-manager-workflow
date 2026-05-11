"""Chat 数据模型

定义会话、消息、任务等核心数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class TaskMode(str, Enum):
    """任务模式枚举"""
    REQUIREMENT = "requirement"
    PROTOTYPE = "prototype"
    PRD = "prd"
    MARKET_RESEARCH = "market_research"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Artifact(BaseModel):
    """任务产出物"""
    type: Literal["document", "prototype", "report"]
    name: str
    url: str
    preview_url: Optional[str] = None


class TaskResult(BaseModel):
    """任务执行结果"""
    task_id: str
    task_mode: TaskMode
    status: TaskStatus
    output: Optional[str] = None
    artifacts: list[Artifact] = []
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class IntentAnalysis(BaseModel):
    """用户意图分析结果"""
    intent: str
    confidence: float
    task_mode: Optional[TaskMode] = None
    entities: dict[str, Any] = {}
    requires_clarification: bool = False
    clarification_questions: list[str] = []


class TaskPlan(BaseModel):
    """任务执行计划"""
    task_id: str
    task_mode: TaskMode
    description: str
    params: dict[str, Any] = {}
    dependencies: list[str] = []


class CoordinatorResponse(BaseModel):
    """主 Agent 响应"""
    message: str
    task_plans: list[TaskPlan] = []
    task_results: list[TaskResult] = []
    requires_user_input: bool = False
    suggested_actions: list[str] = []


class ChatSession(BaseModel):
    """会话"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    user_id: str
    title: str = "新会话"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = {}


class ToolCall(BaseModel):
    """工具/技能调用记录"""
    tool_name: str
    tool_type: Literal["skill", "function", "agent"]
    duration_ms: int = 0
    status: str = "success"
    description: str = ""


class ChatMessage(BaseModel):
    """会话消息"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    session_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    task_mode: Optional[TaskMode] = None
    task_id: Optional[str] = None
    task_status: Optional[TaskStatus] = None
    task_result: Optional[TaskResult] = None
    artifacts: list[Artifact] = []
    thinking_time_ms: int = 0
    token_usage: dict[str, int] = Field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    tool_calls: list[ToolCall] = []
    context_length: int = 0
    context_limit: int = 128000
    created_at: datetime = Field(default_factory=datetime.now)
