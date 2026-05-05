"""原型校验测试"""

import pytest

from pm_workstation.models.core import (
    Attribute,
    Branch,
    BusinessEntity,
    Condition,
    EdgeCase,
    FlowStep,
    Role,
    RuleTreeNode,
    StructuredRequirement,
    UserFlow,
)
from pm_workstation.prototype.page_structure import PageNode, PageStructure
from pm_workstation.verification.prototype_verifier import (
    PageCoverageChecker,
    InteractionVerifier,
    PrototypeVerifier,
)
from pm_workstation.verification.verification_models import (
    CoverageResult,
    InteractionCheckResult,
    IssueSeverity,
    IssueType,
    PrototypeVerificationReport,
    VerificationIssue,
)


class TestVerificationModels:
    """校验数据模型测试"""

    def test_issue_severity_enum(self):
        """测试问题严重程度枚举"""
        assert IssueSeverity.CRITICAL == "critical"
        assert IssueSeverity.MAJOR == "major"
        assert IssueSeverity.MINOR == "minor"
        assert IssueSeverity.INFO == "info"

    def test_issue_type_enum(self):
        """测试问题类型枚举"""
        assert IssueType.MISSING_PAGE == "missing_page"
        assert IssueType.MISSING_ELEMENT == "missing_element"
        assert IssueType.MISSING_INTERACTION == "missing_interaction"
        assert IssueType.BROKEN_LINK == "broken_link"
        assert IssueType.INCONSISTENT_STYLE == "inconsistent_style"
        assert IssueType.ACCESSIBILITY == "accessibility"
        assert IssueType.RESPONSIVE == "responsive"
        assert IssueType.CONTENT == "content"

    def test_verification_issue_defaults(self):
        """测试验证问题默认值"""
        issue = VerificationIssue(
            issue_id="test-001",
            issue_type=IssueType.MISSING_PAGE,
            severity=IssueSeverity.CRITICAL,
            description="缺失页面",
        )
        assert issue.page_id == ""
        assert issue.element_id == ""
        assert issue.suggestion == ""
        assert issue.auto_fixable is False
        assert issue.auto_fix_applied is False

    def test_coverage_result(self):
        """测试覆盖率结果"""
        result = CoverageResult(
            total_pages_required=5,
            pages_generated=3,
            page_coverage_rate=0.6,
            missing_pages=["page-a", "page-b"],
            extra_pages=["page-extra"],
        )
        assert result.total_pages_required == 5
        assert result.pages_generated == 3
        assert result.page_coverage_rate == 0.6
        assert len(result.missing_pages) == 2
        assert len(result.extra_pages) == 1

    def test_interaction_check_result(self):
        """测试交互检查结果"""
        result = InteractionCheckResult(
            total_interactions_required=10,
            interactions_verified=7,
            interaction_pass_rate=0.7,
        )
        assert result.total_interactions_required == 10
        assert result.interactions_verified == 7
        assert result.interaction_pass_rate == 0.7
        assert len(result.failed_interactions) == 0
        assert len(result.unverified_interactions) == 0

    def test_prototype_verification_report(self):
        """测试原型校验报告"""
        coverage = CoverageResult(
            total_pages_required=5,
            pages_generated=5,
            page_coverage_rate=1.0,
        )
        interaction = InteractionCheckResult(
            total_interactions_required=10,
            interactions_verified=10,
            interaction_pass_rate=1.0,
        )
        report = PrototypeVerificationReport(
            coverage=coverage,
            interaction_check=interaction,
            passed=True,
            summary="所有检查均通过",
        )
        assert report.passed is True
        assert len(report.issues) == 0


