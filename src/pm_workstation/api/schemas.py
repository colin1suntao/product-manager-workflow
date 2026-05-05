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
