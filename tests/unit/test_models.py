"""数据模型测试"""

from datetime import datetime

import pytest

from pm_workstation.models.core import (
    Action,
    Attribute,
    Branch,
    BusinessEntity,
    Condition,
    EdgeCase,
    FlowStep,
    Question,
    Relationship,
    Role,
    RuleTreeNode,
    StructuredRequirement,
    UserFlow,
    VerificationReport,
    WorkflowRun,
    WorkflowStatus,
)


class TestWorkflowStatus:
    """WorkflowStatus枚举测试"""
    
    def test_all_statuses_exist(self):
        """测试所有状态枚举存在"""
        assert WorkflowStatus.INIT.value == "init"
        assert WorkflowStatus.PARSING.value == "parsing"
        assert WorkflowStatus.PARSED.value == "parsed"
        assert WorkflowStatus.GENERATING.value == "generating"
        assert WorkflowStatus.GENERATED.value == "generated"
        assert WorkflowStatus.VERIFYING.value == "verifying"
        assert WorkflowStatus.VERIFIED.value == "verified"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.WAITING_USER_INPUT.value == "waiting_user_input"


class TestAttribute:
    """Attribute模型测试"""
    
    def test_create_attribute(self):
        """测试创建属性"""
        attr = Attribute(name="username", type="string", description="用户名", required=True)
        
        assert attr.name == "username"
        assert attr.type == "string"
        assert attr.description == "用户名"
        assert attr.required is True
    
    def test_attribute_defaults(self):
        """测试属性默认值"""
        attr = Attribute(name="email", type="string")
        
        assert attr.description == ""
        assert attr.required is False


class TestRelationship:
    """Relationship模型测试"""
    
    def test_create_relationship(self):
        """测试创建关联关系"""
        rel = Relationship(
            target_entity="Order",
            relationship_type="one-to-many",
            description="一个用户可以有多个订单"
        )
        
        assert rel.target_entity == "Order"
        assert rel.relationship_type == "one-to-many"
        assert rel.description == "一个用户可以有多个订单"


class TestBusinessEntity:
    """BusinessEntity模型测试"""
    
    def test_create_entity(self):
        """测试创建业务实体"""
        entity = BusinessEntity(
            name="User",
            description="用户实体",
            attributes=[
                Attribute(name="username", type="string", required=True),
                Attribute(name="email", type="string", required=True),
            ],
            relationships=[
                Relationship(target_entity="Order", relationship_type="one-to-many")
            ]
        )
        
        assert entity.name == "User"
        assert len(entity.attributes) == 2
        assert len(entity.relationships) == 1
    
    def test_entity_defaults(self):
        """测试业务实体默认值"""
        entity = BusinessEntity(name="Product")
        
        assert entity.description == ""
        assert entity.attributes == []
        assert entity.relationships == []


class TestCondition:
    """Condition模型测试"""
    
    def test_create_condition(self):
        """测试创建条件"""
        condition = Condition(field="age", operator=">=", value="18")
        
        assert condition.field == "age"
        assert condition.operator == ">="
        assert condition.value == "18"


class TestAction:
    """Action模型测试"""
    
    def test_create_action(self):
        """测试创建动作"""
        action = Action(
            action_type="send_email",
            description="发送验证邮件",
            parameters={"to": "user@example.com", "subject": "验证"}
        )
        
        assert action.action_type == "send_email"
        assert action.description == "发送验证邮件"
        assert action.parameters["to"] == "user@example.com"
    
    def test_action_defaults(self):
        """测试动作默认值"""
        action = Action(action_type="log")
        
        assert action.description == ""
        assert action.parameters == {}