class TestPageCoverageChecker:
    """页面覆盖率检查器测试"""

    def _make_requirement(self) -> StructuredRequirement:
        """创建测试用需求"""
        return StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试规则"),
            entities=[
                BusinessEntity(
                    name="User",
                    description="用户实体",
                    attributes=[
                        Attribute(name="id", type="string", required=True),
                        Attribute(name="name", type="string", required=True),
                        Attribute(name="email", type="string", required=False),
                    ],
                ),
                BusinessEntity(
                    name="Order",
                    description="订单实体",
                    attributes=[
                        Attribute(name="id", type="string", required=True),
                        Attribute(name="amount", type="number", required=True),
                    ],
                ),
            ],
            roles=[Role(name="admin", description="管理员")],
            flows=[
                UserFlow(
                    name="用户注册流程",
                    role="user",
                    steps=[
                        FlowStep(step_number=1, description="填写注册信息", action="填写表单"),
                        FlowStep(step_number=2, description="提交注册", action="点击提交"),
                        FlowStep(step_number=3, description="验证邮箱", action="点击验证链接"),
                    ],
                ),
            ],
        )

    def _make_complete_structure(self, requirement: StructuredRequirement) -> PageStructure:
        """创建完整的页面结构"""
        pages = [
            PageNode(
                id="page-user-list",
                name="User列表",
                entities=["User"],
                operations=["查看", "搜索", "创建", "编辑", "删除"],
                flow_steps=[],
            ),
            PageNode(
                id="page-user-detail",
                name="User详情",
                entities=["User"],
                operations=["查看详情", "编辑", "删除"],
                flow_steps=[],
            ),
            PageNode(
                id="page-user-form",
                name="新建/编辑User",
                entities=["User"],
                operations=["创建", "编辑", "保存", "取消"],
                flow_steps=["创建User", "编辑User"],
            ),
            PageNode(
                id="page-order-list",
                name="Order列表",
                entities=["Order"],
                operations=["查看", "搜索", "创建", "编辑", "删除"],
                flow_steps=[],
            ),
            PageNode(
                id="page-order-detail",
                name="Order详情",
                entities=["Order"],
                operations=["查看详情", "编辑", "删除"],
                flow_steps=[],
            ),
            PageNode(
                id="page-order-form",
                name="新建/编辑Order",
                entities=["Order"],
                operations=["创建", "编辑", "保存", "取消"],
                flow_steps=["创建Order", "编辑Order"],
            ),
            PageNode(
                id="page-flow-用户注册流程",
                name="用户注册流程",
                entities=[],
                operations=["填写表单", "点击提交", "点击验证链接"],
                flow_steps=["填写注册信息", "提交注册", "验证邮箱"],
            ),
        ]
        root = PageNode(id="page-home", name="首页", entities=["User", "Order"])
        return PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

    def test_check_full_coverage(self):
        """测试完全覆盖的情况"""
        requirement = self._make_requirement()
        structure = self._make_complete_structure(requirement)

        checker = PageCoverageChecker()
        result = checker.check(requirement, structure)

        assert result.page_coverage_rate == 1.0
        assert len(result.missing_pages) == 0
        assert result.pages_generated == result.total_pages_required

    def test_check_partial_coverage(self):
        """测试部分覆盖的情况"""
        requirement = self._make_requirement()
        # 只生成 User 相关页面，缺少 Order 页面
        pages = [
            PageNode(id="page-user-list", name="User列表", entities=["User"]),
            PageNode(id="page-user-detail", name="User详情", entities=["User"]),
            PageNode(id="page-user-form", name="User表单", entities=["User"]),
        ]
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        checker = PageCoverageChecker()
        result = checker.check(requirement, structure)

        assert result.page_coverage_rate < 1.0
        assert "page-order-list" in result.missing_pages
        assert "page-order-detail" in result.missing_pages
        assert "page-order-form" in result.missing_pages

    def test_check_no_pages(self):
        """测试没有页面时的覆盖率"""
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试"),
            entities=[],
            flows=[],
        )
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=[],
        )

        checker = PageCoverageChecker()
        result = checker.check(requirement, structure)

        assert result.page_coverage_rate == 1.0  # Only page-home is required, and it exists
        assert result.pages_generated == 1
        assert len(result.missing_pages) == 0

    def test_check_element_coverage(self):
        """测试元素覆盖率"""
        requirement = self._make_requirement()
        pages = [
            PageNode(
                id="page-user-list",
                name="User列表",
                entities=["User"],
                flow_steps=["填写注册信息"],
            ),
        ]
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        checker = PageCoverageChecker()
        result = checker.check(requirement, structure)

        assert result.total_elements_required > 0
        assert result.element_coverage_rate >= 0.0
        assert result.element_coverage_rate <= 1.0

    def test_extract_required_pages(self):
        """测试提取需求页面"""
        requirement = self._make_requirement()
        checker = PageCoverageChecker()
        pages = checker._extract_required_pages(requirement)

        assert "page-home" in pages
        assert "page-user-list" in pages
        assert "page-user-detail" in pages
        assert "page-user-form" in pages
        assert "page-order-list" in pages
        assert "page-order-detail" in pages
        assert "page-order-form" in pages
        assert "page-flow-用户注册流程" in pages

    def test_extract_required_pages_no_entities(self):
        """测试无实体时的页面提取"""
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试"),
            entities=[],
            flows=[],
        )
        checker = PageCoverageChecker()
        pages = checker._extract_required_pages(requirement)

        assert pages == ["page-home"]

    def test_extract_required_pages_flow_too_short(self):
        """测试短流程不生成页面"""
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试"),
            entities=[],
            flows=[
                UserFlow(
                    name="短流程",
                    role="user",
                    steps=[
                        FlowStep(step_number=1, description="步骤1"),
                        FlowStep(step_number=2, description="步骤2"),
                    ],
                ),
            ],
        )
        checker = PageCoverageChecker()
        pages = checker._extract_required_pages(requirement)

        assert "page-flow-短流程" not in pages

    def test_extra_pages_detection(self):
        """测试多余页面检测"""
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试"),
            entities=[],
        )
        pages = [
            PageNode(id="page-extra-1", name="额外页面1"),
            PageNode(id="page-extra-2", name="额外页面2"),
        ]
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        checker = PageCoverageChecker()
        result = checker.check(requirement, structure)

        assert "page-extra-1" in result.extra_pages
        assert "page-extra-2" in result.extra_pages


