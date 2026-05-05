"""文档校验核心逻辑

从格式规范、结构完整性和术语一致性三个维度检查生成的 PRD 文档。
"""

import re
import uuid

from pm_workstation.document.markdown_formatter import MarkdownFormatter
from pm_workstation.document.terminology_checker import (
    TerminologyConsistencyChecker,
    TerminologyIssue,
)
from pm_workstation.verification.document_models import (
    DocIssueSeverity,
    DocIssueType,
    DocumentIssue,
    DocumentVerificationReport,
    FormatCheckResult,
    StructureCheckResult,
)


class DocumentFormatChecker:
    """文档格式检查器

    检查 Markdown 文档的格式规范性，包括标题层级、表格格式、链接完整性等。
    """

    def check(self, document_content: str) -> FormatCheckResult:
        """执行格式检查

        Args:
            document_content: Markdown 文档内容

        Returns:
            格式检查结果
        """
        issues = []

        issues.extend(self._check_heading_hierarchy(document_content))
        issues.extend(self._check_table_format(document_content))
        issues.extend(self._check_links(document_content))
        issues.extend(self._check_code_blocks(document_content))
        issues.extend(self._check_line_length(document_content))

        headings = MarkdownFormatter.extract_headings(document_content)
        tables_count = self._count_tables(document_content)
        links_count = self._count_links(document_content)

        return FormatCheckResult(
            passed=len(issues) == 0,
            issues=issues,
            headings_checked=len(headings),
            tables_checked=tables_count,
            links_checked=links_count,
        )

    def _check_heading_hierarchy(self, content: str) -> list[DocumentIssue]:
        """检查标题层级是否合理"""
        issues = []
        headings = MarkdownFormatter.extract_headings(content)

        for i in range(1, len(headings)):
            prev_level = headings[i - 1]["level"]
            curr_level = headings[i]["level"]

            if curr_level > prev_level + 1:
                issues.append(DocumentIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    issue_type=DocIssueType.HEADING_HIERARCHY,
                    severity=DocIssueSeverity.MAJOR,
                    location=f"第{headings[i]['line']}行: {headings[i]['text']}",
                    description=f"标题层级跳跃：从 H{prev_level} 跳到 H{curr_level}",
                    suggestion=f"在 H{prev_level} 和 H{curr_level} 之间补充中间层级标题",
                    auto_fixable=False,
                ))

        if headings and headings[0]["level"] != 1:
            issues.append(DocumentIssue(
                issue_id=str(uuid.uuid4())[:8],
                issue_type=DocIssueType.HEADING_HIERARCHY,
                severity=DocIssueSeverity.MINOR,
                location=f"第{headings[0]['line']}行",
                description=f"文档应以一级标题开头，当前为 H{headings[0]['level']}",
                suggestion="将文档第一个标题设为一级标题",
                auto_fixable=True,
            ))

        return issues

    def _check_table_format(self, content: str) -> list[DocumentIssue]:
        """检查表格格式"""
        issues = []
        lines = content.split('\n')
        in_table = False
        table_start = 0
        table_lines = []

        for i, line in enumerate(lines, 1):
            if '|' in line and line.strip().startswith('|'):
                if not in_table:
                    table_start = i
                    in_table = True
                    table_lines = []
                table_lines.append(line)
            else:
                if in_table and table_lines:
                    table_issues = self._validate_table(table_lines, table_start)
                    issues.extend(table_issues)
                    table_lines = []
                    in_table = False

        if table_lines:
            table_issues = self._validate_table(table_lines, table_start)
            issues.extend(table_issues)

        return issues

    def _validate_table(self, lines: list[str], start_line: int) -> list[DocumentIssue]:
        """验证单个表格格式"""
        issues = []

        if len(lines) < 2:
            issues.append(DocumentIssue(
                issue_id=str(uuid.uuid4())[:8],
                issue_type=DocIssueType.TABLE_FORMAT,
                severity=DocIssueSeverity.MINOR,
                location=f"第{start_line}行",
                description="表格至少需要标题行和分隔行",
                suggestion="补充表格的标题行和分隔行",
                auto_fixable=False,
            ))
            return issues

        separator = lines[1].strip()
        if not re.match(r'^\|[\s\-:]+\|', separator):
            issues.append(DocumentIssue(
                issue_id=str(uuid.uuid4())[:8],
                issue_type=DocIssueType.TABLE_FORMAT,
                severity=DocIssueSeverity.MINOR,
                location=f"第{start_line + 1}行",
                description="表格分隔行格式不正确",
                suggestion="表格第二行应为分隔行，格式如 |---|---|",
                auto_fixable=True,
            ))

        col_counts = []
        for i, line in enumerate(lines):
            cells = [c.strip() for c in line.split('|')[1:-1]]
            col_counts.append(len(cells))

        if len(set(col_counts)) > 1:
            issues.append(DocumentIssue(
                issue_id=str(uuid.uuid4())[:8],
                issue_type=DocIssueType.TABLE_FORMAT,
                severity=DocIssueSeverity.MINOR,
                location=f"第{start_line}行",
                description="表格各行列数不一致",
                suggestion="确保表格每一行的列数相同",
                auto_fixable=False,
            ))

        return issues

    def _check_links(self, content: str) -> list[DocumentIssue]:
        """检查链接格式"""
        issues = []

        broken_links = re.findall(r'\[([^\]]+)\]\(([^\)]*)\)', content)
        for text, url in broken_links:
            if not url.strip():
                issues.append(DocumentIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    issue_type=DocIssueType.LINK,
                    severity=DocIssueSeverity.MINOR,
                    description=f"空链接: [{text}]()",
                    suggestion="删除空链接或补充有效 URL",
                    auto_fixable=True,
                ))
            elif url.startswith('#') and not self._has_anchor(content, url[1:]):
                issues.append(DocumentIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    issue_type=DocIssueType.LINK,
                    severity=DocIssueSeverity.MINOR,
                    description=f"锚点链接指向不存在的目标: [{text}]({url})",
                    suggestion="检查锚点名称是否与文档中标题匹配",
                    auto_fixable=False,
                ))

        return issues

    def _check_code_blocks(self, content: str) -> list[DocumentIssue]:
        """检查代码块格式"""
        issues = []

        code_block_starts = [m.start() for m in re.finditer(r'```', content)]
        if len(code_block_starts) % 2 != 0:
            issues.append(DocumentIssue(
                issue_id=str(uuid.uuid4())[:8],
                issue_type=DocIssueType.FORMAT,
                severity=DocIssueSeverity.MAJOR,
                description="存在未闭合的代码块",
                suggestion="确保每个代码块都有起始和结束的 ``` 标记",
                auto_fixable=False,
            ))

        return issues

    def _check_line_length(self, content: str) -> list[DocumentIssue]:
        """检查行长度"""
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            if len(line) > 120 and not line.startswith('|'):
                issues.append(DocumentIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    issue_type=DocIssueType.STYLE,
                    severity=DocIssueSeverity.INFO,
                    location=f"第{i}行",
                    description=f"行长度超过 120 字符（当前 {len(line)} 字符）",
                    suggestion="考虑将长行拆分为多行以提高可读性",
                    auto_fixable=False,
                ))

        return issues

    def _has_anchor(self, content: str, anchor: str) -> bool:
        """检查文档中是否存在指定的锚点"""
        headings = MarkdownFormatter.extract_headings(content)
        for heading in headings:
            expected_anchor = heading["text"].lower().replace(" ", "-")
            expected_anchor = re.sub(r'[^\w\-]', '', expected_anchor)
            if expected_anchor == anchor:
                return True
        return False

    def _count_tables(self, content: str) -> int:
        """统计表格数量"""
        count = 0
        in_table = False
        for line in content.split('\n'):
            if '|' in line and line.strip().startswith('|'):
                if not in_table:
                    count += 1
                    in_table = True
            else:
                in_table = False
        return count

    def _count_links(self, content: str) -> int:
        """统计链接数量"""
        return len(re.findall(r'\[[^\]]+\]\([^\)]*\)', content))


