"""Workflow Models - 工作流数据模型

定义工作流的结构、步骤、执行结果等。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """步骤状态"""
    PENDING = "pending"
    WAITING = "waiting"  # 等待依赖完成
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class WorkflowStep(BaseModel):
    """工作流步骤"""
    id: str = Field(..., description="步骤 ID")
    name: str = Field(..., description="步骤名称")
    description: str = Field(default="", description="步骤描述")
    mode: str = Field(..., description="任务模式: requirement/prototype/prd/market_research")
    skills: list[str] = Field(default_factory=list, description="使用的技能")
    agent_id: Optional[str] = Field(default=None, description="指定的 Sub-Agent ID")
    depends_on: Optional[str] = Field(default=None, description="依赖的步骤 ID")
    parallel_with: Optional[str] = Field(default=None, description="并行执行的步骤 ID")
    input: dict = Field(default_factory=dict, description="输入参数")
    input_from_dependency: Optional[str] = Field(default=None, description="从依赖步骤获取输入的字段")
    timeout: int = Field(default=90, description="超时秒数")
    retry_on_failure: int = Field(default=0, description="失败重试次数")
    optional: bool = Field(default=False, description="是否可选（失败不影响整体）")
    priority: int = Field(default=5, description="优先级")


class WorkflowDefinition(BaseModel):
    """工作流定义"""
    id: str = Field(..., description="工作流 ID")
    name: str = Field(..., description="工作流名称")
    description: str = Field(default="", description="工作流描述")
    version: str = Field(default="1.0.0", description="版本号")
    category: str = Field(default="general", description="分类: product-design/market-research/user-research")
    steps: list[WorkflowStep] = Field(default_factory=list, description="步骤列表")
    estimated_time: str = Field(default="", description="预估时间: 5-10 minutes")
    best_for: list[str] = Field(default_factory=list, description="适用场景")
    tags: list[str] = Field(default_factory=list, description="标签")
    author: str = Field(default="system", description="作者")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class StepResult(BaseModel):
    """步骤执行结果"""
    step_id: str = Field(..., description="步骤 ID")
    step_name: str = Field(..., description="步骤名称")
    status: StepStatus = Field(..., description="状态")
    output: Optional[str] = Field(default=None, description="输出内容")
    artifacts: list[dict] = Field(default_factory=list, description="产物")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    duration_ms: int = Field(default=0, description="耗时毫秒")
    agent_id: Optional[str] = Field(default=None, description="执行的 Agent ID")
    agent_name: Optional[str] = Field(default=None, description="执行的 Agent 名称")
    token_usage: dict = Field(default_factory=dict, description="Token 用量")
    retry_count: int = Field(default=0, description="重试次数")


class WorkflowExecution(BaseModel):
    """工作流执行记录"""
    execution_id: str = Field(..., description="执行 ID")
    workflow_id: str = Field(..., description="工作流 ID")
    workflow_name: str = Field(..., description="工作流名称")
    user_id: str = Field(..., description="用户 ID")
    session_id: Optional[str] = Field(default=None, description="会话 ID")
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, description="状态")
    steps_results: list[StepResult] = Field(default_factory=list, description="步骤结果")
    current_step_index: int = Field(default=0, description="当前步骤索引")
    parallel_steps_running: list[str] = Field(default_factory=list, description="正在运行的并行步骤")
    total_steps: int = Field(default=0, description="总步骤数")
    completed_steps: int = Field(default=0, description="已完成步骤数")
    failed_steps: int = Field(default=0, description="失败步骤数")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    total_duration_ms: int = Field(default=0, description="总耗时毫秒")
    total_token_usage: dict = Field(default_factory=dict, description="总 Token 用量")
    final_artifacts: list[dict] = Field(default_factory=list, description="最终产物")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    metadata: dict = Field(default_factory=dict, description="元数据")


class WorkflowProgress(BaseModel):
    """工作流进度"""
    execution_id: str
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    progress_percent: float = Field(..., description="进度百分比 0-100")
    current_step: Optional[str] = Field(default=None, description="当前步骤名称")
    current_step_status: Optional[StepStatus] = Field(default=None)
    completed_steps: list[str] = Field(default_factory=list, description="已完成的步骤")
    running_steps: list[str] = Field(default_factory=list, description="正在运行的步骤")
    pending_steps: list[str] = Field(default_factory=list, description="等待的步骤")
    failed_steps: list[str] = Field(default_factory=list, description="失败的步骤")
    artifacts_generated: list[dict] = Field(default_factory=list, description="已生成的产物")
    estimated_remaining_time: Optional[str] = Field(default=None, description="预估剩余时间")


class WorkflowTemplate(BaseModel):
    """工作流模板（用于展示）"""
    id: str
    name: str
    description: str
    category: str
    steps_count: int
    estimated_time: str
    best_for: list[str]
    tags: list[str]
    preview_steps: list[str] = Field(default_factory=list, description="预览步骤名称列表")