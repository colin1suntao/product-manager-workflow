"""三层记忆架构数据模型

Short-term Memory (STM)  - 短期记忆: 当前会话上下文，Token 预算管理
Working Memory (WM)     - 工作记忆: 任务相关记忆，动态加载
Long-term Memory (LTM)  - 长期记忆: 持久化存储，跨会话可检索
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryLayer(StrEnum):
    """记忆层级"""
    SHORT_TERM = "short_term"
    WORKING = "working"
    LONG_TERM = "long_term"


class LongTermCategory(StrEnum):
    """长期记忆分类"""
    PROJECT = "project"
    SESSION = "session"
    USER = "user"
    KNOWLEDGE = "knowledge"
    CUSTOM = "custom"


class MemoryPriority(StrEnum):
    """记忆优先级"""
    CRITICAL = "critical"   # 必须注入
    HIGH = "high"           # 优先注入
    MEDIUM = "medium"       # 空间足够时注入
    LOW = "low"             # 可选


class ShortTermMemory(BaseModel):
    """短期记忆 - 当前会话窗口中的消息和上下文

    特点:
    - 存储在内存中，会话结束即释放
    - 自动管理 Token 预算
    - 滑动窗口机制
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str
    user_id: str

    # 消息列表
    messages: list[dict[str, Any]] = Field(default_factory=list)
    max_messages: int = Field(default=50)

    # Token 预算
    token_budget: int = Field(default=8000)
    current_tokens: int = Field(default=0)

    # 上下文摘要（当消息被截断时生成）
    context_summary: str = ""
    summarized: bool = False

    # 最近实体和关键信息
    active_entities: list[str] = Field(default_factory=list)
    active_topics: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def estimate_tokens(self, text: str) -> int:
        """粗略估算 token 数（约 4 字符 = 1 token）"""
        return max(1, len(text) // 4)

    def add_message(self, role: str, content: str) -> bool:
        """添加消息，返回是否成功（未超预算）"""
        truncated = content[:2000]
        tokens = self.estimate_tokens(truncated)

        if self.current_tokens + tokens > self.token_budget:
            self._compact()

        msg = {
            "role": role,
            "content": truncated,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.messages.append(msg)
        self.current_tokens += tokens

        # 强制执行 max_messages 上限
        while len(self.messages) > self.max_messages:
            self.messages.pop(0)

        self.updated_at = datetime.now(timezone.utc)

        if self.current_tokens > self.token_budget:
            self._compact()
        return True

    def _compact(self):
        """压缩早期消息为摘要"""
        if len(self.messages) <= 10:
            return
        early_msgs = self.messages[:5]
        content_texts = [
            f"[{m.get('role', '?')}]: {m.get('content', '')[:80]}"
            for m in early_msgs
        ]
        if content_texts:
            prefix = " | " if self.context_summary else ""
            self.context_summary += prefix + " | ".join(content_texts)
        self.messages = self.messages[5:]
        self.current_tokens = sum(
            self.estimate_tokens(m.get("content", "")) for m in self.messages
        ) + self.estimate_tokens(self.context_summary)
        self.summarized = True
        self.updated_at = datetime.now(timezone.utc)

    def get_context_for_injection(self) -> str:
        """获取可注入到提示词的上下文"""
        parts = []
        if self.context_summary:
            parts.append(f"[历史对话摘要]\n{self.context_summary}")
        if self.messages:
            recent = self.messages[-10:]
            parts.append("\n[近期对话]\n" + "\n".join(
                f"{m.get('role', '')}: {m.get('content', '')[:200]}" for m in recent
            ))
        if self.active_topics:
            parts.append(f"\n[当前主题]\n" + ", ".join(self.active_topics))
        return "\n".join(parts)


class WorkingMemory(BaseModel):
    """工作记忆 - 当前任务相关的活跃记忆

    特点:
    - 从长期记忆中按需加载
    - 任务完成或切换时更新回长期记忆
    - 支持手动添加（用户自定义）
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str
    task_id: str | None = None
    user_id: str

    # 加载自长期记忆的条目
    loaded_from_ltm: list["LongTermMemoryEntry"] = Field(default_factory=list)

    # 用户手动添加的工作记忆
    manual_entries: list["LongTermMemoryEntry"] = Field(default_factory=list)

    # 当前任务上下文
    task_description: str = ""
    task_type: str = ""

    # 检索配置
    max_loaded_items: int = Field(default=10)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def all_entries(self) -> list["LongTermMemoryEntry"]:
        """所有活跃条目"""
        return self.loaded_from_ltm + self.manual_entries

    def add_manual_entry(self, entry: "LongTermMemoryEntry"):
        """用户手动添加工作记忆

        注意: 会拷贝 entry 并将拷贝的 layer 设为 WORKING，原始对象不受影响。
        """
        entry_copy = entry.model_copy(deep=True)
        entry_copy.layer = MemoryLayer.WORKING
        existing = [e for e in self.manual_entries if e.id == entry_copy.id]
        if not existing:
            self.manual_entries.append(entry_copy)
        else:
            idx = self.manual_entries.index(existing[0])
            self.manual_entries[idx] = entry_copy
        self.updated_at = datetime.now(timezone.utc)

    def clear_task(self):
        """清除当前任务的工作记忆"""
        self.loaded_from_ltm = []
        self.manual_entries = []
        self.task_id = None
        self.task_description = ""
        self.task_type = ""
        self.updated_at = datetime.now(timezone.utc)

    def get_context_for_injection(self, max_tokens: int = 2000) -> str:
        """获取可注入的上下文"""
        entries = sorted(self.all_entries, key=lambda e: e.importance, reverse=True)
        parts = []
        token_count = 0

        for entry in entries:
            text = f"[{entry.category.value}] {entry.title}: {entry.content[:300]}"
            est_tokens = len(text) // 4
            if token_count + est_tokens > max_tokens:
                break
            parts.append(text)
            token_count += est_tokens

        return "\n".join(parts)


class LongTermMemoryEntry(BaseModel):
    """长期记忆条目 - 持久化存储的核心单元

    支持:
    - 自动提取（从工作流、对话、反馈）
    - 用户手动创建/编辑/删除
    - 分类、标签、优先级管理
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    user_id: str
    layer: MemoryLayer = Field(default=MemoryLayer.LONG_TERM)

    # 分类
    category: LongTermCategory = Field(default=LongTermCategory.CUSTOM)

    # 内容
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    summary: str = Field(default="", max_length=500)

    # 元数据
    tags: list[str] = Field(default_factory=list)
    priority: MemoryPriority = Field(default=MemoryPriority.MEDIUM)

    # 重要性和置信度
    importance: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.8, ge=0, le=1)

    # 来源
    source: str = "manual"
    source_id: str = ""

    # 关联
    related_memory_ids: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)

    # 上下文
    context: dict[str, Any] = Field(default_factory=dict)

    # 时间
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = Field(default=0)
    expires_at: datetime | None = None

    # 持久化
    file_path: str = ""
    content_hash: str = ""

    def update_access(self):
        """更新访问记录并提升重要性"""
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1
        if self.access_count >= 5 and self.importance < 0.8:
            self.importance = min(0.95, self.importance + 0.1)
        if self.access_count >= 20:
            self.priority = MemoryPriority.HIGH


class MemoryRetrievalQuery(BaseModel):
    """记忆检索查询"""

    user_id: str | None = None
    categories: list[LongTermCategory] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    keyword: str = ""
    min_importance: float = Field(default=0.0, ge=0, le=1)
    priority: MemoryPriority | None = None

    time_range_start: datetime | None = None
    time_range_end: datetime | None = None

    max_results: int = Field(default=20, ge=1, le=100)
    sort_by: str = "importance"  # importance / recency / relevance


class MemorySystemStats(BaseModel):
    """记忆系统统计"""

    total_memories: int = 0
    by_layer: dict[str, int] = Field(default_factory=lambda: {
        "short_term": 0,
        "working": 0,
        "long_term": 0,
    })
    by_category: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)

    avg_importance: float = 0.0
    total_tokens_stm: int = 0
    total_manual_entries: int = 0

    most_accessed: list[dict[str, Any]] = Field(default_factory=list)
    top_tags: list[tuple[str, int]] = Field(default_factory=list)

    storage_size_bytes: int = 0
    last_updated: datetime | None = None