class TestRuleTreeNode:
    """RuleTreeNode模型测试"""
    
    def test_create_rule_node(self):
        """测试创建规则节点"""
        node = RuleTreeNode(
            rule_text="用户必须年满18岁",
            conditions=[Condition(field="age", operator=">=", value="18")],
            actions=[Action(action_type="allow", description="允许注册")],
            depth=1
        )
        
        assert node.rule_text == "用户必须年满18岁"
        assert len(node.conditions) == 1
        assert len(node.actions) == 1
        assert node.depth == 1
    
    def test_nested_rules(self):
        """测试嵌套规则"""
        child_node = RuleTreeNode(
            rule_text="如果是VIP用户",
            conditions=[Condition(field="user_type", operator="==", value="vip")],
            depth=2
        )
        
        parent_node = RuleTreeNode(
            rule_text="用户登录验证",
            children=[child_node],
            depth=1
        )
        
        assert len(parent_node.children) == 1
        assert parent_node.children[0].depth == 2
    
    def test_rule_defaults(self):
        """测试规则节点默认值"""
        node = RuleTreeNode(rule_text="测试规则")
        
        assert node.conditions == []
        assert node.actions == []
        assert node.children == []
        assert node.depth == 0


class TestFlowStep:
    """FlowStep模型测试"""
    
    def test_create_flow_step(self):
        """测试创建流程步骤"""
        step = FlowStep(
            step_number=1,
            description="输入用户名和密码",
            action="填写表单",
            expected_result="表单验证通过"
        )
        
        assert step.step_number == 1
        assert step.description == "输入用户名和密码"
        assert step.action == "填写表单"
        assert step.expected_result == "表单验证通过"


class TestBranch:
    """Branch模型测试"""
    
    def test_create_branch(self):
        """测试创建分支"""
        branch = Branch(
            name="密码错误",
            branch_type="exception",
            condition="密码验证失败",
            steps=[
                FlowStep(step_number=1, description="显示错误提示")
            ]
        )
        
        assert branch.name == "密码错误"
        assert branch.branch_type == "exception"
        assert len(branch.steps) == 1
    
    def test_branch_defaults(self):
        """测试分支默认值"""
        branch = Branch(name="正常流程", branch_type="normal")
        
        assert branch.condition == ""
        assert branch.steps == []


class TestEdgeCase:
    """EdgeCase模型测试"""
    
    def test_create_edge_case(self):
        """测试创建边界场景"""
        edge_case = EdgeCase(
            description="输入超长用户名",
            condition="用户名长度 > 100",
            expected_behavior="截断或提示超限"
        )
        
        assert edge_case.description == "输入超长用户名"
        assert edge_case.condition == "用户名长度 > 100"
        assert edge_case.expected_behavior == "截断或提示超限"


class TestRole:
    """Role模型测试"""
    
    def test_create_role(self):
        """测试创建角色"""
        role = Role(
            name="admin",
            description="系统管理员",
            permissions=["create", "read", "update", "delete"]
        )
        
        assert role.name == "admin"
        assert len(role.permissions) == 4
    
    def test_role_defaults(self):
        """测试角色默认值"""
        role = Role(name="user")
        
        assert role.description == ""
        assert role.permissions == []


class TestQuestion:
    """Question模型测试"""
    
    def test_create_question(self):
        """测试创建问题"""
        question = Question(
            question="是否需要支持批量操作？",
            context="在删除功能中",
            options=["是", "否"]
        )
        
        assert question.question == "是否需要支持批量操作？"
        assert len(question.options) == 2
    
    def test_question_defaults(self):
        """测试问题默认值"""
        question = Question(question="确认继续？")
        
        assert question.context == ""
        assert question.options == []


class TestUserFlow:
    """UserFlow模型测试"""
    
    def test_create_user_flow(self):
        """测试创建用户流程"""
        flow = UserFlow(
            name="用户登录",
            role="user",
            steps=[
                FlowStep(step_number=1, description="输入用户名和密码"),
                FlowStep(step_number=2, description="点击登录按钮"),
            ],
            branches=[
                Branch(name="登录成功", branch_type="normal"),
                Branch(name="密码错误", branch_type="exception"),
            ],
            entry_point="登录页面",
            exit_points=["首页", "错误页面"]
        )
        
        assert flow.name == "用户登录"
        assert len(flow.steps) == 2
        assert len(flow.branches) == 2
        assert flow.entry_point == "登录页面"
        assert len(flow.exit_points) == 2


