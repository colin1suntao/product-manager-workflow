"""原型校验核心逻辑

从结构化需求和生成的原型中检查页面覆盖率、交互逻辑完整性。
"""

import uuid

from pm_workstation.models.core import (
    Attribute,
    BusinessEntity,
    FlowStep,
    RuleTreeNode,
    StructuredRequirement,
    UserFlow,
)
from pm_workstation.prototype.page_structure import PageNode, PageStructure
from pm_workstation.verification.verification_models import (
    CoverageResult,
    InteractionCheckResult,
    IssueSeverity,
    IssueType,
    PrototypeVerificationReport,
    VerificationIssue,
)


class PageCoverageChecker:
    """页面覆盖率检查器

    检查生成的原型页面是否覆盖了需求中要求的所有页面和元素。
    """

    def check(
        self,
        requirement: StructuredRequirement,
        prototype_structure: PageStructure,
    ) -> CoverageResult:
        """执行页面覆盖率检查

        Args:
            requirement: 结构化需求
            prototype_structure: 生成的原型页面结构

        Returns:
            覆盖率检查结果
        """
        required_pages = self._extract_required_pages(requirement)
        generated_page_ids = {p.id for p in prototype_structure.pages}
        generated_page_ids.add(prototype_structure.root.id)

        missing_pages = []
        for req_page in required_pages:
            if req_page not in generated_page_ids:
                missing_pages.append(req_page)

        extra_pages = []
        required_page_set = set(required_pages)
        for gen_page_id in generated_page_ids:
            if gen_page_id not in required_page_set:
                extra_pages.append(gen_page_id)

        total_pages = len(required_pages)
        pages_generated = total_pages - len(missing_pages)
        page_coverage_rate = pages_generated / total_pages if total_pages > 0 else 1.0

        element_result = self._check_element_coverage(requirement, prototype_structure)

        return CoverageResult(
            total_pages_required=total_pages,
            pages_generated=pages_generated,
            page_coverage_rate=round(page_coverage_rate, 2),
            missing_pages=missing_pages,
            extra_pages=extra_pages,
            total_elements_required=element_result["total"],
            elements_generated=element_result["generated"],
            element_coverage_rate=element_result["rate"],
            missing_elements=element_result["missing"],
        )

    def _extract_required_pages(self, requirement: StructuredRequirement) -> list[str]:
        """从需求中提取要求的页面ID列表"""
        required_pages = ["page-home"]

        for entity in requirement.entities:
            required_pages.append(f"page-{entity.name.lower()}-list")
            required_pages.append(f"page-{entity.name.lower()}-detail")
            required_attrs = [a for a in entity.attributes if a.required]
            if required_attrs:
                required_pages.append(f"page-{entity.name.lower()}-form")

        for flow in requirement.flows:
            if len(flow.steps) >= 3:
                flow_id = f"page-flow-{flow.name.lower().replace(' ', '-')}"
                required_pages.append(flow_id)

        return list(set(required_pages))

    def _check_element_coverage(
        self,
        requirement: StructuredRequirement,
        prototype_structure: PageStructure,
    ) -> dict:
        """检查页面元素覆盖率

        Returns:
            {"total": int, "generated": int, "rate": float, "missing": list[str]}
        """
        required_elements = []
        for entity in requirement.entities:
            for attr in entity.attributes:
                required_elements.append(f"{entity.name}.{attr.name}")

        for flow in requirement.flows:
            for step in flow.steps:
                required_elements.append(f"flow:{flow.name}.step:{step.description}")

        generated_elements = []
        for page in prototype_structure.pages:
            for entity_name in page.entities:
                entity = next(
                    (e for e in requirement.entities if e.name == entity_name),
                    None,
                )
                if entity:
                    for attr in entity.attributes:
                        generated_elements.append(f"{entity.name}.{attr.name}")
            for step_desc in page.flow_steps:
                generated_elements.append(f"flow:{page.name}.step:{step_desc}")

        generated_set = set(generated_elements)
        missing = [e for e in required_elements if e not in generated_set]
        total = len(required_elements)
        generated_count = total - len(missing)
        rate = generated_count / total if total > 0 else 1.0

        return {
            "total": total,
            "generated": generated_count,
            "rate": round(rate, 2),
            "missing": missing,
        }


