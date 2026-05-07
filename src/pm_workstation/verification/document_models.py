"""文档校验相关数据模型"""

from enum import StrEnum

from pydantic import BaseModel, Field


class DocIssueSeverity(StrEnum):
    """文档问题严重程度"""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class DocIssueType(StrEnum):
    """文档问题类型"""
    FORMAT = "format"                    # 格式问题
    HEADING_HIERARCHY = "heading_hierarchy"  # 标题层级问题
    MISSING_SECTION = "missing_section"  # 缺失必需章节
    TERMINOLOGY = "terminology"          # 术语不一致
    TABLE_FORMAT = "table_format"        # 表格格式问题
    LINK = "link"                        # 链接问题
    CONTENT = "content"                  # 内容问题
    STYLE = "style"                      # 样式问题


class DocumentIssue(BaseModel):
    """文档校验发现的问题"""
    issue_id: str = Field(..., description="问题唯一标识")
    issue_type: DocIssueType = Field(..., description="问题类型")
    severity: DocIssueSeverity = Field(..., description="严重程度")
    location: str = Field(default="", description="问题位置（行号或章节名）")
    description: str = Field(..., description="问题描述")
    suggestion: str = Field(default="", description="修复建议")
    auto_fixable: bool = Field(default=False, description="是否可自动修复")


class FormatCheckResult(BaseModel):
    """格式检查结果"""
    passed: bool = Field(..., description="是否通过")
    issues: list[DocumentIssue] = Field(default_factory=list, description="问题列表")
    headings_checked: int = Field(default=0, description="检查的标题数")
    tables_checked: int = Field(default=0, description="检查的表格数")
    links_checked: int = Field(default=0, description="检查的链接数")


class StructureCheckResult(BaseModel):
    """结构完整性检查结果"""
    passed: bool = Field(..., description="是否通过")
    issues: list[DocumentIssue] = Field(default_factory=list, description="问题列表")
    required_sections: list[str] = Field(default_factory=list, description="必需章节列表")
    missing_sections: list[str] = Field(default_factory=list, description="缺失的章节")
    found_sections: list[str] = Field(default_factory=list, description="已找到的章节")


class DocumentVerificationReport(BaseModel):
    """文档校验报告"""
    format_check: FormatCheckResult = Field(..., description="格式检查结果")
    structure_check: StructureCheckResult = Field(..., description="结构完整性检查结果")
    terminology_issues: list[DocumentIssue] = Field(default_factory=list, description="术语问题")
    issues: list[DocumentIssue] = Field(default_factory=list, description="所有问题")
    passed: bool = Field(..., description="是否通过校验")
    summary: str = Field(default="", description="校验总结")