class TestStructuredRequirement:
    """StructuredRequirement模型测试"""
    
    def test_create_structured_requirement(self):
        """测试创建结构化需求"""
        requirement = StructuredRequirement(
            entities=[BusinessEntity(name="User")],
            roles=[Role(name="admin")],
            rules=RuleTreeNode(rule_text="业务规则"),
            flows=[UserFlow(name="登录流程", role="user")],
            branches=[Branch(name="异常处理", branch_type="exception")],
            edge_cases=[EdgeCase(description="边界场景", condition="条件", expected_behavior="行为")],
            clarifications=[Question(question="需要澄清的问题")],
            reasoning_trace="推理路径记录"
        )
        
        assert len(requirement.entities) == 1
        assert len(requirement.roles) == 1
        assert requirement.rules.rule_text == "业务规则"
        assert len(requirement.flows) == 1
        assert requirement.reasoning_trace == "推理路径记录"
    
    def test_serialization(self):
        """测试序列化"""
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试规则")
        )
        
        json_data = requirement.model_dump_json()
        assert json_data is not None
        assert "测试规则" in json_data


class TestVerificationReport:
    """VerificationReport模型测试"""
    
    def test_create_report(self):
        """测试创建校验报告"""
        report = VerificationReport(
            report_id="report-001",
            prototype_issues=[{"issue": "页面缺失"}],
            document_issues=[{"issue": "格式错误"}],
            consistency_issues=[{"issue": "原型与文档不一致"}],
            auto_fixed_issues=[{"issue": "已自动修复"}],
            manual_review_required=[{"issue": "需人工审查"}]
        )
        
        assert report.report_id == "report-001"
        assert len(report.prototype_issues) == 1
        assert len(report.manual_review_required) == 1
    
    def test_report_defaults(self):
        """测试报告默认值"""
        report = VerificationReport(report_id="report-002")
        
        assert isinstance(report.created_at, datetime)
        assert report.prototype_issues == []
        assert report.document_issues == []


class TestWorkflowRun:
    """WorkflowRun模型测试"""
    
    def test_create_workflow_run(self):
        """测试创建工作流运行记录"""
        run = WorkflowRun(
            id="run-001",
            user_id="user-123",
            requirement_text="实现用户登录功能"
        )
        
        assert run.id == "run-001"
        assert run.user_id == "user-123"
        assert run.requirement_text == "实现用户登录功能"
        assert run.status == WorkflowStatus.INIT
        assert isinstance(run.created_at, datetime)
    
    def test_update_status(self):
        """测试更新状态"""
        run = WorkflowRun(
            id="run-001",
            user_id="user-123",
            requirement_text="测试需求"
        )
        
        initial_time = run.updated_at
        run.update_status(WorkflowStatus.PARSING)
        
        assert run.status == WorkflowStatus.PARSING
        assert run.updated_at > initial_time
    
    def test_workflow_with_deliverables(self):
        """测试包含交付物的工作流"""
        run = WorkflowRun(
            id="run-001",
            user_id="user-123",
            requirement_text="测试需求",
            structured_requirement=StructuredRequirement(
                rules=RuleTreeNode(rule_text="业务规则")
            ),
            prototype_url="http://example.com/prototype",
            prd_document_url="http://example.com/prd",
            verification_report=VerificationReport(report_id="report-001")
        )
        
        assert run.structured_requirement is not None
        assert run.prototype_url == "http://example.com/prototype"
        assert run.verification_report.report_id == "report-001"
    
    def test_serialization(self):
        """测试序列化"""
        run = WorkflowRun(
            id="run-001",
            user_id="user-123",
            requirement_text="测试需求"
        )
        
        json_data = run.model_dump_json()
        assert json_data is not None
        assert "run-001" in json_data