class InteractionVerifier:
    """交互逻辑验证器

    验证原型中的交互逻辑是否覆盖了需求中定义的用户流程和业务规则。
    """

    def verify(
        self,
        requirement: StructuredRequirement,
        prototype_structure: PageStructure,
    ) -> InteractionCheckResult:
        """执行交互逻辑验证

        Args:
            requirement: 结构化需求
            prototype_structure: 生成的原型页面结构

        Returns:
            交互逻辑验证结果
        """
        required_interactions = self._extract_required_interactions(requirement)
        failed_interactions = []
        verified_count = 0
        unverified = []

        for interaction in required_interactions:
            result = self._verify_single_interaction(interaction, prototype_structure)
            if result is None:
                verified_count += 1
            else:
                failed_interactions.append(result)
                unverified.append(interaction["id"])

        total = len(required_interactions)
        pass_rate = verified_count / total if total > 0 else 1.0

        return InteractionCheckResult(
            total_interactions_required=total,
            interactions_verified=verified_count,
            interaction_pass_rate=round(pass_rate, 2),
            failed_interactions=failed_interactions,
            unverified_interactions=unverified,
        )

    def _extract_required_interactions(
        self,
        requirement: StructuredRequirement,
    ) -> list[dict]:
        """从需求中提取要求的交互列表"""
        interactions = []

        for entity in requirement.entities:
            operations = self._get_entity_operations(entity)
            for op in operations:
                interactions.append({
                    "id": f"interaction-{entity.name.lower()}-{op.lower().replace(' ', '-')}",
                    "type": "entity_operation",
                    "entity": entity.name,
                    "operation": op,
                    "description": f"用户{op}{entity.name}",
                })

        for flow in requirement.flows:
            for i, step in enumerate(flow.steps):
                interactions.append({
                    "id": f"interaction-flow-{flow.name.lower().replace(' ', '-')}-step-{i + 1}",
                    "type": "flow_step",
                    "flow": flow.name,
                    "step": step,
                    "description": f"流程步骤: {step.description}",
                })

        self._extract_rule_interactions(requirement.rules, interactions)

        return interactions

    def _get_entity_operations(self, entity: BusinessEntity) -> list[str]:
        """获取实体的操作列表"""
        operations = ["查看", "搜索"]
        required_attrs = [a for a in entity.attributes if a.required]
        if required_attrs:
            operations.extend(["创建", "编辑", "删除"])
        return operations

    def _extract_rule_interactions(
        self,
        node: RuleTreeNode,
        interactions: list[dict],
        path: str = "",
    ) -> None:
        """从规则树递归提取交互要求"""
        current_path = f"{path}/{node.rule_text[:20]}" if path else node.rule_text[:20]

        if node.conditions:
            interactions.append({
                "id": f"interaction-rule-{hash(current_path) % 10000:04d}",
                "type": "rule_condition",
                "rule": current_path,
                "description": f"业务规则校验: {node.rule_text}",
            })

        for child in node.children:
            self._extract_rule_interactions(child, interactions, current_path)

    def _verify_single_interaction(
        self,
        interaction: dict,
        prototype_structure: PageStructure,
    ) -> VerificationIssue | None:
        """验证单个交互是否在原型中实现

        Returns:
            None 表示验证通过，否则返回 VerificationIssue
        """
        interaction_type = interaction["type"]

        if interaction_type == "entity_operation":
            return self._verify_entity_operation(interaction, prototype_structure)
        elif interaction_type == "flow_step":
            return self._verify_flow_step(interaction, prototype_structure)
        elif interaction_type == "rule_condition":
            return self._verify_rule_condition(interaction, prototype_structure)

        return None

    def _verify_entity_operation(
        self,
        interaction: dict,
        prototype_structure: PageStructure,
    ) -> VerificationIssue | None:
        """验证实体操作是否在原型中实现"""
        entity_name = interaction["entity"]
        operation = interaction["operation"]

        for page in prototype_structure.pages:
            if entity_name in page.entities and operation in page.operations:
                return None

        return VerificationIssue(
            issue_id=str(uuid.uuid4())[:8],
            issue_type=IssueType.MISSING_INTERACTION,
            severity=IssueSeverity.MAJOR,
            page_id=f"page-{entity_name.lower()}-list",
            description=f"原型中缺失实体操作: {operation} {entity_name}",
            suggestion=f"在 {entity_name} 相关页面中添加 {operation} 交互",
            auto_fixable=False,
        )

    def _verify_flow_step(
        self,
        interaction: dict,
        prototype_structure: PageStructure,
    ) -> VerificationIssue | None:
        """验证流程步骤是否在原型中实现"""
        step = interaction["step"]
        flow_name = interaction["flow"]

        for page in prototype_structure.pages:
            if step.description in page.flow_steps:
                return None

        return VerificationIssue(
            issue_id=str(uuid.uuid4())[:8],
            issue_type=IssueType.MISSING_INTERACTION,
            severity=IssueSeverity.MAJOR,
            description=f"原型中缺失流程步骤: {step.description} (流程: {flow_name})",
            suggestion=f"在原型中添加流程步骤对应的交互: {step.description}",
            auto_fixable=False,
        )

    def _verify_rule_condition(
        self,
        interaction: dict,
        prototype_structure: PageStructure,
    ) -> VerificationIssue | None:
        """验证业务规则是否在原型中体现"""
        rule_desc = interaction["rule"]

        for page in prototype_structure.pages:
            if rule_desc in page.description or rule_desc in page.name:
                return None

        return VerificationIssue(
            issue_id=str(uuid.uuid4())[:8],
            issue_type=IssueType.MISSING_ELEMENT,
            severity=IssueSeverity.MINOR,
            description=f"原型中未体现业务规则: {rule_desc}",
            suggestion="在相关页面中添加业务规则说明或校验提示",
            auto_fixable=False,
        )


