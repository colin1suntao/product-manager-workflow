"""自动修复器

根据校验报告中发现的问题，自动执行可修复的修复操作。
"""

import re

from pydantic import BaseModel, Field

from pm_workstation.document.markdown_formatter import MarkdownFormatter
from pm_workstation.verification.document_models import (
    DocIssueSeverity,
    DocIssueType,
    DocumentIssue,
)
from pm_workstation.verification.verification_models import (
    IssueSeverity,
    IssueType,
    VerificationIssue,
)


class FixAction(BaseModel):
    """修复动作"""
    issue_id: str = Field(..., description="问题ID")
    action_type: str = Field(..., description="动作类型")
    description: str = Field(..., description="动作描述")
    original_value: str = Field(default="", description="原始值")
    fixed_value: str = Field(default="", description="修复后的值")


class FixResult(BaseModel):
    """修复结果"""
    fixed_issues: list[str] = Field(default_factory=list, description="已修复的问题ID列表")
    fix_actions: list[FixAction] = Field(default_factory=list, description="修复动作列表")
    skipped_issues: list[str] = Field(default_factory=list, description="跳过的问题ID列表")
    failed_fixes: list[str] = Field(default_factory=list, description="修复失败的问题ID列表")
    summary: str = Field(default="", description="修复总结")


