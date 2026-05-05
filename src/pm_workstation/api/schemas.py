"""API 请求/响应模型

定义 API 接口使用的 Pydantic 模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from pm_workstation.models.core import WorkflowStatus


class StartWorkflowRequest(BaseModel):
    """启动工作流请求"""
    requirement_text: str = Field(..., description="原始需求文本", min_length=1)
    llm_provider_id: Optional[str] = Field(default=None, description="LLM Provider ID")


class WorkflowResponse(BaseModel):
    """工作流响应"""
    id: str = Field(..., description="工作流ID")
    user_id: str = Field(..., description="用户ID")
    requirement_text: str = Field(..., description="原始需求文本")
    status: WorkflowStatus = Field(..., description="当前状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    structured_requirement: Optional[dict] = Field(default=None, description="结构化需求")
    prototype_url: Optional[str] = Field(default=None, description="原型URL")
    prd_document_url: Optional[str] = Field(default=None, description="PRD文档URL")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class WorkflowListResponse(BaseModel):
    """工作流列表响应"""
    workflows: list[WorkflowResponse] = Field(..., description="工作流列表")
    total: int = Field(..., description="总数")


class PauseWorkflowRequest(BaseModel):
    """暂停工作流请求"""
    reason: Optional[str] = Field(default=None, description="暂停原因")


class ResumeWorkflowRequest(BaseModel):
    """恢复工作流请求"""
    user_responses: Optional[list[dict]] = Field(default=None, description="用户回复")


class DeliverablesResponse(BaseModel):
    """交付物响应"""
    workflow_id: str = Field(..., description="工作流ID")
    prototype_url: Optional[str] = Field(default=None, description="原型URL")
    prd_document_url: Optional[str] = Field(default=None, description="PRD文档URL")
    verification_report: Optional[dict] = Field(default=None, description="校验报告")


class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str = Field(..., description="错误详情")
    code: Optional[str] = Field(default=None, description="错误代码")


# --- LLM Provider 相关 Schema ---

class LLMProviderConfigCreate(BaseModel):
    """创建 LLM Provider 配置请求"""
    name: str = Field(..., description="显示名称", min_length=1, max_length=100)
    provider_type: str = Field(..., description="提供商类型 (openai/anthropic/custom)")
    api_key: str = Field(..., description="API Key", min_length=1)
    base_url: Optional[str] = Field(default=None, description="API Base URL", max_length=500)
    default_model: str = Field(..., description="默认模型名称", min_length=1, max_length=100)
    is_active: bool = Field(default=True, description="是否启用")
    is_default: bool = Field(default=False, description="是否为默认 Provider")


class LLMProviderConfigUpdate(BaseModel):
    """更新 LLM Provider 配置请求"""
    name: Optional[str] = Field(default=None, description="显示名称", min_length=1, max_length=100)
    api_key: Optional[str] = Field(default=None, description="API Key", min_length=1)
    base_url: Optional[str] = Field(default=None, description="API Base URL", max_length=500)
    default_model: Optional[str] = Field(default=None, description="默认模型名称", min_length=1, max_length=100)
    is_active: Optional[bool] = Field(default=None, description="是否启用")
    is_default: Optional[bool] = Field(default=None, description="是否为默认 Provider")


class LLMProviderConfigResponse(BaseModel):
    """LLM Provider 配置响应"""
    id: str
    name: str
    provider_type: str
    api_key: str
    base_url: Optional[str]
    default_model: str
    is_active: bool
    is_default: bool
    created_at: str
    updated_at: str


class LLMProviderListResponse(BaseModel):
    """LLM Provider 列表响应"""
    providers: list[dict] = Field(..., description="Provider 列表")
    total: int = Field(..., description="总数")


class LLMTestRequest(BaseModel):
    """LLM 连通性测试请求"""
    prompt: Optional[str] = Field(default=None, description="测试提示词")


class LLMQuickTestRequest(BaseModel):
    """快速连通性测试请求（无需保存配置）"""
    provider_type: str = Field(..., description="提供商类型 (openai/anthropic/custom)")
    api_key: str = Field(..., description="API Key", min_length=1)
    base_url: Optional[str] = Field(default=None, description="API Base URL", max_length=500)
    default_model: Optional[str] = Field(default=None, description="模型名称", max_length=100)


class LLMModelListRequest(BaseModel):
    """获取模型列表请求"""
    provider_type: str = Field(..., description="提供商类型 (openai/anthropic/custom)")
    api_key: str = Field(..., description="API Key", min_length=1)
    base_url: Optional[str] = Field(default=None, description="API Base URL", max_length=500)


class LLMModelListResponse(BaseModel):
    """模型列表响应"""
    models: list[dict] = Field(..., description="模型列表")
    total: int = Field(..., description="模型总数")


class LLMTestResponse(BaseModel):
    """LLM 连通性测试响应"""
    success: bool = Field(..., description="是否成功")
    response_time_ms: int = Field(..., description="响应时间 (毫秒)")
    model: str = Field(..., description="模型名称")
    message: str = Field(..., description="测试消息")
