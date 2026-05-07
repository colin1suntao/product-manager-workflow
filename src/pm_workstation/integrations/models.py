"""外部系统集成配置

定义外部系统（Jira, Figma, GitHub 等）的配置模型和同步任务管理。
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class IntegrationType(StrEnum):
    """集成类型"""
    JIRA = "jira"
    TRELLO = "trello"
    FEISHU = "feishu"
    FIGMA = "figma"
    SKETCH = "sketch"
    GITHUB = "github"
    GITLAB = "gitlab"
    CUSTOM = "custom"


class SyncStatus(StrEnum):
    """同步状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncDirection(StrEnum):
    """同步方向"""
    IMPORT = "import"
    EXPORT = "export"
    BIDIRECTIONAL = "bidirectional"


class IntegrationConfig(BaseModel):
    """外部系统集成配置"""
    id: str = Field(..., description="配置唯一标识")
    name: str = Field(..., description="配置名称")
    integration_type: IntegrationType = Field(..., description="集成类型")
    enabled: bool = Field(default=True, description="是否启用")

    # 连接信息
    api_endpoint: str = Field(default="", description="API 端点")
    api_key: str = Field(default="", description="API 密钥（加密存储）")
    api_secret: str = Field(default="", description="API 密钥（加密存储）")
    access_token: str = Field(default="", description="访问令牌（加密存储）")

    # 额外配置
    settings: dict | None = Field(default_factory=dict, description="额外配置项")

    # 元数据
    created_by: str = Field(default="", description="创建者")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")


class SyncTask(BaseModel):
    """同步任务"""
    id: str = Field(..., description="任务唯一标识")
    integration_id: str = Field(..., description="关联的集成配置ID")
    workflow_id: str = Field(default="", description="关联的工作流ID")

    # 同步信息
    direction: SyncDirection = Field(default=SyncDirection.IMPORT, description="同步方向")
    status: SyncStatus = Field(default=SyncStatus.PENDING, description="同步状态")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="进度百分比")

    # 数据信息
    source_data: dict | None = Field(default_factory=dict, description="源数据信息")
    result_data: dict | None = Field(default_factory=dict, description="同步结果")
    error_message: str | None = Field(default=None, description="错误信息")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    started_at: datetime | None = Field(default=None, description="开始时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")

    def start(self) -> None:
        """标记任务开始"""
        self.status = SyncStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.progress = 0.0

    def complete(self, result_data: dict | None = None) -> None:
        """标记任务完成"""
        self.status = SyncStatus.COMPLETED
        self.progress = 100.0
        self.completed_at = datetime.utcnow()
        if result_data:
            self.result_data = result_data

    def fail(self, error_message: str) -> None:
        """标记任务失败"""
        self.status = SyncStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()

    def cancel(self) -> None:
        """取消任务"""
        self.status = SyncStatus.CANCELLED
        self.completed_at = datetime.utcnow()