class PrototypeVerifier:
    """原型校验器

    综合检查生成的原型是否满足需求要求，包括页面覆盖率、交互逻辑、
    样式一致性、页面导航完整性等。
    """

    def __init__(self) -> None:
        self.coverage_checker = PageCoverageChecker()
        self.interaction_verifier = InteractionVerifier()

    def verify(
        self,
        requirement: StructuredRequirement,
        prototype_structure: PageStructure,
    ) -> PrototypeVerificationReport:
        """执行完整的原型校验

        Args:
            requirement: 结构化需求
            prototype_structure: 生成的原型页面结构

        Returns:
            原型校验报告
        """
        coverage = self.coverage_checker.check(requirement, prototype_structure)
        interaction_check = self.interaction_verifier.verify(requirement, prototype_structure)

        issues = []
        issues.extend(self._generate_coverage_issues(coverage))
        issues.extend(interaction_check.failed_interactions)
        issues.extend(self._check_navigation_integrity(prototype_structure))

        auto_fixed = [i for i in issues if i.auto_fix_applied]
        manual_review = [i for i in issues if not i.auto_fix_applied and i.severity in (
            IssueSeverity.CRITICAL,
            IssueSeverity.MAJOR,
        )]

        passed = not any(
            i.severity in (IssueSeverity.CRITICAL, IssueSeverity.MAJOR)
            for i in issues
        )

        summary = self._generate_summary(coverage, interaction_check, issues)

        return PrototypeVerificationReport(
            coverage=coverage,
            interaction_check=interaction_check,
            issues=issues,
            passed=passed,
            summary=summary,
        )

    def _generate_coverage_issues(self, coverage: CoverageResult) -> list[VerificationIssue]:
        """根据覆盖率结果生成问题列表"""
        issues = []

        for page_id in coverage.missing_pages:
            issues.append(VerificationIssue(
                issue_id=str(uuid.uuid4())[:8],
                issue_type=IssueType.MISSING_PAGE,
                severity=IssueSeverity.CRITICAL,
                page_id=page_id,
                description=f"需求要求的页面未生成: {page_id}",
                suggestion=f"为需求生成缺失的页面: {page_id}",
                auto_fixable=False,
            ))

        for element_id in coverage.missing_elements:
            severity = IssueSeverity.MAJOR if "." in element_id else IssueSeverity.MINOR
            issues.append(VerificationIssue(
                issue_id=str(uuid.uuid4())[:8],
                issue_type=IssueType.MISSING_ELEMENT,
                severity=severity,
                description=f"需求要求的页面元素未生成: {element_id}",
                suggestion=f"在对应页面中添加元素: {element_id}",
                auto_fixable=False,
            ))

        return issues

    def _check_navigation_integrity(
        self,
        prototype_structure: PageStructure,
    ) -> list[VerificationIssue]:
        """检查页面导航完整性"""
        issues = []
        page_ids = {p.id for p in prototype_structure.pages}
        page_ids.add(prototype_structure.root.id)

        for page in prototype_structure.pages:
            if page.parent_id and page.parent_id not in page_ids:
                issues.append(VerificationIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    issue_type=IssueType.BROKEN_LINK,
                    severity=IssueSeverity.MAJOR,
                    page_id=page.id,
                    description=f"页面 {page.id} 的父页面 {page.parent_id} 不存在",
                    suggestion="修复页面层级关系或创建缺失的父页面",
                    auto_fixable=True,
                    auto_fix_applied=True,
                ))

        return issues

    def _generate_summary(
        self,
        coverage: CoverageResult,
        interaction_check: InteractionCheckResult,
        issues: list[VerificationIssue],
    ) -> str:
        """生成校验总结"""
        parts = []

        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        major_count = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)
        minor_count = sum(1 for i in issues if i.severity == IssueSeverity.MINOR)

        parts.append(
            f"页面覆盖率: {coverage.page_coverage_rate:.0%} "
            f"({coverage.pages_generated}/{coverage.total_pages_required})"
        )
        parts.append(
            f"元素覆盖率: {coverage.element_coverage_rate:.0%} "
            f"({coverage.elements_generated}/{coverage.total_elements_required})"
        )
        parts.append(
            f"交互通过率: {interaction_check.interaction_pass_rate:.0%} "
            f"({interaction_check.interactions_verified}/{interaction_check.total_interactions_required})"
        )

        if critical_count > 0:
            parts.append(f"发现 {critical_count} 个阻断性问题")
        if major_count > 0:
            parts.append(f"发现 {major_count} 个重要问题")
        if minor_count > 0:
            parts.append(f"发现 {minor_count} 个次要问题")
        if not issues:
            parts.append("所有检查均通过")

        return "；".join(parts)