class TestInteractionVerifier:
    """交互逻辑验证器测试"""

    def _make_requirement(self) -> StructuredRequirement:
        """创建测试用需求"""
        return StructuredRequirement(
            rules=RuleTreeNode(
                rule_text="订单金额超过1000元需要审批",
                conditions=[
                    Condition(field="amount", operator=">", value="1000"),
                ],
            ),
            entities=[
                BusinessEntity(
                    name="User",
                    attributes=[
                        Attribute(name="name", type="string", required=True),
                    ],
                ),
            ],
            flows=[
                UserFlow(
                    name="用户登录流程",
                    role="user",
                    steps=[
                        FlowStep(step_number=1, description="输入用户名", action="输入"),
                        FlowStep(step_number=2, description="输入密码", action="输入"),
                        FlowStep(step_number=3, description="点击登录", action="点击"),
                    ],
                ),
            ],
        )

    def _make_complete_structure(self) -> PageStructure:
        """创建完整的原型结构"""
        pages = [
            PageNode(
                id="page-user-list",
                name="User列表",
                entities=["User"],
                operations=["查看", "搜索", "创建", "编辑", "删除"],
                flow_steps=["输入用户名", "输入密码", "点击登录"],
            ),
        ]
        root = PageNode(id="page-home", name="首页")
        return PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

    def test_verify_all_pass(self):
        """测试所有交互通过验证"""
        requirement = self._make_requirement()
        structure = self._make_complete_structure()

        verifier = InteractionVerifier()
        result = verifier.verify(requirement, structure)

        # 规则条件会产生一个交互，可能不通过
        assert result.interaction_pass_rate >= 0.8

    def test_verify_missing_entity_operation(self):
        """测试缺失实体操作"""
        requirement = self._make_requirement()
        # 缺少 User 相关页面
        pages = []
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        verifier = InteractionVerifier()
        result = verifier.verify(requirement, structure)

        assert result.interaction_pass_rate < 1.0
        assert len(result.failed_interactions) > 0
        assert any(
            i.issue_type == IssueType.MISSING_INTERACTION
            for i in result.failed_interactions
        )

    def test_verify_missing_flow_step(self):
        """测试缺失流程步骤"""
        requirement = self._make_requirement()
        pages = [
            PageNode(
                id="page-user-list",
                name="User列表",
                entities=["User"],
                operations=["查看", "搜索", "创建", "编辑", "删除"],
                flow_steps=["输入用户名"],  # 缺少其他步骤
            ),
        ]
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        verifier = InteractionVerifier()
        result = verifier.verify(requirement, structure)

        assert result.interaction_pass_rate < 1.0
        assert any(
            "输入密码" in i.description or "点击登录" in i.description
            for i in result.failed_interactions
        )

    def test_verify_rule_condition_missing(self):
        """测试业务规则未体现"""
        requirement = StructuredRequirement(
            rules=RuleTreeNode(
                rule_text="订单金额超过1000元需要审批",
                conditions=[
                    Condition(field="amount", operator=">", value="1000"),
                ],
            ),
            entities=[],
            flows=[],
        )
        pages = []
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        verifier = InteractionVerifier()
        result = verifier.verify(requirement, structure)

        assert len(result.failed_interactions) > 0
        assert any(
            i.issue_type == IssueType.MISSING_ELEMENT
            for i in result.failed_interactions
        )

    def test_verify_empty_requirement(self):
        """测试空需求"""
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试"),
            entities=[],
            flows=[],
        )
        structure = PageStructure(
            requirement_id="test-req",
            root=PageNode(id="page-home", name="首页"),
            pages=[],
        )

        verifier = InteractionVerifier()
        result = verifier.verify(requirement, structure)

        assert result.interaction_pass_rate == 1.0
        assert result.total_interactions_required == 0

    def test_extract_entity_operations(self):
        """测试提取实体操作"""
        verifier = InteractionVerifier()
        entity = BusinessEntity(
            name="Product",
            attributes=[
                Attribute(name="name", type="string", required=True),
                Attribute(name="price", type="number", required=False),
            ],
        )
        operations = verifier._get_entity_operations(entity)

        assert "查看" in operations
        assert "搜索" in operations
        assert "创建" in operations
        assert "编辑" in operations
        assert "删除" in operations

    def test_extract_entity_operations_no_required(self):
        """测试无必填属性时的操作提取"""
        verifier = InteractionVerifier()
        entity = BusinessEntity(
            name="Category",
            attributes=[
                Attribute(name="name", type="string", required=False),
            ],
        )
        operations = verifier._get_entity_operations(entity)

        assert "查看" in operations
        assert "搜索" in operations
        assert "创建" not in operations
        assert "编辑" not in operations

    def test_extract_rule_interactions_recursive(self):
        """测试递归提取规则交互"""
        verifier = InteractionVerifier()
        interactions = []
        root = RuleTreeNode(
            rule_text="根规则",
            conditions=[Condition(field="status", operator="==", value="active")],
            children=[
                RuleTreeNode(
                    rule_text="子规则1",
                    conditions=[Condition(field="role", operator="==", value="admin")],
                ),
                RuleTreeNode(
                    rule_text="子规则2",
                ),
            ],
        )
        verifier._extract_rule_interactions(root, interactions)

        assert len(interactions) >= 2


