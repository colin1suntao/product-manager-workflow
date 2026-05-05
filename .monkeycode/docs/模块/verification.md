# 校验模块 (verification)

## 概述

校验模块提供多维度的质量保障体系，对生成的原型和 PRD 文档进行全面检查，发现问题后支持自动修复，并生成结构化的综合校验报告。

## 模块结构

```
src/pm_workstation/verification/
├── __init__.py
├── prototype_verifier.py    # 原型校验（覆盖率、交互逻辑）
├── document_verifier.py     # 文档校验（格式、结构、术语）
├── consistency_checker.py   # 原型-文档一致性检查
├── autofixer.py             # 自动修复器
├── issue_reporter.py        # 问题报告生成器
├── verification_models.py   # 原型校验数据模型
└── document_models.py       # 文档校验数据模型
```

## 原型校验 (`prototype_verifier.py`)

### PageCoverageChecker

检查生成的原型页面是否覆盖了需求中要求的所有页面和元素。

```python
class PageCoverageChecker:
    def check(
        self,
        requirement: StructuredRequirement,
        prototype_structure: PageStructure,
    ) -> CoverageResult:
```

**检查维度**:
1. **页面覆盖**: 从需求中提取要求的页面列表（实体 CRUD 页、流程页），与实际生成的页面对比
2. **元素覆盖**: 检查实体的属性、流程步骤是否在原型中体现

**覆盖率计算**:
- `page_coverage_rate = pages_generated / total_pages_required`
- `element_coverage_rate = elements_generated / total_elements_required`

**页面提取规则**:
- 每个实体生成: 列表页 (`page-{entity}-list`)、详情页 (`page-{entity}-detail`)
- 如果实体有必填属性，生成表单页 (`page-{entity}-form`)
- 步骤数 >= 3 的流程生成专用页面 (`page-flow-{name}`)
- 始终包含首页 (`page-home`)

### InteractionVerifier

验证原型中的交互逻辑是否覆盖需求定义的用户流程和业务规则。

```python
class InteractionVerifier:
    def verify(
        self,
        requirement: StructuredRequirement,
        prototype_structure: PageStructure,
    ) -> InteractionCheckResult:
```

**交互提取**:
1. **实体操作**: 查看、搜索（所有实体）；创建、编辑、删除（有必填属性的实体）
2. **流程步骤**: 每个流程步骤作为一个交互
3. **业务规则**: 规则树中的条件节点作为交互

**验证方式**:
- 实体操作: 检查页面的 `entities` 和 `operations` 是否匹配
- 流程步骤: 检查页面的 `flow_steps` 是否包含步骤描述
- 业务规则: 检查页面的 `description` 或 `name` 是否包含规则文本

### PrototypeVerifier

综合校验器，整合覆盖率检查和交互验证。

```python
class PrototypeVerifier:
    def __init__(self):
        self.coverage_checker = PageCoverageChecker()
        self.interaction_verifier = InteractionVerifier()

    def verify(
        self,
        requirement: StructuredRequirement,
        prototype_structure: PageStructure,
    ) -> PrototypeVerificationReport:
```

**额外检查**:
- **导航完整性**: 检查页面的 `parent_id` 是否指向存在的页面

---

## 文档校验 (`document_verifier.py`)

### DocumentFormatChecker

检查 Markdown 文档的格式规范性。

```python
class DocumentFormatChecker:
    def check(self, document_content: str) -> FormatCheckResult:
```

**检查项**:

| 检查项 | 问题类型 | 严重度 | 说明 |
|-------|---------|--------|------|
| 标题层级跳跃 | `HEADING_HIERARCHY` | MAJOR | 如 H2 直接跳到 H4 |
| 首标题非 H1 | `HEADING_HIERARCHY` | MINOR | 文档应以一级标题开头 |
| 表格格式 | `TABLE_FORMAT` | MINOR | 分隔行格式、列数一致性 |
| 空链接 | `LINK` | MINOR | `[text]()` |
| 无效锚点 | `LINK` | MINOR | 锚点指向不存在的标题 |
| 未闭合代码块 | `FORMAT` | MAJOR | ``` 数量为奇数 |
| 行过长 | `STYLE` | INFO | 超过 120 字符（表格行除外） |

### DocumentStructureChecker

检查 PRD 文档是否包含所有必需章节。

```python
class DocumentStructureChecker:
    DEFAULT_REQUIRED_SECTIONS = [
        "概述",
        "目标",
        "用户角色",
        "功能需求",
        "非功能需求",
    ]

    def check(self, document_content: str) -> StructureCheckResult:
```

**匹配策略**: 模糊匹配，支持章节名包含或被包含的情况。

### DocumentVerifier

综合文档校验器，整合格式、结构和术语检查。

```python
class DocumentVerifier:
    def __init__(
        self,
        required_sections: list[str] | None = None,
        glossary: dict[str, str] | None = None,
    ):
        self.format_checker = DocumentFormatChecker()
        self.structure_checker = DocumentStructureChecker(required_sections)
        self.terminology_checker = TerminologyConsistencyChecker(glossary)

    def verify(self, document_content: str) -> DocumentVerificationReport:
```

---

## 一致性检查 (`consistency_checker.py`)

对比原型和文档之间的内容一致性。

```python
class ConsistencyChecker:
    def __init__(self, similarity_threshold: float = 0.6):
    
    def check(
        self,
        requirement: StructuredRequirement,
        prototype_structure: PageStructure,
        document_content: str,
    ) -> ConsistencyCheckResult:
```

### 检查维度

| 检查项 | 说明 | 严重度 |
|-------|------|--------|
| 实体覆盖一致性 | 实体在原型和文档中是否同时存在 | MAJOR / MINOR |
| 流程覆盖一致性 | 流程在原型和文档中是否同时存在 | MAJOR / MINOR |
| 术语使用一致性 | 术语是否在原型和文档中一致使用 | INFO |
| 页面-文档对齐 | 原型页面是否在文档中有对应描述 | INFO |

### 一致性检查逻辑

- **实体在文档中但不在原型中**: MAJOR（原型缺失实现）
- **实体在原型中但不在文档中**: MINOR（文档缺失描述）
- **术语在文档中使用但原型未使用**: INFO（建议统一）
- **页面在原型中但文档未提及**: INFO（建议补充）

---

## 自动修复 (`autofixer.py`)

根据校验发现的问题，自动执行可修复的修复操作。

```python
class AutoFixer:
    def fix_document(self, document_content: str, issues: list[DocumentIssue]) -> FixResult
    def fix_prototype(self, issues: list[VerificationIssue]) -> FixResult
```

### 文档修复

| 问题类型 | 修复动作 | 说明 |
|---------|---------|------|
| 空链接 (`LINK`) | `remove_empty_link` | 将 `[text]()` 替换为 `~~text~~` |
| 未闭合代码块 (`FORMAT`) | `close_code_block` | 在文档末尾追加 ` ``` ` |
| 表格分隔行格式错误 (`TABLE_FORMAT`) | `fix_table_separator` | 修复为 ` \| --- \| --- \| ` |
| 首标题非 H1 (`HEADING_HIERARCHY`) | `fix_heading_level` | 将 H2+ 提升为 H1 |

### 原型修复

| 问题类型 | 修复动作 | 说明 |
|---------|---------|------|
| 断裂导航链接 (`BROKEN_LINK`) | `fix_broken_parent_link` | 重置父页面链接 |

### FixResult

```python
class FixResult(BaseModel):
    fixed_issues: list[str]      # 已修复的问题ID
    fix_actions: list[FixAction] # 修复动作列表
    skipped_issues: list[str]    # 跳过的不可自动修复问题
    failed_fixes: list[str]      # 修复失败的问题
    summary: str                 # 修复总结
```

---

## 问题报告 (`issue_reporter.py`)

汇总所有校验和一致性问题，生成结构化的综合报告。

```python
class IssueReporter:
    def generate_report(
        self,
        requirement_id: str,
        prototype_report: Optional[PrototypeVerificationReport] = None,
        document_report: Optional[DocumentVerificationReport] = None,
        consistency_result: Optional[ConsistencyCheckResult] = None,
        fix_result: Optional[FixResult] = None,
    ) -> VerificationReport:
```

### VerificationReport (综合报告)