class DocumentStructureChecker:
    """文档结构完整性检查器

    检查 PRD 文档是否包含所有必需的章节。
    """

    DEFAULT_REQUIRED_SECTIONS = [
        "概述",
        "目标",
        "用户角色",
        "功能需求",
        "非功能需求",
    ]

    def __init__(self, required_sections: list[str] | None = None):
        self._required_sections = required_sections or self.DEFAULT_REQUIRED_SECTIONS

    def check(self, document_content: str) -> StructureCheckResult:
        """执行结构完整性检查

        Args:
            document_content: Markdown 文档内容

        Returns:
            结构完整性检查结果
        """
        headings = MarkdownFormatter.extract_headings(document_content)
        heading_texts = {h["text"].strip() for h in headings}

        found_sections = []
        missing_sections = []

        for section in self._required_sections:
            if self._section_exists(section, heading_texts):
                found_sections.append(section)
            else:
                missing_sections.append(section)

        issues = []
        for section in missing_sections:
            issues.append(DocumentIssue(
                issue_id=str(uuid.uuid4())[:8],
                issue_type=DocIssueType.MISSING_SECTION,
                severity=DocIssueSeverity.MAJOR,
                description=f"文档缺少必需章节: {section}",
                suggestion=f"补充 {section} 章节内容",
                auto_fixable=False,
            ))

        return StructureCheckResult(
            passed=len(missing_sections) == 0,
            issues=issues,
            required_sections=self._required_sections,
            missing_sections=missing_sections,
            found_sections=found_sections,
        )

    def _section_exists(self, section: str, heading_texts: set[str]) -> bool:
        """检查章节是否存在（支持模糊匹配）"""
        if section in heading_texts:
            return True

        for heading in heading_texts:
            # 要求 section 至少有 2 个字符，避免误匹配
            if len(section) >= 2 and section in heading:
                return True
            if len(heading) >= 2 and heading in section:
                return True

        return False


