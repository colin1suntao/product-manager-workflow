"""原型-文档一致性检查器

对比原型（页面结构）和文档（PRD 内容），检查两者之间的一致性，
包括功能覆盖、术语使用、页面流程等维度。
"""

import re
import uuid
from collections import Counter

from pm_workstation.models.core import StructuredRequirement
from pm_workstation.prototype.page_structure import PageStructure
from pm_workstation.verification.document_models import DocIssueSeverity, DocIssueType, DocumentIssue


class ConsistencyIssue(DocumentIssue):
    """一致性检查问题（复用 DocumentIssue 结构，增加对比维度）"""
    prototype_side: str = ""
    document_side: str = ""


class ConsistencyCheckResult:
    """一致性检查结果"""
    passed: bool
    issues: list[ConsistencyIssue]
    summary: str

    def __init__(
        self,
        passed: bool = True,
        issues: list[ConsistencyIssue] | None = None,
        summary: str = "",
    ) -> None:
        self.passed = passed
        self.issues = issues or []
        self.summary = summary


class ConsistencyChecker:
    """原型-文档一致性检查器

    对比原型和文档之间的功能覆盖、术语使用、页面流程等一致性。
    """

    def __init__(self, similarity_threshold: float = 0.6) -> None:
        self._similarity_threshold = similarity_threshold

    def check(
        self,
        requirement: StructuredRequirement,
        prototype_structure: PageStructure,
        document_content: str,
    ) -> ConsistencyCheckResult:
        """执行一致性检查

        Args:
            requirement: 结构化需求
            prototype_structure: 原型页面结构
            document_content: PRD 文档内容

        Returns:
            一致性检查结果
        """
        issues = []

        issues.extend(self._check_entity_coverage(requirement, prototype_structure, document_content))
        issues.extend(self._check_flow_coverage(requirement, prototype_structure, document_content))
        issues.extend(self._check_terminology_consistency(prototype_structure, document_content))
        issues.extend(self._check_page_document_alignment(prototype_structure, document_content))

        passed = not any(
            i.severity in (DocIssueSeverity.CRITICAL, DocIssueSeverity.MAJOR)
            for i in issues
        )

        summary = self._generate_summary(issues)

        return ConsistencyCheckResult(
            passed=passed,
            issues=issues,
            summary=summary,
        )

    def _check_entity_coverage(
        self,
        requirement: StructuredRequirement,
        prototype_structure: PageStructure,
        document_content: str,
    ) -> list[ConsistencyIssue]:
        """检查实体在原型和文档中的覆盖一致性"""
        issues = []
        entity_names = {e.name for e in requirement.entities}

        for entity_name in entity_names:
            in_prototype = self._entity_in_prototype(entity_name, prototype_structure)
            in_document = self._entity_in_document(entity_name, document_content)

            if not in_prototype and in_document:
                issues.append(ConsistencyIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    issue_type=DocIssueType.CONTENT,
                    severity=DocIssueSeverity.MAJOR,
                    description=f"实体 '{entity_name}' 在文档中提及但未在原型中体现",
                    suggestion="在原型中添加与该实体相关的页面或组件",
                    prototype_side="缺失",
                    document_side="已提及",
                ))
            elif in_prototype and not in_document:
                issues.append(ConsistencyIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    issue_type=DocIssueType.CONTENT,
                    severity=DocIssueSeverity.MINOR,
                    description=f"实体 '{entity_name}' 在原型中实现但未在文档中描述",
                    suggestion="在文档中补充该实体的功能说明",
                    prototype_side="已实现",
                    document_side="缺失",
                ))

        return issues

    def _check_flow_coverage(
        self,
        requirement: StructuredRequirement,
        prototype_structure: PageStructure,
        document_content: str,
    ) -> list[ConsistencyIssue]:
        """检查流程在原型和文档中的覆盖一致性"""
        issues = []

        for flow in requirement.flows:
            in_prototype = self._flow_in_prototype(flow, prototype_structure)
            in_document = flow.name in document_content or flow.name.replace("流程", "") in document_content

            if not in_prototype and in_document:
                issues.append(ConsistencyIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    issue_type=DocIssueType.CONTENT,
                    severity=DocIssueSeverity.MAJOR,
                    description=f"流程 '{flow.name}' 在文档中描述但未在原型中体现",
                    suggestion="在原型中补充该流程相关的页面和交互",
                    prototype_side="缺失",
                    document_side="已描述",
                ))
            elif in_prototype and not in_document:
                issues.append(ConsistencyIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    issue_type=DocIssueType.CONTENT,
                    severity=DocIssueSeverity.MINOR,
                    description=f"流程 '{flow.name}' 在原型中实现但未在文档中描述",
                    suggestion="在文档中补充该流程的说明",
                    prototype_side="已实现",
                    document_side="缺失",
                ))

        return issues

    def _check_terminology_consistency(
        self,
        prototype_structure: PageStructure,
        document_content: str,
    ) -> list[ConsistencyIssue]:
        """检查原型和文档之间术语使用的一致性"""
        issues = []

        prototype_text = self._extract_prototype_text(prototype_structure)

        common_terms = self._extract_common_terms(document_content, prototype_text)
        for term, doc_count, proto_count in common_terms:
            if doc_count > 0 and proto_count == 0:
                issues.append(ConsistencyIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    issue_type=DocIssueType.TERMINOLOGY,
                    severity=DocIssueSeverity.INFO,
                    description=f"术语 '{term}' 在文档中使用但未在原型中出现",
                    suggestion="考虑在原型界面中使用与文档一致的术语",
                    prototype_side="未使用",
                    document_side=f"使用 {doc_count} 次",
                ))

        return issues

    def _check_page_document_alignment(
        self,
        prototype_structure: PageStructure,
        document_content: str,
    ) -> list[ConsistencyIssue]:
        """检查页面和文档章节的对齐情况"""
        issues = []

        for page in prototype_structure.pages:
            if page.page_type != "page":
                continue

            page_keywords = self._extract_page_keywords(page)
            found_in_doc = any(
                keyword in document_content for keyword in page_keywords if len(keyword) >= 2
            )

            if not found_in_doc and page.name:
                issues.append(ConsistencyIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    issue_type=DocIssueType.CONTENT,
                    severity=DocIssueSeverity.INFO,
                    description=f"页面 '{page.name}' 在原型中存在，但文档中未找到相关描述",
                    suggestion="在文档中补充该页面的功能说明",
                    prototype_side=f"页面 '{page.name}'",
                    document_side="未提及",
                ))

        return issues

    def _entity_in_prototype(self, entity_name: str, structure: PageStructure) -> bool:
        """检查实体是否在原型中体现"""
        for page in structure.pages:
            if entity_name in page.entities:
                return True
            if entity_name.lower() in page.name.lower():
                return True
        return False

    def _entity_in_document(self, entity_name: str, document: str) -> bool:
        """检查实体是否在文档中提及"""
        return entity_name in document or entity_name.lower() in document.lower()

    def _flow_in_prototype(self, flow, structure: PageStructure) -> bool:
        """检查流程是否在原型中体现"""
        flow_name = flow.name
        flow_steps = [step.description for step in flow.steps]

        for page in structure.pages:
            if flow_name.lower() in page.name.lower():
                return True
            if flow_name.lower() in page.description.lower():
                return True
            for step_desc in page.flow_steps:
                if any(s in step_desc for s in flow_steps):
                    return True
        return False

    def _extract_prototype_text(self, structure: PageStructure) -> str:
        """从原型结构提取所有文本"""
        parts = []
        for page in structure.pages:
            parts.append(page.name)
            parts.append(page.description)
            parts.extend(page.operations)
            parts.extend(page.entities)
            parts.extend(page.flow_steps)
        return " ".join(parts)

    def _extract_common_terms(self, doc_text: str, proto_text: str) -> list[tuple[str, int, int]]:
        """提取文档和原型中的共同术语及其出现次数"""
        terms = []

        doc_words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', doc_text)
        proto_words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', proto_text)

        doc_set = set(doc_words)
        proto_set = set(proto_words)
        doc_counter = Counter(doc_words)
        proto_counter = Counter(proto_words)

        # 使用差集：文档中存在但原型中不存在的术语
        extra_terms = doc_set - proto_set
        for term in extra_terms:
            if len(term) < 2:
                continue
            terms.append((term, doc_counter[term], proto_counter[term]))

        return sorted(terms, key=lambda x: x[1] + x[2], reverse=True)

    def _extract_page_keywords(self, page) -> list[str]:
        """从页面提取关键词"""
        keywords = []
        if page.name:
            keywords.append(page.name)
        if page.description:
            keywords.append(page.description)
        keywords.extend(page.entities)
        keywords.extend(page.operations)
        keywords.extend(page.flow_steps)
        return [k for k in keywords if k]

    def _generate_summary(self, issues: list[ConsistencyIssue]) -> str:
        """生成一致性检查总结"""
        if not issues:
            return "原型和文档内容一致，未发现不一致问题"

        sev_counter = Counter(i.severity for i in issues)
        major_count = sev_counter.get(DocIssueSeverity.MAJOR, 0)
        minor_count = sev_counter.get(DocIssueSeverity.MINOR, 0)
        info_count = sev_counter.get(DocIssueSeverity.INFO, 0)

        parts = [f"发现 {len(issues)} 个一致性问题"]
        if major_count > 0:
            parts.append(f"{major_count} 个重要问题")
        if minor_count > 0:
            parts.append(f"{minor_count} 个次要问题")
        if info_count > 0:
            parts.append(f"{info_count} 个提示信息")

        return "，".join(parts)
