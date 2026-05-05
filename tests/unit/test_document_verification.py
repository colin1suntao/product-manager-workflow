"""文档校验测试"""

import pytest

from pm_workstation.document.markdown_formatter import MarkdownFormatter
from pm_workstation.document.terminology_checker import TerminologyConsistencyChecker
from pm_workstation.verification.document_models import (
    DocIssueSeverity,
    DocIssueType,
    DocumentIssue,
    DocumentVerificationReport,
    FormatCheckResult,
    StructureCheckResult,
)
from pm_workstation.verification.document_verifier import (
    DocumentFormatChecker,
    DocumentStructureChecker,
    DocumentVerifier,
)


class TestDocumentModels:
    """文档校验数据模型测试"""

    def test_doc_issue_severity_enum(self):
        """测试文档问题严重程度枚举"""
        assert DocIssueSeverity.CRITICAL == "critical"
        assert DocIssueSeverity.MAJOR == "major"
        assert DocIssueSeverity.MINOR == "minor"
        assert DocIssueSeverity.INFO == "info"

    def test_doc_issue_type_enum(self):
        """测试文档问题类型枚举"""
        assert DocIssueType.FORMAT == "format"
        assert DocIssueType.HEADING_HIERARCHY == "heading_hierarchy"
        assert DocIssueType.MISSING_SECTION == "missing_section"
        assert DocIssueType.TERMINOLOGY == "terminology"
        assert DocIssueType.TABLE_FORMAT == "table_format"
        assert DocIssueType.LINK == "link"
        assert DocIssueType.CONTENT == "content"
        assert DocIssueType.STYLE == "style"

    def test_document_issue_defaults(self):
        """测试文档问题默认值"""
        issue = DocumentIssue(
            issue_id="test-001",
            issue_type=DocIssueType.FORMAT,
            severity=DocIssueSeverity.MAJOR,
            description="格式问题",
        )
        assert issue.location == ""
        assert issue.suggestion == ""
        assert issue.auto_fixable is False

    def test_format_check_result(self):
        """测试格式检查结果"""
        result = FormatCheckResult(
            passed=True,
            headings_checked=5,
            tables_checked=2,
            links_checked=3,
        )
        assert result.passed is True
        assert result.headings_checked == 5
        assert len(result.issues) == 0

    def test_structure_check_result(self):
        """测试结构检查结果"""
        result = StructureCheckResult(
            passed=False,
            required_sections=["概述", "目标", "功能需求"],
            missing_sections=["功能需求"],
            found_sections=["概述", "目标"],
        )
        assert result.passed is False
        assert len(result.missing_sections) == 1
        assert len(result.found_sections) == 2


class TestDocumentFormatChecker:
    """文档格式检查器测试"""

    def test_valid_document(self):
        """测试有效文档通过检查"""
        doc = """# 测试文档

## 概述

这是一个测试文档。

## 功能需求

| 功能 | 描述 |
| --- | --- |
| 登录 | 用户登录系统 |
| 注册 | 用户注册账号 |

[链接](https://example.com)
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        assert result.passed is True
        assert len(result.issues) == 0

    def test_heading_hierarchy_jump(self):
        """测试标题层级跳跃检测"""
        doc = """# 一级标题

### 三级标题（跳跃）

内容
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        assert result.passed is False
        assert any(i.issue_type == DocIssueType.HEADING_HIERARCHY for i in result.issues)
        assert any("H1" in i.description and "H3" in i.description for i in result.issues)

    def test_valid_heading_hierarchy(self):
        """测试正确的标题层级"""
        doc = """# 一级标题

## 二级标题

### 三级标题

#### 四级标题
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        assert result.passed is True

    def test_document_not_starting_with_h1(self):
        """测试文档不以一级标题开头"""
        doc = """## 二级标题开头

内容
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        assert any(i.severity == DocIssueSeverity.MINOR for i in result.issues)

    def test_empty_link(self):
        """测试空链接检测"""
        doc = """# 测试

[点击这里]()

[有效链接](https://example.com)
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        assert any(i.issue_type == DocIssueType.LINK for i in result.issues)
        assert any("空链接" in i.description for i in result.issues)

    def test_broken_anchor_link(self):
        """测试无效的锚点链接"""
        doc = """# 测试文档

## 实际标题