class DocumentVerifier:
    """文档校验器

    综合检查生成的 PRD 文档是否满足格式规范、结构完整性和术语一致性要求。
    """

    def __init__(
        self,
        required_sections: list[str] | None = None,
        glossary: dict[str, str] | None = None,
    ) -> None:
        self.format_checker = DocumentFormatChecker()
        self.structure_checker = DocumentStructureChecker(required_sections)
        self.terminology_checker = TerminologyConsistencyChecker(glossary)

    def verify(self, document_content: str) -> DocumentVerificationReport:
        """执行完整的文档校验

        Args:
            document_content: Markdown 文档内容

        Returns:
            文档校验报告
        """
        format_result = self.format_checker.check(document_content)
        structure_result = self.structure_checker.check(document_content)
        terminology_result = self.terminology_checker.check(document_content)

        terminology_issues = self._convert_terminology_issues(terminology_result)

        all_issues = []
        all_issues.extend(format_result.issues)
        all_issues.extend(structure_result.issues)
        all_issues.extend(terminology_issues)

        passed = not any(
            i.severity in (DocIssueSeverity.CRITICAL, DocIssueSeverity.MAJOR)
            for i in all_issues
        )

        summary = self._generate_summary(format_result, structure_result, terminology_result, all_issues)

        return DocumentVerificationReport(
            format_check=format_result,
            structure_check=structure_result,
            terminology_issues=terminology_issues,
            issues=all_issues,
            passed=passed,
            summary=summary,
        )

    def _convert_terminology_issues(
        self,
        result,
    ) -> list[DocumentIssue]:
        """将术语检查问题转换为文档问题格式"""
        issues = []
        for term_issue in result.issues:
            issues.append(DocumentIssue(
                issue_id=str(uuid.uuid4())[:8],
                issue_type=DocIssueType.TERMINOLOGY,
                severity=DocIssueSeverity.MINOR,
                description=f"术语使用不一致: {term_issue.term} 存在变体 {', '.join(term_issue.variants)}",
                suggestion=term_issue.suggestion,
                auto_fixable=False,
            ))
        return issues

    def _generate_summary(
        self,
        format_result: FormatCheckResult,
        structure_result: StructureCheckResult,
        terminology_result,
        issues: list[DocumentIssue],
    ) -> str:
        """生成校验总结"""
        parts = []

        format_status = "通过" if format_result.passed else "未通过"
        parts.append(f"格式检查: {format_status}")

        structure_status = "通过" if structure_result.passed else "未通过"
        parts.append(f"结构检查: {structure_status}")

        terminology_status = "通过" if terminology_result.passed else "未通过"
        parts.append(f"术语检查: {terminology_status} (检查了 {terminology_result.terms_checked} 个术语)")

        critical_count = sum(1 for i in issues if i.severity == DocIssueSeverity.CRITICAL)
        major_count = sum(1 for i in issues if i.severity == DocIssueSeverity.MAJOR)
        minor_count = sum(1 for i in issues if i.severity == DocIssueSeverity.MINOR)
        info_count = sum(1 for i in issues if i.severity == DocIssueSeverity.INFO)

        if critical_count > 0:
            parts.append(f"发现 {critical_count} 个阻断性问题")
        if major_count > 0:
            parts.append(f"发现 {major_count} 个重要问题")
        if minor_count > 0:
            parts.append(f"发现 {minor_count} 个次要问题")
        if info_count > 0:
            parts.append(f"发现 {info_count} 个提示信息")
        if not issues:
            parts.append("所有检查均通过")

        return "；".join(parts)