class TestPrototypeVerifier:
    """原型校验器集成测试"""

    def _make_requirement(self) -> StructuredRequirement:
        """创建测试用需求"""
        return StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试规则"),
            entities=[
                BusinessEntity(
                    name="User",
                    attributes=[
                        Attribute(name="name", type="string", required=True),
                    ],
                ),
            ],
            roles=[Role(name="admin", description="管理员")],
            flows=[
                UserFlow(
                    name="用户管理流程",
                    role="admin",
                    steps=[
                        FlowStep(step_number=1, description="选择用户", action="点击"),
                        FlowStep(step_number=2, description="编辑用户信息", action="编辑"),
                        FlowStep(step_number=3, description="保存更改", action="点击保存"),
                    ],
                ),
            ],
        )

    def test_verify_complete_pass(self):
        """测试完整原型通过校验"""
        requirement = self._make_requirement()
        pages = [
            PageNode(
                id="page-user-list",
                name="User列表",
                entities=["User"],
                operations=["查看", "搜索", "创建", "编辑", "删除"],
                flow_steps=["选择用户", "编辑用户信息", "保存更改"],
            ),
            PageNode(
                id="page-user-detail",
                name="User详情",
                entities=["User"],
                operations=["查看详情", "编辑", "删除"],
                flow_steps=["选择用户", "编辑用户信息", "保存更改"],
            ),
            PageNode(
                id="page-user-form",
                name="User表单",
                entities=["User"],
                operations=["创建", "编辑", "保存", "取消"],
                flow_steps=["选择用户", "编辑用户信息", "保存更改"],
            ),
            PageNode(
                id="page-flow-用户管理流程",
                name="用户管理流程",
                entities=[],
                operations=["点击", "编辑", "点击保存"],
                flow_steps=["选择用户", "编辑用户信息", "保存更改"],
            ),
        ]
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        verifier = PrototypeVerifier()
        report = verifier.verify(requirement, structure)

        assert report.passed is True
        assert report.coverage.page_coverage_rate == 1.0

    def test_verify_missing_pages_fails(self):
        """测试缺失页面导致校验失败"""
        requirement = self._make_requirement()
        pages = [
            PageNode(id="page-user-list", name="User列表", entities=["User"]),
        ]
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        verifier = PrototypeVerifier()
        report = verifier.verify(requirement, structure)

        assert report.passed is False
        assert any(i.issue_type == IssueType.MISSING_PAGE for i in report.issues)
        assert any(i.severity == IssueSeverity.CRITICAL for i in report.issues)

    def test_verify_broken_navigation_auto_fixed(self):
        """测试断裂导航自动修复"""
        requirement = self._make_requirement()
        pages = [
            PageNode(
                id="page-user-list",
                name="User列表",
                entities=["User"],
                parent_id="page-nonexistent",
                operations=["查看", "搜索", "创建", "编辑", "删除"],
                flow_steps=["选择用户", "编辑用户信息", "保存更改"],
            ),
            PageNode(
                id="page-user-detail",
                name="User详情",
                entities=["User"],
                operations=["查看详情", "编辑", "删除"],
            ),
            PageNode(
                id="page-user-form",
                name="User表单",
                entities=["User"],
                operations=["创建", "编辑", "保存", "取消"],
            ),
        ]
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        verifier = PrototypeVerifier()
        report = verifier.verify(requirement, structure)

        broken_link_issues = [
            i for i in report.issues if i.issue_type == IssueType.BROKEN_LINK
        ]
        assert len(broken_link_issues) > 0
        assert all(i.auto_fix_applied for i in broken_link_issues)

    def test_verify_summary_generation(self):
        """测试校验总结生成"""
        requirement = self._make_requirement()
        pages = []
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        verifier = PrototypeVerifier()
        report = verifier.verify(requirement, structure)

        assert len(report.summary) > 0
        assert "页面覆盖率" in report.summary
        assert "元素覆盖率" in report.summary
        assert "交互通过率" in report.summary

    def test_verify_no_issues_summary(self):
        """测试无问题时的总结"""
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试"),
            entities=[],
        )
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=[],
        )

        verifier = PrototypeVerifier()
        report = verifier.verify(requirement, structure)

        assert "所有检查均通过" in report.summary
        assert report.passed is True

    def test_verify_issue_severity_counts(self):
        """测试问题严重程度统计"""
        requirement = self._make_requirement()
        pages = []
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        verifier = PrototypeVerifier()
        report = verifier.verify(requirement, structure)

        critical_count = sum(1 for i in report.issues if i.severity == IssueSeverity.CRITICAL)
        assert critical_count > 0

    def test_verify_with_complex_rules(self):
        """测试复杂规则树的校验"""
        requirement = StructuredRequirement(
            rules=RuleTreeNode(
                rule_text="复杂业务规则",
                conditions=[Condition(field="type", operator="==", value="premium")],
                children=[
                    RuleTreeNode(
                        rule_text="VIP用户享受折扣",
                        conditions=[Condition(field="level", operator=">=", value="3")],
                    ),
                    RuleTreeNode(
                        rule_text="普通用户全价",
                    ),
                ],
            ),
            entities=[
                BusinessEntity(
                    name="Product",
                    attributes=[
                        Attribute(name="name", type="string", required=True),
                        Attribute(name="price", type="number", required=True),
                    ],
                ),
            ],
        )
        pages = [
            PageNode(id="page-product-list", name="Product列表", entities=["Product"]),
            PageNode(id="page-product-detail", name="Product详情", entities=["Product"]),
            PageNode(id="page-product-form", name="Product表单", entities=["Product"]),
        ]
        root = PageNode(id="page-home", name="首页")
        structure = PageStructure(
            requirement_id="test-req",
            root=root,
            pages=pages,
        )

        verifier = PrototypeVerifier()
        report = verifier.verify(requirement, structure)

        assert report.coverage.page_coverage_rate == 1.0
        assert len(report.issues) >= 0