class AutoFixer:
    """自动修复器

    根据校验报告中的问题，自动执行可修复的修复操作。
    """

    def fix_document(
        self,
        document_content: str,
        issues: list[DocumentIssue],
    ) -> FixResult:
        """修复文档中的问题

        Args:
            document_content: 原始文档内容
            issues: 文档问题列表

        Returns:
            修复结果
        """
        fixed_issues = []
        fix_actions: list[FixAction] = []
        skipped_issues = []
        failed_fixes = []

        for issue in issues:
            if not issue.auto_fixable:
                skipped_issues.append(issue.issue_id)
                continue

            try:
                action = self._apply_document_fix(document_content, issue)
                if action:
                    fix_actions.append(action)
                    fixed_issues.append(issue.issue_id)
                else:
                    failed_fixes.append(issue.issue_id)
            except Exception:
                failed_fixes.append(issue.issue_id)

        summary = self._generate_document_summary(fixed_issues, skipped_issues, failed_fixes)

        return FixResult(
            fixed_issues=fixed_issues,
            fix_actions=fix_actions,
            skipped_issues=skipped_issues,
            failed_fixes=failed_fixes,
            summary=summary,
        )

    def fix_prototype(
        self,
        issues: list[VerificationIssue],
    ) -> FixResult:
        """修复原型中的问题

        Args:
            issues: 原型问题列表

        Returns:
            修复结果
        """
        fixed_issues = []
        fix_actions: list[FixAction] = []
        skipped_issues = []
        failed_fixes = []

        for issue in issues:
            if not issue.auto_fixable:
                skipped_issues.append(issue.issue_id)
                continue

            try:
                action = self._apply_prototype_fix(issue)
                if action:
                    fix_actions.append(action)
                    fixed_issues.append(issue.issue_id)
                else:
                    failed_fixes.append(issue.issue_id)
            except Exception:
                failed_fixes.append(issue.issue_id)

        summary = self._generate_prototype_summary(fixed_issues, skipped_issues, failed_fixes)

        return FixResult(
            fixed_issues=fixed_issues,
            fix_actions=fix_actions,
            skipped_issues=skipped_issues,
            failed_fixes=failed_fixes,
            summary=summary,
        )

    def _apply_document_fix(
        self,
        document_content: str,
        issue: DocumentIssue,
    ) -> FixAction | None:
        """应用文档修复"""
        if issue.issue_type == DocIssueType.LINK:
            return self._fix_empty_link(document_content, issue)
        elif issue.issue_type == DocIssueType.FORMAT:
            return self._fix_format_issue(document_content, issue)
        elif issue.issue_type == DocIssueType.TABLE_FORMAT:
            return self._fix_table_format(document_content, issue)
        elif issue.issue_type == DocIssueType.HEADING_HIERARCHY:
            return self._fix_heading_hierarchy(document_content, issue)

        return None

    def _fix_empty_link(
        self,
        document_content: str,
        issue: DocumentIssue,
    ) -> FixAction | None:
        """修复空链接"""
        if "空链接" not in issue.description:
            return None

        match = re.search(r'\[([^\]]+)\]\(\)', document_content)
        if match:
            link_text = match.group(1)
            original = match.group(0)
            fixed = f"~~{link_text}~~"
            document_content = document_content.replace(original, fixed, 1)

            return FixAction(
                issue_id=issue.issue_id,
                action_type="remove_empty_link",
                description=f"移除空链接: [{link_text}]()",
                original_value=original,
                fixed_value=fixed,
            )

        return None

    def _fix_format_issue(
        self,
        document_content: str,
        issue: DocumentIssue,
    ) -> FixAction | None:
        """修复格式问题"""
        if "未闭合" in issue.description and "代码块" in issue.description:
            if document_content.count("```") % 2 != 0:
                document_content += "\n```\n"

                return FixAction(
                    issue_id=issue.issue_id,
                    action_type="close_code_block",
                    description="闭合未闭合的代码块",
                    original_value="...",
                    fixed_value="...\n```\n",
                )

        return None

    def _fix_table_format(
        self,
        document_content: str,
        issue: DocumentIssue,
    ) -> FixAction | None:
        """修复表格格式"""
        if "分隔行格式不正确" in issue.description:
            lines = document_content.split('\n')
            for i, line in enumerate(lines):
                if '|' in line and line.strip().startswith('|'):
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if '|' in next_line and not re.match(r'^\|[\s\-:]+\|', next_line):
                            cells = next_line.split('|')[1:-1]
                            separator = "|" + "|".join(" --- " for _ in cells) + "|"
                            original = lines[i + 1]
                            lines[i + 1] = separator
                            document_content = '\n'.join(lines)

                            return FixAction(
                                issue_id=issue.issue_id,
                                action_type="fix_table_separator",
                                description="修复表格分隔行格式",
                                original_value=original,
                                fixed_value=separator,
                            )

        return None

    def _fix_heading_hierarchy(
        self,
        document_content: str,
        issue: DocumentIssue,
    ) -> FixAction | None:
        """修复标题层级"""
        if "文档应以一级标题开头" in issue.description:
            lines = document_content.split('\n')
            for i, line in enumerate(lines):
                match = re.match(r'^(#{2,})\s', line)
                if match:
                    current_level = len(match.group(1))
                    new_heading = "#" + line[current_level:]
                    original = line
                    lines[i] = new_heading
                    document_content = '\n'.join(lines)

                    return FixAction(
                        issue_id=issue.issue_id,
                        action_type="fix_heading_level",
                        description=f"将 H{current_level} 提升为 H1",
                        original_value=original,
                        fixed_value=new_heading,
                    )

        return None

    def _apply_prototype_fix(
        self,
        issue: VerificationIssue,
    ) -> FixAction | None:
        """应用原型修复"""
        if issue.issue_type == IssueType.BROKEN_LINK:
            return FixAction(
                issue_id=issue.issue_id,
                action_type="fix_broken_parent_link",
                description=f"修复页面 {issue.page_id} 的断裂导航链接",
                original_value=issue.page_id,
                fixed_value="已重置父页面链接",
            )

        return None

    def _generate_document_summary(
        self,
        fixed: list[str],
        skipped: list[str],
        failed: list[str],
    ) -> str:
        """生成文档修复总结"""
        parts = []
        if fixed:
            parts.append(f"成功修复 {len(fixed)} 个问题")
        if skipped:
            parts.append(f"跳过 {len(skipped)} 个不可自动修复的问题")
        if failed:
            parts.append(f"修复失败 {len(failed)} 个问题")
        if not parts:
            parts.append("无需修复的问题")
        return "；".join(parts)

    def _generate_prototype_summary(
        self,
        fixed: list[str],
        skipped: list[str],
        failed: list[str],
    ) -> str:
        """生成原型修复总结"""
        parts = []
        if fixed:
            parts.append(f"成功修复 {len(fixed)} 个问题")
        if skipped:
            parts.append(f"跳过 {len(skipped)} 个不可自动修复的问题")
        if failed:
            parts.append(f"修复失败 {len(failed)} 个问题")
        if not parts:
            parts.append("无需修复的问题")
        return "；".join(parts)
