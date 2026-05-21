"""Sub-Agent Models - Sub-Agent 数据模型

定义 Sub-Agent 的配置、上下文和执行结果。
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SubAgentStatus(str, Enum):
    """Sub-Agent 状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class SubAgentConfig(BaseModel):
    """Sub-Agent 配置
    
    定义一个 Sub-Agent 的能力、默认技能和执行参数。
    """
    agent_id: str = Field(..., description="Sub-Agent ID")
    name: str = Field(..., description="显示名称")
    description: str = Field(..., description="描述")
    capabilities: list[str] = Field(default_factory=list, description="能力标签")
    default_skills: list[str] = Field(default_factory=list, description="默认使用的技能")
    system_prompt: str = Field(default="", description="系统提示词")
    tools: list[str] = Field(default_factory=list, description="所需工具")
    timeout: int = Field(default=90, description="超时秒数")
    max_retries: int = Field(default=2, description="最大重试次数")
    max_concurrent: int = Field(default=1, description="最大并发数")
    priority: int = Field(default=5, description="优先级 (1-10, 高优先级先执行)")
    enabled: bool = Field(default=True, description="是否启用")


class IsolatedContext(BaseModel):
    """隔离上下文
    
    为 Sub-Agent 创建独立的执行空间，隔离主 Agent 和其他 Sub-Agent 的对话历史。
    """
    agent_id: str = Field(..., description="Agent ID")
    task_id: str = Field(..., description="任务 ID")
    messages: list[dict[str, str]] = Field(default_factory=list, description="对话历史")
    workspace: str = Field(default="", description="工作空间目录")
    uploads: str = Field(default="", description="上传文件目录")
    outputs: str = Field(default="", description="输出文件目录")
    shared_data: dict = Field(default_factory=dict, description="共享数据")
    parent_context: str | None = Field(default=None, description="父上下文 ID (用于继承)")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class SubAgentTask(BaseModel):
    """Sub-Agent 任务"""
    task_id: str = Field(..., description="任务 ID")
    agent_id: str = Field(..., description="执行者 Agent ID")
    input: dict = Field(default_factory=dict, description="输入参数")
    skills: list[str] = Field(default_factory=list, description="使用的技能")
    depends_on: str | None = Field(default=None, description="依赖的任务 ID")
    parallel_with: str | None = Field(default=None, description="并行执行的任务 ID")
    timeout_override: int | None = Field(default=None, description="超时覆盖")
    priority: int = Field(default=5, description="优先级")


class SubAgentResult(BaseModel):
    """Sub-Agent 执行结果"""
    task_id: str = Field(..., description="任务 ID")
    agent_id: str = Field(..., description="执行者 Agent ID")
    agent_name: str = Field(..., description="执行者名称")
    status: SubAgentStatus = Field(..., description="执行状态")
    output: str | None = Field(default=None, description="输出内容")
    artifacts: list[dict] = Field(default_factory=list, description="产物")
    error_message: str | None = Field(default=None, description="错误信息")
    thinking_process: list[dict] = Field(default_factory=list, description="思考过程")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")
    duration_ms: int = Field(default=0, description="耗时毫秒")
    token_usage: dict = Field(default_factory=dict, description="Token 用量")
    retries: int = Field(default=0, description="重试次数")


class SubAgentMatch(BaseModel):
    """Sub-Agent 匹配结果"""
    agent_id: str
    name: str
    capabilities: list[str]
    match_score: float = Field(..., description="匹配分数 (0-1)")
    matched_capabilities: list[str] = Field(default_factory=list, description="匹配的能力")


class SubAgentRegistryStats(BaseModel):
    """Sub-Agent 注册表统计"""
    total_agents: int
    enabled_agents: int
    capability_count: dict[str, int] = Field(default_factory=dict, description="各能力的 Agent 数量")
    avg_timeout: float
    top_priority_agents: list[str] = Field(default_factory=list, description="高优先级 Agent")
