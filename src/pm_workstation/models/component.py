"""组件库数据模型"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ComponentCategory(StrEnum):
    """组件分类"""
    LAYOUT = "layout"
    FORM = "form"
    DATA_DISPLAY = "data_display"
    NAVIGATION = "navigation"
    FEEDBACK = "feedback"
    BUTTON = "button"
    INPUT = "input"
    CUSTOM = "custom"


class ComponentStatus(StrEnum):
    """组件状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class ComponentVersionInfo(BaseModel):
    """组件版本信息"""
    version: str = Field(..., description="版本号 (semver)")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    created_by: str = Field(default="", description="创建者")
    changelog: str = Field(default="", description="变更日志")
    is_latest: bool = Field(default=True, description="是否最新版本")


class ComponentMeta(BaseModel):
    """组件元数据"""
    tags: list[str] = Field(default_factory=list, description="标签列表")
    category: ComponentCategory = Field(default=ComponentCategory.CUSTOM, description="组件分类")
    author: str = Field(default="", description="作者")
    description: str = Field(default="", description="组件描述")
    usage_notes: str = Field(default="", description="使用说明")
    dependencies: list[str] = Field(default_factory=list, description="依赖组件列表")
    props_schema: dict = Field(default_factory=dict, description="属性定义")
    events_schema: dict = Field(default_factory=dict, description="事件定义")


class Component(BaseModel):
    """组件定义"""
    id: str = Field(..., description="组件唯一标识")
    name: str = Field(..., description="组件名称")
    display_name: str = Field(default="", description="显示名称")
    description: str = Field(default="", description="组件描述")
    category: ComponentCategory = Field(default=ComponentCategory.CUSTOM, description="分类")
    tags: list[str] = Field(default_factory=list, description="标签")
    status: ComponentStatus = Field(default=ComponentStatus.DRAFT, description="状态")
    current_version: str = Field(default="1.0.0", description="当前版本")
    meta: ComponentMeta = Field(default_factory=ComponentMeta, description="元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class ComponentVersion(BaseModel):
    """组件版本"""
    component_id: str = Field(..., description="组件ID")
    version: str = Field(..., description="版本号")
    html_template: str = Field(default="", description="HTML模板")
    css_content: str = Field(default="", description="CSS内容")
    js_content: str = Field(default="", description="JS内容")
    thumbnail_url: str = Field(default="", description="缩略图URL")
    preview_url: str = Field(default="", description="预览URL")
    changelog: str = Field(default="", description="变更日志")
    is_latest: bool = Field(default=True, description="是否最新版本")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class ComponentSearchRequest(BaseModel):
    """组件搜索请求"""
    query: str = Field(default="", description="搜索关键词")
    category: ComponentCategory | None = Field(default=None, description="分类过滤")
    tags: list[str] = Field(default_factory=list, description="标签过滤")
    status: ComponentStatus | None = Field(default=None, description="状态过滤")
    min_similarity: float = Field(default=0.5, ge=0.0, le=1.0, description="最低相似度阈值")
    limit: int = Field(default=10, ge=1, le=100, description="返回数量限制")


class ComponentSearchResult(BaseModel):
    """组件搜索结果"""
    component: Component = Field(..., description="组件信息")
    version: ComponentVersion | None = Field(default=None, description="匹配的版本")
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0, description="相似度分数")
    match_reason: str = Field(default="", description="匹配原因")


class ComponentUploadRequest(BaseModel):
    """组件上传请求"""
    name: str = Field(..., description="组件名称")
    display_name: str = Field(default="", description="显示名称")
    description: str = Field(default="", description="组件描述")
    category: ComponentCategory = Field(default=ComponentCategory.CUSTOM, description="分类")
    tags: list[str] = Field(default_factory=list, description="标签")
    version: str = Field(default="1.0.0", description="版本号")
    html_template: str = Field(default="", description="HTML模板")
    css_content: str = Field(default="", description="CSS内容")
    js_content: str = Field(default="", description="JS内容")
    changelog: str = Field(default="", description="变更日志")
    props_schema: dict = Field(default_factory=dict, description="属性定义")


class ComponentMatchRequest(BaseModel):
    """组件匹配请求（用于原型生成）"""
    description: str = Field(..., description="组件功能描述")
    required_props: list[str] = Field(default_factory=list, description="需要的属性")
    category_hint: ComponentCategory | None = Field(default=None, description="分类提示")
    min_similarity: float = Field(default=0.6, ge=0.0, le=1.0, description="最低相似度")
