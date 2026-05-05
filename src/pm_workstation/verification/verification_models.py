"""原型校验相关数据模型"""

from enum import Enum

from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    """问题严重程度"""
    CRITICAL = "critical"  # 阻断性问题
    MAJOR = "major"        # 重要问题
    MINOR = "minor"        # 次要问题
    INFO = "info"          # 提示信息


class IssueType(str, Enum):
    """问题类型"""
    MISSING_PAGE = "missing_page"              # 缺失页面
    MISSING_ELEMENT = "missing_element"         # 缺失页面元素
    MISSING_INTERACTION = "missing_interaction" # 缺失交互逻辑
    BROKEN_LINK = "broken_link"                # 断裂的页面链接
    INCONSISTENT_STYLE = "inconsistent_style"   # 样式不一致
    ACCESSIBILITY = "accessibility"            # 可访问性问题
    RESPONSIVE = "responsive"                  # 响应式问题
    CONTENT = "content"                        # 内容问题


class VerificationIssue(BaseModel):
    """校验发现的问题"""
    issue_id: str = Field(..., description="问题唯一标识")
    issue_type: IssueType = Field(..., description="问题类型")
    severity: IssueSeverity = Field(..., description="严重程度")
    page_id: str = Field(default="", description="关联页面ID")
    element_id: str = Field(default="", description="关联元素ID")
    description: str = Field(..., description="问题描述")
    suggestion: str = Field(default="", description="修复建议")
    auto_fixable: bool = Field(default=False, description="是否可自动修复")
    auto_fix_applied: bool = Field(default=False, description="是否已自动修复")


class CoverageResult(BaseModel):
    """覆盖率检查结果"""
    total_pages_required: int = Field(..., description="需求要求的页面总数")
    pages_generated: int = Field(..., description="实际生成的页面数")
    page_coverage_rate: float = Field(..., description="页面覆盖率 (0.0 - 1.0)")
    missing_pages: list[str] = Field(default_factory=list, description="缺失的页面ID列表")
    extra_pages: list[str] = Field(default_factory=list, description="多余的页面ID列表")
    
    total_elements_required: int = Field(default=0, description="需求要求的元素总数")
    elements_generated: int = Field(default=0, description="实际生成的元素数")
    element_coverage_rate: float = Field(default=0.0, description="元素覆盖率 (0.0 - 1.0)")
    missing_elements: list[str] = Field(default_factory=list, description="缺失的元素ID列表")


class InteractionCheckResult(BaseModel):
    """交互逻辑检查结果"""
    total_interactions_required: int = Field(..., description="需求要求的交互总数")
    interactions_verified: int = Field(..., description="已验证的交互数")
    interaction_pass_rate: float = Field(..., description="交互通过率 (0.0 - 1.0)")
    failed_interactions: list[VerificationIssue] = Field(default_factory=list, description="失败的交互列表")
    unverified_interactions: list[str] = Field(default_factory=list, description="未验证的交互列表")


class PrototypeVerificationReport(BaseModel):
    """原型校验报告"""
    coverage: CoverageResult = Field(..., description="覆盖率检查结果")
    interaction_check: InteractionCheckResult = Field(..., description="交互逻辑检查结果")
    issues: list[VerificationIssue] = Field(default_factory=list, description="所有发现的问题")
    passed: bool = Field(..., description="是否通过校验")
    summary: str = Field(default="", description="校验总结")
