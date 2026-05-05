"""问题报告生成器

汇总所有校验和一致性问题，生成结构化的问题报告。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from pm_workstation.verification.autofixer import FixResult
from pm_workstation.verification.consistency_checker import ConsistencyCheckResult
from pm_workstation.verification.document_models import (
    DocIssueSeverity,
    DocIssueType,
    DocumentVerificationReport,
)
from pm_workstation.verification.verification_models import (
    IssueSeverity,
    PrototypeVerificationReport,
)


class IssueSummary(BaseModel):
    """问题汇总统计"""
    total_issues: int = Field(..., description="问题总数")
    critical_count: int = Field(default=0, description="阻断性问题数量")
    major_count: int = Field(default=0, description="重要问题数量")
    minor_count: int = Field(default=0, description="次要问题数量")
    info_count: int = Field(default=0, description="提示信息数量")
    auto_fixed_count: int = Field(default=0, description="已自动修复数量")
    manual_review_count: int = Field(default=0, description="需人工审查数量")


class CategorizedIssue(BaseModel):
    """分类后的问题"""
    issue_id: str = Field(..., description="问题ID")
    category: str = Field(..., description="问题类别 (prototype, document, consistency)")
    issue_type: str = Field(..., description="问题类型")
    severity: str = Field(..., description="严重程度")
    description: str = Field(..., description="问题描述")
    suggestion: str = Field(default="", description="修复建议")
    location: str = Field(default="", description="问题位置")
    auto_fixable: bool = Field(default=False, description="是否可自动修复")
    auto_fixed: bool = Field(default=False, description="是否已自动修复")


class VerificationReport(BaseModel):
    """综合校验报告"""
    report_id: str = Field(..., description="报告唯一标识")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="生成时间")
    requirement_id: str = Field(default="", description="需求ID")

    # 各维度校验结果
    prototype_passed: bool = Field(default=True, description="原型校验是否通过")
    document_passed: bool = Field(default=True, description="文档校验是否通过")
    consistency_passed: bool = Field(default=True, description="一致性校验是否通过")

    # 问题列表
    issues: list[CategorizedIssue] = Field(default_factory=list, description="所有问题")
    summary: IssueSummary = Field(..., description="问题汇总统计")

    # 修复结果
    auto_fix_result: Optional[FixResult] = Field(default=None, description="自动修复结果")

    # 总结
    overall_passed: bool = Field(..., description="总体是否通过")
    summary_text: str = Field(default="", description="报告总结")


class IssueReporter:
    """问题报告生成器

    汇总原型校验、文档校验和一致性检查的结果，生成综合校验报告。
    """

    def generate_report(
        self,
        requirement_id: str,
        prototype_report: Optional[PrototypeVerificationReport] = None,
        document_report: Optional[DocumentVerificationReport] = None,
        consistency_result: Optional[ConsistencyCheckResult] = None,
        fix_result: Optional[FixResult] = None,
    ) -> VerificationReport:
        """生成综合校验报告

        Args:
            requirement_id: 需求ID
            prototype_report: 原型校验报告
            document_report: 文档校验报告
            consistency_result: 一致性检查结果
            fix_result: 自动修复结果

        Returns:
            综合校验报告
        """
        all_issues = []

        if prototype_report:
            all_issues.extend(self._convert_prototype_issues(prototype_report))

        if document_report:
            all_issues.extend(self._convert_document_issues(document_report))

        if consistency_result:
            all_issues.extend(self._convert_consistency_issues(consistency_result))

        if fix_result:
            self._mark_auto_fixed_issues(all_issues, fix_result)

        summary = self._compute_summary(all_issues, fix_result)

        overall_passed = summary.manual_review_count == 0 and summary.critical_count == 0 and summary.major_count == 0

        summary_text = self._generate_summary_text(
            prototype_report,
            document_report,
            consistency_result,
            summary,
            fix_result,
        )

        return VerificationReport(
            report_id=f"vr-{requirement_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            requirement_id=requirement_id,
            prototype_passed=prototype_report.passed if prototype_report else True,
            document_passed=document_report.passed if document_report else True,
            consistency_passed=consistency_result.passed if consistency_result else True,
            issues=all_issues,
            summary=summary,
            auto_fix_result=fix_result,
            overall_passed=overall_passed,
            summary_text=summary_text,
        )

    def _convert_prototype_issues(
        self,
        report: PrototypeVerificationReport,
    ) -> list[CategorizedIssue]:
        """转换原型校验问题"""
        issues = []
        for issue in report.issues:
            issues.append(CategorizedIssue(
                issue_id=issue.issue_id,
                category="prototype",
                issue_type=issue.issue_type.value if hasattr(issue.issue_type, "value") else str(issue.issue_type),
                severity=issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
                description=issue.description,
                suggestion=issue.suggestion,
                location=issue.page_id or issue.element_id,
                auto_fixable=issue.auto_fixable,
                auto_fixed=issue.auto_fix_applied,
            ))
        return issues

    def _convert_document_issues(
        self,
        report: DocumentVerificationReport,
    ) -> list[CategorizedIssue]:
        """转换文档校验问题"""
        issues = []
        for issue in report.issues:
            issues.append(CategorizedIssue(
                issue_id=issue.issue_id,
                category="document",
                issue_type=issue.issue_type.value if hasattr(issue.issue_type, "value") else str(issue.issue_type),
                severity=issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
                description=issue.description,
                suggestion=issue.suggestion,
                location=issue.location,
                auto_fixable=issue.auto_fixable,
                auto_fixed=False,
            ))
        return issues

    def _convert_consistency_issues(
        self,
        result: ConsistencyCheckResult,
    ) -> list[CategorizedIssue]:
        """转换一致性问题"""
        issues = []
        for issue in result.issues:
            issues.append(CategorizedIssue(
                issue_id=issue.issue_id,
                category="consistency",
                issue_type=issue.issue_type.value if hasattr(issue.issue_type, "value") else str(issue.issue_type),
                severity=issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
                description=issue.description,
                suggestion=issue.suggestion,
                location=f"原型: {issue.prototype_side} | 文档: {issue.document_side}",
                auto_fixable=False,
                auto_fixed=False,
            ))
        return issues

    def _mark_auto_fixed_issues(
        self,
        issues: list[CategorizedIssue],
        fix_result: FixResult,
    ) -> None:
        """标记已自动修复的问题"""
        fixed_ids = set(fix_result.fixed_issues)
        for issue in issues:
            if issue.issue_id in fixed_ids:
                issue.auto_fixed = True

    def _compute_summary(
        self,
        issues: list[CategorizedIssue],
        fix_result: Optional[FixResult] = None,
    ) -> IssueSummary:
        """计算问题汇总统计"""
        critical = sum(1 for i in issues if i.severity == "critical")
        major = sum(1 for i in issues if i.severity == "major")
        minor = sum(1 for i in issues if i.severity == "minor")
        info = sum(1 for i in issues if i.severity == "info")

        auto_fixed = fix_result.fixed_issues if fix_result else []
        auto_fixed_count = len(auto_fixed)

        manual_review = sum(
            1 for i in issues
            if i.severity in ("critical", "major") and i.issue_id not in auto_fixed
        )

        return IssueSummary(
            total_issues=len(issues),
            critical_count=critical,
            major_count=major,
            minor_count=minor,
            info_count=info,
            auto_fixed_count=auto_fixed_count,
            manual_review_count=manual_review,
        )

    def _generate_summary_text(
        self,
        prototype_report: Optional[PrototypeVerificationReport],
        document_report: Optional[DocumentVerificationReport],
        consistency_result: Optional[ConsistencyCheckResult],
        summary: IssueSummary,
        fix_result: Optional[FixResult],
    ) -> str:
        """生成报告总结文本"""
        parts = []

        if prototype_report:
            proto_status = "通过" if prototype_report.passed else "未通过"
            parts.append(f"原型校验: {proto_status}")

        if document_report:
            doc_status = "通过" if document_report.passed else "未通过"
            parts.append(f"文档校验: {doc_status}")

        if consistency_result:
            cons_status = "通过" if consistency_result.passed else "未通过"
            parts.append(f"一致性校验: {cons_status}")

        parts.append(f"共发现 {summary.total_issues} 个问题")

        if summary.critical_count > 0:
            parts.append(f"  - {summary.critical_count} 个阻断性问题")
        if summary.major_count > 0:
            parts.append(f"  - {summary.major_count} 个重要问题")
        if summary.minor_count > 0:
            parts.append(f"  - {summary.minor_count} 个次要问题")
        if summary.info_count > 0:
            parts.append(f"  - {summary.info_count} 个提示信息")

        if summary.auto_fixed_count > 0:
            parts.append(f"已自动修复 {summary.auto_fixed_count} 个问题")

        if summary.manual_review_count > 0:
            parts.append(f"需人工审查 {summary.manual_review_count} 个问题")

        if fix_result and fix_result.summary:
            parts.append(f"修复结果: {fix_result.summary}")

        return "\n".join(parts)

    def generate_markdown_report(self, report: VerificationReport) -> str:
        """生成 Markdown 格式的报告

        Args:
            report: 综合校验报告

        Returns:
            Markdown 格式的报告文本
        """
        lines = []

        lines.append(f"# 综合校验报告")
        lines.append("")
        lines.append(f"- **报告 ID**: {report.report_id}")
        lines.append(f"- **生成时间**: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **需求 ID**: {report.requirement_id}")
        lines.append(f"- **总体结果**: {'通过' if report.overall_passed else '未通过'}")
        lines.append("")

        lines.append("## 校验维度")
        lines.append("")
        lines.append(f"| 维度 | 状态 |")
        lines.append(f"| --- | --- |")
        proto_status = "通过" if report.prototype_passed else "未通过"
        doc_status = "通过" if report.document_passed else "未通过"
        cons_status = "通过" if report.consistency_passed else "未通过"
        lines.append(f"| 原型校验 | {proto_status} |")
        lines.append(f"| 文档校验 | {doc_status} |")
        lines.append(f"| 一致性校验 | {cons_status} |")
        lines.append("")

        lines.append("## 问题汇总")
        lines.append("")
        s = report.summary
        lines.append(f"- **问题总数**: {s.total_issues}")
        lines.append(f"- **阻断性**: {s.critical_count}")
        lines.append(f"- **重要**: {s.major_count}")
        lines.append(f"- **次要**: {s.minor_count}")
        lines.append(f"- **提示**: {s.info_count}")
        lines.append(f"- **已自动修复**: {s.auto_fixed_count}")
        lines.append(f"- **需人工审查**: {s.manual_review_count}")
        lines.append("")

        if report.issues:
            lines.append("## 问题列表")
            lines.append("")

            by_severity = {"critical": [], "major": [], "minor": [], "info": []}
            for issue in report.issues:
                by_severity.setdefault(issue.severity, []).append(issue)

            severity_labels = {
                "critical": "阻断性",
                "major": "重要",
                "minor": "次要",
                "info": "提示",
            }

            for severity in ["critical", "major", "minor", "info"]:
                severity_issues = by_severity.get(severity, [])
                if not severity_issues:
                    continue

                lines.append(f"### {severity_labels[severity]}问题 ({len(severity_issues)})")
                lines.append("")

                for issue in severity_issues:
                    fixed_badge = " [已修复]" if issue.auto_fixed else ""
                    lines.append(f"#### [{issue.issue_id}]{fixed_badge}")
                    lines.append("")
                    lines.append(f"- **类别**: {issue.category}")
                    lines.append(f"- **类型**: {issue.issue_type}")
                    lines.append(f"- **描述**: {issue.description}")
                    if issue.suggestion:
                        lines.append(f"- **建议**: {issue.suggestion}")
                    if issue.location:
                        lines.append(f"- **位置**: {issue.location}")
                    lines.append("")

        if report.summary_text:
            lines.append("## 总结")
            lines.append("")
            lines.append(report.summary_text)
            lines.append("")

        return "\n".join(lines)