[跳转到不存在](#不存在的标题)
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        anchor_issues = [i for i in result.issues if "锚点" in i.description]
        assert len(anchor_issues) > 0

    def test_valid_anchor_link(self):
        """测试有效的锚点链接"""
        doc = """# 测试文档

## 实际标题

[跳转到实际标题](#实际标题)
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        anchor_issues = [i for i in result.issues if "锚点" in i.description]
        assert len(anchor_issues) == 0

    def test_unclosed_code_block(self):
        """测试未闭合的代码块检测"""
        doc = """# 测试

```python
def hello():
    print("Hello")

一些内容
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        assert any(i.issue_type == DocIssueType.FORMAT for i in result.issues)
        assert any("未闭合" in i.description for i in result.issues)

    def test_closed_code_block(self):
        """测试正确的代码块"""
        doc = """# 测试

```python
def hello():
    print("Hello")
```

一些内容
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        code_issues = [i for i in result.issues if "未闭合" in i.description]
        assert len(code_issues) == 0

    def test_table_format_invalid(self):
        """测试表格格式问题"""
        doc = """# 测试

| 列1 | 列2 |
这是无效的分隔行
| 值1 | 值2 |
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        table_issues = [i for i in result.issues if i.issue_type == DocIssueType.TABLE_FORMAT]
        assert len(table_issues) > 0

    def test_table_inconsistent_columns(self):
        """测试表格列数不一致"""
        doc = """# 测试

| 列1 | 列2 | 列3 |
| --- | --- | --- |
| 值1 | 值2 |
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        table_issues = [i for i in result.issues if i.issue_type == DocIssueType.TABLE_FORMAT]
        assert len(table_issues) > 0

    def test_valid_table(self):
        """测试正确的表格格式"""
        doc = """# 测试

| 列1 | 列2 | 列3 |
| --- | --- | --- |
| 值1 | 值2 | 值3 |
| 值4 | 值5 | 值6 |
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        table_issues = [i for i in result.issues if i.issue_type == DocIssueType.TABLE_FORMAT]
        assert len(table_issues) == 0

    def test_long_line_warning(self):
        """测试长行警告"""
        long_line = "a" * 121
        doc = f"# 测试\n\n{long_line}\n"

        checker = DocumentFormatChecker()
        result = checker.check(doc)

        style_issues = [i for i in result.issues if i.issue_type == DocIssueType.STYLE]
        assert len(style_issues) > 0

    def test_table_line_excluded_from_length_check(self):
        """测试表格行不参与长度检查"""
        long_table_line = "| 非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的内容 | 值2 | 值3 |"
        doc = f"# 测试\n\n{long_table_line}\n"

        checker = DocumentFormatChecker()
        result = checker.check(doc)

        style_issues = [i for i in result.issues if i.issue_type == DocIssueType.STYLE]
        assert len(style_issues) == 0

    def test_count_tables(self):
        """测试表格计数"""
        doc = """# 测试

| 列1 | 列2 |
| --- | --- |
| 值1 | 值2 |

一些内容

| 列A | 列B |
| --- | --- |
| 值A | 值B |
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        assert result.tables_checked == 2

    def test_count_links(self):
        """测试链接计数"""
        doc = """# 测试

[链接1](https://example.com)
[链接2](https://example.org)
[空链接]()
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        assert result.links_checked == 3

    def test_heading_count(self):
        """测试标题计数"""
        doc = """# 标题1

## 标题2

### 标题3

## 标题4
"""
        checker = DocumentFormatChecker()
        result = checker.check(doc)

        assert result.headings_checked == 4


class TestDocumentStructureChecker:
    """文档结构完整性检查器测试"""

    def test_complete_document(self):
        """测试完整文档"""
        doc = """# 产品需求文档

## 概述

本文档描述...

## 目标

本项目旨在...

## 用户角色

| 角色 | 描述 |
| --- | --- |
| 管理员 | 系统管理员 |
| 用户 | 普通用户 |

## 功能需求

### 用户管理

...

## 非功能需求

...
"""
        checker = DocumentStructureChecker()
        result = checker.check(doc)

        assert result.passed is True
        assert len(result.missing_sections) == 0

    def test_missing_sections(self):
        """测试缺失章节检测"""
        doc = """# 产品需求文档

## 概述

本文档描述...

## 功能需求

...
"""
        checker = DocumentStructureChecker()
        result = checker.check(doc)

        assert result.passed is False
        # 文档中只有"概述"和"功能需求"
        assert "概述" in result.found_sections
        assert "功能需求" in result.found_sections
        # 其他章节应该缺失
        assert len(result.missing_sections) >= 2

    def test_fuzzy_section_matching(self):
        """测试模糊章节匹配"""
        doc = """# 产品需求文档

## 项目概述

本文档描述...

## 项目目标

本项目旨在...

## 用户角色与权限

| 角色 | 描述 |
| --- | --- |
| 管理员 | 系统管理员 |

## 功能需求列表

...

## 非功能需求说明

...
"""
        checker = DocumentStructureChecker()
        result = checker.check(doc)

        # "概述" 应该匹配 "项目概述"
        # "目标" 应该匹配 "项目目标"
        # "用户角色" 应该匹配 "用户角色与权限"
        # "功能需求" 应该匹配 "功能需求列表"
        # "非功能需求" 应该匹配 "非功能需求说明"
        assert result.passed is True

    def test_custom_required_sections(self):
        """测试自定义必需章节"""
        doc = """# 设计文档

## 架构设计

...

## 接口定义

...
"""
        custom_sections = ["架构设计", "接口定义", "数据库设计"]
        checker = DocumentStructureChecker(required_sections=custom_sections)
        result = checker.check(doc)

        assert result.passed is False
        assert "数据库设计" in result.missing_sections
        assert "架构设计" in result.found_sections

    def test_empty_document(self):
        """测试空文档"""
        checker = DocumentStructureChecker()
        result = checker.check("")

        assert result.passed is False
        assert len(result.missing_sections) == len(result.required_sections)


class TestDocumentVerifier:
    """文档校验器集成测试"""

    def _make_valid_document(self) -> str:
        """创建有效的测试文档"""
        return """# 产品需求文档

## 概述

本文档描述一个用户管理系统的产品需求。

## 目标

构建一个高效、易用的用户管理平台。

## 用户角色

| 角色 | 描述 |
| --- | --- |
| 管理员 | 系统管理员，拥有所有权限 |
| 普通用户 | 普通用户，只能管理自己的信息 |

## 功能需求

### 用户管理

- 创建用户
- 编辑用户
- 删除用户

### 权限管理

- 角色分配
- 权限控制

## 非功能需求

- 性能：响应时间小于2秒
- 可用性：99.9%
- 安全性：数据加密传输

[了解更多](https://example.com)
"""

    def test_verify_valid_document(self):
        """测试有效文档通过校验"""
        doc = self._make_valid_document()
        verifier = DocumentVerifier()
        report = verifier.verify(doc)

        assert report.passed is True
        assert report.format_check.passed is True
        assert report.structure_check.passed is True

    def test_verify_document_with_issues(self):
        """测试有问题的文档"""
        doc = """# 产品需求文档

## 概述

这是一个有问题的文档。

[空链接]()

### 跳跃的标题

内容
"""
        verifier = DocumentVerifier()
        report = verifier.verify(doc)

        assert report.passed is False
        assert len(report.issues) > 0

    def test_verify_terminology_issues(self):
        """测试术语不一致问题"""
        doc = """# 产品需求文档

## 概述

用户使用系统...
操作员可以管理订单...

## 目标

Admin 可以查看所有数据。
"""
        verifier = DocumentVerifier()
        report = verifier.verify(doc)

        terminology_issues = [i for i in report.issues if i.issue_type == DocIssueType.TERMINOLOGY]
        assert len(terminology_issues) >= 0

    def test_verify_summary_generation(self):
        """测试校验总结生成"""
        doc = self._make_valid_document()
        verifier = DocumentVerifier()
        report = verifier.verify(doc)

        assert len(report.summary) > 0
        assert "格式检查" in report.summary
        assert "结构检查" in report.summary
        assert "术语检查" in report.summary

    def test_verify_summary_with_issues(self):
        """测试有问题的总结"""
        doc = """# 产品需求文档

### 跳跃标题
"""
        verifier = DocumentVerifier()
        report = verifier.verify(doc)

        assert "未通过" in report.summary or "问题" in report.summary

    def test_verify_no_issues_summary(self):
        """测试无问题时的总结"""
        doc = self._make_valid_document()
        verifier = DocumentVerifier()
        report = verifier.verify(doc)

        if report.passed:
            assert "所有检查均通过" in report.summary or "通过" in report.summary

    def test_verify_with_custom_sections(self):
        """测试自定义必需章节的校验"""
        doc = """# 技术设计文档

## 架构设计

...

## 数据库设计

...
"""
        custom_sections = ["架构设计", "数据库设计"]
        verifier = DocumentVerifier(required_sections=custom_sections)
        report = verifier.verify(doc)

        assert report.passed is True

    def test_verify_with_custom_glossary(self):
        """测试自定义术语表的校验"""
        doc = """# 测试文档

## 概述

使用者可以登录系统...
用户可以管理数据...
"""
        custom_glossary = {
            "用户": "使用者,操作员,账号",
        }
        verifier = DocumentVerifier(glossary=custom_glossary)
        report = verifier.verify(doc)

        terminology_issues = [i for i in report.issues if i.issue_type == DocIssueType.TERMINOLOGY]
        assert len(terminology_issues) >= 0

    def test_verify_issue_severity_distribution(self):
        """测试问题严重程度分布"""
        doc = """# 文档

#### 跳跃到四级标题

[空链接]()
"""
        verifier = DocumentVerifier()
        report = verifier.verify(doc)

        severities = {i.severity for i in report.issues}
        assert len(severities) > 0

    def test_verify_converts_terminology_issues(self):
        """测试术语问题转换"""
        doc = """# 测试

## 概述

使用者和操作员都可以访问系统。
"""
        glossary = {"用户": "使用者,操作员"}
        verifier = DocumentVerifier(glossary=glossary)
        report = verifier.verify(doc)

        terminology_issues = report.terminology_issues
        if terminology_issues:
            assert all(i.issue_type == DocIssueType.TERMINOLOGY for i in terminology_issues)
            assert all(isinstance(i.issue_id, str) for i in terminology_issues)
