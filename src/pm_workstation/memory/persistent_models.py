"""持久化记忆数据模型

扩展原有 Memory 模型，支持项目级、会话级、用户级多层级记忆。
"""

import hashlib
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MemoryLevel(StrEnum):
    """记忆层级"""
    PROJECT = "project_level"
    SESSION = "session_level"
    USER = "user_level"
    ARCHIVED = "archived"


class PreferenceCategory(StrEnum):
    """偏好类别"""
    LANGUAGE = "language"
    OUTPUT_FORMAT = "format"
    COMMUNICATION_STYLE = "style"
    WORKFLOW = "workflow"
    TOOL_USAGE = "tool"
    RESPONSE_LENGTH = "length"
    DETAIL_LEVEL = "detail"


class MemoryType(StrEnum):
    """通用记忆类型"""
    KNOWLEDGE = "knowledge"
    DECISION = "decision"
    PATTERN = "pattern"
    MISTAKE = "mistake"
    FEEDBACK = "feedback"
    CONSTRAINT = "constraint"


class ProjectMemoryType(StrEnum):
    """项目记忆类型"""
    CONSTRAINT = "constraint"
    DECISION = "decision"
    PATTERN = "pattern"
    ARTIFACT_REFERENCE = "artifact"
    ERROR_LESSON = "error_lesson"
    OPTIMIZATION = "optimization"


class SessionMemoryType(StrEnum):
    """会话记忆类型"""
    CONTEXT = "context"
    ENTITY = "entity"
    TASK_STATE = "task"
    ERROR_CONTEXT = "error"
    FILE_REFERENCE = "file"
    USER_CORRECTION = "correction"


class PersistentMemoryEntry(BaseModel):
    """持久化记忆条目"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    user_id: str
    project_id: str | None = None
    session_id: str | None = None
    level: MemoryLevel
    memory_type: str

    content: str
    summary: str = ""
    keywords: list[str] = Field(default_factory=list)

    importance: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.8, ge=0, le=1)

    source_type: str = ""
    source_id: str = ""

    context: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    access_count: int = Field(default=0)

    content_hash: str = ""
    file_path: str = ""

    def compute_hash(self) -> str:
        """计算内容哈希"""
        content_normalized = self.content.strip().lower()
        return hashlib.md5(content_normalized.encode()).hexdigest()

    def update_access(self) -> None:
        """更新访问记录"""
        self.last_accessed = datetime.now()
        self.access_count += 1
        if self.access_count >= 5 and self.importance < 0.8:
            self.importance = min(0.9, self.importance + 0.1)


class UserPreference(BaseModel):
    """用户偏好"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    user_id: str
    category: PreferenceCategory
    key: str
    value: str
    description: str | None = None
    confidence: float = Field(default=0.8, ge=0, le=1)
    learned_from: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    file_path: str = ""


class ProjectMemory(BaseModel):
    """项目记忆"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    project_id: str
    user_id: str
    memory_type: ProjectMemoryType

    title: str
    content: str
    impact: str = ""

    related_files: list[str] = Field(default_factory=list)
    related_artifacts: list[str] = Field(default_factory=list)

    importance: float = Field(default=0.5)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    file_path: str = ""


class SessionMemory(BaseModel):
    """会话记忆"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    session_id: str
    user_id: str
    memory_type: SessionMemoryType

    content: str
    entities: list[str] = Field(default_factory=list)
    files_mentioned: list[str] = Field(default_factory=list)

    importance: float = Field(default=0.5)

    created_at: datetime = Field(default_factory=datetime.now)

    file_path: str = ""


class MemorySearchResult(BaseModel):
    """记忆搜索结果"""
    memory: PersistentMemoryEntry
    relevance_score: float = Field(default=0.0, ge=0, le=1)
    match_reason: str = ""
    matched_keywords: list[str] = Field(default_factory=list)


class MemoryStats(BaseModel):
    """记忆统计"""
    total_memories: int = 0
    by_level: dict[str, int] = Field(default_factory=dict)
    by_type: dict[str, int] = Field(default_factory=dict)
    total_preferences: int = 0
    total_project_memories: int = 0
    total_session_memories: int = 0
    archived_count: int = 0
    storage_size_bytes: int = 0
    last_updated: datetime | None = None


class MemoryExtractionRule(BaseModel):
    """记忆提取规则"""
    name: str
    source_type: str
    trigger_conditions: dict[str, Any]
    extract_patterns: list[str]
    default_level: MemoryLevel
    default_importance: float = 0.5
    enabled: bool = True


class MemoryInjectionConfig(BaseModel):
    """记忆注入配置"""
    max_memories: int = Field(default=20)
    max_tokens: int = Field(default=2000)
    include_user_preferences: bool = Field(default=True)
    include_project_memories: bool = Field(default=True)
    include_session_memories: bool = Field(default=True)
    min_importance: float = Field(default=0.3)
    format_type: str = Field(default="markdown")