```python
class VerificationReport(BaseModel):
    report_id: str                # 报告ID (vr-{requirement_id}-{timestamp})
    generated_at: datetime
    requirement_id: str
    prototype_passed: bool        # 原型校验是否通过
    document_passed: bool         # 文档校验是否通过
    consistency_passed: bool      # 一致性校验是否通过
    issues: list[CategorizedIssue] # 所有问题
    summary: IssueSummary         # 问题统计
    auto_fix_result: Optional[FixResult]
    overall_passed: bool          # 总体是否通过
    summary_text: str             # 报告总结文本
```

### IssueSummary (统计)

```python
class IssueSummary(BaseModel):
    total_issues: int
    critical_count: int    # 阻断性问题
    major_count: int       # 重要问题
    minor_count: int       # 次要问题
    info_count: int        # 提示信息
    auto_fixed_count: int  # 已自动修复
    manual_review_count: int  # 需人工审查
```

### CategorizedIssue (分类问题)

```python
class CategorizedIssue(BaseModel):
    issue_id: str
    category: str          # "prototype", "document", "consistency"
    issue_type: str
    severity: str
    description: str
    suggestion: str
    location: str          # 问题位置
    auto_fixable: bool
    auto_fixed: bool
```

### Markdown 报告生成

```python
def generate_markdown_report(self, report: VerificationReport) -> str:
```

生成包含以下部分的 Markdown 报告：
1. 报告基本信息（ID、时间、需求ID、总体结果）
2. 校验维度状态表
3. 问题汇总统计
4. 按严重程度分类的问题列表
5. 总结

---

## 数据模型

### 原型校验模型 (`verification_models.py`)

| 模型 | 说明 |
|-----|------|
| `IssueSeverity` | 枚举: CRITICAL, MAJOR, MINOR, INFO |
| `IssueType` | 枚举: MISSING_PAGE, MISSING_ELEMENT, MISSING_INTERACTION, BROKEN_LINK, INCONSISTENT_STYLE, ACCESSIBILITY, RESPONSIVE, CONTENT |
| `VerificationIssue` | 单个问题: issue_id, issue_type, severity, page_id, element_id, description, suggestion, auto_fixable, auto_fix_applied |
| `CoverageResult` | 覆盖率: total_pages_required, pages_generated, page_coverage_rate, missing_pages, extra_pages, element_coverage_rate |
| `InteractionCheckResult` | 交互检查: total_interactions_required, interactions_verified, interaction_pass_rate, failed_interactions |
| `PrototypeVerificationReport` | 原型报告: coverage, interaction_check, issues, passed, summary |

### 文档校验模型 (`document_models.py`)

| 模型 | 说明 |
|-----|------|
| `DocIssueSeverity` | 枚举: CRITICAL, MAJOR, MINOR, INFO |
| `DocIssueType` | 枚举: FORMAT, HEADING_HIERARCHY, MISSING_SECTION, TERMINOLOGY, TABLE_FORMAT, LINK, CONTENT, STYLE |
| `DocumentIssue` | 单个问题: issue_id, issue_type, severity, location, description, suggestion, auto_fixable |
| `FormatCheckResult` | 格式检查: passed, issues, headings_checked, tables_checked, links_checked |
| `StructureCheckResult` | 结构检查: passed, issues, required_sections, missing_sections, found_sections |
| `DocumentVerificationReport` | 文档报告: format_check, structure_check, terminology_issues, issues, passed, summary |

---

## 校验通过判定

| 维度 | 通过条件 |
|-----|---------|
| 原型校验 | 无 CRITICAL 或 MAJOR 问题 |
| 文档校验 | 无 CRITICAL 或 MAJOR 问题 |
| 一致性校验 | 无 CRITICAL 或 MAJOR 问题 |
| 总体通过 | `manual_review_count == 0` 且 `critical_count == 0` 且 `major_count == 0` |

---

## 测试文件

| 测试文件 | 测试内容 |
|---------|---------|
| `tests/unit/test_verification.py` | 原型校验、文档校验、一致性检查 |
| `tests/unit/test_document_verification.py` | 文档格式、结构、术语校验 |
| `tests/unit/test_verification_fix.py` | 自动修复功能 |
