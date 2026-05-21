"""Artifact Models - 产物数据模型

定义产物的结构、版本管理等。
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    """产物类型"""
    PROTOTYPE = "prototype"  # 原型 HTML
    DOCUMENT = "document"    # 文档 Markdown
    REPORT = "report"        # 报告
    IMAGE = "image"          # 图片
    DATA = "data"            # 数据文件
    CODE = "code"            # 代码
    OTHER = "other"          # 其他


class ArtifactStatus(str, Enum):
    """产物状态"""
    DRAFT = "draft"          # 草稿
    PUBLISHED = "published"  # 已发布
    ARCHIVED = "archived"    # 已归档
    DELETED = "deleted"      # 已删除


class ArtifactVersion(BaseModel):
    """产物版本"""
    version_id: str = Field(..., description="版本 ID")
    version_number: int = Field(..., description="版本号")
    content: str = Field(..., description="内容")
    content_type: str = Field(default="text/markdown", description="内容类型")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    created_by: str = Field(..., description="创建者 (user_id 或 agent_id)")
    created_by_name: str = Field(default="", description="创建者名称")
    diff_summary: Optional[str] = Field(default=None, description="与上一版本的差异摘要")
    diff_detail: Optional[dict] = Field(default=None, description="详细差异")
    size_bytes: int = Field(default=0, description="大小（字节）")
    metadata: dict = Field(default_factory=dict, description="元数据")


class Artifact(BaseModel):
    """产物"""
    artifact_id: str = Field(..., description="产物 ID")
    name: str = Field(..., description="名称")
    type: ArtifactType = Field(..., description="类型")
    status: ArtifactStatus = Field(default=ArtifactStatus.DRAFT, description="状态")
    description: str = Field(default="", description="描述")
    session_id: Optional[str] = Field(default=None, description="会话 ID")
    workflow_id: Optional[str] = Field(default=None, description="工作流 ID")
    workflow_execution_id: Optional[str] = Field(default=None, description="工作流执行 ID")
    step_id: Optional[str] = Field(default=None, description="步骤 ID")
    agent_id: Optional[str] = Field(default=None, description="生成 Agent ID")
    user_id: str = Field(..., description="用户 ID")
    versions: list[ArtifactVersion] = Field(default_factory=list, description="版本历史")
    current_version: int = Field(default=1, description="当前版本号")
    tags: list[str] = Field(default_factory=list, description="标签")
    preview_url: Optional[str] = Field(default=None, description="预览 URL")
    download_url: Optional[str] = Field(default=None, description="下载 URL")
    file_path: Optional[str] = Field(default=None, description="文件路径")
    is_editable: bool = Field(default=True, description="是否可编辑")
    is_public: bool = Field(default=False, description="是否公开")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    metadata: dict = Field(default_factory=dict, description="元数据")


class ArtifactDiff(BaseModel):
    """产物差异"""
    version_from: int = Field(..., description="起始版本")
    version_to: int = Field(..., description="目标版本")
    additions: int = Field(default=0, description="新增行数")
    deletions: int = Field(default=0, description="删除行数")
    modifications: int = Field(default=0, description="修改行数")
    similarity: float = Field(default=1.0, description="相似度 0-1")
    diff_content: Optional[str] = Field(default=None, description="差异内容 (diff 格式)")


class ArtifactComparison(BaseModel):
    """产物版本对比"""
    artifact_id: str
    version_from: ArtifactVersion
    version_to: ArtifactVersion
    diff: ArtifactDiff


class ArtifactListItem(BaseModel):
    """产物列表项（用于展示）"""
    artifact_id: str
    name: str
    type: ArtifactType
    type_display: str  # 类型显示名称
    status: ArtifactStatus
    status_display: str  # 状态显示名称
    version_count: int
    current_version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    workflow_name: Optional[str] = None
    session_title: Optional[str] = None
    preview_url: Optional[str] = None
    tags: list[str]


class ArtifactStats(BaseModel):
    """产物统计"""
    total_artifacts: int
    total_versions: int
    by_type: dict[str, int] = Field(default_factory=dict, description="各类型数量")
    by_status: dict[str, int] = Field(default_factory=dict, description="各状态数量")
    total_size_bytes: int = Field(default=0, description="总大小")
    avg_versions: float = Field(default=0, description="平均版本数")
    recent_artifacts: list[str] = Field(default_factory=list, description="最近产物 ID")