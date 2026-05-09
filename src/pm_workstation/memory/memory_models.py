"""Memory 数据模型

定义 Agent Soul、用户偏好、记忆条目、反思记录等核心数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """记忆类型枚举"""
    SOUL = "soul"  # Agent Soul 相关
    PREFERENCE = "preference"  # 用户偏好
    EXPERIENCE = "experience"  # 成功经验
    MISTAKE = "mistake"  # 错误记录
    LEARNING = "learning"  # 学习总结
    USER_FEEDBACK = "user_feedback"  # 用户反馈


class AgentSoul(BaseModel):
    """Agent Soul - 个性特征和行为准则"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    user_id: str
    name: str = "通用助手"
    personality: str = "专业、友好、高效"
    values: list[str] = Field(default_factory=lambda: ["准确性", "用户至上", "持续学习"])
    behavior_rules: list[str] = Field(default_factory=lambda: [
        "回答问题前先理解用户意图",
        "不确定时主动询问",
        "承认错误并及时纠正",
    ])
    communication_style: str = "清晰简洁，使用专业但易懂的语言"
    expertise_areas: list[str] = Field(default_factory=lambda: ["产品管理", "需求分析", "项目管理"])
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True


class UserPreference(BaseModel):
    """用户偏好"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    user_id: str
    category: str  # 偏好分类：language, format, style, workflow 等
    key: str  # 偏好键
    value: str  # 偏好值
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class MemoryEntry(BaseModel):
    """记忆条目"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    user_id: str
    memory_type: MemoryType
    content: str  # 记忆内容
    summary: str  # 摘要（简短描述）
    tags: list[str] = Field(default_factory=list)  # 标签
    importance: float = 0.5  # 重要性评分 0-1
    source: str = ""  # 来源（会话ID、任务ID等）
    context: dict[str, Any] = Field(default_factory=dict)  # 上下文信息
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    access_count: int = 0


class Reflection(BaseModel):
    """反思记录"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    user_id: str
    period_start: datetime
    period_end: datetime
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    key_learnings: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class MemorySearchResult(BaseModel):
    """记忆搜索结果"""
    memory: MemoryEntry
    relevance_score: float  # 相关性评分
    match_reason: str  # 匹配原因


class MemoryStats(BaseModel):
    """记忆统计"""
    total_memories: int
    by_type: dict[str, int]
    recent_reflection: Optional[datetime] = None
    top_tags: list[tuple[str, int]]  # (tag, count)
